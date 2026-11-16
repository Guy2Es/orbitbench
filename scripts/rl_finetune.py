# scripts/rl_finetune.py
"""The Colab side of the RL study: LoRA fine-tune from the base model on a file written by scripts/rl_round.py, merge, export to
GGUF Q4_K_M, hashes. Standalone: it imports nothing from orbitbench, only the SFT jsonl (messages, tools, prompt_tokens).

NOT RUN by its author: written from the Unsloth notebook Qwen3_(4B)-Instruct.ipynb (unslothai/notebooks) and the Unsloth Qwen3
guide, read on 15 Nov 2026. Three things those sources do not confirm are handled here by explicit choices and a check:
  * fp16 on a T4: fp16/bf16 are set from `is_bfloat16_supported()`.
  * the instruction and response strings of `train_on_responses_only`: the ChatML prefixes of Qwen3 are passed explicitly.
  * how the chat template renders tool calls: `check` renders the first prompt and compares its token count with the one Ollama
    recorded in the log. Run it before any training; if the counts differ, serve through `llama-server --jinja` instead.

Colab (T4 runtime), with the Drive folder of scripts/rl_colab.py; BASE is the local copy of arm 0 (/content/models/qwen3-4b):
  !python rl_finetune.py export-base --out models/qwen3-4b           # arm 0: the original weights, byte for byte
  !python rl_finetune.py check  --model BASE --data sft/t0-r0-reward.jsonl
  !python rl_finetune.py train  --model BASE --data sft/t0-r01-reward.jsonl --out models/t0-reward --seed 0
Give `--model BASE` to `check` and `train`: the fine-tune then starts from the very files of arm 0 (their hashes go in the
manifest), with the tokenizer and chat template the server used. `train` does nothing if its output already has a manifest
(`--force` to redo it), so a cell can be relaunched.
`train` loads the base in 16 bits (not 4-bit QLoRA), so that the merged model is exactly base + adapter and arm 0 is the
untouched base; if the GPU runs out of memory, `--load-4bit` trains a QLoRA instead, and the arms then differ from the base by
the 4-bit rounding: say so in the results. The merged 16-bit model (out/merged) is what vLLM serves on Colab. The GGUF is made at
home by scripts/rl_gguf.py (the same path for every model, arm 0 included); `--gguf` makes it here instead, and
`--adapter-only` skips the merge (RAM fallback: convert the adapter with llama.cpp's convert_lora_to_gguf.py).
Fixed by the protocol, not tuned on results: LoRA r = 16, learning rate 2e-4, 3 epochs, loss on assistant turns only."""
import argparse
import hashlib
import json
import random
import shutil
from pathlib import Path

BASE_MODEL = "unsloth/Qwen3-4B-Instruct-2507"      # change with the model chosen by phase 0 (rl_plan.md); keep everything else
MAX_SEQ = 8192                                     # examples longer than this are dropped and counted (T4 memory)
LORA_R, LR, EPOCHS = 16, 2e-4, 3
# Qwen ChatML: tool results are rendered inside a user turn, so they are masked with the user turns.
INSTRUCTION_PART, RESPONSE_PART = "<|im_start|>user\n", "<|im_start|>assistant\n"


def read_rows(path) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line]


