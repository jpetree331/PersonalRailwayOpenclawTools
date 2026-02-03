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

Create or update a file in the OpenClaw Playground folder. If a file with the same name already exists, it is updated; otherwise a new file is created. Supports **text** (via `content`), **binary** (via `file_url`): audio, video, Office (.ppt, .doc, .docx, .xls, .xlsx, .pptx), or **empty Google Docs/Sheets/Slides** (omit both `content` and `file_url` and set `mime_type` to the Google app type). Use the appropriate `mime_type` for the file.

**Parameters (JSON Schema):**

```json
{
  "type": "object",
  "properties": {
    "name": {
      "type": "string",
      "description": "File name (e.g. notes.txt, recording.mp3, deck.pptx)."
    },
    "content": {
      "type": "string",
      "description": "Full text content. Use for text/markdown/plain. Omit when using file_url."
    },
    "file_url": {
      "type": "string",
      "description": "HTTP or signed URL to the file to upload (binary). Use for audio, video, Office, etc. Omit when using content."
    },
    "mime_type": {
      "type": "string",
      "description": "MIME type. Default text/plain. Office: .ppt application/vnd.ms-powerpoint, .doc application/vnd.ms-word, .docx application/vnd.openxmlformats-officedocument.wordprocessingml.document, .xls application/vnd.ms-excel, .xlsx application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, .pptx application/vnd.openxmlformats-officedocument.presentationml.presentation. Google: application/vnd.google-apps.document (Docs), application/vnd.google-apps.spreadsheet (Sheets), application/vnd.google-apps.presentation (Slides). For empty Google Doc/Sheet/Slide omit content and file_url.",
      "default": "text/plain"
    },
    "folder_id": {
      "type": "string",
      "description": "Optional. Drive folder ID to write into (from drive_playground_list). Omit for Playground root."
    }
  },
  "required": ["name"]
}
```

Note: Provide exactly one of (a) `content`, (b) `file_url`, or (c) neither for empty Google Doc/Sheet/Slide (use `mime_type` application/vnd.google-apps.document | .spreadsheet | .presentation).

**HTTP request:**

- **Method:** `POST`
- **URL:** `{baseUrl}/write`
- **Headers:**
  - `X-API-Key: {apiKey}` or `Authorization: Bearer {apiKey}`
  - `Content-Type: application/json`
- **Body (text):** `{ "name": "<filename>", "content": "<text>", "mime_type": "text/plain" }`
- **Body (binary):** `{ "name": "<filename>", "file_url": "<https://...>", "mime_type": "audio/mpeg" }` (or Office/other MIME)
- **Body (empty Google Doc/Sheet/Slide):** `{ "name": "<filename>", "mime_type": "application/vnd.google-apps.document" }` (or `.spreadsheet` or `.presentation`; omit content and file_url)

**Response:** JSON `{ "id": "<drive_file_id>", "action": "created" }` or `"updated"`.

**MIME types:**

| Format | MIME type |
|--------|-----------|
| Plain / Markdown | `text/plain`, `text/markdown` |
| Audio / Video / PDF | `audio/mpeg`, `video/mp4`, `application/pdf` |
| .ppt | `application/vnd.ms-powerpoint` |
| .pptx | `application/vnd.openxmlformats-officedocument.presentationml.presentation` |
| .doc | `application/vnd.ms-word` |
| .docx | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` |
| .xls | `application/vnd.ms-excel` |
| .xlsx | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` |
| Google Docs | `application/vnd.google-apps.document` (empty: omit content & file_url) |
| Google Sheets | `application/vnd.google-apps.spreadsheet` (empty: omit content & file_url) |
| Google Slides | `application/vnd.google-apps.presentation` (empty: omit content & file_url) |

---

## Enabling in OpenClaw

The OpenClaw repo has an extension **`extensions/drive-playground`** that implements these three tools. In your OpenClaw config:

1. Set `plugins.entries["drive-playground"].enabled` to `true`.
2. Set `config.baseUrl` to your TOOLS deployment URL (e.g. `https://your-tools.up.railway.app`).
3. Set `config.apiKey` to `"${DRIVE_PLAYGROUND_API_KEY}"` and set that env var to the same value as on the TOOLS service.
4. Add `drive_playground_list`, `drive_playground_read`, `drive_playground_write` to `tools.allow`.

See the root README in this repo for Railway deploy steps.
