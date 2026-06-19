"""
PyCoin node entry point.

Usage:
    python main.py [--port PORT] [--peer HOST:PORT]

Examples:
    # Start node on default port 5000
    python main.py

    # Start a second node on port 5001 and connect to the first
    python main.py --port 5001 --peer localhost:5000
"""

import argparse
from pycoin.node import Node


def main():
    parser = argparse.ArgumentParser(description="PyCoin node")
    parser.add_argument("--host", default="0.0.0.0", help="Bind address")
    parser.add_argument("--port", type=int, default=5000, help="Listen port")
    parser.add_argument("--peer", action="append", default=[], metavar="HOST:PORT",
                        help="Peer to connect to on startup (repeatable)")
    args = parser.parse_args()

    node = Node(host=args.host, port=args.port)
    print(f"[PyCoin] Node starting on port {args.port}")
    print(f"[PyCoin] Wallet address: {node.wallet.address}")

    for peer in args.peer:
        print(f"[PyCoin] Connecting to peer {peer}")
        node.connect_to_peer(peer)

    node.run()


if __name__ == "__main__":
    main()
