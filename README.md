# 🎵 Audiera — AI Song Agent

> Create full songs from plain English. Describe what you want — Audiera writes the lyrics, generates the music, and delivers it straight to your Telegram. Now with **fully autonomous mode** that generates songs on its own with zero human input.

**Developer:** Saqueeb

---

## What's New in v3.2.0

| Feature | Details |
|---|---|
| `/auto_mode` | Fully autonomous generation — no human input needed |
| Time-aware moods | Mood chosen by time-of-day (morning = energetic, night = dark/chill) |
| Day-aware styles | Style chosen by day-of-week (Friday = Dance/EDM, Sunday = Soul/Jazz) |
| Adaptive interval | Loop speeds up on success, backs off on failure automatically |
| Artist rotation | Cycles through all 12 artists so no one is skipped |
| Modern CLI design | Structured log lines with timestamps, icons, and colors |
| Live spinner | Shows elapsed time `[01:23]` while generating |
| Rounded card UI | All panels use modern `╭─╮` rounded borders |

---

## Quick Setup

### Step 1 — Prerequisites

- **Python 3.8+** — check with `python --version`
- **pip** package manager
- A **Telegram** account

### Step 2 — Install Dependencies

```bash
pip install requests web3
```

`web3` is optional — only needed for the `/balance` wallet feature.

### Step 3 — Get Your Credentials

| What you need | Where to get it |
|---|---|
| Telegram Bot Token | Message `@BotFather` → `/newbot` |
| Telegram Chat ID | Message `@userinfobot` → `/start` |
| Audiera API Key | https://ai.audiera.fi → API Keys |

### Step 4 — Configure

Edit `config.py` and fill in the three required fields:

```python
TG_BOT_TOKEN = "1234567890:AABBccDDee…"   # from @BotFather
TG_CHAT_ID   = "987654321"                  # from @userinfobot
AUDIERA_KEYS = [
    {"key": "sk_audiera_your_key_here", "status": "active"},
]
```

### Step 5 — Run

```bash
# Windows quick-launch
song_agent.bat

# Standard
python song_agent.py

# Interactive CLI menu (recommended for first run)
python song_agent.py --menu
```

When anything is misconfigured, the bot prints a numbered, color-coded guide explaining exactly what is wrong and how to fix it.

---

## How to Use

### Natural Language (recommended)

Just type what you want in Telegram — no command needed:

```
"Make a happy pop song about summer"
"I want a chill R&B track with soft vocals"
"Create something dark and electronic"
"Romantic ballad for my girlfriend"
```

### Direct Commands

```
/song a chill lo-fi track about rainy evenings
/custom about=summer vibes /artist=Kira /bpm=110
/modern
/auto_mode on
```

---

## Full Command Reference

### Song Creation

| Command | What it does |
|---|---|
| `/song <description>` | Create a song from a plain English description |
| `/custom` | Full manual control — theme, artist, BPM, custom lyrics |
| `/modern` | Instant trending song with randomly picked styles |
| `/rewrite` | Regenerate the last song with a fresh twist |
| `/retry` | Retry after a failed generation |

**Custom song syntax:**
```
/custom about=<theme> /artist=<name> /bpm=<70-200> /lyrics=<optional>
```

Examples:
```
/custom about=heartbreak /artist=Rhea Monroe /bpm=85
/custom about=gym anthem /lyrics=push harder every rep /artist=Ray /bpm=155
```

---

### Autonomous Mode

Run the bot with zero human input. It picks moods, styles, themes, and artists automatically and adapts over time.

| Command | What it does |
|---|---|
| `/auto_mode on` | Start fully autonomous generation |
| `/auto_mode off` | Stop the autonomous loop |
| `/auto_mode pause` | Pause without stopping |
| `/auto_mode resume` | Resume after pausing |
| `/auto_mode status` | Show current cycle, streak, interval, next mood |
| `/auto_mode set interval=20` | Change minutes between cycles |
| `/auto_mode set songs=2` | Songs to generate per cycle (1–5) |
| `/auto_mode set report=3` | Send a status report every N cycles |

**How the intelligence works:**

