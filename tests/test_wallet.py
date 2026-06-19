import os
import tempfile
import pytest
from pycoin.wallet import Wallet, verify_signature


def test_wallet_generates_address():
    w = Wallet()
    assert len(w.address) > 20
    assert w.address[0] in "123456789"


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


# ------------------------------------------------------------------
# BIP39 mnemonic tests
# ------------------------------------------------------------------

def test_new_with_mnemonic():
    w = Wallet.new_with_mnemonic()
    assert len(w.mnemonic.split()) == 12
    assert len(w.address) > 20


def test_from_mnemonic_deterministic():
    w1 = Wallet.new_with_mnemonic()
    w2 = Wallet.from_mnemonic(w1.mnemonic)
    assert w1.address == w2.address
    assert w1.public_key_hex == w2.public_key_hex


def test_from_mnemonic_invalid():
    with pytest.raises(ValueError):
        Wallet.from_mnemonic("not valid mnemonic at all ever really")


def test_mnemonic_wallet_signs():
    w = Wallet.new_with_mnemonic()
    data = b"sign with mnemonic wallet"
    sig = w.sign(data)
    assert verify_signature(w.public_key_hex, data, sig)


# ------------------------------------------------------------------
# Encrypted file storage
# ------------------------------------------------------------------

def test_save_load_unencrypted(tmp_path):
    w = Wallet.new_with_mnemonic()
    path = str(tmp_path / "wallet.json")
    w.save_to_file(path)
    w2 = Wallet.load_from_file(path)
    assert w2.address == w.address
    assert w2.mnemonic == w.mnemonic


def test_save_load_encrypted(tmp_path):
    w = Wallet.new_with_mnemonic()
    path = str(tmp_path / "wallet_enc.json")
    w.save_to_file(path, password="s3cr3t")
    w2 = Wallet.load_from_file(path, password="s3cr3t")
    assert w2.address == w.address


def test_wrong_password_fails(tmp_path):
    w = Wallet()
    path = str(tmp_path / "wallet_enc.json")
    w.save_to_file(path, password="correct")
    with pytest.raises(Exception):
        Wallet.load_from_file(path, password="wrong")
