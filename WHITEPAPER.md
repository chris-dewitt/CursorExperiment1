# Enigma Whitepaper

**Version 2.0 — Compute Currency**

---

## Abstract

Enigma (ENIG) is a quantum-ready, AI-native compute currency. Proof-of-Work mining represents verifiable compute capacity on the network; the mempool and fee market represent settlement demand. A live **compute supply/demand ratio** drives dynamic fee guidance — the economic core of Enigma.

Built on double SHA-256 consensus, secp256k1 ECDSA signatures, BIP39 wallet recovery, and a 21M ENIG supply cap with Bitcoin-style halving, Enigma is designed for the era where compute is the scarcest resource.

---

## 1. Introduction

The AI revolution has made compute the new oil. GPU clusters, inference farms, and distributed proof-of-work networks all compete for the same finite resource: verifiable computational capacity.

Enigma answers a simple question: **what is compute worth right now?**

Unlike static-fee blockchains, Enigma continuously measures:

1. **Compute supply** — network hashrate implied by PoW difficulty and peer mesh size
2. **Compute demand** — mempool congestion, pending transaction value, and fee urgency
3. **Market equilibrium** — a demand/supply ratio that drives suggested fees and network status

Enigma is implemented from first principles in Python — fully auditable, transparent, and compatible with Bitcoin-style JSON-RPC tooling.

---

## 2. Cryptographic Foundations

### 2.1 Digital Signatures (Classical + Quantum Path)

All transactions are signed with **ECDSA over secp256k1** — battle-tested, Bitcoin-compatible cryptography.

Block headers include a **`version` field**:

| Version | Scheme |
|---------|--------|
| **1** (current) | secp256k1 ECDSA |
| **2** (reserved) | Post-quantum signature migration (ML-DSA / SPHINCS+ path) |

This versioned header enables a coordinated hard-fork to post-quantum signatures without breaking address compatibility planning.

### 2.2 Address Derivation

```
address = Base58Check(0x00 || RIPEMD160(SHA256(compressed_pubkey)))
```

Identical to Bitcoin P2PKH — hardware wallet compatible.

### 2.3 Block Hashing — Double SHA-256

Enigma uses **double SHA-256** (Bitcoin-style) for block headers:

```
block_hash = SHA256(SHA256(header_bytes))
```

This provides stronger collision resistance than single-round hashing and aligns with industry-standard PoW security assumptions.

A valid hash must have at least `difficulty` leading zero hex digits.

### 2.4 Wallet Encryption

Wallet files use **Fernet (AES-128-CBC + HMAC-SHA256)** with keys derived via **PBKDF2-HMAC-SHA256 at 600,000 iterations** — exceeding OWASP 2023 recommendations for password-based key derivation.

---

## 3. The Compute Market

### 3.1 Supply — Verifiable Compute Capacity

Network compute supply is estimated from:

```
hashrate ≈ (difficulty × 16⁴ × active_peers) / target_block_time
supply_score = hashrate / 1,000,000
```

PoW difficulty scales with actual mining effort. Peer count scales with distributed compute mesh size. Together they approximate verifiable compute capacity on the network.

### 3.2 Demand — Settlement Pressure

Compute demand aggregates:

```
demand_score = (mempool_size × 2) + (pending_value × 5) + (pending_fees × 200)
```

Mempool congestion, economic value awaiting settlement, and fee urgency all signal demand for block-space — the scarce compute resource miners provide.

### 3.3 Equilibrium — Dynamic Fee Guidance

```
ratio = demand_score / supply_score
```

| Ratio | Status | Suggested Fee |
|-------|--------|---------------|
| < 0.6 | **Surplus** | 0.0001 ENIG |
| 0.6 – 1.4 | **Balanced** | 0.001 ENIG |
| > 1.4 | **Constrained** | 0.001 × ratio (capped) |

This model is exposed via:

- `GET /compute/stats` — JSON snapshot
- `GET /compute` — visual dashboard
- RPC `getcomputeinfo` — full market data
- RPC `getmininginfo` — includes compute metrics
- RPC `getblockchaininfo` — includes `compute_market` object

### 3.4 AI & Quantum Positioning

Enigma's compute market is the settlement layer for a future **AI inference mesh**:

- **Phase 1 (now):** PoW proves compute; mempool prices settlement
- **Phase 2:** Provider registration with attested GPU/TPU capacity
- **Phase 3:** AI job routing with ENIG micropayments per inference token
- **Phase 4:** Post-quantum signature migration via header version 2

