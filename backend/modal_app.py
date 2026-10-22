"""Modal app "chalk-talk": the FastAPI + MCP web app as one ASGI function `web`.

    modal deploy backend/modal_app.py      # from the repo root

The repo's engine/, backend/, phone/, renderer/ and echo-show-mcp-sim/ are copied to
/root/chalk-talk so backend.engine_loader finds the engine and the static pages at
the same relative paths as locally. State lives in modal.Dict "chalk-talk-state".
"""

from pathlib import Path

import modal

ROOT = Path(__file__).resolve().parent.parent
REMOTE_ROOT = "/root/chalk-talk"
COMPONENTS = ["engine", "backend", "phone", "renderer", "echo-show-mcp-sim"]
IGNORE = ["**/node_modules", "**/__pycache__", "**/.pytest_cache", "**/screenshots", "**/*.png", "**/*.mp4"]

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("fastmcp==4.1.3", "mcp==2.3.0", "fastapi", "uvicorn", "httpx")
    .env({"LLM_BASE_URL": "https://m-simakhov--chalk-talk-llm.us-east.modal.run/v1", "LLM_MODEL": "qwen2.5-3b-instruct"})
)
for component in COMPONENTS:
    if (ROOT / component).exists():
        image = image.add_local_dir(ROOT / component, f"{REMOTE_ROOT}/{component}", ignore=IGNORE)

app = modal.App("chalk-talk")


@app.function(image=image, min_containers=0, scaledown_window=600, timeout=300)
@modal.concurrent(max_inputs=100)  # TV long-polls hold a request open for up to 10 s
@modal.asgi_app(label="chalk-talk-web")
def web():
    import sys
    sys.path.insert(0, REMOTE_ROOT)
    from backend.app import create_app
    return create_app()
