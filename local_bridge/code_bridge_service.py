#!/usr/bin/env python3
"""
Local code bridge for OpenClaw.

Runs on your PC. OpenClaw (on Railway) calls this via ngrok/Tailscale so the bot
can read/write files and run commands in a project folder you choose.

Env:
  CODE_BRIDGE_API_KEY — secret for OpenClaw to call this API (required).
  CODE_BRIDGE_PROJECT_ROOT — absolute path to the folder the bridge can access (required).
  CODE_BRIDGE_ALLOW_RUN — set to "1" to allow POST /run (optional; off by default).

Run: python code_bridge_service.py  (or uvicorn code_bridge_service:app --host 0.0.0.0 --port 8766)
"""

import os
import subprocess
from pathlib import Path

from fastapi import FastAPI, HTTPException, Header, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------


def get_api_key() -> str:
    key = (os.environ.get("CODE_BRIDGE_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("Set CODE_BRIDGE_API_KEY in the environment.")
    return key


def get_project_root() -> Path:
    root = (os.environ.get("CODE_BRIDGE_PROJECT_ROOT") or "").strip()
    if not root:
        raise RuntimeError("Set CODE_BRIDGE_PROJECT_ROOT to the absolute path of the folder OpenClaw can access.")
    path = Path(root).resolve()
    if not path.is_dir():
        raise NotADirectoryError(f"CODE_BRIDGE_PROJECT_ROOT is not a directory: {path}")
    return path


def allow_run() -> bool:
    return (os.environ.get("CODE_BRIDGE_ALLOW_RUN") or "").strip().lower() in ("1", "true", "yes")


def require_api_key(x_api_key: str | None = Header(None), authorization: str | None = Header(None)):
    key = get_api_key()
    bearer = (authorization or "").strip().removeprefix("Bearer ")
    if (x_api_key or bearer) != key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


def resolve_safe_path(relative_path: str) -> Path:
    """Resolve path relative to project root; raise 400 if it escapes the root."""
    root = get_project_root().resolve()
    path = Path(relative_path.strip().lstrip("/")) if relative_path.strip() else Path(".")
    resolved = (root / path).resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        raise HTTPException(status_code=400, detail="Path escapes project root")
    return resolved


# -----------------------------------------------------------------------------
# FastAPI app
# -----------------------------------------------------------------------------
app = FastAPI(
    title="Code Bridge API",
    description="Read/write files and optionally run commands in a local project folder for OpenClaw.",
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/list")
def list_dir(
    x_api_key: str | None = Header(None),
    authorization: str | None = Header(None),
    path: str = Query("", description="Relative path under project root (e.g. src or .)"),
):
    require_api_key(x_api_key, authorization)
    target = resolve_safe_path(path) if path.strip() else get_project_root()
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="Not a directory")
    entries = []
    for e in target.iterdir():
        entries.append({"name": e.name, "type": "dir" if e.is_dir() else "file"})
    return {"path": path or ".", "entries": entries}


@app.get("/read")
def read_file(
    x_api_key: str | None = Header(None),
    authorization: str | None = Header(None),
    path: str = Query(..., description="Relative path to file under project root"),
):
    require_api_key(x_api_key, authorization)
    target = resolve_safe_path(path)
    if not target.is_file():
        raise HTTPException(status_code=404, detail="Not a file or not found")
    try:
        return PlainTextResponse(target.read_text(encoding="utf-8", errors="replace"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class WriteBody(BaseModel):
    path: str
    content: str


@app.post("/write")
def write_file(
    body: WriteBody,
    x_api_key: str | None = Header(None),
    authorization: str | None = Header(None),
):
    require_api_key(x_api_key, authorization)
    target = resolve_safe_path(body.path)
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        target.write_text(body.content, encoding="utf-8")
        return {"path": body.path, "ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class RunBody(BaseModel):
    command: str
    cwd: str = ""


@app.post("/run")
def run_command(
    body: RunBody,
    x_api_key: str | None = Header(None),
    authorization: str | None = Header(None),
):
    require_api_key(x_api_key, authorization)
    if not allow_run():
        raise HTTPException(status_code=403, detail="CODE_BRIDGE_ALLOW_RUN is not set; run is disabled.")
    cwd = get_project_root()
    if body.cwd.strip():
        cwd = resolve_safe_path(body.cwd)
        if not cwd.is_dir():
            raise HTTPException(status_code=400, detail="cwd is not a directory")
    try:
        result = subprocess.run(
            body.command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Command timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8766"))
    uvicorn.run(app, host="0.0.0.0", port=port)
