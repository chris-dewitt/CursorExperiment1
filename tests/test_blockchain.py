import pytest
from pycoin.wallet import Wallet
from pycoin.transaction import Transaction
from pycoin.block import Blockchain, MINING_REWARD


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

    # Give miner some coins first
    bc.mine_pending_transactions(miner.address)
    assert bc.get_balance(miner.address) == MINING_REWARD

    # Transfer to recipient
    tx = Transaction.create_and_sign(miner, recipient.address, 10.0)
    assert bc.add_transaction(tx)
    bc.mine_pending_transactions(miner.address)   # mine again to confirm

    assert bc.get_balance(recipient.address) == 10.0
    # Miner received reward for both blocks minus the 10 sent
    assert bc.get_balance(miner.address) == pytest.approx(MINING_REWARD * 2 - 10.0)


def test_insufficient_balance_rejected():
    bc = Blockchain()
    poor_wallet = Wallet()
    tx = Transaction.create_and_sign(poor_wallet, "rich_addr", 100.0)
    assert not bc.add_transaction(tx)


def test_chain_validity():
    bc = Blockchain()
    bc.mine_pending_transactions(MINER_ADDR)
    bc.mine_pending_transactions(MINER_ADDR)
    assert bc.is_valid_chain()


def test_tampered_chain_invalid():
    bc = Blockchain()
    bc.mine_pending_transactions(MINER_ADDR)
    # Tamper with block data
    bc.chain[1].transactions[0].amount = 999999
    assert not bc.is_valid_chain()


def test_serialise_round_trip():
    bc = Blockchain()
    bc.mine_pending_transactions(MINER_ADDR)
    bc2 = Blockchain.from_dict(bc.to_dict())
    assert bc2.is_valid_chain()
    assert len(bc2.chain) == len(bc.chain)
