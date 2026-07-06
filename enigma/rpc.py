"""
JSON-RPC 2.0 endpoint — Bitcoin-compatible subset.

Supported methods:
    getblockchaininfo
    getblockcount
    getblockhash          (height)
    getblock              (hash)
    gettransaction        (txid)
    getbalance            (address)
    sendrawtransaction    (tx_json_b64)
    getmininginfo
    getcomputeinfo
    getnewaddress
"""

import base64
import json

from flask import Blueprint, request, jsonify

from .block import Blockchain
from .transaction import Transaction
from .wallet import Wallet
from .compute import compute_market_snapshot

rpc_bp = Blueprint("rpc", __name__)

_blockchain_ref: Blockchain = None   # set by node at startup
_node_wallet_ref: Wallet = None
_peer_count_fn = None


def init_rpc(blockchain: Blockchain, wallet: Wallet, peer_count_fn=None) -> None:
    global _blockchain_ref, _node_wallet_ref, _peer_count_fn
    _blockchain_ref = blockchain
    _node_wallet_ref = wallet
    _peer_count_fn = peer_count_fn or (lambda: 1)


def _ok(result, req_id):
    return {"jsonrpc": "2.0", "result": result, "id": req_id}


def _err(code: int, message: str, req_id):
    return {"jsonrpc": "2.0", "error": {"code": code, "message": message}, "id": req_id}


@rpc_bp.route("/rpc", methods=["POST"])
def rpc():
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify(_err(-32700, "Parse error", None)), 200

    req_id = data.get("id")
    method = data.get("method", "")
    params = data.get("params", [])

    bc = _blockchain_ref
    wallet = _node_wallet_ref

    try:
        if method == "getblockchaininfo":
            market = compute_market_snapshot(bc, _peer_count_fn())
            result = {
                "chain": "enigma",
                "blocks": bc.height,
                "difficulty": bc.last_block.difficulty,
                "total_supply": bc.total_mined,
                "max_supply": 21_000_000,
                "chain_valid": bc.is_valid_chain(),
                "compute_market": market.to_dict(),
            }

        elif method == "getblockcount":
            result = bc.height

        elif method == "getblockhash":
            height = int(params[0])
            block = bc.get_block_by_height(height)
            if block is None:
                return jsonify(_err(-5, "Block height out of range", req_id)), 200
            result = block.hash

        elif method == "getblock":
            block = bc.get_block_by_hash(params[0])
            if block is None:
                return jsonify(_err(-5, "Block not found", req_id)), 200
            result = block.to_dict()

        elif method == "gettransaction":
            tx, block = bc.get_transaction(params[0])
            if tx is None:
                return jsonify(_err(-5, "Transaction not found", req_id)), 200
            result = {**tx.to_dict(), "block_hash": block.hash, "confirmations": bc.height - block.index + 1}

        elif method == "getbalance":
            result = bc.get_balance(params[0])

        elif method == "sendrawtransaction":
            # params[0] = base64-encoded JSON transaction dict
            raw = base64.b64decode(params[0].encode()).decode()
            tx_dict = json.loads(raw)
            tx = Transaction.from_dict(tx_dict)
            if not bc.add_transaction(tx):
                return jsonify(_err(-26, "Transaction rejected", req_id)), 200
            result = tx.tx_id()

        elif method == "getmininginfo":
            market = compute_market_snapshot(bc, _peer_count_fn())
            result = {
                "blocks": bc.height,
                "difficulty": bc.last_block.difficulty,
                "pooledtx": len(bc.pending_transactions),
                "reward": bc.last_block.transactions[0].amount if bc.chain and bc.chain[-1].transactions else 0,
                "compute_supply": market.supply_score,
                "compute_demand": market.demand_score,
                "compute_ratio": market.ratio,
                "suggested_fee": market.suggested_fee,
            }

        elif method == "getcomputeinfo":
            result = compute_market_snapshot(bc, _peer_count_fn()).to_dict()

        elif method == "getnewaddress":
            new_wallet = Wallet.new_with_mnemonic()
            result = {
                "address": new_wallet.address,
                "mnemonic": new_wallet.mnemonic,
                "public_key": new_wallet.public_key_hex,
            }

        else:
            return jsonify(_err(-32601, f"Method not found: {method}", req_id)), 200

        return jsonify(_ok(result, req_id)), 200

    except (IndexError, TypeError, ValueError) as exc:
        return jsonify(_err(-32602, f"Invalid params: {exc}", req_id)), 200
    except Exception as exc:
        return jsonify(_err(-32603, f"Internal error: {exc}", req_id)), 200
