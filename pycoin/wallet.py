"""
Wallet: ECDSA secp256k1 key-pair, Bitcoin-style addresses, BIP39 mnemonic
        support, signing, and encrypted key-file persistence.
"""

import hashlib
import hmac as _hmac
import json
import os
import base64

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.ec import derive_private_key, SECP256K1
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import Fernet
from mnemonic import Mnemonic

_MNEMO = Mnemonic("english")
_SECP256K1_ORDER = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141


def _sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def _ripemd160(data: bytes) -> bytes:
    h = hashlib.new("ripemd160")
    h.update(data)
    return h.digest()


def _fernet_key_from_password(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480_000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))


class Wallet:
    """ECDSA secp256k1 wallet with BIP39 mnemonic and encrypted file storage."""

    def __init__(self):
        self._private_key = ec.generate_private_key(SECP256K1(), default_backend())
        self._public_key = self._private_key.public_key()
        self.mnemonic: str = ""

    # ------------------------------------------------------------------
    # Factories
    # ------------------------------------------------------------------

    @classmethod
    def new_with_mnemonic(cls) -> "Wallet":
        """Generate a fresh wallet with a 12-word BIP39 recovery phrase."""
        phrase = _MNEMO.generate(strength=128)
        return cls.from_mnemonic(phrase)

    @classmethod
    def from_mnemonic(cls, phrase: str, passphrase: str = "") -> "Wallet":
        """Restore a wallet from a BIP39 mnemonic phrase (BIP39 seed + BIP32 master key)."""
        if not _MNEMO.check(phrase):
            raise ValueError("Invalid BIP39 mnemonic phrase")
        seed = hashlib.pbkdf2_hmac(
            "sha512",
            phrase.encode(),
            ("mnemonic" + passphrase).encode(),
            iterations=2048,
            dklen=64,
        )
        I = _hmac.new(b"Bitcoin seed", seed, hashlib.sha512).digest()
        key_int = int.from_bytes(I[:32], "big")
        if key_int == 0 or key_int >= _SECP256K1_ORDER:
            raise ValueError("Derived key out of range; try a different passphrase")
        w = cls.__new__(cls)
        w._private_key = derive_private_key(key_int, SECP256K1(), default_backend())
        w._public_key = w._private_key.public_key()
        w.mnemonic = phrase
        return w

    @classmethod
    def from_pem(cls, pem: str) -> "Wallet":
        w = cls.__new__(cls)
        w._private_key = serialization.load_pem_private_key(
            pem.encode(), password=None, backend=default_backend()
        )
        w._public_key = w._private_key.public_key()
        w.mnemonic = ""
        return w

    # ------------------------------------------------------------------
    # Key material
    # ------------------------------------------------------------------

    @property
    def public_key_bytes(self) -> bytes:
        return self._public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.CompressedPoint,
        )

    @property
    def public_key_hex(self) -> str:
        return self.public_key_bytes.hex()

    @property
    def private_key_hex(self) -> str:
        return self._private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode()

    @property
    def address(self) -> str:
        """Bitcoin-style base58check address: RIPEMD160(SHA256(pubkey))."""
        pub_hash = _ripemd160(_sha256(self.public_key_bytes))
        versioned = b"\x00" + pub_hash
        checksum = _sha256(_sha256(versioned))[:4]
        return _base58_encode(versioned + checksum)

    # ------------------------------------------------------------------
    # Signing
    # ------------------------------------------------------------------

    def sign(self, data: bytes) -> str:
        sig = self._private_key.sign(data, ec.ECDSA(hashes.SHA256()))
        return sig.hex()

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "address": self.address,
            "public_key": self.public_key_hex,
            "private_key_pem": self.private_key_hex,
            "mnemonic": self.mnemonic,
        }

    # ------------------------------------------------------------------
    # Encrypted file storage
    # ------------------------------------------------------------------

    def save_to_file(self, path: str, password: str | None = None) -> None:
        data = json.dumps(self.to_dict()).encode()
        if password:
            salt = os.urandom(16)
            fernet = Fernet(_fernet_key_from_password(password, salt))
            payload = {
                "encrypted": True,
                "salt": salt.hex(),
                "data": fernet.encrypt(data).decode(),
            }
        else:
            payload = {"encrypted": False, "data": data.decode()}
        with open(path, "w") as f:
            json.dump(payload, f, indent=2)

    @classmethod
    def load_from_file(cls, path: str, password: str | None = None) -> "Wallet":
        with open(path) as f:
            payload = json.load(f)
        if payload["encrypted"]:
            if not password:
                raise ValueError("Wallet is encrypted; provide --password")
            salt = bytes.fromhex(payload["salt"])
            fernet = Fernet(_fernet_key_from_password(password, salt))
            inner = json.loads(fernet.decrypt(payload["data"].encode()))
        else:
            inner = json.loads(payload["data"])
        w = cls.from_pem(inner["private_key_pem"])
        w.mnemonic = inner.get("mnemonic", "")
        return w


# ------------------------------------------------------------------
# Standalone helpers
# ------------------------------------------------------------------

def address_from_public_key_hex(public_key_hex: str) -> str:
    """Derive the base58check address from a compressed public key hex string."""
    pub_bytes = bytes.fromhex(public_key_hex)
    pub_hash = _ripemd160(_sha256(pub_bytes))
    versioned = b"\x00" + pub_hash
    checksum = _sha256(_sha256(versioned))[:4]
    return _base58_encode(versioned + checksum)


def verify_signature(public_key_hex: str, data: bytes, signature_hex: str) -> bool:
    try:
        pub_bytes = bytes.fromhex(public_key_hex)
        pub_key = ec.EllipticCurvePublicKey.from_encoded_point(SECP256K1(), pub_bytes)
        pub_key.verify(bytes.fromhex(signature_hex), data, ec.ECDSA(hashes.SHA256()))
        return True
    except Exception:
        return False


# ------------------------------------------------------------------
# Base-58 encoding
# ------------------------------------------------------------------

_ALPHABET = b"123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def _base58_encode(payload: bytes) -> str:
    n = int.from_bytes(payload, "big")
    result = []
    while n:
        n, r = divmod(n, 58)
        result.append(_ALPHABET[r : r + 1])
    for byte in payload:
        if byte == 0:
            result.append(_ALPHABET[0:1])
        else:
            break
    return b"".join(reversed(result)).decode()
