# tests/test_rl.py
"""The RL helpers: the training mix, the seeds kept apart, the reward equal to the grader's, the benchmark prompt."""
import collections

import pytest

from orbitbench.answer import render_reply
from orbitbench.families import FAMILIES
from orbitbench.harness.prompt import system_prompt
from orbitbench.rl import (TRAIN_FIRST_SEED, TRAIN_SCHEDULE, chat_of, format_ok, harness_system_message, reward_of,
                           train_instances)


def test_the_mix_follows_the_schedule_and_keeps_the_traps_a_fixed_share():
    inst = train_instances(36)
    assert collections.Counter(i.family for i in inst)["tsiolkovsky"] == 6
    assert sum(not i.well_posed for i in inst) == 6      # 3 traps per cycle of 18
    assert sum(i.family.endswith("_twin") for i in inst) == 6


def test_instances_are_deterministic_and_seeds_start_apart_from_dev_and_test():
    assert train_instances(20) == train_instances(20)
    assert min(i.seed for i in train_instances(20)) == TRAIN_FIRST_SEED
    with pytest.raises(ValueError):
        train_instances(5, first_seed=9)


def test_the_training_statements_are_not_the_development_ones():
    dev = {FAMILIES[f].generate(s, m).statement for f, m in set(TRAIN_SCHEDULE) for s in range(10)}
    assert not dev & {i.statement for i in train_instances(36)}


def test_the_reference_answer_earns_the_full_reward():
    for inst in train_instances(36):
        assert reward_of(inst, render_reply(FAMILIES[inst.family].reference(inst))) == 1.0


def test_a_trap_pays_only_for_ill_posed():
    trap = next(i for i in train_instances(18) if not i.well_posed)
    value = render_reply(FAMILIES["hohmann"].reference(next(i for i in train_instances(18) if i.family == "hohmann")))
    assert reward_of(trap, value) == 0.0
    assert reward_of(trap, '<final_answer>{"schema_version": "1.0", "status": "ill_posed", "reason": "x"}</final_answer>') == 1.0


def test_a_reply_without_the_schema_version_earns_nothing_and_is_not_a_valid_format():
    inst = next(i for i in train_instances(18) if i.family == "hohmann")
    key = next(iter(inst.tolerances))
    bad = f'<final_answer>{{"status": "solved", "values": {{"{key}": 1.0}}}}</final_answer>'
    assert reward_of(inst, bad) == 0.0 and not format_ok(bad)
    assert format_ok('<final_answer>{"schema_version": "1.0", "status": "ill_posed", "reason": "x"}</final_answer>')
    assert not format_ok("no block at all")


def test_the_instances_are_all_distinct_and_a_trap_shares_its_seed_with_its_twin():
    inst = train_instances(54)
    assert len({(i.family, i.seed) for i in inst}) == 54
    assert len({f"{i.family}:{i.mode}:{i.seed}" for i in inst}) == 54      # Inspect needs unique sample ids
    for cycle in range(3):
        block = {i.family: i.seed for i in inst[18 * cycle:18 * cycle + 18]}
        for kind in ("radius", "isp", "period"):
            assert block[f"trap_{kind}"] == block[f"trap_{kind}_twin"]


def test_the_chat_is_the_system_message_the_harness_really_sends():
    inst = train_instances(1)[0]
    chat = chat_of(inst, "B")
    assert chat[1]["content"] == inst.statement
    assert chat[0]["content"].startswith(system_prompt("B"))             # prompt.py text first
    assert "Do some reasoning before your actions" in chat[0]["content"]  # then Inspect's default paragraph
    assert chat[0]["content"] == harness_system_message("B")


def test_chat_of_equals_the_system_message_of_a_real_mockllm_run():
    from inspect_ai import eval
    from inspect_ai.model import get_model

    from orbitbench.harness.task import build_task
    inst = train_instances(1)[0]
    log = eval(build_task([inst], "A", sandbox=None), model=get_model("mockllm/model"), display="none")[0]
    first = log.samples[0].messages[0]
    assert first.role == "system" and first.text == chat_of(inst, "A")[0]["content"]


def test_the_blocks_of_the_loop_never_overlap_and_stay_below_phase_zero():
    from orbitbench.rl.data import PHASE0_FIRST_SEED, block_first_seed
    seen = set()
    for t in range(3):
        for r in (0, 1):
            for d in (0, 1):
                block = {(i.family, i.seed) for i in train_instances(144, block_first_seed(t, r, d))}
                assert len(block) == 144 and not block & seen
                seen |= block
    assert max(s for _, s in seen) < PHASE0_FIRST_SEED
    with pytest.raises(ValueError):
        block_first_seed(3, 0)
