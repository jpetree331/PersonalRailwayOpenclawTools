#!/usr/bin/env python3
"""
Google Drive "OpenClaw Playground" service for OpenClaw.

Scopes access to a single folder:
  My Drive --> Personal --> AI Research --> OpenClaw Playground

Exposes a small HTTP API (list, read, write) so an OpenClaw tool can call it.
Run: uvicorn drive_playground_service:app --host 0.0.0.0 --port 8765

Setup:
  1. Create a project in Google Cloud Console, enable Google Drive API.
  2. Create OAuth 2.0 credentials (Desktop app), download as credentials.json
     into this directory (or set GOOGLE_APPLICATION_CREDENTIALS).
  3. Set DRIVE_PLAYGROUND_API_KEY (secret for OpenClaw to call this API).
  4. Set DRIVE_PLAYGROUND_FOLDER_ID to your folder ID (from Drive URL when you
     open the folder), OR leave unset to resolve by path:
     Personal / AI Research / OpenClaw Playground
  5. For Railway: set GOOGLE_DRIVE_TOKEN_JSON (full token.json from a local OAuth run).
"""

import json
import os
import io
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Header, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

# Google Drive
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload

# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------
SCOPES = ["https://www.googleapis.com/auth/drive"]
SCRIPT_DIR = Path(__file__).resolve().parent
CREDENTIALS_FILE = SCRIPT_DIR / "credentials.json"
TOKEN_FILE = SCRIPT_DIR / "token.json"
# Folder path to resolve if DRIVE_PLAYGROUND_FOLDER_ID is not set (under My Drive root)
PLAYGROUND_PATH = ["Personal", "AI Research", "OpenClaw Playground"]


