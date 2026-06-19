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


def test_signed_transaction_with_fee():
    w = Wallet()
    tx = Transaction.create_and_sign(w, "recipient_address", 10.0, fee=0.001)
    assert tx.is_valid()
    assert tx.fee == 0.001


def test_zero_amount_invalid():
    w = Wallet()
    tx = Transaction.create_and_sign(w, "addr", 0.0)
    assert not tx.is_valid()


def test_negative_amount_invalid():
    w = Wallet()
    tx = Transaction.create_and_sign(w, "addr", -5.0)
    assert not tx.is_valid()


def test_negative_fee_invalid():
    w = Wallet()
    tx = Transaction.create_and_sign(w, "addr", 5.0, fee=-1.0)
    assert not tx.is_valid()


def test_tampered_amount_invalid():
    w = Wallet()
    tx = Transaction.create_and_sign(w, "addr", 10.0)
    tx.amount = 9999.0
    assert not tx.is_valid()


def test_tampered_fee_invalid():
    w = Wallet()
    tx = Transaction.create_and_sign(w, "addr", 10.0, fee=0.001)
    tx.fee = 999.0
    assert not tx.is_valid()


def test_serialise_round_trip():
    w = Wallet()
    tx = Transaction.create_and_sign(w, "addr", 7.5, fee=0.01)
    tx2 = Transaction.from_dict(tx.to_dict())
    assert tx2.is_valid()
    assert tx2.tx_id() == tx.tx_id()
    assert tx2.fee == tx.fee


def test_from_dict_missing_fee_defaults_zero():
    w = Wallet()
    tx = Transaction.create_and_sign(w, "addr", 5.0)
    d = tx.to_dict()
    del d["fee"]
    tx2 = Transaction.from_dict(d)
    assert tx2.fee == 0.0
