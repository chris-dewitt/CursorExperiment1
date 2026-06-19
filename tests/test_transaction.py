import pytest
from pycoin.wallet import Wallet
from pycoin.transaction import Transaction


def test_coinbase_valid():
    tx = Transaction.coinbase("someaddress", 50.0)
    assert tx.is_valid()


def test_signed_transaction_valid():
    w = Wallet()
    tx = Transaction.create_and_sign(w, "recipient_address", 10.0)
    assert tx.is_valid()


def test_zero_amount_invalid():
    w = Wallet()
    tx = Transaction.create_and_sign(w, "addr", 0.0)
    assert not tx.is_valid()


def test_negative_amount_invalid():
    w = Wallet()
    tx = Transaction.create_and_sign(w, "addr", -5.0)
    assert not tx.is_valid()


def test_tampered_amount_invalid():
    w = Wallet()
    tx = Transaction.create_and_sign(w, "addr", 10.0)
    tx.amount = 9999.0   # tamper after signing
    assert not tx.is_valid()


def test_serialise_round_trip():
    w = Wallet()
    tx = Transaction.create_and_sign(w, "addr", 7.5)
    tx2 = Transaction.from_dict(tx.to_dict())
    assert tx2.is_valid()
    assert tx2.tx_id() == tx.tx_id()
