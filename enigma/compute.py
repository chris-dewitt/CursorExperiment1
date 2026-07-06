"""
Compute Market — models decentralized compute supply vs settlement demand.

Enigma treats Proof-of-Work mining as verifiable compute capacity on the network.
The mempool, fee pressure, and peer mesh represent demand for block-space and
future AI inference routing. The demand/supply ratio drives dynamic fee guidance.
"""

from dataclasses import asdict, dataclass

from .block import TARGET_BLOCK_TIME

# Rough hashes required per difficulty hex digit (16^n scaling)
_HASHES_PER_DIFFICULTY = 16**4


@dataclass
class ComputeMarketSnapshot:
    supply_score: float
    demand_score: float
    ratio: float
    suggested_fee: float
    network_hashrate_estimate: float
    active_peers: int
    mempool_size: int
    pending_value: float
    status: str
    tagline: str

    def to_dict(self) -> dict:
        return asdict(self)


def compute_market_snapshot(blockchain, peer_count: int = 1) -> ComputeMarketSnapshot:
    """Derive live compute supply/demand metrics from chain + network state."""
    bc = blockchain
    difficulty = max(1, bc.last_block.difficulty)
    mempool = bc.pending_transactions
    mempool_size = len(mempool)
    pending_fees = sum(tx.fee for tx in mempool)
    pending_value = sum(tx.amount for tx in mempool)

    peers = max(1, peer_count)

    # Supply: PoW difficulty × peer mesh ≈ verifiable compute capacity
    hashrate = (difficulty * _HASHES_PER_DIFFICULTY * peers) / TARGET_BLOCK_TIME
    supply_score = hashrate / 1_000_000

    # Demand: mempool congestion + economic urgency
    demand_score = (
        mempool_size * 2.0
        + pending_value * 5.0
        + pending_fees * 200.0
    )

    ratio = demand_score / max(supply_score, 1e-9)

    if ratio < 0.6:
        status = "surplus"
        suggested_fee = 0.0001
        tagline = "Compute surplus — low fees, instant settlement"
    elif ratio < 1.4:
        status = "balanced"
        suggested_fee = 0.001
        tagline = "Market equilibrium — optimal compute allocation"
    else:
        status = "constrained"
        suggested_fee = min(0.05, round(0.001 * ratio, 6))
        tagline = "High demand — prioritize with competitive fees"

    return ComputeMarketSnapshot(
        supply_score=round(supply_score, 4),
        demand_score=round(demand_score, 4),
        ratio=round(ratio, 4),
        suggested_fee=suggested_fee,
        network_hashrate_estimate=round(hashrate, 2),
        active_peers=peers,
        mempool_size=mempool_size,
        pending_value=round(pending_value, 6),
        status=status,
        tagline=tagline,
    )
