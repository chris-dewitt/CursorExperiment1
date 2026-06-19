# PyCoin Whitepaper

**Version 1.0 — Draft**

---

## Abstract

PyCoin (PYC) is a peer-to-peer electronic cash system implementing the core design of Bitcoin in Python. It uses Proof-of-Work consensus, secp256k1 ECDSA cryptography, BIP39 mnemonic wallet recovery, and an adaptive-difficulty mining schedule. The total supply is capped at **21,000,000 PYC**, mirroring Bitcoin's scarcity model. This document describes the protocol, cryptographic primitives, economic model, and node API.

---

## 1. Introduction

PyCoin is an educational and production-capable cryptocurrency designed to be fully transparent, auditable, and compatible with existing tooling through a Bitcoin-compatible JSON-RPC API. Unlike many altcoins that fork an existing codebase, PyCoin is implemented from first principles, making every design decision explicit.

---

## 2. Cryptographic Foundations

### 2.1 Digital Signatures

All transactions are signed using **ECDSA over the secp256k1 elliptic curve** — the same curve used by Bitcoin and Ethereum. Each wallet holds:

- A **256-bit private key** (randomly generated or derived from a BIP39 mnemonic)
- A **33-byte compressed public key** (SEC X9.62 compressed point)
- A **Bitcoin-style address** derived as:

```
address = Base58Check(0x00 || RIPEMD160(SHA256(compressed_pubkey)))
```

### 2.2 Transaction Signing

The signed payload is the JSON-serialised (sorted keys) object:

```json
{
  "sender": "<public_key_hex>",
  "recipient": "<address>",
  "amount": <float>,
  "fee": <float>,
  "timestamp": <unix_float>
}
```

The DER-encoded ECDSA signature over SHA-256 of this payload is embedded in the transaction.

### 2.3 Block Hashing

Block headers are hashed with **SHA-256**. A valid hash must have at least `difficulty` leading zero hex digits.

---

## 3. Wallet System

### 3.1 BIP39 Mnemonic Recovery

PyCoin wallets support **BIP39** 12-word mnemonic phrases (128-bit entropy). Seed derivation follows the BIP39 standard:

```
seed = PBKDF2-HMAC-SHA512(mnemonic, "mnemonic" + passphrase, 2048, 64 bytes)
```

The master private key is derived using BIP32 HMAC-SHA512:

```
I = HMAC-SHA512(key="Bitcoin seed", data=seed)
private_key = I[0:32]   # must be in range [1, secp256k1_order - 1]
```

### 3.2 Encrypted Key Storage

Wallet files are stored as JSON. When a password is provided, the key material is encrypted with **Fernet (AES-128-CBC + HMAC-SHA256)** using a key derived via **PBKDF2-HMAC-SHA256** (480,000 iterations).

---

## 4. Transactions

Each transaction specifies:

| Field | Description |
|---|---|
| `sender` | Sender's compressed public key (hex), or `"COINBASE"` |
| `recipient` | Recipient's base58check address |
| `amount` | Coins to transfer (float, > 0) |
| `fee` | Miner tip (float, ≥ 0) |
| `timestamp` | Unix timestamp |
| `signature` | DER ECDSA signature over the canonical payload |

**Validation rules:**
1. Amount must be positive; fee must be non-negative.
2. Signature must verify against `sender` public key.
3. Sender's on-chain balance must cover `amount + fee`.
4. Coinbase transactions have exactly `"COINBASE"` as sender and are only created by miners.

**Transaction ID:** `SHA256(payload_bytes || signature_hex)`

---

## 5. Blocks

### 5.1 Block Header

```json
{
  "index": <int>,
  "previous_hash": "<hex64>",
  "timestamp": <float>,
  "nonce": <int>,
  "tx_ids": ["<hex64>", ...],
  "difficulty": <int>
}
```

The block hash is `SHA256(JSON(header, sorted_keys))`.

### 5.2 Proof of Work

A block is valid if its hash begins with at least `difficulty` hex zeros (i.e., `hash < 16^(64-difficulty)`). Miners increment the nonce until the condition is met.

### 5.3 Difficulty Adjustment

Every 10 blocks, the node compares the actual time elapsed over those blocks to the 60-second target:

- Actual < 30 s → difficulty + 1
- Actual > 120 s → difficulty − 1 (minimum 1)

---

## 6. Supply & Economics

