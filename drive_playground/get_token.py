#!/usr/bin/env python3
"""
One-time script to get a Google Drive OAuth token.

Run this once on your PC (with credentials.json in this folder). A browser will
open for Google sign-in. When done, token.json is saved here. Copy its full
contents into Railway as the GOOGLE_DRIVE_TOKEN_JSON variable.

Usage:
  cd drive_playground
  pip install -r requirements.txt   # if you haven't already
  python get_token.py
"""

from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/drive"]
SCRIPT_DIR = Path(__file__).resolve().parent
CREDENTIALS_FILE = SCRIPT_DIR / "credentials.json"
TOKEN_FILE = SCRIPT_DIR / "token.json"


def main():
    if not CREDENTIALS_FILE.exists():
        print(f"Put credentials.json in this folder: {SCRIPT_DIR}")
        print("Get it from Google Cloud Console → APIs & Services → Credentials → OAuth 2.0 Desktop client.")
        return 1
    print("Opening browser for Google sign-in...")
    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
    creds = flow.run_local_server(port=0)
    with open(TOKEN_FILE, "w") as f:
        f.write(creds.to_json())
    print(f"Saved token to: {TOKEN_FILE}")
    print("")
    print("Next: Copy the ENTIRE contents of token.json and paste it into Railway")
    print("as the variable GOOGLE_DRIVE_TOKEN_JSON (Railway → your TOOLS service → Variables).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
