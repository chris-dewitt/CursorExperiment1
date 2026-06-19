"""
PyCoin node entry point.

Usage:
    python main.py [--host HOST] [--port PORT] [--peer HOST:PORT] [--data-dir DIR]

Examples:
    # Node 1 on default port 5000
    python main.py

    # Node 2 connecting to node 1
    python main.py --port 5001 --peer localhost:5000 --data-dir data2
"""

import argparse
from pycoin.node import Node


def main():
    parser = argparse.ArgumentParser(description="PyCoin node")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--peer", action="append", default=[], metavar="HOST:PORT",
                        help="Peer to connect to on startup (repeatable)")
    parser.add_argument("--data-dir", default="data", metavar="DIR",
                        help="Directory for blockchain and wallet persistence")
    args = parser.parse_args()

    node = Node(host=args.host, port=args.port, data_dir=args.data_dir)
    print(f"[PyCoin] Node starting on port {args.port}")
    print(f"[PyCoin] Wallet address : {node.wallet.address}")
    print(f"[PyCoin] Data directory : {args.data_dir}")
    print(f"[PyCoin] Block explorer : http://localhost:{args.port}/")

    for peer in args.peer:
        print(f"[PyCoin] Connecting to peer {peer}")
        node.connect_to_peer(peer)

    node.run()


if __name__ == "__main__":
    main()
