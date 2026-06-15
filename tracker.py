#!/usr/bin/env python3
"""AI Token Tracker — desktop panel.

Pulls Claude usage automatically:
  1. live: https://api.anthropic.com/api/oauth/usage (official 5h / 7d utilization %)
  2. cache: ~/.tokentracker/tracker/claude-usage-limits-cache.json
  3. jsonl: token estimate from ~/.claude/projects/**/*.jsonl
Codex usage is pulled through the local Codex app-server and mirrored to YAML.
Antigravity is manual for now (values come from config/config.yaml).
The UI opens as a real desktop window via pywebview.
"""

import base64
import glob
import json
import os
import queue
import shutil
import sqlite3
import ssl
import subprocess
import sys
import threading
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

import yaml

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(BASE_DIR, "config")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.yaml")
UI_PATH = os.path.join(BASE_DIR, "ui.html")

# Default paths; can be overridden by config/user.config.yaml.
_DEFAULT_PATHS = {
    "claude_credentials": "~/.claude/.credentials.json",
    "claude_projects_glob": "~/.claude/projects/**/*.jsonl",
    "claude_usage_cache": "~/.tokentracker/tracker/claude-usage-limits-cache.json",
    "codex_home": "~/.codex",
    "codex_binary": "",
}


def _load_yaml(path):
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except (OSError, yaml.YAMLError):
        return {}


def _load_user_config():
    """User-specific settings. Prefer user.config.yaml, fall back to the example template."""
    for fn in ("user.config.yaml", "user.config.example.yaml"):
        path = os.path.join(CONFIG_DIR, fn)
        if os.path.exists(path):
            data = _load_yaml(path)
            if data:
                return data
    return {}


_USER_CFG = _load_user_config()
_paths = {**_DEFAULT_PATHS, **_USER_CFG.get("paths", {})}


def _resolve_path(path):
    expanded = os.path.expanduser(path)
    if os.path.isabs(expanded):
        return expanded
    return os.path.join(BASE_DIR, expanded)


CLAUDE_GLOB = os.path.expanduser(_paths["claude_projects_glob"])
CLAUDE_CACHE = os.path.expanduser(_paths["claude_usage_cache"])
CLAUDE_CREDS = os.path.expanduser(_paths["claude_credentials"])
CODEX_HOME = _resolve_path(_paths["codex_home"])
CODEX_AUTH = os.path.join(CODEX_HOME, "auth.json")
CODEX_STATE_DB = os.path.join(CODEX_HOME, "state_5.sqlite")


def load_config():
    return _load_yaml(CONFIG_PATH)