def get_api_key() -> str:
    key = (os.environ.get("DRIVE_PLAYGROUND_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("Set DRIVE_PLAYGROUND_API_KEY in the environment.")
    return key


def get_drive_service():
    """Load credentials from env (Railway) or from token/credentials files (local)."""
    creds = None
    token_json = (os.environ.get("GOOGLE_DRIVE_TOKEN_JSON") or "").strip()
    if token_json:
        try:
            token_data = json.loads(token_json)
            creds = Credentials.from_authorized_user_info(token_data, SCOPES)
        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(
                "GOOGLE_DRIVE_TOKEN_JSON is set but invalid. Paste the full contents of token.json (from a local OAuth run)."
            ) from e
    elif TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if creds and not creds.valid and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    if not creds or not creds.valid:
        # First-time OAuth (local only; use credentials file or env)
        creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or CREDENTIALS_FILE
        credentials_json = (os.environ.get("GOOGLE_DRIVE_CREDENTIALS_JSON") or "").strip()
        if credentials_json:
            try:
                client_config = json.loads(credentials_json)
                flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
                creds = flow.run_local_server(port=0)
            except (json.JSONDecodeError, ValueError) as e:
                raise ValueError(
                    "GOOGLE_DRIVE_CREDENTIALS_JSON is set but invalid. Paste the full contents of credentials.json."
                ) from e
        elif creds_path and Path(creds_path).exists():
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        else:
            raise FileNotFoundError(
                "Google OAuth credentials not found. For Railway: set GOOGLE_DRIVE_TOKEN_JSON (full token.json from a local OAuth run). "
                "For local first run: save credentials.json here or set GOOGLE_DRIVE_CREDENTIALS_JSON."
            )
        if not token_json and TOKEN_FILE.exists() is False:
            with open(TOKEN_FILE, "w") as f:
                f.write(creds.to_json())
    return build("drive", "v3", credentials=creds)


def get_playground_folder_id(service) -> str:
    folder_id = (os.environ.get("DRIVE_PLAYGROUND_FOLDER_ID") or "").strip()
    if folder_id:
        return folder_id
    # Resolve by path: My Drive -> Personal -> AI Research -> OpenClaw Playground
    parent_id = "root"
    for name in PLAYGROUND_PATH:
        result = (
            service.files()
            .list(
                q=f"'{parent_id}' in parents and name = '{name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false",
                spaces="drive",
                fields="files(id, name)",
                pageSize=1,
            )
            .execute()
        )
        files = result.get("files", [])
        if not files:
            raise ValueError(
                f"Folder not found: {' / '.join(PLAYGROUND_PATH)}. "
                f"Missing after: {name}. Create the folder in Drive or set DRIVE_PLAYGROUND_FOLDER_ID to the folder ID."
            )
        parent_id = files[0]["id"]
    return parent_id


def is_under_playground(service, file_id: str, playground_id: str) -> bool:
    """Return True if file_id is the playground folder or is inside it (any depth)."""
    visited = set()
    to_visit = [file_id]
    while to_visit:
        fid = to_visit.pop()
        if fid in visited:
            continue
        visited.add(fid)
        if fid == playground_id:
            return True
        try:
            meta = service.files().get(fileId=fid, fields="parents").execute()
        except Exception:
            return False
        parents = meta.get("parents") or []
        to_visit.extend(p for p in parents if p not in visited)
    return False


def require_api_key(x_api_key: str | None = Header(None), authorization: str | None = Header(None)):
    key = get_api_key()
    bearer = (authorization or "").strip().removeprefix("Bearer ")
    if (x_api_key or bearer) != key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


# -----------------------------------------------------------------------------
# FastAPI app
# -----------------------------------------------------------------------------
app = FastAPI(
    title="Drive Playground API",
    description="List, read, and write files in OpenClaw Playground folder on Google Drive.",
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/list", dependencies=[])
def list_files(
    x_api_key: str | None = Header(None),
    authorization: str | None = Header(None),
    folder_id: str | None = Query(None, description="Folder ID to list inside; omit for Playground root. Use ID from a previous list (e.g. a subfolder)."),
    page_token: str | None = Query(None),
    page_size: int = Query(50, ge=1, le=100),
):
    require_api_key(x_api_key, authorization)
    service = get_drive_service()
    playground_id = get_playground_folder_id(service)
    parent_id = (folder_id or "").strip() or playground_id
    if parent_id != playground_id and not is_under_playground(service, parent_id, playground_id):
        raise HTTPException(
            status_code=403,
            detail="Folder is not the Playground root or inside it. Use a folder ID from drive_playground_list.",
        )
    q = f"'{parent_id}' in parents and trashed = false"
    result = (
        service.files()
        .list(
            q=q,
            spaces="drive",
            fields="nextPageToken, files(id, name, mimeType, modifiedTime, size)",
            pageSize=page_size,
            pageToken=page_token or "",
        )
        .execute()
    )
    return {
        "files": result.get("files", []),
        "nextPageToken": result.get("nextPageToken"),
        "folderId": parent_id,
    }


@app.get("/files/{file_id}/content")
def read_file(
    file_id: str,
    x_api_key: str | None = Header(None),
    authorization: str | None = Header(None),
):
    require_api_key(x_api_key, authorization)
    service = get_drive_service()
    playground_id = get_playground_folder_id(service)
    meta = service.files().get(fileId=file_id, fields="id, name, mimeType, parents").execute()
    if not is_under_playground(service, file_id, playground_id):
        raise HTTPException(
            status_code=403,
            detail="File is not inside the Playground folder (root or any subfolder). Use drive_playground_list to get file IDs.",
        )
    try:
        request = service.files().get_media(fileId=file_id)
        buf = io.BytesIO()
        downloader = MediaIoBaseDownload(buf, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        buf.seek(0)
        return PlainTextResponse(buf.read().decode("utf-8", errors="replace"))
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


# Google native app MIME types: create empty Doc/Sheet/Slide with no media
GOOGLE_APP_MIME_TYPES = {
    "application/vnd.google-apps.document",
    "application/vnd.google-apps.spreadsheet",
    "application/vnd.google-apps.presentation",
}


class WriteBody(BaseModel):
    """Provide content (text), file_url (binary), or neither for empty Google Doc/Sheet/Slide."""
    name: str
    content: str | None = None   # text content
    file_url: str | None = None  # HTTP/signed URL to download binary (e.g. MP3, Office, etc.)
    mime_type: str = "text/plain"
    folder_id: str | None = None  # Omit for Playground root; use a subfolder ID to write inside it


@app.post("/write")
def write_file(
    body: WriteBody,
    x_api_key: str | None = Header(None),
    authorization: str | None = Header(None),
):
    has_content = body.content is not None
    has_file_url = bool((body.file_url or "").strip())
    empty_google_app = body.mime_type in GOOGLE_APP_MIME_TYPES and not has_content and not has_file_url

    if not has_content and not has_file_url and not empty_google_app:
        raise HTTPException(
            status_code=400,
            detail="Provide 'content' (text), 'file_url' (binary), or use mime_type Google Doc/Sheet/Slide for an empty file.",
        )
    if has_content and has_file_url:
        raise HTTPException(
            status_code=400,
            detail="Provide only one of 'content' or 'file_url', not both.",
        )
    require_api_key(x_api_key, authorization)
    service = get_drive_service()
    playground_id = get_playground_folder_id(service)
    parent_id = (body.folder_id or "").strip() or playground_id
    if parent_id != playground_id and not is_under_playground(service, parent_id, playground_id):
        raise HTTPException(
            status_code=403,
            detail="Folder is not the Playground root or inside it. Use a folder ID from drive_playground_list.",
        )

    meta = {"name": body.name, "mimeType": body.mime_type, "parents": [parent_id]}
    media = None

    if body.file_url:
        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.get(body.file_url)
                resp.raise_for_status()
                raw = resp.content
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Failed to fetch file_url: {e}") from e
        media = MediaIoBaseUpload(
            io.BytesIO(raw),
            mimetype=body.mime_type,
            resumable=True,
        )
    elif has_content:
        media = MediaIoBaseUpload(
            io.BytesIO((body.content or "").encode("utf-8")),
            mimetype=body.mime_type,
            resumable=False,
        )
    # else: empty_google_app — no media

    # Check if file exists (same name in folder)
    existing = (
        service.files()
        .list(
            q=f"'{parent_id}' in parents and name = '{body.name}' and trashed = false",
            fields="files(id)",
            pageSize=1,
        )
        .execute()
    )
    files = existing.get("files", [])

    if files:
        file_id = files[0]["id"]
        if media is None:
            raise HTTPException(
                status_code=409,
                detail="A file with this name already exists. Provide content or file_url to update.",
            )
        service.files().update(fileId=file_id, body={"name": body.name, "mimeType": body.mime_type}).execute()
        service.files().update(fileId=file_id, media_body=media).execute()
        return {"id": file_id, "action": "updated"}
    else:
        if media is not None:
            created = service.files().create(body=meta, media_body=media, fields="id").execute()
        else:
            created = service.files().create(body=meta, fields="id").execute()
        return {"id": created["id"], "action": "created"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8765"))
    uvicorn.run(app, host="0.0.0.0", port=port)
