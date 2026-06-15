"""Temporary Windows locator — finds the claude CLI and codex.exe.
Run from the project folder:  .venv\\Scripts\\python diag_win2.py
Safe to delete afterwards.
"""
import os
import subprocess


def run(cmd, timeout=120):
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        txt = out.stdout.strip()
        if out.stderr.strip():
            txt = (txt + "\n" + out.stderr.strip()).strip()
        return txt or "(empty)"
    except Exception as e:
        return f"ERR {type(e).__name__}: {e}"


home = os.path.expanduser("~")

print("== CLAUDE ==")
print("where claude :", run(["where", "claude"]))
print("creds file   :", os.path.exists(os.path.join(home, ".claude", ".credentials.json")))

print("\n== CODEX.EXE SEARCH ==")
print("where codex  :", run(["where", "codex"]))
for env in ("USERPROFILE", "LOCALAPPDATA", "APPDATA", "ProgramFiles", "ProgramFiles(x86)"):
    root = os.environ.get(env)
    if root and os.path.isdir(root):
        print(f"\n[{env}] {root}")
        print(run(["where", "/r", root, "codex.exe"]))

print("\n== CODEX APP FOLDERS ==")
for env in ("LOCALAPPDATA", "ProgramFiles", "ProgramFiles(x86)"):
    root = os.environ.get(env)
    if root and os.path.isdir(root):
        print(f"[{env}] codex dirs:", run(["cmd", "/c", "dir", "/s", "/b", "/ad",
                                           os.path.join(root, "*codex*")]))
