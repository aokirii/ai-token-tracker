# AI Token Tracker

A small desktop panel that shows your **Claude**, **Codex**, and **Antigravity** token
usage at a glance. Built with [pywebview](https://pywebview.flowrl.com/) — a real native
window with an HTML/CSS UI (no Electron).

For Claude it pulls the **official** usage percentages (5-hour and 7-day rolling windows)
straight from Anthropic, so what you see matches your plan limits — not a guess.
For Codex it reads your local `~/.codex` login through the Codex app-server.

```
AI Token Tracker
┌────────────────────────────────────────────────┐
│ ● Claude  PRO                             27%    │
│ ████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│ 27% · 5h window                       18.6.26: 3%│
│ resets in 4h 13m · live                          │
├────────────────────────────────────────────────┤
│ ● Codex  PLUS                             12%    │
│ 12% · 5h window                      18.6.26: 4%│
├────────────────────────────────────────────────┤
│ ● Antigravity  FREE                        0%    │
└────────────────────────────────────────────────┘
```

## Features

- **Live Claude usage** — official 5h / 7d utilization % and exact reset time.
- **Live Codex usage** — Codex plan and rate-limit percentage from your local `~/.codex`
  session.
- **Per-provider plan badge** next to each name — Claude and Codex can be auto-detected.
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
| **Linux** | Tested, working | Needs WebKit2GTK (`gir1.2-webkit2-4.1` / `libwebkit2gtk-4.1`). `install.sh` adds a GNOME app launcher. |
| **macOS** | Tested, working | Uses the built-in WebKit. Claude token is read from the login Keychain; the Codex.app binary is auto-detected. Run with `./run.sh` or `python tracker.py`. |
| **Windows** | Not yet tested | Should work (`pywebview` is cross-platform), but live Claude/Codex data hasn't been verified on Windows yet. Needs the [WebView2 runtime](https://developer.microsoft.com/microsoft-edge/webview2/). Run `python tracker.py` (the `.sh` scripts and `.desktop` launcher are POSIX-only). |

## Requirements

- Python 3.9+
- Dependencies in [`requirements.txt`](requirements.txt): `pywebview`, `PyYAML`
- A platform webview backend (see the table above)
- Claude Code logged in (provides `~/.claude/.credentials.json`) for live Claude data
- Codex logged in (provides `~/.codex/auth.json`) for live Codex data

## Installation

### Step 1 — Get the project (all platforms)

Clone it with Git, or download it as a ZIP from GitHub (**Code → Download ZIP**) and extract:

```bash
git clone https://github.com/aokirii/ai-token-tracker.git ai-token-tracker
cd ai-token-tracker
```

> Downloaded the ZIP instead of cloning? The extracted folder is named `ai-token-tracker-main`, so use
> `cd ai-token-tracker-main`. You must be inside this folder (it contains `tracker.py`) for the steps below.

No config file is required to run — the app uses sensible `~`-based defaults.

### Step 2 — Set up for your OS

Follow the one section that matches your system.

#### Linux

Prerequisite: WebKit2GTK (`gir1.2-webkit2-4.1` / `libwebkit2gtk-4.1`).

Quickest — `install.sh` creates the venv, installs dependencies, and registers a GNOME app launcher:

```bash
./install.sh
```

Or do it manually:

```bash
python3 -m venv --system-site-packages .venv   # --system-site-packages pulls in the system GTK/WebKit
.venv/bin/pip install -r requirements.txt
.venv/bin/python tracker.py
```

#### macOS

Uses the built-in WebKit (no extra runtime). The Claude token is read from the login Keychain — click
**Always Allow** if macOS prompts — and the Codex.app binary is auto-detected.

Quickest:

```bash
./install.sh
```

Or do it manually (note: **no** `--system-site-packages` on macOS):

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python tracker.py
```

#### Windows

Prerequisites: [Python 3.9+](https://www.python.org/downloads/) (tick **"Add python.exe to PATH"**) and
the [WebView2 runtime](https://developer.microsoft.com/microsoft-edge/webview2/) (preinstalled on
Windows 11). The `.sh` installer is POSIX-only, so use the steps below. They work in both
**Command Prompt (cmd)** and **PowerShell** — only the activation step (2) differs.

**1. Create the virtual environment** (same in both shells):

```bat
python -m venv .venv
```

**2. Activate it** — use the line for your shell:

```bat
:: Command Prompt (cmd)
.venv\Scripts\activate.bat
```

```powershell
# PowerShell
.venv\Scripts\Activate.ps1
```

Your prompt should now start with `(.venv)`. If PowerShell blocks the script with a policy error, run
once `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then activate again.

**3. Install and run** (same in both shells, with `(.venv)` active):

```bat
pip install -r requirements.txt
python tracker.py
```

> Use backslashes `\` in Windows paths. In cmd, forward-slash paths like `.venv/Scripts/...` fail with
> *"is not recognized"*, and the Linux `.venv/bin/...` paths don't exist on Windows. Don't pass
> `--system-site-packages` (Linux-only).

## Usage

- Run `./run.sh`, or launch **AI Token Tracker** from your app menu (Linux).
- Windows/macOS: `python tracker.py`.

## Configuration

All settings live under `config/` as YAML. The defaults work out of the box, so you can run the app
without editing anything — the keys below are only for customizing it.

### `config/config.yaml` — app / display settings (committed)

| Key | Meaning |
|-----|---------|
| `window_hours` | Rolling window length (Claude Pro = 5h). |
| `refresh_seconds` | How often the UI refreshes. |
| `live_interval_seconds` | Minimum gap between live API calls. |
| `providers[]` | Each provider's `name`, `color`, `source`, `plan`, and fallback `used` / `limit`. |

`source` is `claude_auto`, `codex_auto`, or `manual`.

`plan` is the small badge shown next to the provider name. Use `auto` on `claude_auto` or
`codex_auto` to detect it from local credentials, or set a fixed label (e.g. `plus`,
`free`).

### `config/user.config.yaml` — optional path overrides (git-ignored)

**Not required to run the app** — it falls back to the defaults below (all `~`-based, so they resolve
to your own home). Create this file only to point at non-default locations. `~` expands to your home
directory.

```yaml
paths:
  claude_credentials: ~/.claude/.credentials.json
  claude_projects_glob: ~/.claude/projects/**/*.jsonl
  claude_usage_cache: ~/.tokentracker/tracker/claude-usage-limits-cache.json
  codex_home: ~/.codex
  codex_binary: auto
```

If this file is missing, the app falls back to the example template and then to the default
`~` paths.

## How it works

For Claude, data is resolved in priority order:

1. **Live** — calls `https://api.anthropic.com/api/oauth/usage` with the OAuth token from
   `~/.claude/.credentials.json`. Returns official `five_hour` / `seven_day` utilization and
   reset times. Also refreshes the local cache.
2. **Cache** — reads `claude-usage-limits-cache.json`  when the token is expired or offline.
3. **Estimate** — sums token counts from `~/.claude/projects/**/*.jsonl` over the window as a
   last resort.

The live call is throttled by `live_interval_seconds`, so frequent UI refreshes don't spam
the endpoint.

For Codex, data is resolved in priority order:

1. **Live** — starts the local Codex app-server over stdio and reads `account/rateLimits/read`
   plus `account/usage/read`.
2. **Local fallback** — decodes the plan from `~/.codex/auth.json` and reads local
   `state_5.sqlite` token totals when the app-server is unavailable.

Codex usage is not written back to YAML; only the manual path and display settings live in
the config files.

## Limitations

- **Antigravity is manual** for now — set `used`/`limit` in `config.yaml`.
- Live Claude data stops when the OAuth token expires; run `claude` once to refresh it, and the
  app falls back to the cache in the meantime.
- The `.desktop` launcher uses an absolute path; if you move the project, re-run `install.sh`.

## License

[MIT](LICENSE)
