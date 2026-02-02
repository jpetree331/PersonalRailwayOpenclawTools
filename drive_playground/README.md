# Google Drive OpenClaw Playground service

Small HTTP API so your OpenClaw bot can list, read, and write files in a single Google Drive folder:

**My Drive → Personal → AI Research → OpenClaw Playground**

## 1. Google Cloud setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create a project (or pick one) and enable **Google Drive API** (APIs & Services → Enable APIs).
3. **OAuth consent screen**: Configure if needed (External, add your email as test user).
4. **Credentials** → Create credentials → **OAuth client ID** → Application type: **Desktop app** → Create.
5. Download the JSON and save it as `credentials.json` in this directory (`drive_playground/`).

## 2. Folder in Drive

Create this structure in Google Drive (or use an existing one):

- **My Drive** → **Personal** → **AI Research** → **OpenClaw Playground**

Alternatively, open the folder you want in Drive, copy the folder ID from the URL  
(`https://drive.google.com/drive/folders/<FOLDER_ID>`) and set:

```bash
export DRIVE_PLAYGROUND_FOLDER_ID="your-folder-id"
```

Then the path above is ignored.

## 3. API key for OpenClaw

Choose a secret (e.g. a long random string) and set it so only your bot can call this API:

```bash
export DRIVE_PLAYGROUND_API_KEY="your-secret-api-key"
```

Use the same value in your OpenClaw tool config when calling this service.

### Running on Railway (TOOLS deployment)

Set these as **Railway Variables** (no credential files):

- **GOOGLE_DRIVE_TOKEN_JSON** — Full contents of `token.json` (do OAuth once locally, then paste the file content).
- **DRIVE_PLAYGROUND_API_KEY** — Secret for the OpenClaw tool to call this API.
- **DRIVE_PLAYGROUND_FOLDER_ID** — (optional) Your Drive folder ID.
- **PORT** — Railway sets this; override only if needed.

## 4. Run the service

```bash
cd drive_playground
pip install -r requirements.txt
python drive_playground_service.py
```

First run will open a browser for Google sign-in; the token is saved to `token.json` (do not commit it).

Default port **8765**. Override with `PORT=9000 python drive_playground_service.py`.

## 5. API endpoints

All requests require header: `X-API-Key: <DRIVE_PLAYGROUND_API_KEY>` or `Authorization: Bearer <DRIVE_PLAYGROUND_API_KEY>`.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | No auth; returns `{"status":"ok"}`. |
| GET | `/list` | List files in the Playground folder. Query: `page_token`, `page_size` (default 50). |
| GET | `/files/{file_id}/content` | Read file content (direct children of Playground only). |
| POST | `/write` | Create or update a file. Body: `{"name": "filename.txt", "content": "...", "mime_type": "text/plain"}`. |

## 6. OpenClaw tool

The OpenClaw **drive-playground** extension (in the OpenClaw repo) calls this API. In OpenClaw config set `plugins.entries["drive-playground"].config.baseUrl` to this service’s URL (e.g. `https://your-tools.up.railway.app`) and `apiKey` to the same value as `DRIVE_PLAYGROUND_API_KEY`. Add the three tools to `tools.allow`. See the root README in this repo and `OPENCLAW_TOOL_SCHEMA.md` for the API contract.
