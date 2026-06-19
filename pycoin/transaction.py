"""
Transaction: a signed transfer of coins between two addresses.
"""

import hashlib
import json
import time

from .wallet import verify_signature


class Transaction:
    """
    A coin transfer.

    Fields:
        sender      – sender's public key hex (or 'COINBASE')
        recipient   – recipient address
        amount      – coins transferred
        timestamp   – unix timestamp of creation
        signature   – DER-encoded ECDSA signature (hex) over the canonical payload
    """

    def __init__(
        self,
        sender: str,
        recipient: str,
        amount: float,
        signature: str = "",
        timestamp: float | None = None,
    ):
        self.sender = sender
        self.recipient = recipient
        self.amount = amount
        self.timestamp = timestamp or time.time()
        self.signature = signature

    # ------------------------------------------------------------------
    # Canonical payload (what is signed / hashed)
    # ------------------------------------------------------------------

    def _payload_bytes(self) -> bytes:
        payload = {
            "sender": self.sender,
            "recipient": self.recipient,
            "amount": self.amount,
            "timestamp": self.timestamp,
        }
        return json.dumps(payload, sort_keys=True).encode()

    def tx_id(self) -> str:
        return hashlib.sha256(self._payload_bytes() + self.signature.encode()).hexdigest()

    # ------------------------------------------------------------------
    # Factory helpers
    # ------------------------------------------------------------------

    @classmethod
    def coinbase(cls, recipient: str, reward: float) -> "Transaction":
        """Block reward transaction with no sender."""
        tx = cls(sender="COINBASE", recipient=recipient, amount=reward)
        tx.signature = "COINBASE"
        return tx

    @classmethod
    def create_and_sign(cls, wallet, recipient: str, amount: float) -> "Transaction":
        tx = cls(sender=wallet.public_key_hex, recipient=recipient, amount=amount)
        tx.signature = wallet.sign(tx._payload_bytes())
        return tx

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def is_valid(self) -> bool:
        if self.amount <= 0:
            return False
        if self.sender == "COINBASE":
            return self.signature == "COINBASE"
        return verify_signature(self.sender, self._payload_bytes(), self.signature)

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "sender": self.sender,
            "recipient": self.recipient,
            "amount": self.amount,
            "timestamp": self.timestamp,
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Transaction":
        return cls(
            sender=d["sender"],
            recipient=d["recipient"],
            amount=d["amount"],
            signature=d["signature"],
            timestamp=d["timestamp"],
        )
