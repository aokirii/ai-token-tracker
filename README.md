# AI Token Tracker

A small desktop panel that shows your **Claude**, **Codex**, and **Antigravity** token
usage at a glance. Built with [pywebview](https://pywebview.flowrl.com/) — a real native
window with an HTML/CSS UI (no Electron).

For Claude it pulls the **official** usage percentages (5-hour and 7-day rolling windows)
straight from Anthropic, so what you see matches your plan limits — not a guess. It also
shows, **for Claude only**, how full the context window of each open Claude Code session
is (one bar per session), and splits every Claude bar into **input / cache / output**
token segments so you can see what your usage is made of. A **☰ menu** (top-left) switches
between three views: **live**, an **offline** summary of your Claude token usage over the last
day / week / month, and a **heatmap** of daily and hour-of-day usage.
For Codex it reads your local `~/.codex` login through the Codex app-server.

```
☰  AI Token Tracker
┌────────────────────────────────────────────────┐
│ ● Claude  PRO                             27%    │
│ input 2% · cache 19% · output 6%                 │
│ ████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│ 27% · 5h window                       18.6.26: 3%│
│ resets in 4h 13m · live                          │
│ CONTEXT 1                                  12%   │
│ input 1% · cache 8% · output 3%                  │
│ █████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│ 120,000 / 1,000,000 tokens          claude-opus │
│ CONTEXT 2                                  31%   │
│ input 1% · cache 23% · output 7%                 │
│ ██████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│ 310,000 / 1,000,000 tokens          claude-opus │
├────────────────────────────────────────────────┤
│ ● Codex  PLUS                             12%    │
│ 12% · 5h window                      18.6.26: 4%│
├────────────────────────────────────────────────┤
│ ● Antigravity  FREE                        0%    │
└────────────────────────────────────────────────┘
```

The **offline** view (☰ → Offline) summarises Claude token usage per window, each split the
same way:

```
☰  AI Token Tracker
┌────────────────────────────────────────────────┐
│ Daily · 24h                     1,250,000 tokens │
│ input 4% · cache 70% · output 26%                │
│ ██░░████████████████████████████░░███████████░  │
├────────────────────────────────────────────────┤
│ Weekly · 7d                     8,400,000 tokens │
│ input 3% · cache 71% · output 26%                │
│ █░░█████████████████████████████░░███████████░  │
├────────────────────────────────────────────────┤
│ Monthly · 30d                  21,900,000 tokens │
│ input 3% · cache 72% · output 25%                │
│ █░░██████████████████████████████░░██████████░  │
└────────────────────────────────────────────────┘
```

## Features

- **Live Claude usage** — official 5h / 7d utilization % and exact reset time.
- **Claude context window** *(Claude only)* — a separate bar per open Claude Code session
  showing how full its context window is (tokens used / window size), with the session's
  model. Open sessions are detected automatically, so each stays visible while it runs.
- **Token-type breakdown** *(Claude only)* — every Claude bar (the 5h rate window and each
  session's context) is split into **input**, **cache**, and **output** colored segments
  that sum to the bar's fill, so you can see what your usage is made of.
- **Live / Offline / Heatmap views** *(Claude only)* — a **☰ menu** switches between the live
  dashboard, an **offline** summary of your Claude token usage over the last day / week / month
  (same input / cache / output split), and a **heatmap** showing daily usage over the last 12
  weeks plus an hour-of-day punch-card (weekday × hour). Offline and heatmap are snapshots,
  computed on demand.
- **Live Codex usage** — Codex plan and rate-limit percentage from your local `~/.codex`
  session.
- **Per-provider plan badge** next to each name — Claude and Codex can be auto-detected.
- **Auto-refresh** with a network throttle (the UI polls often, the API is hit at most
  once per minute).
- **Graceful fallback chain**: live API → official local cache → token estimate from logs.
- **Color-coded** — each percentage figure goes green < 70%, amber < 90%, red ≥ 90%.
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

You only install once. To launch the app on later runs, you **don't** need to reinstall or activate
the venv — just call the venv's Python directly from the project folder:

- **Linux** — `./run.sh`, or launch **AI Token Tracker** from your app menu (registered by `install.sh`).
- **macOS** — `.venv/bin/python tracker.py` (or `./run.sh`).
- **Windows** — `.venv\Scripts\python tracker.py`

Activating the venv first (`source .venv/bin/activate` / `.venv\Scripts\activate.bat`) is optional — it
only lets you type the shorter `python tracker.py`.

### Double-click launchers (no terminal)

After the one-time install, you can start the app without a terminal:

- **Windows** — double-click **`start.bat`** (runs with `pythonw`, so no console window appears).
- **macOS** — double-click **`start.command`**. The first time, right-click it → **Open** to get past
  Gatekeeper (it's an unsigned script); after that a normal double-click works.

Both live in the project folder and just run the app from `.venv`.

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
| `providers[].context_limit` | *(Claude only)* Context-window size. `auto` reads the configured model for the `[1m]` beta, else assumes 200k and bumps to 1M once usage passes 200k. Or pin `200000` / `1000000`. |
| `providers[].context_sessions` | *(Claude only)* Max number of open Claude sessions to show separate context bars for (default `3`). |

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
  claude_settings: ~/.claude/settings.json
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

### Claude context window (Claude only)

Separately from the rate windows above, each open Claude Code session gets its own context
bar:

1. **Detect open sessions** — from running `claude` processes and their working directories
   (`/proc` on Linux, `pgrep` + `lsof` on macOS). On other platforms, or if that can't be
   read, it falls back to the session logs written most recently. So a session stays visible
   for as long as it is open, even while idle.
2. **Read each session** — the latest entry in that session's
   `~/.claude/projects/**/*.jsonl` gives the tokens occupying the window (input + cache +
   output). Each bar is labelled by the session's working directory so you can tell them
   apart.
3. **Window size** — `auto` reads the configured model from `~/.claude/settings.json` (and
   any project settings); the `[1m]` beta means a 1M window, otherwise 200k. You can pin it
   with `context_limit`.

### Token-type breakdown (Claude only)

Every Claude bar — the 5h rate window and each session's context — is split into **input**,
**cache**, and **output** segments:

- The proportions come from the session (or, for the rate bar, the rate window) totals of
  `input_tokens`, `cache_creation_input_tokens`, and `output_tokens`. **Cache *reads* are
  excluded** — they re-count the same history every turn and would otherwise drown out
  everything else.
- Those proportions are scaled to the bar's fill, so the three segments always sum to the
  percent shown. `input` is usually small because most input gets cached (and so shows up
  under `cache`); `output` is what Claude generated.

### Offline view (Claude only)

The **☰ → Offline** view sums the same `input` / `cache-write` / `output` tokens (cache reads
again excluded) across `~/.claude/projects/**/*.jsonl` over three rolling windows — the last
**24h**, **7d** and **30d** — and shows each period's total with its input/cache/output split.
It's computed on demand when you open it (not polled), so the heavier 30-day scan doesn't run
while you're watching the live view.

### Heatmap view (Claude only)

The **☰ → Heatmap** view buckets the same tokens (cache reads excluded) by **local** time into
two grids, each cell shaded 0–4 by intensity relative to the busiest bucket:

- **Daily** — a GitHub-style grid of the last 12 weeks (columns = weeks, rows = Mon–Sun), one
  cell per calendar day.
- **By hour of day** — a punch-card of weekday × hour (rows = Mon–Sun, columns = 0–23h), so you
  can see when in the day and week you actually use Claude.

Hover any cell for its date/hour and token total. Also computed on demand.

All of this is read-only and local — nothing here is sent anywhere.

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
- **Context bars are Claude-only.** Process-based detection of open sessions runs on Linux and
  macOS; elsewhere it falls back to the most recently active session logs.
- The `.desktop` launcher uses an absolute path; if you move the project, re-run `install.sh`.

## License

[MIT](LICENSE)
