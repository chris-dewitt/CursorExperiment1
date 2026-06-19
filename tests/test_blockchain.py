import pytest
from pycoin.wallet import Wallet
from pycoin.transaction import Transaction
from pycoin.block import Blockchain, MINING_REWARD, get_block_reward


MINER_ADDR = "miner_address_123"


def test_genesis_block_exists():
    bc = Blockchain()
    assert len(bc.chain) == 1
    assert bc.chain[0].index == 0
    assert bc.is_valid_chain()


def test_mine_block_earns_reward():
    bc = Blockchain()
    bc.mine_pending_transactions(MINER_ADDR)
    assert bc.get_balance(MINER_ADDR) == MINING_REWARD


def test_transfer_coins():
    bc = Blockchain()
    miner = Wallet()
    recipient = Wallet()

    bc.mine_pending_transactions(miner.address)
    assert bc.get_balance(miner.address) == MINING_REWARD

    tx = Transaction.create_and_sign(miner, recipient.address, 10.0)
    assert bc.add_transaction(tx)
    bc.mine_pending_transactions(miner.address)

    assert bc.get_balance(recipient.address) == 10.0
    assert bc.get_balance(miner.address) == pytest.approx(MINING_REWARD * 2 - 10.0)


def test_transfer_with_fee():
    bc = Blockchain()
    miner = Wallet()
    recipient = Wallet()

    bc.mine_pending_transactions(miner.address)

    tx = Transaction.create_and_sign(miner, recipient.address, 10.0, fee=0.5)
    assert bc.add_transaction(tx)
    block = bc.mine_pending_transactions(miner.address)

    # Miner reward = block_reward + fee
    assert bc.get_balance(recipient.address) == pytest.approx(10.0)
    coinbase = block.transactions[0]
    assert coinbase.amount == pytest.approx(MINING_REWARD + 0.5)


def test_insufficient_balance_rejected():
    bc = Blockchain()
    poor_wallet = Wallet()
    tx = Transaction.create_and_sign(poor_wallet, "rich_addr", 100.0)
    assert not bc.add_transaction(tx)


def test_insufficient_balance_including_fee():
    bc = Blockchain()
    miner = Wallet()
    bc.mine_pending_transactions(miner.address)
    # Try to send more than balance when fee is included
    tx = Transaction.create_and_sign(miner, "addr", MINING_REWARD, fee=0.001)
    assert not bc.add_transaction(tx)


def test_chain_validity():
    bc = Blockchain()
    bc.mine_pending_transactions(MINER_ADDR)
    bc.mine_pending_transactions(MINER_ADDR)
    assert bc.is_valid_chain()


def test_tampered_chain_invalid():
    bc = Blockchain()
    bc.mine_pending_transactions(MINER_ADDR)
    bc.chain[1].transactions[0].amount = 999999
    assert not bc.is_valid_chain()


def test_serialise_round_trip():
    bc = Blockchain()
    bc.mine_pending_transactions(MINER_ADDR)
    bc2 = Blockchain.from_dict(bc.to_dict())
    assert bc2.is_valid_chain()
    assert len(bc2.chain) == len(bc.chain)


def test_halving_schedule():
    assert get_block_reward(0) == 50.0
    assert get_block_reward(209_999) == 50.0
    assert get_block_reward(210_000) == 25.0
    assert get_block_reward(420_000) == 12.5
    assert get_block_reward(210_000 * 64) == 0.0


def test_total_supply_cap():
    # Sum of all block rewards converges to 21M
    total = sum(get_block_reward(i * 210_000) * 210_000 for i in range(64))
    assert abs(total - 21_000_000) < 1e-3


def test_total_mined():
    bc = Blockchain()
    assert bc.total_mined == 0.0
    bc.mine_pending_transactions(MINER_ADDR)
    assert bc.total_mined == pytest.approx(MINING_REWARD)


def test_lookup_helpers():
    bc = Blockchain()
    block = bc.mine_pending_transactions(MINER_ADDR)
    assert bc.get_block_by_hash(block.hash) is block
    assert bc.get_block_by_height(1) is block
    tx = block.transactions[0]
    found_tx, found_block = bc.get_transaction(tx.tx_id())
    assert found_tx is tx
    assert found_block is block
