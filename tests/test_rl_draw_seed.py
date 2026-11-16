# tests/test_rl_draw_seed.py
"""The draw of the private test range of the RL study: where it may fall, and its commitment."""
import importlib.util
from pathlib import Path

from orbitbench.rl import TRAIN_FIRST_SEED

spec = importlib.util.spec_from_file_location("rl_draw_seed", Path(__file__).resolve().parents[1] / "scripts" / "rl_draw_seed.py")
ds = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ds)


def test_the_range_stays_below_the_training_seeds_and_away_from_development_and_spent_seeds():
    assert ds.HIGH + 20 < TRAIN_FIRST_SEED and ds.LOW > 9
    assert not ds.allowed(5) and not ds.allowed(TRAIN_FIRST_SEED)
    for spent in ds.SPENT:
        assert not ds.allowed(spent) and not ds.allowed(spent + 999) and not ds.allowed(spent - 999)
        assert ds.allowed(spent + 1000)


def test_a_draw_that_falls_on_a_spent_range_is_drawn_again():
    values = iter([ds.SPENT[0] - ds.LOW, 12_345])       # the first lands on the v0.1 seed, the second is free
    assert ds.draw(lambda n: next(values)) == ds.LOW + 12_345


def test_the_commitment_depends_on_the_seed_and_on_the_salt_and_hides_nothing_else():
    c = ds.commitment(123_456, "ab")
    assert c == ds.commitment(123_456, "ab") and len(c) == 64
    assert c != ds.commitment(123_457, "ab") and c != ds.commitment(123_456, "ac")


def test_the_env_reader_ignores_comments_and_quotes():
    assert ds.read_env('# a=1\nA = "x"\nB=2\n\nnot a pair') == {"A": "x", "B": "2"}