The economic primitives — supply measurement, demand pricing, equilibrium fees — are designed to extend from block settlement to AI compute markets without redesigning the token.

---

## 4. Wallet System

### 4.1 BIP39 Mnemonic Recovery

12-word BIP39 phrases (128-bit entropy). Master key derivation via BIP32 HMAC-SHA512 with the standard `"Bitcoin seed"` domain separator.

### 4.2 Encrypted Key Storage

JSON wallet files with optional Fernet encryption. 600,000-iteration PBKDF2 key derivation.

---

## 5. Transactions

| Field | Description |
|---|---|
| `sender` | Compressed public key (hex), or `"COINBASE"` |
| `recipient` | Base58Check address |
| `amount` | ENIG to transfer (> 0) |
| `fee` | Miner tip (≥ 0) — priced by compute market |
| `timestamp` | Unix timestamp |
| `signature` | DER ECDSA over canonical JSON payload |

**Transaction ID:** `SHA256(payload_bytes || signature_hex)`

---

## 6. Blocks

### 6.1 Block Header

```json
{
  "version": 1,
  "index": <int>,
  "previous_hash": "<hex64>",
  "timestamp": <float>,
  "nonce": <int>,
  "tx_ids": ["<hex64>", ...],
  "difficulty": <int>
}
```

Block hash: `SHA256(SHA256(JSON(header, sorted_keys)))`.

### 6.2 Proof of Work

Miners increment nonce until `hash` begins with `difficulty` hex zeros. Mining proves compute capacity and earns ENIG rewards.

### 6.3 Difficulty Adjustment

Every 10 blocks, compare actual block time to the 60-second target. Adjust difficulty ±1 to maintain equilibrium between compute supply and network demand for blocks.

---

## 7. Supply & Economics

| Parameter | Value |
|---|---|
| Maximum supply | 21,000,000 ENIG |
| Initial block reward | 50 ENIG |
| Halving interval | Every 210,000 blocks |
| Block target | 60 seconds |
| Smallest unit | qubit (10⁻⁸ ENIG) |
| Transaction fees | Market-determined via compute ratio |

```
reward = 50 / 2^floor(h / 210_000)   for h < 210_000 × 64
reward = 0                           for h ≥ 210_000 × 64
```

Scarcity meets compute: ENIG rewards those who prove capacity while the compute market prices access to it.

---

## 8. Peer-to-Peer Network

HTTP-based P2P with longest-chain consensus. Peers register via `POST /peers/register` or `--peer` CLI flag. Each peer contributes to the compute supply score.

---

## 9. Node API

### 9.1 REST Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/chain` | Full blockchain |
| GET | `/compute/stats` | Compute market JSON |
| GET | `/compute` | Compute dashboard |
| POST | `/mine` | Mine pending transactions |
| POST | `/transaction/new` | Submit signed transaction |

### 9.2 JSON-RPC 2.0

Bitcoin-compatible subset plus Enigma extensions:

- `getcomputeinfo` — full compute market snapshot
- `getblockchaininfo` — includes `compute_market` object
- `getmininginfo` — includes supply, demand, ratio, suggested fee

---

## 10. Security Considerations

- **Double SHA-256** block hashing for collision resistance
- **600,000-iteration PBKDF2** wallet encryption
- **Versioned block headers** for post-quantum migration path
- Private keys never leave the signing process
- Full chain validation before block append
- Double-spend protection via balance scanning

**Known limitations:** HTTP transport (TLS recommended for production), O(n) balance model (UTXO set planned), no SPV light clients yet.

---

## 11. Roadmap

| Phase | Milestone |
|---|---|
| 1 | Core protocol + compute market + explorer ✓ |
| 2 | Mainnet genesis + seed node mesh |
| 3 | TLS + authenticated P2P transport |
| 4 | AI inference provider registration |
| 5 | Post-quantum signature migration (header v2) |
| 6 | UTXO set + SPV light clients |
| 7 | Exchange listings |

---

## 12. Conclusion

Enigma is compute currency for the AI age. Proof-of-Work proves capacity. The mempool signals demand. The ratio prices access. Double SHA-256 secures the chain. A quantum migration path protects the future. And 21 million ENIG ensures scarcity meets silicon.

**Supply meets demand. Compute meets currency. Enigma.**

---

*This whitepaper is a living document. Security disclosures and contributions welcome via GitHub.*
