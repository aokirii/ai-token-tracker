"""Temporary diagnostic for Claude live data (esp. macOS Keychain).
Run from the project folder:  .venv/bin/python diag_claude.py
Safe to delete afterwards.
"""
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone

import tracker

c = tracker._read_creds()
print("creds keys :", list(c.keys()))
tok = c.get("accessToken")
exp = c.get("expiresAt")
print("has token  :", bool(tok), "| len:", len(tok or ""))
print("expiresAt  :", exp)
if exp:
    try:
        print("expired?   :", int(exp) / 1000 <= datetime.now(timezone.utc).timestamp())
    except (TypeError, ValueError):
        print("expired?   : (could not parse expiresAt)")

if not tok:
    print("=> No accessToken found. Check the 'creds keys' line for the real key name.")
else:
    req = urllib.request.Request(
        "https://api.anthropic.com/api/oauth/usage",
        headers={
            "Authorization": f"Bearer {tok}",
            "anthropic-beta": "oauth-2025-04-20",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            d = json.load(r)
        print("LIVE OK     :", list(d.keys()))
    except urllib.error.HTTPError as e:
        print("HTTPError   :", e.code, e.read()[:200])
    except Exception as e:
        print("ERR         :", type(e).__name__, e)
