from enigma.block import Blockchain
from enigma.compute import compute_market_snapshot


def test_compute_market_snapshot():
    bc = Blockchain()
    market = compute_market_snapshot(bc, peer_count=2)
    assert market.status in ("surplus", "balanced", "constrained")
    assert market.ratio >= 0
    assert market.suggested_fee > 0
    assert market.active_peers == 2


def test_compute_market_demand_increases_with_mempool():
    bc = Blockchain()
    baseline = compute_market_snapshot(bc).demand_score

    from enigma.wallet import Wallet
    from enigma.transaction import Transaction

    miner = Wallet()
    bc.mine_pending_transactions(miner.address)
    tx = Transaction.create_and_sign(miner, "recipient_addr", 1.0, fee=0.01)
    bc.add_transaction(tx)

    congested = compute_market_snapshot(bc)
    assert congested.demand_score > baseline
    assert congested.mempool_size == 1
