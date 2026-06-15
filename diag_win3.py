"""Temporary Windows locator — hunts for where Claude Code keeps its login.
Run from the project folder:  .venv\\Scripts\\python diag_win3.py
Safe to delete afterwards.
"""
import os
import subprocess


def run(cmd, timeout=180):
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        txt = (out.stdout or "") + (("\n" + out.stderr) if out.stderr else "")
        return txt.strip() or "(empty)"
    except Exception as e:
        return f"ERR {type(e).__name__}: {e}"


home = os.path.expanduser("~")
appdata = os.environ.get("APPDATA", "")
localappdata = os.environ.get("LOCALAPPDATA", "")

print("== claude.exe / claude-named folders ==")
for env in ("USERPROFILE", "LOCALAPPDATA", "APPDATA", "ProgramFiles", "ProgramFiles(x86)"):
    root = os.environ.get(env)
    if root and os.path.isdir(root):
        print(f"[{env}] claude.exe:", run(["where", "/r", root, "claude.exe"]))
for env in ("APPDATA", "LOCALAPPDATA"):
    root = os.environ.get(env)
    if root and os.path.isdir(root):
        print(f"[{env}] *laude* dirs:",
              run(["cmd", "/c", "dir", "/s", "/b", "/ad", os.path.join(root, "*laude*")]))

print("\n== files containing the OAuth token ==")
search_dirs = [
    os.path.join(home, ".claude"),
    os.path.join(appdata, "Claude"),
    os.path.join(localappdata, "Claude"),
    os.path.join(localappdata, "AnthropicClaude"),
    os.path.join(localappdata, "Programs", "claude"),
]
for d in search_dirs:
    if d and os.path.isdir(d):
        print(f"[{d}]")
        print(run(["findstr", "/s", "/i", "/m", "claudeAiOauth", os.path.join(d, "*")]))

print("\n== .credentials.json anywhere under home ==")
print(run(["where", "/r", home, ".credentials.json"]))

print("\n== Credential Manager (full list — look for Claude/Anthropic) ==")
print(run(["cmdkey", "/list"]))