```
Time of day  →  Mood
────────────────────────────────────────────
05:00–09:00  →  Happy, Energetic
09:00–12:00  →  Energetic, Happy
12:00–15:00  →  Chill, Romantic
15:00–18:00  →  Energetic, Dark
18:00–21:00  →  Romantic, Chill, Nostalgic
21:00–24:00  →  Dark, Chill
00:00–05:00  →  Dark, Sad, Chill

Day of week  →  Style boost
────────────────────────────────────────────
Monday       →  Electronic, Hip-Hop
Tuesday      →  Pop, R&B
Wednesday    →  Rock, Indie
Thursday     →  Dance, EDM
Friday       →  Dance, Pop, Electronic
Saturday     →  House, Techno, EDM
Sunday       →  Soul, Jazz, Ambient
```

The interval adapts automatically:
- After a successful generation → interval × 0.85 (speed up, floor 15 min)
- After a failed generation → interval × 1.30 (back off, ceiling 90 min)
- On 2+ consecutive failures in multi-key mode → auto-rotates API key

Every N cycles (default 5) a progress report is sent to Telegram with recent songs, success streak, and current interval.

---

### Information

| Command | What it does |
|---|---|
| `/genres` | List all 24 available music styles |
| `/artists` | List all 12 artists with descriptions |
| `/history` | Your last 10 created songs |
| `/status` | System health, uptime, auto mode state, API metrics |

### API Key Management

| Command | What it does |
|---|---|
| `/keys` | View all keys and their status |
| `/addkey sk_audiera_…` | Add a new key |
| `/removekey <index>` | Remove a key by its list index |
| `/rotatekey` | Switch to the next key (multi-key mode) |

To enable automatic key rotation on failures, set `AUDIERA_MODE = "multi"` in `config.py` and add multiple keys.

### Wallet & $BEAT

| Command | What it does |
|---|---|
| `/wallet` | Show wallet address and contract info |
| `/setwallet 0x…` | Set your EVM wallet address |
| `/balance` | Check your $BEAT token balance |

### System

| Command | What it does |
|---|---|
| `/status` | Full system status including auto mode |
| `/debug` | Detailed debug dump (API metrics, key info, auto mode state) |
| `/notifications on\|off` | Toggle Telegram notifications |
| `/reset` | Clear all memory, history, and counters |
| `/help` | Full command reference in Telegram |

---

## CLI Modes

```bash
# for termux and etc
git clone https://github.com/zcsaqueeb/BeatForge-AI.git
cd BeatForge-AI
pip install requests web3

# Interactive menu — modern arrow-key navigation, live clock
python song_agent.py --menu

# Generate one song and exit
python song_agent.py --once
python song_agent.py --once --theme "midnight city" --styles Electronic Pop

# Auto-generate on a schedule (uses structured log output)
python song_agent.py --loop
python song_agent.py --loop --interval 15    # every 15 minutes

# Disable ANSI colors (plain terminals / CI environments)
python song_agent.py --no-color
```

### CLI Log Format

All events print in a consistent structured format:

```
  HH:MM:SS  ICON  LEVEL  message   detail
```

Example output:
```
  14:32:07  ♫  GEN   Cycle 3  ·  chill  ·  velvet hours   Electronic, Ambient  ·  Talia Brooks
  14:34:51  ✔  OK    Song generated  ·  total 6            next cycle in 22 min
  14:34:51  ◌  WAIT  Sleeping 22 min…
  14:56:51  ⚡  AUTO  Cycle 4  ·  energetic  ·  blazing trail   Rock, Indie  ·  Jason Miller
  14:59:12  ✔  OK    Song generated  ·  total 7            next cycle in 19 min
```

Log level reference:

| Icon | Level | Color | Used for |
|---|---|---|---|
| ✔ | OK | Green | Successful generation, config loaded |
| ◆ | INFO | Cyan | Theme / style / artist details |
| ▲ | WARN | Yellow | Warnings, loop stopped |
| ✖ | ERR | Red | Errors, generation failures |
| ♫ | GEN | Magenta | New generation starting |
| ⚡ | AUTO | Pink | Auto mode events |
| ◌ | WAIT | Gray | Sleep / idle |

---

## Configuration Reference