| Parameter | Value |
|---|---|
| Maximum supply | 21,000,000 PYC |
| Initial block reward | 50 PYC |
| Halving interval | Every 210,000 blocks |
| Block target | 60 seconds |
| Transaction fees | Market-determined, paid to miner |

Block reward at height `h`:

```
reward = 50 / 2^floor(h / 210_000)   for h < 210_000 * 64
reward = 0                             for h ≥ 210_000 * 64
```

Total supply converges to exactly **21,000,000 PYC** (geometric series: 50 × 210,000 × (1 + 0.5 + 0.25 + …) = 21,000,000).

---

## 7. Peer-to-Peer Network

Each node exposes an HTTP API. Peers are discovered by:

1. Manual registration (`POST /peers/register`).
2. The `--peer` CLI flag on startup.

**Consensus:** When a node receives a block that doesn't fit its current chain, or on startup, it performs **longest-chain consensus**: it queries all peers' chains and adopts the longest valid one.

---

## 8. Node API

### 8.1 REST Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/chain` | Full serialised blockchain |
| GET | `/pending` | Pending transactions (mempool) |
| GET | `/balance/<address>` | Address balance |
| GET | `/wallet` | Node wallet info |
| GET | `/peers` | Registered peers |
| POST | `/transaction/new` | Submit a signed transaction |
| POST | `/mine` | Mine pending transactions |
| POST | `/peers/register` | Register a peer |

### 8.2 JSON-RPC 2.0 — `POST /rpc`

Bitcoin-compatible subset. Request format:

```json
{"jsonrpc":"2.0","method":"getblockchaininfo","params":[],"id":1}
```

Supported methods: `getblockchaininfo`, `getblockcount`, `getblockhash`, `getblock`, `gettransaction`, `getbalance`, `sendrawtransaction`, `getmininginfo`, `getnewaddress`.

---

## 9. Exchange Integration

### 9.1 Technical Requirements Checklist

- [x] secp256k1 ECDSA signatures
- [x] Bitcoin-style base58check addresses
- [x] BIP39 mnemonic wallet recovery
- [x] JSON-RPC 2.0 API (Bitcoin-compatible subset)
- [x] Deterministic transaction IDs
- [x] Block explorer web interface
- [x] Docker deployment
- [x] Documented coin specification (`coin_spec.json`)
- [ ] Mainnet genesis block (requires community launch)
- [ ] Independent security audit
- [ ] Liquidity / market maker arrangement

### 9.2 Listing Applications

- **Coinbase Asset Hub:** https://www.coinbase.com/en-gb/blog/how-coinbase-lists-assets
- **Kraken Listing Application:** Contact Kraken's asset listing team via their official website
- **CoinGecko / CoinMarketCap:** List for tracking (required before exchange listing for most exchanges)

### 9.3 Exchange Wallet Integration

Exchanges typically run a full node and use the JSON-RPC API to:

1. Generate deposit addresses: `getnewaddress`
2. Monitor incoming transactions: poll `getblock` / `gettransaction`
3. Broadcast withdrawals: `sendrawtransaction`
4. Check confirmation count: `gettransaction` → `confirmations`

---

## 10. Security Considerations

- Private keys never leave the wallet file or the signing process.
- Wallet encryption uses PBKDF2 (480,000 iterations) + Fernet AES.
- Block validity is checked before appending to the chain.
- Double-spend protection: the balance check in `add_transaction` scans the full on-chain history.
- **Known limitations (for production hardening):** HTTP transport (should be TLS), no mempool eviction policy, simple balance model (no UTXO set — O(n) scan), no Bloom filter for SPV.

---

## 11. Roadmap

| Phase | Milestone |
|---|---|
| 1 | Core protocol + block explorer (complete) |
| 2 | Mainnet genesis launch + seed nodes |
| 3 | TLS + authenticated P2P transport |
| 4 | UTXO set for O(1) balance queries |
| 5 | SPV / light-client support |
| 6 | Smart contract layer (optional) |
| 7 | Exchange listings |

---

## 12. Conclusion

PyCoin demonstrates that a fully functional, cryptographically sound cryptocurrency can be built transparently. The 21M supply cap and halving schedule establish provable scarcity; BIP39 wallet support ensures compatibility with hardware wallets and standard tooling; and the JSON-RPC API enables straightforward exchange integration.

---

*This whitepaper is a living document. Contributions and security disclosures are welcome via the GitHub repository.*
