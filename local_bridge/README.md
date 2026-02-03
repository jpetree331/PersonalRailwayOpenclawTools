# Local code bridge for OpenClaw

Runs **on your PC**. OpenClaw (on Railway) calls this service via ngrok or Tailscale so the bot can read/write files and run commands in a project folder you choose.

**Security:** All paths are restricted to one folder (`CODE_BRIDGE_PROJECT_ROOT`). The `/run` endpoint is off by default; set `CODE_BRIDGE_ALLOW_RUN=1` to enable it.

---

## 1. Set env vars (on your PC)

```bash
export CODE_BRIDGE_API_KEY="your-secret-api-key"   # same value in OpenClaw config
export CODE_BRIDGE_PROJECT_ROOT="E:/git/my-project"   # or C:\Users\You\projects\my-project
# Optional: allow OpenClaw to run shell commands in the project
export CODE_BRIDGE_ALLOW_RUN=1
```

Use an **absolute path** for `CODE_BRIDGE_PROJECT_ROOT` — the folder your IDE uses for that project.

---

## 2. Run the bridge (on your PC)

```bash
cd local_bridge
pip install -r requirements.txt
python code_bridge_service.py
```

Default port **8766**. Override with `PORT=9000 python code_bridge_service.py`.

---

## 3. Expose to OpenClaw (ngrok or Tailscale)

OpenClaw runs on Railway and must reach your PC.

- **ngrok:** `ngrok http 8766` → use the HTTPS URL (e.g. `https://abc123.ngrok.io`) as the bridge baseUrl in OpenClaw.
- **Tailscale:** Run the bridge on your PC; use your Tailscale machine URL (e.g. `http://100.x.x.x:8766`) as baseUrl. OpenClaw would need to be on the same Tailnet or use Tailscale Funnel.

---

## 4. OpenClaw config

In your OpenClaw config, add the **code-bridge** plugin (see the OpenClaw repo `extensions/code-bridge`) and set:

- **baseUrl** — your bridge URL (ngrok or Tailscale), e.g. `https://abc123.ngrok.io`
- **apiKey** — same value as `CODE_BRIDGE_API_KEY`

Add the tools to `tools.allow`: `code_bridge_list`, `code_bridge_read`, `code_bridge_write`, and optionally `code_bridge_run`.

---

## 5. API endpoints

All requests need header: `X-API-Key: <CODE_BRIDGE_API_KEY>` or `Authorization: Bearer <key>`.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | No auth; returns `{"status":"ok"}`. |
| GET | `/list?path=...` | List directory. `path` is relative to project root (default `.`). |
| GET | `/read?path=...` | Read file. `path` is relative to project root. |
| POST | `/write` | Write file. Body: `{"path": "src/foo.py", "content": "..."}`. |
| POST | `/run` | Run shell command. Body: `{"command": "npm install", "cwd": ""}`. Requires `CODE_BRIDGE_ALLOW_RUN=1`. |

Paths must stay inside `CODE_BRIDGE_PROJECT_ROOT`; `..` is rejected.
