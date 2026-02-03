# TOOLS — OpenClaw tool backends

Separate Railway deployment that runs the **tool backends** your OpenClaw bot calls via API. Keeps the main OpenClaw deployment simple and stable; you add or change tools here without touching the OpenClaw repo.

**Current tools:**

- **Drive Playground** — List, read, and write files in a single Google Drive folder (My Drive → Personal → AI Research → OpenClaw Playground). See `drive_playground/README.md`.
- **Local code bridge** — Runs **on your PC** (not on Railway). OpenClaw calls it via ngrok/Tailscale so the bot can read/write files and run commands in a project folder. See `local_bridge/README.md`.

**Adding more tools:** Add new subfolders (e.g. `journal/`, `files/`) with their own Dockerfile or extend this repo to run multiple services. OpenClaw extensions that call these APIs live in the OpenClaw repo; this repo is only the server side.

---

## Deploy to Railway

1. **Push this repo to GitHub** and connect it to a new Railway project (or use Railway CLI).

2. **Variables** — Set these in Railway → your service → Variables (all secrets as variables; no files in the image):

   **Drive Playground (required if you use it):**
   - `GOOGLE_DRIVE_TOKEN_JSON` — Full contents of `token.json` from a one-time OAuth run on your PC (run `drive_playground` locally once, sign in with Google, then copy `drive_playground/token.json`).
   - `DRIVE_PLAYGROUND_API_KEY` — A secret you choose; the OpenClaw Drive Playground tool uses it to call this API.

   **Optional:**
   - `DRIVE_PLAYGROUND_FOLDER_ID` — Your Google Drive folder ID (from the folder URL). If unset, the service uses the path **Personal → AI Research → OpenClaw Playground**.
   - `PORT` — Railway sets this automatically; override only if needed.

3. **Build & deploy** — Railway builds the Dockerfile and runs the Drive Playground app. Enable **HTTP Proxy** and note the public URL (e.g. `https://your-tools.up.railway.app`).

4. **OpenClaw config** — In your OpenClaw config (e.g. `railway-config.json` or `openclaw.json`), point the Drive Playground plugin at this service:

   ```json
   "plugins": {
     "entries": {
       "drive-playground": {
         "enabled": true,
         "config": {
           "baseUrl": "https://YOUR-TOOLS-RAILWAY-URL",
           "apiKey": "${DRIVE_PLAYGROUND_API_KEY}"
         }
       }
     }
   },
   "tools": {
     "allow": ["drive_playground_list", "drive_playground_read", "drive_playground_write"]
   }
   ```

   Use your actual Tools Railway URL (no trailing slash). Set `DRIVE_PLAYGROUND_API_KEY` in **OpenClaw’s** environment to the same value as on the TOOLS service so the plugin can send it.

---

## Local run

```bash
cd drive_playground
pip install -r requirements.txt
# Set GOOGLE_DRIVE_TOKEN_JSON + DRIVE_PLAYGROUND_API_KEY (or use credentials.json + token.json from first run)
python drive_playground_service.py
```

Default port **8765**. OpenClaw can call `http://localhost:8765` when running locally, or use ngrok/Tailscale to expose it.

---

## Layout

```
TOOLS/
├── README.md           (this file)
├── Dockerfile          (builds and runs Drive Playground on Railway)
├── .gitignore
├── drive_playground/   (Google Drive list/read/write API — deploy to Railway)
│   ├── drive_playground_service.py
│   ├── requirements.txt
│   ├── README.md
│   └── OPENCLAW_TOOL_SCHEMA.md
└── local_bridge/       (Local code bridge — run on your PC, expose via ngrok/Tailscale)
    ├── code_bridge_service.py
    ├── requirements.txt
    └── README.md
```

Future tools: add more subfolders; OpenClaw extensions in the OpenClaw repo call these APIs.