All settings live in `config.py`:

```python
# ── Required ──────────────────────────────────────────────────
TG_BOT_TOKEN = "…"          # Telegram bot token
TG_CHAT_ID   = "…"          # Your Telegram chat ID
AUDIERA_KEYS = [{"key": "sk_audiera_…", "status": "active"}]

# ── Key mode ──────────────────────────────────────────────────
AUDIERA_MODE = "single"     # "single" or "multi" (auto-rotate on errors)

# ── Wallet (optional) ─────────────────────────────────────────
EVM_ADDRESS   = "0x…"
BEAT_CONTRACT = "0xcf32…"

# ── Defaults ──────────────────────────────────────────────────
DEFAULT_STYLES           = ["Pop", "Electronic"]
DEFAULT_ARTIST           = "Kira"
DEFAULT_INTERVAL_MINUTES = 30

# ── Autonomous mode ───────────────────────────────────────────
AUTONOMOUS_MODE  = False    # start auto mode on boot
SONGS_PER_LOOP   = 1        # songs per auto mode cycle

# ── Features ──────────────────────────────────────────────────
SEND_WELCOME_MESSAGE       = True
VERBOSE_LOGGING            = False
ENABLE_PREFERENCE_LEARNING = True
ENABLE_AUTO_RETRY          = True
MAX_RETRY_ATTEMPTS         = 3
```

---

## Troubleshooting

**Bot doesn't start / prints errors**
The startup validator checks your config before anything runs. Read the numbered cards it prints — each one tells you exactly what to fix.

**"Invalid API Key" in Telegram**
Your Audiera key was rejected. Use `/keys` to inspect keys, and `/addkey` to add a fresh one from https://ai.audiera.fi.

**"Rate Limited"**
The Audiera API is throttling requests. Wait 30–60 seconds, then use `/retry`. For heavy use, add multiple keys and set `AUDIERA_MODE = "multi"` — auto mode will rotate keys on failures automatically.

**Song generation times out**
This happens occasionally when Audiera is under load. Use `/retry`. The poll window is 5 minutes. Auto mode will back off the interval automatically.

**Wallet balance fails**
Make sure `pip install web3` ran successfully, then restart the bot. Use `/debug` to confirm web3 is detected.

**Bot responds to wrong chat**
Check `TG_CHAT_ID` — it must match your personal chat ID exactly (get it from `@userinfobot`).

**Auto mode keeps failing**
Check `/status` for the failure streak. If you have multiple API keys, switch to `AUDIERA_MODE = "multi"` — auto mode will rotate keys after every 2 failures automatically.

---

## File Structure

```
SONG_AGENT/
├── song_agent.py        ← Main bot
├── config.py            ← Credentials and settings
├── song_agent.bat       ← Windows quick-launch
├── memory/
│   ├── history.json           ← Song history (last 200)
│   ├── dedup.json             ← Used themes (prevents repeats)
│   ├── preferences.json       ← Learned user preferences
│   ├── audiera_keys.json      ← API key state and rotation index
│   └── song_count.json        ← Persistent song counter
└── logs/
    └── song_agent_YYYYMMDD.log   ← Optional log file
```

---

## Available Artists

| Artist | Voice | Best for |
|---|---|---|
| Kira | Soft, melodic | Emotional, ballads |
| Ray | Electronic, synth | Modern beats |
| Jason Miller | Raw, powerful | Rock, intense tracks |
| Dylan Cross | Dark, moody | Atmospheric music |
| Rhea Monroe | Soulful, warm | R&B, love songs |
| Trevor Knox | Edgy, bold | Hip-hop, rap |
| Kayden West | Experimental | Innovative sounds |
| Talia Brooks | Gentle, flowing | Soft melodies |
| Sienna Blake | Dynamic, versatile | Many genres |
| Briana Rose | Powerful vocals | Gospel, soul |
| Leo Martin | Classical training | Orchestral |
| Amelia Clarke | Indie, folk | Acoustic tracks |

---

## Links

- Audiera API: https://ai.audiera.fi
- $BEAT Contract: `0xcf3232b85b43bca90e51d38cc06cc8bb8c8a3e36`

---

MIT License — Free to use and modify.
