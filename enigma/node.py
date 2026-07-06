"""
P2P Node: Flask HTTP server (REST + JSON-RPC) with block-explorer web UI
          and disk persistence.
"""

import json
import os
import time

import requests
from flask import Flask, request, jsonify, render_template, redirect, url_for

from .block import Blockchain, Block
from .transaction import Transaction
from .wallet import Wallet, address_from_public_key_hex
from .storage import save_chain, load_chain
from .rpc import rpc_bp, init_rpc
from .compute import compute_market_snapshot

_HERE = os.path.dirname(os.path.abspath(__file__))
_TEMPLATE_DIR = os.path.join(_HERE, "..", "templates")


class Node:
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 5000,
        data_dir: str = "data",
    ):
        self.host = host
        self.port = port
        self.data_dir = data_dir
        self._chain_file = os.path.join(data_dir, "chain.json")
        self._wallet_file = os.path.join(data_dir, "node_wallet.json")

        os.makedirs(data_dir, exist_ok=True)

        self.blockchain = load_chain(self._chain_file) or Blockchain()
        self.wallet = self._load_or_create_wallet()
        self.peers: set[str] = set()

        self.app = Flask(__name__, template_folder=_TEMPLATE_DIR)
        self._register_routes()

        init_rpc(self.blockchain, self.wallet, lambda: len(self.peers) + 1)
        self.app.register_blueprint(rpc_bp)

    # ------------------------------------------------------------------
    # Wallet persistence
    # ------------------------------------------------------------------

    def _load_or_create_wallet(self) -> Wallet:
        if os.path.exists(self._wallet_file):
            return Wallet.load_from_file(self._wallet_file)
        w = Wallet.new_with_mnemonic()
        w.save_to_file(self._wallet_file)
        return w

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _save(self):
        save_chain(self.blockchain, self._chain_file)

    def _chain_stats(self) -> dict:
        bc = self.blockchain
        recent_blocks = []
        for b in reversed(bc.chain[-20:]):
            recent_blocks.append({
                "index": b.index,
                "hash": b.hash,
                "tx_count": len(b.transactions),
                "age": _human_age(b.timestamp),
            })

        recent_txs = []
        for b in reversed(bc.chain[-5:]):
            for tx in b.transactions:
                sender_addr = tx.sender
                if sender_addr not in ("COINBASE",):
                    try:
                        sender_addr = address_from_public_key_hex(sender_addr)
                    except Exception:
                        pass
                recent_txs.append({
                    "tx_id": tx.tx_id(),
                    "amount": tx.amount,
                    "sender": tx.sender,
                    "sender_short": (sender_addr[:12] + "…") if len(sender_addr) > 12 else sender_addr,
                })
        return {
            "height": bc.height,
            "total_mined": bc.total_mined,
            "difficulty": bc.last_block.difficulty,
            "pending_txs": len(bc.pending_transactions),
            "recent_blocks": recent_blocks,
            "recent_txs": recent_txs[:20],
            "compute": compute_market_snapshot(bc, len(self.peers) + 1).to_dict(),
        }

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------

    def _register_routes(self):
        app = self.app

        # ---- Web UI ----

        @app.route("/")
        def index():
            return render_template("index.html", stats=self._chain_stats())

        @app.route("/block/<block_hash>")
        def block_detail(block_hash):
            block = self.blockchain.get_block_by_hash(block_hash)
            if block is None:
                return "Block not found", 404
            return render_template("block.html", block=block)

        @app.route("/tx/<tx_id>")
        def tx_detail(tx_id):
            tx, block = self.blockchain.get_transaction(tx_id)
            if tx is None:
                return "Transaction not found", 404
            sender_addr = tx.sender
            if sender_addr not in ("COINBASE",):
                try:
                    sender_addr = address_from_public_key_hex(sender_addr)
                except Exception:
                    pass
            return render_template(
                "tx.html",
                tx_id=tx_id,
                block_height=block.index,
                block_hash=block.hash,
                confirmations=self.blockchain.height - block.index + 1,
                timestamp=tx.timestamp,
                sender=sender_addr,
                recipient=tx.recipient,
                amount=tx.amount,
                fee=tx.fee,
            )

        @app.route("/address/<address>")
        def address_detail(address):
            balance = self.blockchain.get_balance(address)
            txs = self.blockchain.get_address_transactions(address)
            return render_template("address.html", address=address, balance=balance, txs=txs)

        @app.route("/wallet")
        def wallet_page():
            # Content-negotiation: browsers get HTML, API clients get JSON
            if request.accept_mimetypes.best_match(["text/html", "application/json"]) == "application/json":
                return jsonify(self.wallet.to_dict()), 200
            balance = self.blockchain.get_balance(self.wallet.address)
            market = compute_market_snapshot(self.blockchain, len(self.peers) + 1)
            return render_template("wallet.html", wallet=self.wallet, balance=balance,
                                   market=market, flash_msg=None, flash_type=None)

        @app.route("/send", methods=["POST"])
        def send():
            recipient = request.form.get("recipient", "").strip()
            try:
                amount = float(request.form.get("amount", 0))
                fee = float(request.form.get("fee", 0))
            except ValueError:
                amount, fee = 0, 0
            tx = Transaction.create_and_sign(self.wallet, recipient, amount, fee)
            ok = self.blockchain.add_transaction(tx)
            self._save()
            self._broadcast_transaction(tx)
            balance = self.blockchain.get_balance(self.wallet.address)
            market = compute_market_snapshot(self.blockchain, len(self.peers) + 1)
            msg = f"Transaction {tx.tx_id()[:16]}… submitted." if ok else "Transaction rejected (insufficient balance or invalid)."
            return render_template("wallet.html", wallet=self.wallet, balance=balance,
                                   market=market, flash_msg=msg, flash_type="success" if ok else "danger")

        @app.route("/search")
        def search():
            q = request.args.get("q", "").strip()
            if len(q) == 64:
                block = self.blockchain.get_block_by_hash(q)
                if block:
                    return redirect(url_for("block_detail", block_hash=q))
                tx, _ = self.blockchain.get_transaction(q)
                if tx:
                    return redirect(url_for("tx_detail", tx_id=q))
            if q:
                return redirect(url_for("address_detail", address=q))
            return redirect(url_for("index"))

        @app.route("/docs")
        def docs():
            return render_template("docs.html")

        @app.route("/compute", methods=["GET"])
        def compute_market():
            snapshot = compute_market_snapshot(self.blockchain, len(self.peers) + 1)
            if request.accept_mimetypes.best_match(["text/html", "application/json"]) == "application/json":
                return jsonify(snapshot.to_dict()), 200
            return render_template("compute.html", market=snapshot)

        @app.route("/compute/stats", methods=["GET"])
        def compute_stats():
            snapshot = compute_market_snapshot(self.blockchain, len(self.peers) + 1)
            return jsonify(snapshot.to_dict()), 200

        # ---- REST API ----

        @app.route("/chain", methods=["GET"])
        def get_chain():
            return jsonify(self.blockchain.to_dict()), 200

        @app.route("/pending", methods=["GET"])
        def get_pending():
            return jsonify([tx.to_dict() for tx in self.blockchain.pending_transactions]), 200

        @app.route("/transaction/new", methods=["POST"])
        def new_transaction():
            data = request.get_json(force=True)
            try:
                tx = Transaction.from_dict(data)
            except (KeyError, ValueError) as exc:
                return jsonify({"error": str(exc)}), 400
            if self.blockchain.add_transaction(tx):
                self._save()
                self._broadcast_transaction(tx)
                return jsonify({"tx_id": tx.tx_id()}), 201
            return jsonify({"error": "invalid or insufficient balance"}), 400

        @app.route("/mine", methods=["POST"])
        def mine():
            block = self.blockchain.mine_pending_transactions(self.wallet.address)
            self._save()
            self._broadcast_block(block)
            return jsonify(block.to_dict()), 200

        @app.route("/block/new", methods=["POST"])
        def receive_block():
            data = request.get_json(force=True)
            block = Block.from_dict(data)
            last = self.blockchain.last_block
            if (
                block.index == last.index + 1
                and block.previous_hash == last.hash
                and block.is_valid()
            ):
                self.blockchain.chain.append(block)
                self._save()
                return jsonify({"status": "accepted"}), 200
            self._resolve_conflicts()
            return jsonify({"status": "replaced or rejected"}), 200

        @app.route("/peers", methods=["GET"])
        def get_peers():
            return jsonify(list(self.peers)), 200

        @app.route("/peers/register", methods=["POST"])
        def register_peer():
            data = request.get_json(force=True)
            peer = data.get("peer")
            if peer:
                self.peers.add(peer)
                return jsonify({"status": "registered"}), 200
            return jsonify({"error": "missing peer"}), 400

        @app.route("/balance/<identifier>", methods=["GET"])
        def balance(identifier):
            bal = self.blockchain.get_balance(identifier)
            return jsonify({"identifier": identifier, "balance": bal}), 200

    # ------------------------------------------------------------------
    # P2P
    # ------------------------------------------------------------------

    def _broadcast_transaction(self, tx: Transaction):
        for peer in list(self.peers):
            try:
                requests.post(f"http://{peer}/transaction/new", json=tx.to_dict(), timeout=3)
            except requests.RequestException:
                pass

    def _broadcast_block(self, block: Block):
        for peer in list(self.peers):
            try:
                requests.post(f"http://{peer}/block/new", json=block.to_dict(), timeout=5)
            except requests.RequestException:
                pass

    def connect_to_peer(self, peer: str):
        self.peers.add(peer)
        try:
            requests.post(
                f"http://{peer}/peers/register",
                json={"peer": f"{self.host}:{self.port}"},
                timeout=3,
            )
        except requests.RequestException:
            pass
        self._resolve_conflicts()

    def _resolve_conflicts(self):
        best_chain = self.blockchain.chain
        best_len = len(best_chain)
        for peer in list(self.peers):
            try:
                resp = requests.get(f"http://{peer}/chain", timeout=5)
                candidate = Blockchain.from_dict(resp.json())
                if len(candidate.chain) > best_len and candidate.is_valid_chain():
                    best_len = len(candidate.chain)
                    best_chain = candidate.chain
            except Exception:
                pass
        if best_chain is not self.blockchain.chain:
            self.blockchain.chain = best_chain
            self._save()

    # ------------------------------------------------------------------
    # Start
    # ------------------------------------------------------------------

    def run(self):
        self.app.run(host=self.host, port=self.port)


def _human_age(timestamp: float) -> str:
    diff = time.time() - timestamp
    if diff < 60:
        return f"{int(diff)}s ago"
    if diff < 3600:
        return f"{int(diff/60)}m ago"
    return f"{int(diff/3600)}h ago"
