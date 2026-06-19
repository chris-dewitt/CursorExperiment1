#!/usr/bin/env python3
"""
PyCoin Wallet CLI

Commands:
  new                       Generate a new wallet (prints mnemonic — store it safely)
  recover <mnemonic>        Restore wallet from 12-word BIP39 mnemonic
  info <wallet_file>        Show address and public key
  balance <address>         Check balance on a running node
  send <wallet_file>        Sign and broadcast a transaction
  mine                      Ask the node to mine the next block

Examples:
  python wallet_cli.py new --save alice.wallet
  python wallet_cli.py recover "word1 word2 ... word12" --save alice.wallet
  python wallet_cli.py info alice.wallet
  python wallet_cli.py balance 1A2B3C... --node localhost:5000
  python wallet_cli.py send alice.wallet --to 1B2C3D... --amount 10 --fee 0.001 --node localhost:5000
  python wallet_cli.py mine --node localhost:5000
"""

import argparse
import getpass
import json
import sys

import requests

from pycoin.wallet import Wallet
from pycoin.transaction import Transaction


def cmd_new(args):
    w = Wallet.new_with_mnemonic()
    print("\n=== New PyCoin Wallet ===")
    print(f"Address   : {w.address}")
    print(f"Public Key: {w.public_key_hex}")
    print(f"\n⚠  Recovery Phrase (store offline — never share!):")
    print(f"   {w.mnemonic}\n")
    if args.save:
        password = None
        if args.password:
            password = getpass.getpass("Encryption password: ")
        w.save_to_file(args.save, password)
        print(f"Wallet saved to {args.save}")


def cmd_recover(args):
    phrase = " ".join(args.mnemonic)
    try:
        w = Wallet.from_mnemonic(phrase)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"\n=== Recovered Wallet ===")
    print(f"Address   : {w.address}")
    print(f"Public Key: {w.public_key_hex}")
    if args.save:
        password = getpass.getpass("Encryption password (leave blank for none): ") or None
        w.save_to_file(args.save, password)
        print(f"Wallet saved to {args.save}")


def cmd_info(args):
    w = _load_wallet(args.wallet_file)
    print(f"\nAddress   : {w.address}")
    print(f"Public Key: {w.public_key_hex}")
    if w.mnemonic:
        print(f"Mnemonic  : {w.mnemonic}")


def cmd_balance(args):
    url = f"http://{args.node}/balance/{args.address}"
    try:
        resp = requests.get(url, timeout=5)
        data = resp.json()
        print(f"{data['balance']:.6f} PYC  ({args.address})")
    except requests.RequestException as exc:
        print(f"Error contacting node: {exc}", file=sys.stderr)
        sys.exit(1)


def cmd_send(args):
    w = _load_wallet(args.wallet_file)
    tx = Transaction.create_and_sign(w, args.to, args.amount, args.fee)
    url = f"http://{args.node}/transaction/new"
    try:
        resp = requests.post(url, json=tx.to_dict(), timeout=5)
        if resp.ok:
            data = resp.json()
            print(f"Transaction submitted: {data.get('tx_id', '?')}")
        else:
            print(f"Rejected: {resp.json()}", file=sys.stderr)
            sys.exit(1)
    except requests.RequestException as exc:
        print(f"Error contacting node: {exc}", file=sys.stderr)
        sys.exit(1)


def cmd_mine(args):
    url = f"http://{args.node}/mine"
    try:
        resp = requests.post(url, timeout=120)
        block = resp.json()
        print(f"Block #{block['index']} mined: {block['hash']}")
        print(f"Transactions: {len(block['transactions'])}")
    except requests.RequestException as exc:
        print(f"Error contacting node: {exc}", file=sys.stderr)
        sys.exit(1)


def _load_wallet(path: str) -> Wallet:
    try:
        with open(path) as f:
            payload = json.load(f)
        if payload.get("encrypted"):
            password = getpass.getpass("Wallet password: ")
        else:
            password = None
        return Wallet.load_from_file(path, password)
    except FileNotFoundError:
        print(f"Wallet file not found: {path}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"Failed to load wallet: {exc}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="PyCoin wallet CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_new = sub.add_parser("new", help="Generate a new wallet")
    p_new.add_argument("--save", metavar="FILE", help="Save wallet to file")
    p_new.add_argument("--password", action="store_true", help="Encrypt wallet file")

    p_recover = sub.add_parser("recover", help="Restore wallet from mnemonic")
    p_recover.add_argument("mnemonic", nargs="+", help="12-word BIP39 mnemonic")
    p_recover.add_argument("--save", metavar="FILE", help="Save wallet to file")

    p_info = sub.add_parser("info", help="Show wallet details")
    p_info.add_argument("wallet_file")

    p_bal = sub.add_parser("balance", help="Check address balance")
    p_bal.add_argument("address")
    p_bal.add_argument("--node", default="localhost:5000", metavar="HOST:PORT")

    p_send = sub.add_parser("send", help="Send PYC")
    p_send.add_argument("wallet_file")
    p_send.add_argument("--to", required=True, metavar="ADDRESS")
    p_send.add_argument("--amount", type=float, required=True)
    p_send.add_argument("--fee", type=float, default=0.0)
    p_send.add_argument("--node", default="localhost:5000", metavar="HOST:PORT")

    p_mine = sub.add_parser("mine", help="Mine the next block on a running node")
    p_mine.add_argument("--node", default="localhost:5000", metavar="HOST:PORT")

    args = parser.parse_args()
    dispatch = {
        "new": cmd_new,
        "recover": cmd_recover,
        "info": cmd_info,
        "balance": cmd_balance,
        "send": cmd_send,
        "mine": cmd_mine,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
