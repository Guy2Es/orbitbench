# tests/test_rl_rollouts.py
"""Episodes to fine-tuning data: transcripts as chat messages, the two selections of a round, the manifest."""
import hashlib
import json

from inspect_ai import eval as inspect_eval
from inspect_ai.model import ModelOutput, get_model
from inspect_ai.tool import Tool, tool

from orbitbench.answer import render_reply
from orbitbench.families import FAMILIES
from orbitbench.harness.task import build_task
from orbitbench.rl import chat_of, train_instances
from orbitbench.rl.rollouts import episodes_from_dir, episodes_of, read_sft, select, write_sft

MODEL = "mockllm/model"


@tool
def calc() -> Tool:
    async def execute(expression: str):
        """Evaluate an arithmetic expression.

        Args:
            expression: the expression
        """
        return str(eval(expression, {"__builtins__": {}}))   # test tool, scripted inputs only
    return execute


def play(insts, outputs, tmp_path, tools=()):
    model = get_model(MODEL, custom_outputs=outputs)
    return inspect_eval(build_task(insts, "B", tools=list(tools), sandbox=None), model=model, display="none",
                        log_dir=str(tmp_path), max_samples=1)


def good(inst) -> str:
    return render_reply(FAMILIES[inst.family].reference(inst))


def wrong(inst) -> str:
    """A reply that parses but is wrong: the reference with its number moved."""
    ref = FAMILIES[inst.family].reference(inst)
    key = next(iter(ref.values))
    ref.values[key] = ref.values[key] * 1.5 + 1000
    return render_reply(ref)


def test_an_episode_carries_chat_messages_the_tools_and_whether_the_reply_parses(tmp_path):
    inst = train_instances(1)[0]
    outputs = [ModelOutput.for_tool_call(MODEL, "calc", {"expression": "1+1"}), ModelOutput.from_content(MODEL, good(inst))]
    [log] = play([inst], outputs, tmp_path, tools=[calc()])
    [ep] = episodes_of(log, "B")
    roles = [m["role"] for m in ep["messages"]]
    assert roles == ["system", "user", "assistant", "tool", "assistant"]
    assert ep["messages"][2]["tool_calls"][0]["function"] == {"name": "calc", "arguments": {"expression": "1+1"}}
    assert ep["messages"][3]["content"] == "2" and ep["messages"][3]["name"] == "calc"
    assert ep["messages"][:2] == chat_of(inst, "B")[:2]          # the system message and statement of the benchmark
    assert [t["function"]["name"] for t in ep["tools"]] == ["calc"]
    assert ep["format_ok"] is True and ep["reward"] == 1.0 and ep["id"] == f"{inst.family}:{inst.mode}:{inst.seed}"


def test_the_selection_pairs_the_arms_on_size_caps_two_per_instance_and_keeps_the_shortest(tmp_path):
    insts = train_instances(4)
    # instance 0: three good replies (two are kept); instance 1: one good and one wrong; 2: wrong; 3: no block at all
    replies = [good(insts[0])] * 3 + [good(insts[1]), wrong(insts[1])] + [wrong(insts[2])] + ["no block"]
    fake = []
    for n, (inst, reply) in enumerate(zip([insts[0]] * 3 + [insts[1]] * 2 + [insts[2], insts[3]], replies)):
        fake.append({"id": f"{inst.family}:{inst.mode}:{inst.seed}", "epoch": n, "reward": 1.0 if reply == good(inst) else 0.0,
                     "format_ok": reply.startswith("<final_answer>"), "output_tokens": 100 - n, "messages": [], "tools": []})
    chosen = select(fake, seed=0)
    rewarded, parsing = chosen["reward"], chosen["format"]
    assert [e["epoch"] for e in rewarded] == [2, 1, 3]            # shortest two of instance 0, then instance 1's one
    assert len(parsing) == len(rewarded) == 3                       # same size
    assert all(e["format_ok"] for e in parsing)
    assert 6 not in {e["epoch"] for e in parsing}                   # the reply without a block is never kept
    assert select(fake, seed=0) == chosen                           # deterministic


def test_the_format_arm_never_exceeds_two_per_instance():
    fake = [{"id": "a:values:1", "epoch": n, "reward": 1.0, "format_ok": True, "output_tokens": n, "messages": [], "tools": []}
            for n in range(5)] + [{"id": "b:values:1", "epoch": 0, "reward": 0.0, "format_ok": True, "output_tokens": 1,
                                   "messages": [], "tools": []}]
    chosen = select(fake)
    assert len(chosen["reward"]) == 2 and len(chosen["format"]) == 2


