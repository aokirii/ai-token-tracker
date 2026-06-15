"""Temporary Codex app-server diagnostic — dumps raw JSON-RPC responses.
Run from the project folder:  .venv/bin/python diag_codex.py
Safe to delete afterwards.
"""
import json
import queue
import subprocess
import threading
import time

import tracker

codex = tracker._codex_binary()
print("codex binary:", codex)
if not codex:
    raise SystemExit("No codex binary found. Check `which codex` and ~/.codex/...")

requests = [
    {"jsonrpc": "2.0", "id": 1, "method": "initialize",
     "params": {"clientInfo": {"name": "diag", "version": "0.1"},
                "capabilities": {"experimentalApi": True}}},
    {"jsonrpc": "2.0", "id": 2, "method": "account/read", "params": {"refreshToken": False}},
    {"jsonrpc": "2.0", "id": 3, "method": "account/rateLimits/read", "params": None},
    {"jsonrpc": "2.0", "id": 4, "method": "account/usage/read", "params": None},
]

proc = subprocess.Popen(
    [codex, "app-server", "--stdio"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    text=True, bufsize=1,
)

q = queue.Queue()


def reader(stream, label):
    for line in iter(stream.readline, ""):
        q.put((label, line))


for lbl, st in (("OUT", proc.stdout), ("ERR", proc.stderr)):
    threading.Thread(target=reader, args=(st, lbl), daemon=True).start()

for r in requests:
    proc.stdin.write(json.dumps(r) + "\n")
    proc.stdin.flush()

deadline = time.time() + 15
while time.time() < deadline:
    try:
        lbl, line = q.get(timeout=0.5)
    except queue.Empty:
        continue
    line = line.rstrip()
    if line:
        print(lbl, line[:900])

proc.terminate()
try:
    proc.wait(timeout=2)
except subprocess.TimeoutExpired:
    proc.kill()
