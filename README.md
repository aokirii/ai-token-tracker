# AI Token Tracker

A small desktop panel that shows your **Claude**, **Codex**, and **Antigravity** token
usage at a glance. Built with [pywebview](https://pywebview.flowrl.com/) — a real native
window with an HTML/CSS UI (no Electron).

For Claude it pulls the **official** usage percentages (5-hour and 7-day rolling windows)
straight from Anthropic, so what you see matches your plan limits — not a guess.

```
AI Token Tracker
┌────────────────────────────────────────────────┐
│ ● Claude  PRO                             27%    │
│ ████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│ 27% · 5h window                         7-day: 3%│
│ resets in 4h 13m · live                          │
├────────────────────────────────────────────────┤
│ ● Codex  PLUS                              0%    │
│ 0 / 1,000,000 tokens                      manual │
├────────────────────────────────────────────────┤
│ ● Antigravity  FREE                        0%    │
└────────────────────────────────────────────────┘
```

## Features

- **Live Claude usage** — official 5h / 7d utilization % and exact reset time.
- **Per-provider plan badge** next to each name — Claude's is auto-detected from your
  credentials; the others are set in config.
- **Auto-refresh** with a network throttle (the UI polls often, the API is hit at most
  once per minute).
- **Graceful fallback chain**: live API → official local cache → token estimate from logs.
- **Color-coded** progress bars (green < 70%, amber < 90%, red ≥ 90%).
- **YAML config**, with user-specific settings kept in a separate, git-ignored file.

## Platform support

This is **not Linux-only**. `pywebview` is cross-platform, and the data sources
(`~/.claude/...`) exist anywhere Claude Code is installed.

| OS | Status | Notes |
|----|--------|-------|
| **Linux** | Primary | Needs WebKit2GTK (`gir1.2-webkit2-4.1` / `libwebkit2gtk-4.1`). `install.sh` adds a GNOME app launcher. |
| **macOS** | Supported | Uses the built-in WebKit. Run with `./run.sh` or `python tracker.py`. |
| **Windows** | Supported | Needs the [WebView2 runtime](https://developer.microsoft.com/microsoft-edge/webview2/). Run `python tracker.py` (the `.sh` scripts and `.desktop` launcher are POSIX-only). |

## Requirements

- Python 3.9+
- Dependencies in [`requirements.txt`](requirements.txt): `pywebview`, `PyYAML`
- A platform webview backend (see the table above)
- Claude Code logged in (provides `~/.claude/.credentials.json`) for live Claude data

## Installation

### Linux / macOS (recommended)

```bash
git clone <your-repo-url> ai-token-tracker
cd ai-token-tracker
./install.sh
```

`install.sh` creates a `.venv`, installs dependencies, copies the config template to
`config/user.config.yaml`, and (on Linux) registers a desktop launcher.

### Manual / Windows

```bash
python3 -m venv --system-site-packages .venv   # omit --system-site-packages on Windows/macOS
.venv/bin/pip install -r requirements.txt        # Windows: .venv\Scripts\pip
cp config/user.config.example.yaml config/user.config.yaml
.venv/bin/python tracker.py                       # Windows: .venv\Scripts\python tracker.py
```

## Usage

- Run `./run.sh`, or launch **AI Token Tracker** from your app menu (Linux).
- Windows/macOS: `python tracker.py`.

## Configuration

All settings live under `config/` as YAML.

### `config/config.yaml` — app / display settings (committed)

| Key | Meaning |
|-----|---------|
| `window_hours` | Rolling window length (Claude Pro = 5h). |
| `refresh_seconds` | How often the UI refreshes. |
| `live_interval_seconds` | Minimum gap between live API calls. |
| `providers[]` | Each provider's `name`, `color`, `source`, `plan`, and (for manual ones) `used` / `limit`. |

`source` is either `claude_auto` (fetched automatically) or `manual` (you fill in `used`/`limit`).

`plan` is the small badge shown next to the provider name. Use `auto` on `claude_auto` to
detect it from your Claude credentials, or set a fixed label (e.g. `plus`, `free`) for the
others.

### `config/user.config.yaml` — user-specific (git-ignored)

Copied from `config/user.config.example.yaml`. Holds your identity and the paths the app
reads from. `~` expands to your home directory.

```yaml
user:
  name: your-username
  home: /home/you
paths:
  claude_credentials: ~/.claude/.credentials.json
  claude_projects_glob: ~/.claude/projects/**/*.jsonl
  claude_usage_cache: ~/.tokentracker/tracker/claude-usage-limits-cache.json
```

If this file is missing, the app falls back to the example template and then to the default
`~` paths.

## How it works

For Claude, data is resolved in priority order:

1. **Live** — calls `https://api.anthropic.com/api/oauth/usage` with the OAuth token from
   `~/.claude/.credentials.json`. Returns official `five_hour` / `seven_day` utilization and
   reset times. Also refreshes the local cache.
2. **Cache** — reads `claude-usage-limits-cache.json` (written by the live call above and by
   [tokentracker-cli](https://www.npmjs.com/package/tokentracker-cli) if you use it) when the
   token is expired or offline.
3. **Estimate** — sums token counts from `~/.claude/projects/**/*.jsonl` over the window as a
   last resort.

The live call is throttled by `live_interval_seconds`, so frequent UI refreshes don't spam
the endpoint.

## Limitations

- **Codex & Antigravity are manual** for now — set `used`/`limit` in `config.yaml`. (The same
  approach could be wired to their usage endpoints later.)
- Live Claude data stops when the OAuth token expires; run `claude` once to refresh it, and the
  app falls back to the cache in the meantime.
- The `.desktop` launcher uses an absolute path; if you move the project, re-run `install.sh`.

## License

[MIT](LICENSE)
