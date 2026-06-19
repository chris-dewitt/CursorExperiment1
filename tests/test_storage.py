from pycoin.block import Blockchain
from pycoin.storage import save_chain, load_chain


MINER = "miner123"


def test_save_and_load(tmp_path):
    bc = Blockchain()
    bc.mine_pending_transactions(MINER)
    bc.mine_pending_transactions(MINER)

    path = str(tmp_path / "chain.json")
    save_chain(bc, path)

    bc2 = load_chain(path)
    assert bc2 is not None
    assert bc2.is_valid_chain()
    assert len(bc2.chain) == len(bc.chain)
    assert bc2.chain[-1].hash == bc.chain[-1].hash


def test_load_missing_file(tmp_path):
    result = load_chain(str(tmp_path / "nonexistent.json"))
    assert result is None


def test_load_corrupt_file(tmp_path):
    path = str(tmp_path / "bad.json")
    with open(path, "w") as f:
        f.write("not json at all {{{{")
    result = load_chain(path)
    assert result is None
