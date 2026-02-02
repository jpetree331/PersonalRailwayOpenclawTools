# OpenClaw tool schema: Google Drive Playground

Explicit schema for three tools that call the Drive Playground service (`drive_playground_service.py`). Use this to implement an OpenClaw plugin or custom tool.

**Base URL:** Set via OpenClaw plugin config (e.g. your TOOLS Railway URL: `https://your-tools.up.railway.app`).

**Auth:** Every request must include the API key:

- Header: `X-API-Key: <DRIVE_PLAYGROUND_API_KEY>`  
- Or: `Authorization: Bearer <DRIVE_PLAYGROUND_API_KEY>`

---

## Tool 1: `drive_playground_list`

**Description (for the model):**

List files in the OpenClaw Playground folder on Google Drive (My Drive → Personal → AI Research → OpenClaw Playground). Returns file id, name, mimeType, modifiedTime, size. Use this to discover file IDs before reading.

**Parameters (JSON Schema):**

```json
{
  "type": "object",
  "properties": {
    "page_token": {
      "type": "string",
      "description": "Optional. Token from previous list response for pagination."
    },
    "page_size": {
      "type": "integer",
      "description": "Max number of files to return (1–100). Default 50.",
      "minimum": 1,
      "maximum": 100,
      "default": 50
    }
  }
}
```

**HTTP request:**

- **Method:** `GET`
- **URL:** `{baseUrl}/list`
  - Query: `page_token` (optional), `page_size` (optional, default 50)
- **Headers:** `X-API-Key: {apiKey}` or `Authorization: Bearer {apiKey}`

**Response:** JSON with `files` (array of `{ id, name, mimeType, modifiedTime, size }`) and optional `nextPageToken`.

---

## Tool 2: `drive_playground_read`

**Description (for the model):**

Read the text content of a file in the OpenClaw Playground folder. The file must be a direct child of that folder (use drive_playground_list to get file IDs).

**Parameters (JSON Schema):**

```json
{
  "type": "object",
  "properties": {
    "file_id": {
      "type": "string",
      "description": "Google Drive file ID (from drive_playground_list)."
    }
  },
  "required": ["file_id"]
}
```

**HTTP request:**

- **Method:** `GET`
- **URL:** `{baseUrl}/files/{file_id}/content`
- **Headers:** `X-API-Key: {apiKey}` or `Authorization: Bearer {apiKey}`

**Response:** Plain text (file body). 403 if file is not in the Playground folder; 404 if not found.

---

## Tool 3: `drive_playground_write`

**Description (for the model):**

Create or update a file in the OpenClaw Playground folder. If a file with the same name already exists, it is updated; otherwise a new file is created.

**Parameters (JSON Schema):**

```json
{
  "type": "object",
  "properties": {
    "name": {
      "type": "string",
      "description": "File name (e.g. notes.txt, journal-2026-02-15.md)."
    },
    "content": {
      "type": "string",
      "description": "Full text content to write."
    },
    "mime_type": {
      "type": "string",
      "description": "MIME type. Default text/plain.",
      "default": "text/plain"
    }
  },
  "required": ["name", "content"]
}
```

**HTTP request:**

- **Method:** `POST`
- **URL:** `{baseUrl}/write`
- **Headers:**
  - `X-API-Key: {apiKey}` or `Authorization: Bearer {apiKey}`
  - `Content-Type: application/json`
- **Body:** JSON `{ "name": "<filename>", "content": "<text>", "mime_type": "text/plain" }`

**Response:** JSON `{ "id": "<drive_file_id>", "action": "created" }` or `"updated"`.

---

## Enabling in OpenClaw

The OpenClaw repo has an extension **`extensions/drive-playground`** that implements these three tools. In your OpenClaw config:

1. Set `plugins.entries["drive-playground"].enabled` to `true`.
2. Set `config.baseUrl` to your TOOLS deployment URL (e.g. `https://your-tools.up.railway.app`).
3. Set `config.apiKey` to `"${DRIVE_PLAYGROUND_API_KEY}"` and set that env var to the same value as on the TOOLS service.
4. Add `drive_playground_list`, `drive_playground_read`, `drive_playground_write` to `tools.allow`.

See the root README in this repo for Railway deploy steps.
