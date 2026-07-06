"""
Block and Blockchain: Enigma Proof-of-Work chain with supply cap and halving.

Block headers use double SHA-256 (Bitcoin-style) and a version field reserved
for post-quantum signature migration.
"""

import hashlib
import json
import time
from typing import List

from .transaction import Transaction
from .wallet import address_from_public_key_hex

# -----------------------------------------------------------------------
# Enigma economics — compute-backed scarcity (Bitcoin-style halving)
# -----------------------------------------------------------------------
TOTAL_SUPPLY = 21_000_000.0       # maximum ENIG ever
INITIAL_REWARD = 50.0             # ENIG per block at genesis
HALVING_INTERVAL = 210_000        # blocks between halvings
MINING_REWARD = INITIAL_REWARD    # kept as alias for tests / external code

HEADER_VERSION = 1                # v1 = secp256k1; v2 reserved for PQC
INITIAL_DIFFICULTY = 4
DIFFICULTY_ADJUSTMENT = 10        # adjust every N blocks
TARGET_BLOCK_TIME = 60            # seconds per block target


def get_block_reward(block_height: int) -> float:
    """Return the coinbase reward for a given block height (halving every 210,000 blocks)."""
    halvings = block_height // HALVING_INTERVAL
    if halvings >= 64:
        return 0.0
    return INITIAL_REWARD / (2 ** halvings)


class Block:
    def __init__(
        self,
        index: int,
        transactions: List[Transaction],
        previous_hash: str,
        difficulty: int,
        timestamp: float | None = None,
        nonce: int = 0,
        block_hash: str = "",
    ):
        self.index = index
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.difficulty = difficulty
        self.timestamp = timestamp or time.time()
        self.nonce = nonce
        self.hash = block_hash or self._compute_hash()

    # ------------------------------------------------------------------
    # Hashing
    # ------------------------------------------------------------------

    def _header(self) -> str:
        tx_ids = [tx.tx_id() for tx in self.transactions]
        return json.dumps(
            {
                "version": HEADER_VERSION,
                "index": self.index,
                "previous_hash": self.previous_hash,
                "timestamp": self.timestamp,
                "nonce": self.nonce,
                "tx_ids": tx_ids,
                "difficulty": self.difficulty,
            },
            sort_keys=True,
        )

    def _compute_hash(self) -> str:
        header_bytes = self._header().encode()
        return hashlib.sha256(hashlib.sha256(header_bytes).digest()).hexdigest()

    def _meets_difficulty(self, h: str) -> bool:
        return h.startswith("0" * self.difficulty)

    # ------------------------------------------------------------------
    # Mining
    # ------------------------------------------------------------------

    def mine(self):
        self.nonce = 0
        self.hash = self._compute_hash()
        while not self._meets_difficulty(self.hash):
            self.nonce += 1
            self.hash = self._compute_hash()

    # ------------------------------------------------------------------
    # Stats helpers
    # ------------------------------------------------------------------

    @property
    def total_fees(self) -> float:
        return sum(tx.fee for tx in self.transactions if tx.sender != "COINBASE")

    @property
    def miner_address(self) -> str:
        """Address that received the coinbase reward."""
        for tx in self.transactions:
            if tx.sender == "COINBASE":
                return tx.recipient
        return ""

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def is_valid(self) -> bool:
        if self.hash != self._compute_hash():
            return False
        if not self._meets_difficulty(self.hash):
            return False
        coinbases = [tx for tx in self.transactions if tx.sender == "COINBASE"]
        if len(coinbases) != 1:
            return False
        expected_reward = get_block_reward(self.index) + self.total_fees
        if coinbases[0].amount > expected_reward + 1e-9:
            return False
        for tx in self.transactions:
            if not tx.is_valid():
                return False
        return True

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "transactions": [tx.to_dict() for tx in self.transactions],
            "previous_hash": self.previous_hash,
            "difficulty": self.difficulty,
            "timestamp": self.timestamp,
            "nonce": self.nonce,
            "hash": self.hash,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Block":
        txs = [Transaction.from_dict(t) for t in d["transactions"]]
        return cls(
            index=d["index"],
            transactions=txs,
            previous_hash=d["previous_hash"],
            difficulty=d["difficulty"],
            timestamp=d["timestamp"],
            nonce=d["nonce"],
            block_hash=d["hash"],
        )


