# Enigma

**The compute currency.** ENIG prices settlement by live proof-of-work supply vs mempool demand — quantum-ready, AI-native, cryptographically maximal.

```
◈ ENIGMA — where compute meets scarcity
```

## What is Enigma?

Enigma (ticker **ENIG**) is a peer-to-peer cryptocurrency built for the age of AI and distributed compute. Unlike static fee models, Enigma tracks a live **compute market**:

- **Supply** — network PoW difficulty × peer mesh size (verifiable hashrate capacity)
- **Demand** — mempool congestion, pending value, and fee urgency
- **Equilibrium** — dynamic fee suggestions driven by the demand/supply ratio

Miners prove compute capacity. Users pay what the market demands. The chain settles it all with double SHA-256 proof-of-work and secp256k1 signatures — with a header version field reserved for post-quantum migration.

## Quick Start

```bash
pip install -r requirements.txt

# Start a node (block explorer at http://localhost:5000)
python main.py

# Generate a wallet
python wallet_cli.py new --save my.wallet

# Check compute market
python wallet_cli.py compute

# Run tests
pytest
```

## Docker

```bash
docker compose up --build
# Node 1: http://localhost:5000
# Node 2: http://localhost:5001
```

## Key Features

| Feature | Details |
|---------|---------|
| **Ticker** | ENIG |
| **Supply cap** | 21,000,000 ENIG (Bitcoin-style halving) |
| **Consensus** | Double SHA-256 Proof-of-Work |
| **Signatures** | secp256k1 ECDSA (PQC-ready header v2 path) |
| **Wallets** | BIP39 mnemonic + AES-encrypted storage (600k PBKDF2) |
| **Compute market** | Live supply/demand ratio + suggested fees |
| **API** | REST + Bitcoin-compatible JSON-RPC + `getcomputeinfo` |
| **Explorer** | Dark quantum-themed UI with compute dashboard |

## Compute Market API

```bash
# REST
curl http://localhost:5000/compute/stats

# JSON-RPC
curl -X POST http://localhost:5000/rpc \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"getcomputeinfo","params":[],"id":1}'
```

## Documentation

- [WHITEPAPER.md](WHITEPAPER.md) — full protocol specification
- [coin_spec.json](coin_spec.json) — exchange listing metadata
- Block explorer `/docs` — live API reference

## Security

- Double SHA-256 block hashing (Bitcoin-grade collision resistance)
- 600,000-iteration PBKDF2 wallet encryption
- Block header version field for future post-quantum signature schemes
- Full chain validation before append; double-spend protection on every transaction

## License

Open source. See repository for details.