def test_write_sft_hashes_the_file_and_the_rounds_can_be_added(tmp_path):
    rows = [{"id": "a:values:1", "epoch": 0, "reward": 1.0, "output_tokens": 7,
             "messages": [{"role": "user", "content": "x"}], "tools": []}]
    manifest = write_sft(rows, tmp_path / "r0.jsonl", arm="reward", round_=0, train_seed=1)
    assert manifest["sha256"] == hashlib.sha256((tmp_path / "r0.jsonl").read_bytes()).hexdigest()
    assert (manifest["examples"], manifest["instances"], manifest["arm"]) == (1, 1, "reward")
    assert json.loads((tmp_path / "r0.jsonl.manifest.json").read_text(encoding="utf-8")) == manifest
    both = read_sft(tmp_path / "r0.jsonl") + read_sft(tmp_path / "r0.jsonl")
    assert write_sft(both, tmp_path / "r01.jsonl", arm="reward", round_=1, train_seed=1)["examples"] == 2


def test_episodes_are_read_back_from_a_run_folder(tmp_path):
    insts = train_instances(2)
    play(insts, [ModelOutput.from_content(MODEL, good(i)) for i in insts], tmp_path)
    eps = episodes_from_dir(tmp_path, "B")
    assert len(eps) == 2 and all(e["format_ok"] and e["reward"] == 1.0 for e in eps)


def test_the_format_set_can_be_sized_by_the_other_arm():
    fake = [{"id": f"a:values:{n}", "epoch": 0, "reward": 0.0, "format_ok": True, "output_tokens": 1, "messages": [], "tools": []}
            for n in range(10)]
    assert len(select(fake, count=4)["format"]) == 4 and len(select(fake, count=40)["format"]) == 10


def test_long_transcripts_are_in_neither_set_and_are_removed_before_the_sizes_are_matched():
    def ep(n, tokens, reward):
        return {"id": f"a:values:{n}", "epoch": 0, "reward": reward, "format_ok": True, "output_tokens": 1,
                "context_tokens": tokens, "messages": [], "tools": []}
    fake = [ep(0, 9000, 1.0), ep(1, 500, 1.0), ep(2, 9000, 0.0), ep(3, 600, 0.0), ep(4, None, 0.0)]
    chosen = select(fake, max_tokens=8192)
    assert [e["id"] for e in chosen["reward"]] == ["a:values:1"]            # the long rewarded reply is not kept
    assert len(chosen["format"]) == 1 and all((e["context_tokens"] or 0) <= 8192 for e in chosen["format"])
    assert len(select(fake)["reward"]) == 2                                 # without the limit nothing is removed
    kept = select(fake, count=10, max_tokens=8192)["format"]
    assert {e["id"] for e in kept} == {"a:values:1", "a:values:3", "a:values:4"}     # an unknown length is not too long


def test_an_episode_says_how_long_its_transcript_is(tmp_path):
    inst = train_instances(1)[0]
    [log] = play([inst], [ModelOutput.from_content(MODEL, good(inst))], tmp_path)
    [ep] = episodes_of(log, "B")
    assert "context_tokens" in ep and "prompt_tokens" in ep
    manifest_rows = read_sft(tmp_path / "x.jsonl") if write_sft([ep], tmp_path / "x.jsonl", arm="reward", round_=0, train_seed=0) else []
    assert "context_tokens" in manifest_rows[0]


def test_tools_are_taken_as_sent_with_their_attachments_put_back():
    from types import SimpleNamespace as NS

    from orbitbench.rl.rollouts import sent_tools
    sent = [{"type": "function", "function": {"name": "python", "description": "attachment://abc", "strict": True,
                                              "parameters": {"type": "object", "properties": {"code": {"type": "string"}}}}}]
    sample = NS(attachments={"abc": "Use the python function to execute code."})
    out = sent_tools(sample, NS(call=NS(request={"tools": sent}), tools=[]))
    assert out[0]["function"]["description"] == "Use the python function to execute code."
    assert out[0]["function"]["strict"] is True                          # as the server received it
    assert sent[0]["function"]["description"] == "attachment://abc"      # the log's own data is not modified
    import pytest
    with pytest.raises(ValueError):
        sent_tools(NS(attachments={}), NS(call=NS(request={"tools": sent}), tools=[]))     # an unknown reference is refused
