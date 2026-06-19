"""
P2P Node: Flask HTTP server that peers can sync from and broadcast to.
"""

import json
import threading

import requests
from flask import Flask, request, jsonify

from .block import Blockchain, Block
from .transaction import Transaction
from .wallet import Wallet


class Node:
    def __init__(self, host: str = "0.0.0.0", port: int = 5000):
        self.host = host
        self.port = port
        self.blockchain = Blockchain()
        self.peers: set[str] = set()      # "host:port" strings
        self.wallet = Wallet()
        self.app = self._build_app()

    # ------------------------------------------------------------------
    # Flask routes
    # ------------------------------------------------------------------

    def _build_app(self) -> Flask:
        app = Flask(__name__)

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
                self._broadcast_transaction(tx)
                return jsonify({"tx_id": tx.tx_id()}), 201
            return jsonify({"error": "invalid transaction"}), 400

        @app.route("/mine", methods=["POST"])
        def mine():
            block = self.blockchain.mine_pending_transactions(self.wallet.address)
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
                return jsonify({"status": "accepted"}), 200
            # Block doesn't fit — try to resolve conflicts
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

        @app.route("/wallet", methods=["GET"])
        def wallet_info():
            return jsonify(self.wallet.to_dict()), 200

        return app

    # ------------------------------------------------------------------
    # P2P helpers
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
        """Register ourselves with peer and sync their chain."""
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
        """Longest valid chain wins."""
        best_chain = self.blockchain.chain
        best_len = len(best_chain)

        for peer in list(self.peers):
            try:
                resp = requests.get(f"http://{peer}/chain", timeout=5)
                data = resp.json()
                candidate = Blockchain.from_dict(data)
                if len(candidate.chain) > best_len and candidate.is_valid_chain():
                    best_len = len(candidate.chain)
                    best_chain = candidate.chain
            except (requests.RequestException, Exception):
                pass

        self.blockchain.chain = best_chain

    # ------------------------------------------------------------------
    # Startup
    # ------------------------------------------------------------------

    def run(self):
        self.app.run(host=self.host, port=self.port)
