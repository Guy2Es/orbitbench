# scripts/rl_colab.py
"""Colab glue for the RL study: a vLLM server for a merged 16-bit model kept on Drive. Nothing here trains (rl_finetune.py) or
plays (rl_round.py). Not run by its author (no GPU, no Colab account here): the first Colab session is the test.

Drive layout, under MyDrive/orbitbench-rl/ (= $RL_DIR; Drive is a slow mount, so models are copied to local disk first):
  models/<name>/merged/   merged 16-bit weights (rl_finetune.py train / export-base)     sft/   training files + manifests
  rl_round.py writes its t*-r*-d*-<arm> and phase0-* folders directly under $RL_DIR.
Every step is restartable: a block's folder resumes when the same command is relaunched, files on Drive survive the session.

The cells, in order, are in notebooks/orbitbench_rl_colab.ipynb. The commands of this file:
  python scripts/rl_colab.py install-vllm           # a separate venv: vLLM and Unsloth pin different torch/transformers versions
  python scripts/rl_colab.py serve --model qwen3-4b            # copies models/qwen3-4b/merged to local disk, starts the server
  python scripts/rl_colab.py stop                   # frees the GPU before a fine-tune
  python scripts/rl_colab.py local --model qwen3-4b            # only the local copy, and its path (the base of a fine-tune)
The server is started in its own session: a process started by a notebook cell is otherwise stopped when the cell ends.
The Python tool runs on the Colab VM (--sandbox local, with network): a deviation recorded in docs/rl_plan.md, for training
rollouts only. The final evaluation is played at home, in Docker, on GMAT replay."""
import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

PORT = 8000
LOCAL = Path("/content/models")
VENV = Path("/content/vllm-env")
PID_FILE = Path("/content/vllm.pid")
LOG_FILE = Path("/content/vllm.log")
MAX_MODEL_LEN = 16384            # as the 16k context of the audit and the rl_plan.md protocol
BASE_URL = f"http://localhost:{PORT}/v1"
SAMPLING_KEYS = ("temperature", "top_p", "top_k", "repetition_penalty")


def rl_dir() -> Path:
    return Path(os.environ["RL_DIR"]) if "RL_DIR" in os.environ else Path("/content/drive/MyDrive/orbitbench-rl")


def serve_command(model_dir: str, name: str, parser: str = "hermes", max_len: int = MAX_MODEL_LEN, vllm: str = "vllm") -> list[str]:
    """The `vllm serve` command: fp16 (the T4 has no bf16), tool calls parsed server-side, the name the harness will use."""
    return [vllm, "serve", model_dir, "--served-model-name", name, "--dtype", "half", "--max-model-len", str(max_len),
            "--gpu-memory-utilization", "0.90", "--enable-auto-tool-choice", "--tool-call-parser", parser,
            "--port", str(PORT), "--seed", "0"]


def install_plans(package: str, uv: str | None, python: str = sys.executable) -> list[list[list[str]]]:
    """Ways to make the venv and install vLLM in it, tried in order. `uv` (shipped with Colab) needs no ensurepip, which
    Colab's Python lacks; then the standard venv module; then virtualenv, which brings its own pip."""
    pip = str(VENV / "bin" / "pip")
    plans = []
    if uv:
        plans.append([[uv, "venv", str(VENV), "--python", python],
                      [uv, "pip", "install", "--python", str(VENV / "bin" / "python"), package]])
    plans.append([[python, "-m", "venv", str(VENV)], [pip, "install", "-q", package]])
    plans.append([[python, "-m", "pip", "install", "-q", "virtualenv"], [python, "-m", "virtualenv", str(VENV)],
                  [pip, "install", "-q", package]])
    return plans


def sampling_of(model_dir: Path) -> dict:
    """The sampling settings vLLM reads from the model folder (generation_config.json); empty if the file is missing."""
    path = Path(model_dir) / "generation_config.json"
    if not path.exists():
        return {}
    cfg = json.loads(path.read_text(encoding="utf-8"))
    return {k: cfg[k] for k in SAMPLING_KEYS if k in cfg}


