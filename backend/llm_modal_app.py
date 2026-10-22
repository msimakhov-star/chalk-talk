"""Separate Modal app "chalk-talk-llm": a llama.cpp server with Qwen2.5-3B-Instruct (GGUF Q4_K_M)
behind an OpenAI-compatible /v1/chat/completions, used by backend/llm.py in production.

    modal run backend/llm_modal_app.py::download_model     # once: ~2.1 GB into the Volume
    modal deploy backend/llm_modal_app.py                   # -> https://m-simakhov--chalk-talk-llm.us-east.modal.run
    CHALK_LLM_GPU=none modal deploy backend/llm_modal_app.py   # CPU variant (measured in README.md)
"""

import os
import subprocess

import modal

MODEL_REPO = "Qwen/Qwen2.5-3B-Instruct-GGUF"
MODEL_FILE = "qwen2.5-3b-instruct-q4_k_m.gguf"
MODEL_URL = f"https://huggingface.co/{MODEL_REPO}/resolve/main/{MODEL_FILE}"
MODEL_DIR = "/models"
MODEL_PATH = f"{MODEL_DIR}/{MODEL_FILE}"
ALIAS = "qwen2.5-3b-instruct"
PORT = 8080
GPU = os.environ.get("CHALK_LLM_GPU", "T4")  # "none" deploys the CPU build
USE_GPU = GPU.lower() != "none"

volume = modal.Volume.from_name("chalk-talk-models", create_if_missing=True)
image = modal.Image.from_registry(
    "ghcr.io/ggml-org/llama.cpp:server-cuda" if USE_GPU else "ghcr.io/ggml-org/llama.cpp:server",
    add_python="3.12",
).entrypoint([])

app = modal.App("chalk-talk-llm")


@app.function(image=modal.Image.debian_slim(python_version="3.12"), volumes={MODEL_DIR: volume}, timeout=1800)
def download_model():
    import urllib.request
    if os.path.exists(MODEL_PATH):
        print("already downloaded", MODEL_PATH, os.path.getsize(MODEL_PATH))
        return
    print("downloading", MODEL_URL)
    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH + ".part")
    os.rename(MODEL_PATH + ".part", MODEL_PATH)
    volume.commit()
    print("done", os.path.getsize(MODEL_PATH))


@app.function(
    image=image,
    gpu=GPU if USE_GPU else None,
    cpu=8 if not USE_GPU else None,
    memory=8192 if not USE_GPU else None,
    volumes={MODEL_DIR: volume},
    scaledown_window=900,
    timeout=600,
)
@modal.concurrent(max_inputs=4)
@modal.web_server(PORT, startup_timeout=600, label="chalk-talk-llm")
def llm():
    cmd = ["/app/llama-server", "--model", MODEL_PATH, "--alias", ALIAS, "--host", "0.0.0.0", "--port", str(PORT),
           "--jinja", "--ctx-size", "4096", "--parallel", "2", "--no-webui"]
    if USE_GPU:
        cmd += ["--n-gpu-layers", "99"]
    subprocess.Popen(cmd)
