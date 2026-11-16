# scripts/rl_gguf.py
"""At home: a merged 16-bit model downloaded from Drive -> GGUF Q4_K_M -> an Ollama tag, the same way for every model of the
evaluation (the base included). Needs a llama.cpp checkout and build (convert_hf_to_gguf.py, llama-quantize) and Ollama.
Not run by its author (no model here).

  python scripts/rl_gguf.py --model-dir D:/orbitbench-rl/models/t0-reward/merged --name t0-reward \\
        --llama-cpp D:/tools/llama.cpp --template-from qwen3-4b-instruct-16k

`--template-from` is the Ollama tag of a model with the same architecture whose Modelfile (TEMPLATE, stop tokens, tool block)
is reused, so that every model of the evaluation is rendered by the same template. The context is 16k, as in the protocol.
The GGUF and Modelfile hashes are written next to the output, to be copied in the manifest of the model."""
import argparse
import hashlib
import subprocess
import sys
from pathlib import Path


def sha256_of(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def modelfile_text(gguf: Path, template_from_text: str, num_ctx: int = 16384) -> str:
    """The Modelfile of a converted model: its own weights, the reused TEMPLATE and stop parameters, a 16k context."""
    keep = [ln for ln in template_from_text.splitlines() if not ln.startswith(("FROM", "PARAMETER num_ctx"))]
    return "\n".join([f"FROM {gguf.resolve().as_posix()}", *keep, f"PARAMETER num_ctx {num_ctx}"]) + "\n"


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.check_call(cmd)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model-dir", required=True, type=Path, help="the merged/ folder of the model (safetensors + tokenizer)")
    ap.add_argument("--name", required=True, help="Ollama tag to create")
    ap.add_argument("--llama-cpp", required=True, type=Path)
    ap.add_argument("--template-from", required=True, help="Ollama tag whose Modelfile supplies the TEMPLATE")
    ap.add_argument("--out", type=Path, help="folder for the GGUF files (default: next to the model folder)")
    a = ap.parse_args(argv)
    out = a.out or a.model_dir.parent / "gguf"
    out.mkdir(parents=True, exist_ok=True)
    f16, q4 = out / f"{a.name}-F16.gguf", out / f"{a.name}-Q4_K_M.gguf"
    run([sys.executable, str(a.llama_cpp / "convert_hf_to_gguf.py"), str(a.model_dir), "--outfile", str(f16), "--outtype", "f16"])
    quantize = next((p for p in (a.llama_cpp / "build" / "bin" / "llama-quantize.exe", a.llama_cpp / "build" / "bin" / "llama-quantize")
                     if p.exists()), None)
    if quantize is None:
        raise SystemExit("llama-quantize not found under <llama.cpp>/build/bin: build llama.cpp first")
    run([str(quantize), str(f16), str(q4), "Q4_K_M"])
    f16.unlink()
    shown = subprocess.run(["ollama", "show", a.template_from, "--modelfile"], capture_output=True, text=True, check=True).stdout
    modelfile = out / f"{a.name}.Modelfile"
    modelfile.write_text(modelfile_text(q4, shown), encoding="utf-8")
    run(["ollama", "create", a.name, "-f", str(modelfile)])
    for path in (q4, modelfile):
        print(f"{sha256_of(path)}  {path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
