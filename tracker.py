#!/usr/bin/env python3
"""AI Token Tracker — desktop panel.

Pulls Claude usage automatically:
  1. live   -> https://api.anthropic.com/api/oauth/usage (official 5h / 7d utilization %)
  2. cache  -> ~/.tokentracker/tracker/claude-usage-limits-cache.json (written by tokentracker-cli)
  3. jsonl  -> token estimate from ~/.claude/projects/**/*.jsonl
Codex / Antigravity are manual for now (values come from config/config.yaml).
The UI opens as a real desktop window via pywebview.
"""

import json
import glob
import os
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
CLAUDE_GLOB = os.path.expanduser(_paths["claude_projects_glob"])
CLAUDE_CACHE = os.path.expanduser(_paths["claude_usage_cache"])
CLAUDE_CREDS = os.path.expanduser(_paths["claude_credentials"])


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


def _read_creds():
    try:
        return json.load(open(CLAUDE_CREDS, encoding="utf-8")).get("claudeAiOauth", {})
    except (OSError, ValueError):
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
        "seven_day_resets_in": _minutes_until((sd or {}).get("resets_at")),
        "origin": origin,
    }


def claude_live():
    """Call Anthropic /api/oauth/usage directly (same as tokentracker-cli). None on failure."""
    creds = _read_creds()
    tok = creds.get("accessToken")
    exp = creds.get("expiresAt")
    if not tok:
        return None
    if exp and int(exp) / 1000 <= datetime.now(timezone.utc).timestamp():
        return None  # token expired -> fall back to cache
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


class Api:
    """Bridge exposed to the pywebview frontend."""

    def get_data(self):
        cfg = load_config()
        window_hours = cfg.get("window_hours", 5)
        out = {
            "subscription": subscription_type(),
            "window_hours": window_hours,
            "refresh_seconds": cfg.get("refresh_seconds", 30),
            "providers": [],
        }
        for p in cfg.get("providers", []):
            card = {"name": p.get("name"), "color": p.get("color", "#888")}
            if p.get("source") == "claude_auto":
                data = claude_auto(cfg.get("live_interval_seconds", 60))
                if data:
                    note = "live" if data["origin"] == "live" else "cache (official)"
                    sub = _fmt_reset(data["resets_in"])
                    card.update(
                        pct=data["pct"],
                        primary=f"{data['pct']}% · {window_hours}h window",
                        sub=f"{sub} · {note}" if sub else note,
                        extra=(f"7-day: {data['seven_day_pct']}%"
                               if data["seven_day_pct"] is not None else ""),
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