def cmd_install_vllm(a) -> int:
    if (VENV / "bin" / "vllm").exists():
        print(f"vLLM is already installed in {VENV}")
        return 0
    for plan in install_plans(a.package, shutil.which("uv")):
        shutil.rmtree(VENV, ignore_errors=True)
        try:
            for cmd in plan:
                print("+", " ".join(cmd), flush=True)
                subprocess.check_call(cmd)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"this way failed ({e}); trying the next one", flush=True)
            continue
        if (VENV / "bin" / "vllm").exists():
            print(f"vLLM installed in {VENV}")
            return 0
    raise SystemExit("vLLM could not be installed: copy the messages above")


def local_copy(model: str) -> Path:
    """The model on the local disk, copied from $RL_DIR/models/<model>/merged the first time of a session. A marker file
    is written last, so that an interrupted copy is done again."""
    dst = LOCAL / model
    if (dst / ".complete").exists():
        return dst
    src = rl_dir() / "models" / model / "merged"
    if not (src / "config.json").exists():
        raise SystemExit(f"no merged model at {src} (rl_finetune.py train or export-base writes it)")
    print(f"copying {src} to {dst} (Drive is slow to read: several minutes) ...", flush=True)
    shutil.copytree(src, dst, dirs_exist_ok=True)
    (dst / ".complete").write_text("")
    return dst


def cmd_local(a) -> int:
    print(local_copy(a.model))
    return 0


def cmd_serve(a) -> int:
    dst = local_copy(a.model)
    sampling = sampling_of(dst)
    print(f"sampling settings of {a.model}: {sampling}" if sampling else
          f"WARNING: {a.model} has no generation_config.json: vLLM would sample with its own defaults, not those of the "
          "base model. Copy the file from the base model's folder before playing.", flush=True)
    cmd_stop(a)
    with open(LOG_FILE, "wb") as log:
        proc = subprocess.Popen(serve_command(str(dst), a.model, a.parser, a.max_len, str(VENV / "bin" / "vllm")),
                                stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True)
    PID_FILE.write_text(str(proc.pid))
    deadline = time.time() + a.wait
    while time.time() < deadline:
        if proc.poll() is not None:
            raise SystemExit(f"vLLM exited with code {proc.returncode}; see {LOG_FILE}")
        try:
            # vLLM reads VLLM_API_KEY from the environment and then refuses calls without it (401): send it.
            request = urllib.request.Request(f"{BASE_URL}/models", headers={
                "Authorization": f"Bearer {os.environ.get('VLLM_API_KEY', '')}"})
            urllib.request.urlopen(request, timeout=2)
            print(f"serving {a.model} at {BASE_URL} (the harness needs VLLM_BASE_URL={BASE_URL} and VLLM_API_KEY, "
                  "set by the notebook)")
            return 0
        except OSError:
            time.sleep(5)
    raise SystemExit(f"vLLM not ready after {a.wait} s; see {LOG_FILE}")


def cmd_stop(a) -> int:
    """Stop the server and its engine process (one process group, see `start_new_session`), and wait until they are gone
    so that the GPU memory is free for what follows."""
    if not PID_FILE.exists():
        return 0
    try:
        pid = int(PID_FILE.read_text())
        os.killpg(pid, signal.SIGTERM)
        for _ in range(30):
            time.sleep(1)
            os.killpg(pid, 0)               # raises ProcessLookupError once the group is gone
        os.killpg(pid, signal.SIGKILL)
        time.sleep(2)
    except (ProcessLookupError, PermissionError, ValueError):
        pass
    PID_FILE.unlink(missing_ok=True)
    print("vLLM stopped")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("install-vllm", help="a venv with vLLM, apart from Unsloth's environment")
    p.add_argument("--package", default="vllm", help="pin a version here once the first session worked, e.g. vllm==X.Y.Z")
    p = sub.add_parser("serve", help="copy models/<model>/merged to local disk and start the server")
    p.add_argument("--model", required=True)
    p.add_argument("--parser", default="hermes", help="vLLM tool-call parser (hermes for Qwen3)")
    p.add_argument("--max-len", type=int, default=MAX_MODEL_LEN)
    p.add_argument("--wait", type=int, default=900, help="seconds to wait for the server")
    sub.add_parser("stop", help="stop the server and free the GPU")
    p = sub.add_parser("local", help="copy models/<model>/merged to local disk and print the folder")
    p.add_argument("--model", required=True)
    a = ap.parse_args(argv)
    return {"install-vllm": cmd_install_vllm, "serve": cmd_serve, "stop": cmd_stop, "local": cmd_local}[a.command](a)


if __name__ == "__main__":
    sys.exit(main())
