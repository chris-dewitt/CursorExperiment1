import pytest
from pycoin.wallet import Wallet, verify_signature


def test_wallet_generates_address():
    w = Wallet()
    assert len(w.address) > 20
    assert w.address[0] in "123456789"   # base58, no 0/O/l/I


def test_wallet_sign_verify():
    w = Wallet()
    data = b"hello pycoin"
    sig = w.sign(data)
    assert verify_signature(w.public_key_hex, data, sig)


def test_verify_rejects_tampered_data():
    w = Wallet()
    sig = w.sign(b"legit")
    assert not verify_signature(w.public_key_hex, b"tampered", sig)


def test_wallet_round_trip():
    w = Wallet()
    pem = w.private_key_hex
    w2 = Wallet.from_pem(pem)
    assert w2.address == w.address
