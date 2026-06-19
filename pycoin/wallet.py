"""
Wallet: ECDSA key-pair generation, address derivation, and transaction signing.
"""

import hashlib
import json
import base64

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend


def _sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def _ripemd160(data: bytes) -> bytes:
    h = hashlib.new("ripemd160")
    h.update(data)
    return h.digest()


class Wallet:
    """An ECDSA P-256 wallet.  Address = base58check( RIPEMD160(SHA256(pubkey)) )."""

    def __init__(self):
        self._private_key = ec.generate_private_key(ec.SECP256K1(), default_backend())
        self._public_key = self._private_key.public_key()

    # ------------------------------------------------------------------
    # Serialisation helpers
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
        """Bitcoin-style address: base58check of RIPEMD160(SHA256(pubkey))."""
        pub_hash = _ripemd160(_sha256(self.public_key_bytes))
        versioned = b"\x00" + pub_hash          # version byte 0x00
        checksum = _sha256(_sha256(versioned))[:4]
        payload = versioned + checksum
        return _base58_encode(payload)

    # ------------------------------------------------------------------
    # Signing
    # ------------------------------------------------------------------

    def sign(self, data: bytes) -> str:
        """Sign arbitrary bytes; return DER signature as hex."""
        sig = self._private_key.sign(data, ec.ECDSA(hashes.SHA256()))
        return sig.hex()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "address": self.address,
            "public_key": self.public_key_hex,
            "private_key_pem": self.private_key_hex,
        }

    @classmethod
    def from_pem(cls, pem: str) -> "Wallet":
        w = cls.__new__(cls)
        w._private_key = serialization.load_pem_private_key(
            pem.encode(), password=None, backend=default_backend()
        )
        w._public_key = w._private_key.public_key()
        return w


# ------------------------------------------------------------------
# Standalone helpers (used by blockchain/transaction without a Wallet)
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
        pub_key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256K1(), pub_bytes)
        pub_key.verify(bytes.fromhex(signature_hex), data, ec.ECDSA(hashes.SHA256()))
        return True
    except Exception:
        return False


# ------------------------------------------------------------------
# Base-58
# ------------------------------------------------------------------

_ALPHABET = b"123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def _base58_encode(payload: bytes) -> str:
    n = int.from_bytes(payload, "big")
    result = []
    while n:
        n, r = divmod(n, 58)
        result.append(_ALPHABET[r:r+1])
    for byte in payload:
        if byte == 0:
            result.append(_ALPHABET[0:1])
        else:
            break
    return b"".join(reversed(result)).decode()
