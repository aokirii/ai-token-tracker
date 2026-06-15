"""Temporary Windows diagnostic for Claude + Codex data sources.
Run from the project folder:  .venv\\Scripts\\python diag_win.py
Safe to delete afterwards.
"""
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

import tracker

print("== ENV ==")
print("platform    :", sys.platform)
print("home (~)    :", os.path.expanduser("~"))

print("\n== CLAUDE ==")
print("creds path  :", tracker.CLAUDE_CREDS)
print("file exists :", os.path.exists(tracker.CLAUDE_CREDS))
claude_dir = os.path.dirname(tracker.CLAUDE_CREDS)
print(".claude dir :", claude_dir, "| exists:", os.path.isdir(claude_dir))
if os.path.isdir(claude_dir):
    try:
        print(".claude ls  :", os.listdir(claude_dir))
    except OSError as e:
        print(".claude ls  : ERR", e)
creds = tracker._read_creds()
print("creds keys  :", list(creds.keys()))
if sys.platform == "win32":
    try:
        out = subprocess.run(["cmdkey", "/list"], capture_output=True, text=True, timeout=10).stdout
        hits = [ln.strip() for ln in out.splitlines() if "claude" in ln.lower()]
        print("cmdkey claude:", hits or "(none found in Credential Manager)")
    except Exception as e:
        print("cmdkey      : ERR", type(e).__name__, e)

print("\n== CODEX ==")
print("codex home  :", tracker.CODEX_HOME, "| exists:", os.path.isdir(tracker.CODEX_HOME))
print("auth.json   :", os.path.exists(tracker.CODEX_AUTH))
print("state db    :", os.path.exists(tracker.CODEX_STATE_DB))
print("binary      :", tracker._codex_binary())
try:
    out = subprocess.run(["where", "codex"], capture_output=True, text=True, timeout=10)
    print("where codex :", out.stdout.strip() or out.stderr.strip() or "(not found)")
except Exception as e:
    print("where codex : ERR", type(e).__name__, e)

print("\n== CLAUDE LIVE TEST ==")
tok = creds.get("accessToken")
if not tok:
    print("No accessToken -> live can't run (this is why Claude shows 'estimate').")
else:
    req = urllib.request.Request(
        "https://api.anthropic.com/api/oauth/usage",
        headers={"Authorization": f"Bearer {tok}",
                 "anthropic-beta": "oauth-2025-04-20",
                 "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=12, context=tracker._SSL_CTX) as r:
            d = json.load(r)
        print("LIVE OK     :", list(d.keys()))
    except urllib.error.HTTPError as e:
        print("HTTPError   :", e.code, e.read()[:200])
    except Exception as e:
        print("ERR         :", type(e).__name__, e)
