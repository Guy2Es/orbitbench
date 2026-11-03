# tests/test_estimate_cost.py
"""The cost estimator: prices, the batch discount, the fallback to a model's mean, and the plan it multiplies."""
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("estimate_cost", Path(__file__).resolve().parents[1] / "scripts" / "estimate_cost.py")
est = importlib.util.module_from_spec(spec)
spec.loader.exec_module(est)


def row(model="anthropic/claude-haiku-5-5", condition="B", family="hohmann", mode="values", **tokens):
    base = dict(input_tokens=0, cache_write_tokens=0, cache_read_tokens=0, output_tokens=0)
    return {"model": model, "condition": condition, "family": family, "mode": mode, **base, **tokens}


def test_the_model_is_read_from_its_name():
    assert est.family_of("anthropic/claude-sonnet-5-5") == "sonnet" and est.family_of("claude-opus-5-5") == "opus"
    with pytest.raises(ValueError):
        est.family_of("gpt-5")


def test_a_million_tokens_cost_the_listed_price():
    assert est.usd(row(input_tokens=1_000_000), "haiku") == pytest.approx(0.10)
    assert est.usd(row(output_tokens=1_000_000), "sonnet") == pytest.approx(10.0)
    assert est.usd(row(cache_read_tokens=1_000_000, cache_write_tokens=1_000_000), "opus") == pytest.approx(5.20)


def test_batch_halves_the_total_and_k_multiplies_it():
    rows = [row(condition=c, output_tokens=1_000_000) for c in ("B", "C")]
    _, full, _ = est.estimate(rows, ["haiku"], 1, 1.0, False, 1.0)
    _, batch, margin = est.estimate(rows, ["haiku"], 1, 1.0, True, 1.3)
    _, triple, _ = est.estimate(rows, ["haiku"], 3, 1.0, False, 1.0)
    assert batch == pytest.approx(full / 2) and margin == pytest.approx(batch * 1.3) and triple == pytest.approx(3 * full)


def test_a_line_without_a_sample_is_priced_from_the_models_mean():
    [(_, episodes, spent, fallback)], _, _ = est.estimate([row(output_tokens=2_000_000)], ["haiku"], 1, 1.0, False, 1.0)
    assert fallback > 0 and episodes > 0 and spent == pytest.approx(1.0 * episodes)


def test_a_model_without_sample_is_left_out():
    [(_, episodes, spent, _)], total, _ = est.estimate([row()], ["sonnet"], 3, 1.0, True, 1.3)
    assert (episodes, spent, total) == (0, 0.0, 0.0)