def _parse_ts(ts):
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def _minutes_until(ts_str):
    dt = _parse_ts(ts_str)
    if dt is None:
        return None
    return max(0, int((dt - datetime.now(timezone.utc)).total_seconds() // 60))


def _minutes_until_epoch(value):
    if value in (None, ""):
        return None
    try:
        ts = float(value)
    except (TypeError, ValueError):
        return None
    if ts > 10_000_000_000:
        ts = ts / 1000
    dt = datetime.fromtimestamp(ts, timezone.utc)
    return max(0, int((dt - datetime.now(timezone.utc)).total_seconds() // 60))


def _read_creds():
    """Claude OAuth creds. Linux/Windows use the file; macOS stores them in the
    login Keychain (the file is absent there)."""
    try:
        return json.load(open(CLAUDE_CREDS, encoding="utf-8")).get("claudeAiOauth", {})
    except (OSError, ValueError):
        pass
    if sys.platform == "darwin":
        try:
            out = subprocess.run(
                ["security", "find-generic-password", "-s", "Claude Code-credentials", "-w"],
                capture_output=True, text=True, timeout=5,
            ).stdout.strip()
            if out:
                return json.loads(out).get("claudeAiOauth", {})
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
    return {}


def subscription_type():
    return _read_creds().get("subscriptionType")


def _shape(fh, sd, origin):
    """Normalize Anthropic/cache windows into a common shape."""
    fh, sd = fh or {}, sd or {}
    if not fh:
        return None
    return {
        "pct": fh.get("utilization", 0),
        "resets_in": _minutes_until(fh.get("resets_at")),
        "seven_day_pct": (sd or {}).get("utilization"),
        "seven_day_resets_at": (sd or {}).get("resets_at"),
        "seven_day_resets_in": _minutes_until((sd or {}).get("resets_at")),
        "origin": origin,
    }


def _ssl_context():
    """certifi-backed CA bundle so HTTPS works on macOS python.org Python,
    which otherwise fails with CERTIFICATE_VERIFY_FAILED (no local CA issuer)."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


_SSL_CTX = _ssl_context()


def claude_live():
    """Call Anthropic /api/oauth/usage directly. None on failure."""
    creds = _read_creds()
    tok = creds.get("accessToken")
    exp = creds.get("expiresAt")
    if not tok:
        return None
    if exp and int(exp) / 1000 <= datetime.now(timezone.utc).timestamp():
        return None  # token expired: fall back to cache
    req = urllib.request.Request(
        "https://api.anthropic.com/api/oauth/usage",
        headers={
            "Authorization": f"Bearer {tok}",
            "anthropic-beta": "oauth-2025-04-20",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=12, context=_SSL_CTX) as r:
            d = json.load(r)
    except (urllib.error.URLError, OSError, ValueError):
        return None
    res = _shape(d.get("five_hour"), d.get("seven_day"), "live")
    if res:
        _write_cache(d)  # keep the cache warm too
    return res


def _write_cache(body):
    try:
        os.makedirs(os.path.dirname(CLAUDE_CACHE), exist_ok=True)
        json.dump({"claude": {
            "five_hour": body.get("five_hour"),
            "seven_day": body.get("seven_day"),
            "seven_day_opus": body.get("seven_day_opus"),
            "extra_usage": body.get("extra_usage"),
            "cached_at": datetime.now(timezone.utc).isoformat(),
        }}, open(CLAUDE_CACHE, "w", encoding="utf-8"))
    except OSError:
        pass


def claude_from_cache():
    """Return Claude utilization from the official cache, or None."""
    try:
        c = json.load(open(CLAUDE_CACHE, encoding="utf-8")).get("claude", {})
    except (OSError, ValueError):
        return None
    return _shape(c.get("five_hour"), c.get("seven_day"), "cache")


# Live-call throttle: even if the UI refreshes often, the network is hit at most
# once per min_interval seconds.
_live = {"at": 0.0, "data": None}


def claude_auto(min_interval):
    now = time.time()
    if now - _live["at"] >= min_interval:
        _live["at"] = now
        fresh = claude_live()
        if fresh:
            _live["data"] = fresh
    return _live["data"] or claude_from_cache()


def claude_from_jsonl(window_hours):
    """Fallback when no cache: estimate tokens from the last window_hours of jsonl."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=window_hours)
    total, earliest = 0, None
    for path in glob.glob(CLAUDE_GLOB, recursive=True):
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    try:
                        d = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    ts = _parse_ts(d.get("timestamp"))
                    if ts is None or ts < cutoff:
                        continue
                    u = (d.get("message") or {}).get("usage")
                    if not u:
                        continue
                    total += (u.get("input_tokens", 0) + u.get("output_tokens", 0)
                              + u.get("cache_creation_input_tokens", 0)
                              + u.get("cache_read_input_tokens", 0))
                    if earliest is None or ts < earliest:
                        earliest = ts
        except OSError:
            continue
    resets_in = None
    if earliest is not None:
        resets_in = max(0, int(((earliest + timedelta(hours=window_hours)) - now)
                              .total_seconds() // 60))
    return total, resets_in


def _fmt_reset(minutes):
    if minutes is None:
        return ""
    h, m = divmod(minutes, 60)
    if h >= 24:
        d, h = divmod(h, 24)
        return f"resets in {d}d {h}h"
    return "resets in " + (f"{h}h {m}m" if h else f"{m}m")


def _fmt_tokens(n):
    return f"{n:,}"


def _fmt_window(minutes):
    if not minutes:
        return "rate window"
    h, m = divmod(int(minutes), 60)
    if h and not m:
        return f"{h}h window"
    if h:
        return f"{h}h {m}m window"
    return f"{m}m window"


def _fmt_date_epoch(value):
    if value in (None, ""):
        return ""
    try:
        ts = float(value)
    except (TypeError, ValueError):
        return ""
    if ts > 10_000_000_000:
        ts = ts / 1000
    dt = datetime.fromtimestamp(ts, timezone.utc)
    return f"{dt.day}.{dt.month}.{dt.strftime('%y')}"


def _fmt_date_ts(value):
    dt = _parse_ts(value)
    if dt is None:
        return ""
    return f"{dt.day}.{dt.month}.{dt.strftime('%y')}"


def _jwt_payload(token):
    parts = (token or "").split(".")
    if len(parts) < 2:
        return {}
    payload = parts[1] + "=" * ((4 - len(parts[1]) % 4) % 4)
    try:
        return json.loads(base64.urlsafe_b64decode(payload))
    except (ValueError, TypeError):
        return {}


def _codex_auth():
    try:
        return json.load(open(CODEX_AUTH, encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def codex_plan_from_auth():
    tokens = (_codex_auth().get("tokens") or {})
    for key in ("access_token", "id_token"):
        auth_claims = _jwt_payload(tokens.get(key)).get("https://api.openai.com/auth") or {}
        plan = auth_claims.get("chatgpt_plan_type")
        if plan:
            return plan
    return None


def _codex_binary():
    configured = _paths.get("codex_binary")
    if configured and str(configured).lower() != "auto":
        path = _resolve_path(configured)
        return path if os.path.exists(path) else configured
    candidates = glob.glob(os.path.join(CODEX_HOME, "packages/standalone/releases/*/bin/codex"))
    if candidates:
        return max(candidates, key=os.path.getmtime)
    # npm / homebrew installs land on PATH
    found = shutil.which("codex")
    if found:
        return found
    # Well-known locations not on PATH — the macOS Codex.app (where `codex` is only a
    # shell alias) and the Windows Codex install under %LOCALAPPDATA%.
    localappdata = os.environ.get("LOCALAPPDATA", "")
    candidates = [
        "/Applications/Codex.app/Contents/Resources/codex",
        os.path.expanduser("~/Applications/Codex.app/Contents/Resources/codex"),
        "/opt/homebrew/bin/codex",
        "/usr/local/bin/codex",
        os.path.expanduser("~/.codex/bin/codex"),
    ]
    if localappdata:
        candidates.append(os.path.join(localappdata, "OpenAI", "Codex", "bin", "codex.exe"))
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def _stream_reader(stream, label, out):
    try:
        for line in iter(stream.readline, ""):
            out.put((label, line))
    except (OSError, ValueError):
        pass


def _codex_rpc(timeout=18):
    codex = _codex_binary()
    if not codex:
        return {}
    requests = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "clientInfo": {"name": "token-tracker", "version": "0.1"},
                "capabilities": {"experimentalApi": True},
            },
        },
        {"jsonrpc": "2.0", "id": 2, "method": "account/read", "params": {"refreshToken": False}},
        {"jsonrpc": "2.0", "id": 3, "method": "account/rateLimits/read", "params": None},
        {"jsonrpc": "2.0", "id": 4, "method": "account/usage/read", "params": None},
    ]
    proc = None
    try:
        proc = subprocess.Popen(
            [codex, "app-server", "--stdio"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        lines = queue.Queue()
        for label, stream in (("stdout", proc.stdout), ("stderr", proc.stderr)):
            threading.Thread(target=_stream_reader, args=(stream, label, lines), daemon=True).start()
        for req in requests:
            proc.stdin.write(json.dumps(req) + "\n")
            proc.stdin.flush()
        results = {}
        deadline = time.time() + timeout
        while time.time() < deadline and len(results) < len(requests):
            try:
                label, line = lines.get(timeout=max(0.1, min(0.5, deadline - time.time())))
            except queue.Empty:
                continue
            if label != "stdout":
                continue
            try:
                msg = json.loads(line)
            except ValueError:
                continue
            req_id = msg.get("id")
            if req_id is not None:
                results[req_id] = msg.get("result")
        return results
    except (OSError, ValueError, subprocess.SubprocessError):
        return {}
    finally:
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()


def _codex_local_tokens():
    if not os.path.exists(CODEX_STATE_DB):
        return None
    try:
        con = sqlite3.connect(f"file:{CODEX_STATE_DB}?mode=ro", uri=True)
        row = con.execute("select coalesce(sum(tokens_used), 0) from threads").fetchone()
        return int(row[0] or 0)
    except (OSError, sqlite3.Error, TypeError, ValueError):
        return None


def _codex_snapshot_from_rpc(results):
    account = ((results.get(2) or {}).get("account") or {})
    rate = results.get(3) or {}
    usage = results.get(4) or {}
    by_id = rate.get("rateLimitsByLimitId") or {}
    snap = by_id.get("codex") or rate.get("rateLimits") or {}
    primary = snap.get("primary") or {}
    secondary = snap.get("secondary") or {}
    summary = usage.get("summary") or {}
    plan = snap.get("planType") or account.get("planType") or codex_plan_from_auth()
    pct = primary.get("usedPercent")
    if pct is None:
        pct = 0
    return {
        "plan": plan,
        "pct": pct,
        "origin": "live",
        "limit_id": snap.get("limitId") or "codex",
        "limit_name": snap.get("limitName"),
        "primary": {
            "used_percent": primary.get("usedPercent"),
            "resets_at": primary.get("resetsAt"),
            "resets_in": _minutes_until_epoch(primary.get("resetsAt")),
            "window_duration_mins": primary.get("windowDurationMins"),
        },
        "secondary": {
            "used_percent": secondary.get("usedPercent"),
            "resets_at": secondary.get("resetsAt"),
            "resets_in": _minutes_until_epoch(secondary.get("resetsAt")),
            "window_duration_mins": secondary.get("windowDurationMins"),
        },
        "usage": {
            "lifetime_tokens": summary.get("lifetimeTokens"),
        },
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def _codex_fallback_snapshot():
    plan = codex_plan_from_auth()
    tokens = _codex_local_tokens()
    if not plan and tokens is None:
        return None
    return {
        "plan": plan,
        "pct": 0,
        "origin": "local",
        "limit_id": "codex",
        "limit_name": None,
        "primary": {},
        "secondary": {},
        "usage": {"lifetime_tokens": tokens},
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


_codex_live = {"at": 0.0, "data": None}


def codex_auto(min_interval):
    now = time.time()
    if now - _codex_live["at"] >= min_interval:
        _codex_live["at"] = now
        data = None
        results = _codex_rpc()
        if results.get(3):
            data = _codex_snapshot_from_rpc(results)
        if not data:
            data = _codex_fallback_snapshot()
        if data:
            _codex_live["data"] = data
    return _codex_live["data"]


class Api:
    """Bridge exposed to the pywebview frontend."""

    def get_data(self):
        cfg = load_config()
        window_hours = cfg.get("window_hours", 5)
        out = {
            "window_hours": window_hours,
            "refresh_seconds": cfg.get("refresh_seconds", 30),
            "providers": [],
        }
        for p in cfg.get("providers", []):
            # Per-provider plan label. 'auto' (or missing) on claude_auto: detect
            # from credentials; otherwise use the literal value from config.
            source = p.get("source")
            plan = p.get("plan")
            if source == "claude_auto" and (plan in (None, "auto")):
                plan = subscription_type()
            elif source == "codex_auto" and (plan in (None, "auto")):
                plan = codex_plan_from_auth()
            card = {
                "name": p.get("name"),
                "color": p.get("color", "#888"),
                "plan": plan or "",
            }
            if source == "claude_auto":
                data = claude_auto(cfg.get("live_interval_seconds", 60))
                if data:
                    note = "live" if data["origin"] == "live" else "cache (official)"
                    sub = _fmt_reset(data["resets_in"])
                    card.update(
                        pct=data["pct"],
                        primary=f"{data['pct']}% · {window_hours}h window",
                        sub=f"{sub} · {note}" if sub else note,
                        extra=(f"{_fmt_date_ts(data['seven_day_resets_at'])}: "
                               f"{data['seven_day_pct']}%"
                               if data["seven_day_pct"] is not None
                               and _fmt_date_ts(data["seven_day_resets_at"]) else ""),
                        source=data["origin"],
                    )
                else:
                    used, resets_in = claude_from_jsonl(window_hours)
                    limit = p.get("limit", 0) or 0
                    pct = round(used / limit * 100, 1) if limit else 0
                    card.update(
                        pct=pct,
                        primary=f"{_fmt_tokens(used)} / {_fmt_tokens(limit)} tokens",
                        sub=_fmt_reset(resets_in) or "estimate (no cache)",
                        extra="", source="jsonl",
                    )
            elif source == "codex_auto":
                data = codex_auto(cfg.get("live_interval_seconds", 60))
                if data:
                    primary = data.get("primary") or {}
                    secondary = data.get("secondary") or {}
                    usage = data.get("usage") or {}
                    pct = data.get("pct") or 0
                    plan = data.get("plan") or card["plan"]
                    reset = _fmt_reset(primary.get("resets_in"))
                    window = _fmt_window(primary.get("window_duration_mins"))
                    lifetime = usage.get("lifetime_tokens")
                    secondary_date = _fmt_date_epoch(secondary.get("resets_at"))
                    secondary_pct = secondary.get("used_percent")
                    card.update(
                        plan=plan or "",
                        pct=pct,
                        primary=f"{pct}% · {window}",
                        sub=f"{reset} · {data['origin']}" if reset else data["origin"],
                        extra=(f"{secondary_date}: {secondary_pct}%"
                               if secondary_date and secondary_pct is not None
                               else (f"lifetime: {_fmt_tokens(lifetime)}"
                                     if lifetime is not None else "")),
                        source=data["origin"],
                    )
                else:
                    used, limit = p.get("used", 0), p.get("limit", 0) or 0
                    pct = round(used / limit * 100, 1) if limit else 0
                    card.update(
                        pct=pct,
                        primary=f"{_fmt_tokens(used)} / {_fmt_tokens(limit)} tokens",
                        sub="codex unavailable", extra="", source="manual",
                    )
            else:
                used, limit = p.get("used", 0), p.get("limit", 0) or 0
                pct = round(used / limit * 100, 1) if limit else 0
                card.update(
                    pct=pct,
                    primary=f"{_fmt_tokens(used)} / {_fmt_tokens(limit)} tokens",
                    sub="manual", extra="", source="manual",
                )
            out["providers"].append(card)
        return out


def main():
    import webview
    cfg = load_config()
    window = webview.create_window(
        "AI Token Tracker", UI_PATH, js_api=Api(),
        width=420, height=540, resizable=True, background_color="#15151a",
    )
    webview.start()
    _ = (window, cfg)


if __name__ == "__main__":
    main()
