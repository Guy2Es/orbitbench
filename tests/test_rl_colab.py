# tests/test_rl_colab.py
"""The pure parts of the Colab and home scripts: the vLLM command and the Modelfile of a converted model."""
import importlib.util
from pathlib import Path


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parents[1] / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_the_vllm_command_is_fp16_with_server_side_tool_parsing_and_a_16k_context():
    cmd = load("rl_colab").serve_command("/content/models/m", "m")
    assert cmd[:3] == ["vllm", "serve", "/content/models/m"]
    assert cmd[cmd.index("--served-model-name") + 1] == "m" and cmd[cmd.index("--dtype") + 1] == "half"
    assert cmd[cmd.index("--max-model-len") + 1] == "16384" and "--enable-auto-tool-choice" in cmd
    assert cmd[cmd.index("--tool-call-parser") + 1] == "hermes"


def test_the_modelfile_keeps_the_parameters_not_the_template_and_sets_the_weights_and_the_context():
    gguf = load("rl_gguf")
    text = gguf.modelfile_text(Path("m-Q4_K_M.gguf"), 'FROM old.gguf\nTEMPLATE """x"""\nPARAMETER num_ctx 4096\nPARAMETER stop "<|im_end|>"')
    lines = text.splitlines()
    assert lines[0].startswith("FROM ") and lines[0].endswith("m-Q4_K_M.gguf")
    assert not any("TEMPLATE" in ln for ln in lines)             # a copied template loses the tool calls in Ollama
    assert 'PARAMETER stop "<|im_end|>"' in lines
    assert lines.count("PARAMETER num_ctx 16384") == 1 and "PARAMETER num_ctx 4096" not in lines


def test_vllm_is_installed_with_uv_when_colab_has_it_and_with_venv_or_virtualenv_otherwise():
    colab = load("rl_colab")
    with_uv = colab.install_plans("vllm", "/usr/bin/uv", "/usr/bin/python3")
    assert with_uv[0][0][:2] == ["/usr/bin/uv", "venv"] and with_uv[0][1][:3] == ["/usr/bin/uv", "pip", "install"]
    without = colab.install_plans("vllm==1.0", None, "/usr/bin/python3")
    assert without[0][0] == ["/usr/bin/python3", "-m", "venv", str(colab.VENV)]
    assert without[-1][1] == ["/usr/bin/python3", "-m", "virtualenv", str(colab.VENV)]
    assert all(plan[-1][-1] == "vllm==1.0" for plan in without) and len(with_uv) == len(without) + 1


def test_the_sampling_settings_a_server_would_use_are_read_from_the_model_folder(tmp_path):
    colab = load("rl_colab")
    assert colab.sampling_of(tmp_path) == {}
    (tmp_path / "generation_config.json").write_text('{"temperature": 0.7, "top_p": 0.8, "top_k": 20, "eos_token_id": 1}')
    assert colab.sampling_of(tmp_path) == {"temperature": 0.7, "top_p": 0.8, "top_k": 20}


def test_a_finished_fine_tune_is_not_done_again_and_keeps_the_sampling_settings_of_the_base(tmp_path):
    ft = load("rl_finetune")
    base, out = tmp_path / "base", tmp_path / "out"
    (out / "merged").mkdir(parents=True)
    base.mkdir()
    assert not ft.already_done(out)
    (out / "manifest.json").write_text("{}")
    assert ft.already_done(out) and not ft.already_done(out, force=True)
    assert not ft.keep_sampling_settings(base, out / "merged")              # the base has no file: nothing to copy
    (base / "generation_config.json").write_text('{"temperature": 0.7}')
    assert ft.keep_sampling_settings(base, out / "merged")
    assert (out / "merged" / "generation_config.json").read_text() == '{"temperature": 0.7}'
    assert not ft.keep_sampling_settings(base, out / "merged")              # already there: left as it is
    assert ft.base_hashes("Qwen/some-hub-name") == {}
    (base / "model.safetensors").write_bytes(b"abc")
    assert ft.base_hashes(base) == {"model.safetensors": ft.sha256_of(base / "model.safetensors")}