def sha256_of(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def render(tokenizer, row: dict, *, generation_prompt: bool, upto: int | None = None) -> str:
    """The text of a transcript through the model's own chat template, tools included. `upto`: only the first messages."""
    messages = row["messages"][:upto]
    return tokenizer.apply_chat_template(messages, tools=row["tools"] or None, tokenize=False,
                                         add_generation_prompt=generation_prompt)


def load_model(name: str, four_bit: bool = False):
    from unsloth import FastLanguageModel
    return FastLanguageModel.from_pretrained(model_name=name, max_seq_length=MAX_SEQ, load_in_4bit=four_bit)


def cmd_check(a) -> int:
    """The first prompt (system message, tools, statement) must have the token count the server recorded in the log."""
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(a.model)
    rows = [r for r in read_rows(a.data) if r.get("prompt_tokens")][: a.n]
    if not rows:
        raise SystemExit("no row with a recorded prompt_tokens")
    bad = 0
    for r in rows:
        mine = len(tok(render(tok, r, generation_prompt=True, upto=2), add_special_tokens=False)["input_ids"])
        print(f"{r['id']}: log {r['prompt_tokens']}, rendered here {mine}" + ("" if mine == r["prompt_tokens"] else "   DIFFERENT"))
        bad += mine != r["prompt_tokens"]
    print("OK: the render matches the log" if not bad else
          f"{bad} of {len(rows)} differ: do not train yet. Ollama renders tools with its own template; serve through "
          "llama-server --jinja, or fix the template, and replay the rollouts if the prompts differ.")
    return 1 if bad else 0


def already_done(out, force: bool = False) -> bool:
    """True if a fine-tune already wrote its manifest there (the last file written), and it is not asked again."""
    return (Path(out) / "manifest.json").exists() and not force


def cmd_train(a) -> int:
    if already_done(a.out, a.force):
        print(f"{a.out} already holds a finished fine-tune (manifest.json): nothing to do. --force to train it again.")
        return 0
    from unsloth import FastLanguageModel, is_bfloat16_supported
    from unsloth.chat_templates import train_on_responses_only
    from datasets import Dataset
    from trl import SFTConfig, SFTTrainer

    model, tokenizer = load_model(a.model, a.load_4bit)
    rows = read_rows(a.data)
    texts = [render(tokenizer, r, generation_prompt=False) for r in rows]
    kept = [t for t in texts if len(tokenizer(t, add_special_tokens=False)["input_ids"]) <= MAX_SEQ]
    print(f"{len(rows)} examples, {len(rows) - len(kept)} dropped for exceeding {MAX_SEQ} tokens")
    if len(kept) < len(rows):
        print("WARNING: the selection already removes long transcripts, so nothing should be dropped here. The two arms may "
              "no longer have the same number of examples: write the two counts in the results.")
    if not kept:
        raise SystemExit("nothing left to train on")
    random.Random(a.seed).shuffle(kept)
    model = FastLanguageModel.get_peft_model(
        model, r=LORA_R, lora_alpha=LORA_R, lora_dropout=0, bias="none", use_gradient_checkpointing="unsloth",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"], random_state=a.seed)
    bf16 = is_bfloat16_supported()
    trainer = SFTTrainer(
        model=model, tokenizer=tokenizer, train_dataset=Dataset.from_dict({"text": kept}),
        args=SFTConfig(dataset_text_field="text", max_seq_length=MAX_SEQ, per_device_train_batch_size=1,
                       gradient_accumulation_steps=8, warmup_steps=5, num_train_epochs=EPOCHS, learning_rate=LR,
                       logging_steps=1, optim="adamw_8bit", weight_decay=0.001, lr_scheduler_type="linear", seed=a.seed,
                       fp16=not bf16, bf16=bf16, report_to="none", save_strategy="no",
                       output_dir=str(Path(a.out) / "trainer")))
    trainer = train_on_responses_only(trainer, instruction_part=INSTRUCTION_PART, response_part=RESPONSE_PART)
    sample = trainer.train_dataset[0]
    shown = tokenizer.decode([t for t, l in zip(sample["input_ids"], sample["labels"]) if l != -100])
    print("first example, the tokens that carry loss (must be assistant turns only):\n" + shown[:1500])
    trainer.train()
    out = Path(a.out)
    model.save_pretrained(str(out / "adapter"))
    tokenizer.save_pretrained(str(out / "adapter"))
    if not a.adapter_only:
        model.save_pretrained_merged(str(out / "merged"), tokenizer, save_method="merged_16bit")
        keep_sampling_settings(a.model, out / "merged")
        if a.gguf:
            export(model, tokenizer, out)
    write_manifest(out, a, len(kept))
    return 0


def keep_sampling_settings(base, merged: Path) -> bool:
    """A server reads its default sampling settings in generation_config.json. If the merge did not write the file and the
    base is a local folder that has it, copy it, so that every model of the study is sampled the same way."""
    src, dst = Path(base) / "generation_config.json", Path(merged) / "generation_config.json"
    if dst.exists() or not src.exists():
        return False
    shutil.copyfile(src, dst)
    return True


def base_hashes(base) -> dict:
    """SHA-256 of the weight files of a base given as a local folder (the files of arm 0); empty for a hub name."""
    folder = Path(base)
    return {p.name: sha256_of(p) for p in sorted(folder.glob("*.safetensors"))} if folder.is_dir() else {}


def export(model, tokenizer, out: Path) -> None:
    """Write a Q4_K_M GGUF of the merged model (Unsloth's merge and llama.cpp conversion); optional on Colab."""
    model.save_pretrained_gguf(str(out / "gguf"), tokenizer, quantization_method="q4_k_m")


def write_manifest(out: Path, a, examples: int) -> None:
    files = {str(p.relative_to(out)): sha256_of(p) for p in sorted(out.rglob("*"))
             if p.is_file() and p.suffix in (".gguf", ".safetensors")}
    base = getattr(a, "model", None) or getattr(a, "hf_repo", None)
    meta = {"base_model": base, "base_files": base_hashes(base) if getattr(a, "model", None) else {},
            "hf_revision": getattr(a, "hf_revision", None),
            "data": Path(a.data).name if getattr(a, "data", None) else None,
            "data_sha256": sha256_of(a.data) if getattr(a, "data", None) else None, "examples": examples,
            "seed": getattr(a, "seed", None), "lora_r": LORA_R, "lr": LR, "epochs": EPOCHS,
            "load_4bit": bool(getattr(a, "load_4bit", False)), "files": files}
    (out / "manifest.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    for name, digest in files.items():
        print(f"{digest}  {name}")


def cmd_export_base(a) -> int:
    """Arm 0: the original weights of the base model, downloaded as they are (no adapter, no re-quantization)."""
    from huggingface_hub import model_info, snapshot_download
    out = Path(a.out)
    if already_done(out):
        print(f"{out} already holds the base model (manifest.json): nothing to do.")
        return 0
    a.hf_revision = model_info(a.hf_repo).sha          # the commit of the repository that is downloaded, for the manifest
    snapshot_download(repo_id=a.hf_repo, revision=a.hf_revision, local_dir=str(out / "merged"),
                      allow_patterns=["*.json", "*.safetensors", "*.txt", "*.model"])
    write_manifest(out, a, 0)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("check", help="render the first prompts and compare their token count with the log")
    p.add_argument("--data", required=True)
    p.add_argument("--model", default="Qwen/Qwen3-4B-Instruct-2507",
                   help="Hugging Face repo of the tokenizer and chat template (the Qwen original, not the Unsloth copy)")
    p.add_argument("--n", type=int, default=5)
    p = sub.add_parser("train", help="LoRA fine-tune from the base, merge, GGUF, hashes")
    p.add_argument("--data", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--model", default=BASE_MODEL, help="the base: give the local folder of arm 0 (rl_colab.py local)")
    p.add_argument("--force", action="store_true", help="train again although the output already has a manifest")
    p.add_argument("--adapter-only", action="store_true", help="skip the merge and the GGUF (RAM fallback)")
    p.add_argument("--gguf", action="store_true", help="also write a Q4_K_M GGUF here (default: made at home)")
    p.add_argument("--load-4bit", action="store_true",
                   help="QLoRA instead of 16-bit LoRA: the last resort, if the L4 runs out of memory too (rl_plan.md)")
    p = sub.add_parser("export-base", help="the original weights of the base model, hashed (arm 0)")
    p.add_argument("--out", required=True)
    p.add_argument("--hf-repo", default="Qwen/Qwen3-4B-Instruct-2507")
    a = ap.parse_args(argv)
    return {"check": cmd_check, "train": cmd_train, "export-base": cmd_export_base}[a.command](a)


if __name__ == "__main__":
    raise SystemExit(main())
