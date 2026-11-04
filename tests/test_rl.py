# tests/test_rl.py
"""The RL helpers: the training mix, the seeds kept apart, the reward equal to the grader's, the benchmark prompt."""
import collections

import pytest

from orbitbench.answer import render_reply
from orbitbench.families import FAMILIES
from orbitbench.harness.prompt import system_prompt
from orbitbench.rl import TRAIN_FIRST_SEED, TRAIN_SCHEDULE, chat_of, format_ok, reward_of, train_instances


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


def test_the_chat_is_the_benchmark_prompt_unchanged():
    inst = train_instances(1)[0]
    chat = chat_of(inst, "A")
    assert chat[0] == {"role": "system", "content": system_prompt("A")} and chat[1]["content"] == inst.statement