class Blockchain:
    def __init__(self):
        self.chain: List[Block] = []
        self.pending_transactions: List[Transaction] = []
        self._create_genesis_block()

    def _create_genesis_block(self):
        genesis = Block(
            index=0,
            transactions=[],
            previous_hash="0" * 64,
            difficulty=INITIAL_DIFFICULTY,
        )
        genesis.mine()
        self.chain.append(genesis)

    # ------------------------------------------------------------------
    # Chain helpers
    # ------------------------------------------------------------------

    @property
    def last_block(self) -> Block:
        return self.chain[-1]

    @property
    def height(self) -> int:
        return len(self.chain) - 1

    @property
    def total_mined(self) -> float:
        total = 0.0
        for block in self.chain:
            for tx in block.transactions:
                if tx.sender == "COINBASE":
                    total += tx.amount
        return total

    def _current_difficulty(self) -> int:
        if len(self.chain) < DIFFICULTY_ADJUSTMENT:
            return INITIAL_DIFFICULTY
        recent = self.chain[-DIFFICULTY_ADJUSTMENT:]
        elapsed = recent[-1].timestamp - recent[0].timestamp or 1
        actual_per_block = elapsed / DIFFICULTY_ADJUSTMENT
        difficulty = self.last_block.difficulty
        if actual_per_block < TARGET_BLOCK_TIME / 2:
            difficulty += 1
        elif actual_per_block > TARGET_BLOCK_TIME * 2:
            difficulty = max(1, difficulty - 1)
        return difficulty

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_transaction(self, tx: Transaction) -> bool:
        if not tx.is_valid():
            return False
        if tx.sender != "COINBASE":
            sender_address = address_from_public_key_hex(tx.sender)
            if self.get_balance(sender_address) < tx.amount + tx.fee:
                return False
        self.pending_transactions.append(tx)
        return True

    def mine_pending_transactions(self, miner_address: str) -> Block:
        fees = sum(tx.fee for tx in self.pending_transactions)
        next_index = len(self.chain)
        reward = get_block_reward(next_index) + fees
        reward_tx = Transaction.coinbase(miner_address, reward)
        txs = [reward_tx] + list(self.pending_transactions)
        self.pending_transactions = []

        block = Block(
            index=next_index,
            transactions=txs,
            previous_hash=self.last_block.hash,
            difficulty=self._current_difficulty(),
        )
        block.mine()
        self.chain.append(block)
        return block

    def get_balance(self, identifier: str) -> float:
        balance = 0.0
        for block in self.chain:
            for tx in block.transactions:
                if tx.recipient == identifier:
                    balance += tx.amount
                sender_id = tx.sender
                if sender_id not in ("COINBASE",):
                    try:
                        sender_id = address_from_public_key_hex(sender_id)
                    except Exception:
                        pass
                if sender_id == identifier:
                    balance -= tx.amount + tx.fee
        return balance

    def get_block_by_hash(self, block_hash: str) -> Block | None:
        for block in self.chain:
            if block.hash == block_hash:
                return block
        return None

    def get_block_by_height(self, height: int) -> Block | None:
        if 0 <= height < len(self.chain):
            return self.chain[height]
        return None

    def get_transaction(self, tx_id: str) -> tuple[Transaction | None, Block | None]:
        for block in self.chain:
            for tx in block.transactions:
                if tx.tx_id() == tx_id:
                    return tx, block
        return None, None

    def get_address_transactions(self, address: str) -> list:
        result = []
        for block in self.chain:
            for tx in block.transactions:
                sender_addr = tx.sender
                if sender_addr not in ("COINBASE",):
                    try:
                        sender_addr = address_from_public_key_hex(sender_addr)
                    except Exception:
                        pass
                if sender_addr == address or tx.recipient == address:
                    result.append((tx, block))
        return result

    def is_valid_chain(self) -> bool:
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]
            if not current.is_valid():
                return False
            if current.previous_hash != previous.hash:
                return False
        return True

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "chain": [b.to_dict() for b in self.chain],
            "pending_transactions": [tx.to_dict() for tx in self.pending_transactions],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Blockchain":
        bc = cls.__new__(cls)
        bc.chain = [Block.from_dict(b) for b in d["chain"]]
        bc.pending_transactions = [Transaction.from_dict(t) for t in d["pending_transactions"]]
        return bc
