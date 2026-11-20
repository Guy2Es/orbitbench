# tests/test_rl_round.py
"""The phase-0 rule of the RL study, fixed before any run: eligibility, the choice, the 90 s switch to smaller blocks."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("rl_round", Path(__file__).resolve().parents[1] / "scripts" / "rl_round.py")
rr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rr)


def ep(family, solved=0.0, tools=1, seconds=30.0, content="ok", tokens=500):
    return {"family": family, "solved": solved, "tool_calls": tools, "total_time_s": seconds, "output_tokens": tokens,
            "messages": [{"role": "assistant", "content": content}]}


def good_episodes(**kw):
    """Six episodes, solved in the four number families."""
    return [ep(f, 1.0, **kw) for f in rr.NUMBER_FAMILIES] + [ep("hohmann", **kw), ep("trap_isp", **kw)]


def test_a_candidate_is_eligible_only_if_all_four_conditions_hold():
    assert rr.phase0_row("a", good_episodes(), True)["eligible"]
    assert not rr.phase0_row("a", good_episodes(), False)["eligible"]                       # fine-tune or export failed
    assert not rr.phase0_row("a", good_episodes(tools=0), True)["eligible"]                 # never calls a tool
    assert not rr.phase0_row("a", good_episodes(content="<think>hmm</think>"), True)["eligible"]
    two = [ep(f, 1.0) for f in rr.NUMBER_FAMILIES[:2]] + [ep(f) for f in rr.NUMBER_FAMILIES[2:]]
    assert not rr.phase0_row("a", two, True)["eligible"]                                    # solved in 2 families only


def test_the_choice_is_the_most_solved_per_gpu_hour_among_the_eligible_else_the_default():
    slow = rr.phase0_row("slow", good_episodes(seconds=120.0), True)
    fast = rr.phase0_row("fast", good_episodes(seconds=30.0), True)
    ineligible = rr.phase0_row("best", [ep(f, 1.0, tools=0, seconds=1.0) for f in rr.NUMBER_FAMILIES], True)
    assert rr.choose([slow, fast, ineligible]) == "fast"
    assert rr.choose([ineligible], default="qwen3-4b") == "qwen3-4b"


def test_the_table_says_when_blocks_shrink_to_96_instances():
    text = rr.render_bakeoff([rr.phase0_row("slow", good_episodes(seconds=120.0), True)])
    assert "choice by the rule: slow" in text and "96 instances" in text
    assert "96 instances" not in rr.render_bakeoff([rr.phase0_row("fast", good_episodes(seconds=30.0), True)])
    assert "no candidate eligible" in rr.render_bakeoff([rr.phase0_row("x", good_episodes(), False)])


def test_the_server_picks_the_model_name_the_parallelism_and_the_evaluation_stays_home():
    from types import SimpleNamespace as NS
    assert rr.model_name("ollama", "q") == "ollama/q" and rr.model_name("vllm", "q") == "vllm/q"
    assert rr.samples_of(NS(server="ollama", max_samples=None)) == 1 and rr.samples_of(NS(server="vllm", max_samples=None)) == 8
    assert rr.samples_of(NS(server="vllm", max_samples=3)) == 3
    import pytest
    with pytest.raises(SystemExit):
        rr.cmd_evaluate(NS(server="vllm", sandbox="local", condition="B", arm="x", tag="t", epochs=3, max_samples=None))


def test_the_evaluation_parts_split_the_138_instances_into_40_and_98_without_overlap(monkeypatch, tmp_path):
    from types import SimpleNamespace as NS
    from orbitbench.harness.catalog import RL_LINES, instances
    held = instances([ln for ln in RL_LINES if ln[0] in rr.HELD_OUT_FAMILIES])
    rest = instances([ln for ln in RL_LINES if ln[0] in rr.REST_FAMILIES])
    assert len(held) == 40 and len(rest) == 98 and len(instances(RL_LINES)) == 138
    assert not {i.family for i in held} & {i.family for i in rest}
    calls = []
    monkeypatch.setattr(rr, "RL", tmp_path)
    monkeypatch.setattr(rr, "private_first_seed", lambda: 7)
    monkeypatch.setattr(rr, "harness", lambda cmd: calls.append(cmd) or 0)
    base = dict(server="ollama", sandbox="docker", condition="B", arm="x", tag="t", epochs=3, max_samples=None)
    rr.cmd_evaluate(NS(**base, part="held"))
    rr.cmd_evaluate(NS(**base, part="rest"))
    rr.cmd_evaluate(NS(**base))                                                    # no part: the whole suite, as before
    assert calls[0][calls[0].index("--families") + 1:calls[0].index("--families") + 3] == list(rr.HELD_OUT_FAMILIES)
    assert calls[0][-1].endswith("eval-x-held") and calls[1][-1].endswith("eval-x-rest") and calls[2][-1].endswith("eval-x")
    assert "--families" in calls[1] and "--families" not in calls[2]


def test_on_colab_the_block_size_follows_the_units_and_not_the_90_s_rule():
    slow = rr.phase0_row("q", good_episodes(seconds=120.0), True)       # 6 episodes of 120 s, played 8 at a time
    est = rr.block_estimate(slow, parallel=8, units_per_hour=1.5)
    assert abs(est["block_hours"] - 2.4) < 1e-9 and abs(est["units"] - 32.4) < 1e-9     # 576 episodes; 9 blocks
    text = rr.render_bakeoff([slow], parallel=8, units_per_hour=1.5)
    assert "96 instances" not in text and "about 32 Colab units" in text and "blocks of 144 instances" in text
    assert "blocks of 96 instances" in rr.render_bakeoff([slow], parallel=8, units_per_hour=10.0)      # 216 units > 150
    assert "Colab units" not in rr.render_bakeoff([slow], parallel=8)                                  # no rate, no units


def test_a_real_arm_cannot_be_played_from_another_seed():
    from types import SimpleNamespace as NS
    import pytest
    with pytest.raises(SystemExit):
        rr.cmd_play(NS(first_seed=1_950_000, arm="base", train_seed=0, round=0, redraw=0, block_n=2))


def _round0(monkeypatch, tmp_path, blocks, rewarded_per_block):
    """A round 0 whose blocks `blocks` exist, each holding `rewarded_per_block` rewarded replies of distinct instances."""
    from types import SimpleNamespace as NS
    monkeypatch.setattr(rr, "RL", tmp_path)
    for d in blocks:
        rr.block_dir("base", 0, 0, d).mkdir(parents=True)

    def episodes(folder, condition):
        d = int(folder.name.split("-d")[1][0])
        return [{"id": f"hohmann:values:{d * 1000 + i}", "epoch": 1, "reward": 1.0, "format_ok": True, "output_tokens": 100,
                 "context_tokens": 500, "messages": [], "tools": []} for i in range(rewarded_per_block)]

    monkeypatch.setattr(rr, "episodes_from_dir", episodes)
    return NS(train_seed=0, round=0, base_arm="base", only=None, count=None)


def test_round_zero_asks_for_another_block_until_48_replies_are_rewarded(monkeypatch, tmp_path):
    assert rr.cmd_select(_round0(monkeypatch, tmp_path, [0], 8)) == 3                # 8 < 48 and 7 blocks left
    assert rr.cmd_select(_round0(monkeypatch, tmp_path / "b", [0, 1, 2], 16)) == 0   # 48 replies in 3 blocks, pooled


def test_round_zero_stops_asking_after_the_last_block(monkeypatch, tmp_path, capsys):
    a = _round0(monkeypatch, tmp_path, list(range(rr.MAX_BLOCKS_R0)), 1)
    assert rr.cmd_select(a) == 0
    assert "after the 8 blocks allowed" in capsys.readouterr().out
