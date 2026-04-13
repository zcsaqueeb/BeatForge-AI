# 🎧 BeatForge AI — Autonomous Song Generation Agent

Generate full songs using natural language via Telegram.
Describe the vibe → get a track.

**Developer:** Saqueeb

---

## ⚡ What This Actually Does

BeatForge AI is a Telegram-based agent that:

* Converts text prompts → structured music requests
* Calls Audiera API for song generation
* Manages keys, rate limits, and history
* Supports customization (genre, BPM, artist, mood)

---

## 🚀 Quick Start (No Confusion)

### 1. Requirements

* Python 3.8+
* Telegram account

### 2. Get Credentials

| Service      | Action                |
| ------------ | --------------------- |
| Telegram Bot | Message @BotFather    |
| Chat ID      | Message @userinfobot  |
| Audiera API  | https://ai.audiera.fi |

---

### 3. Setup

```bash
git clone https://github.com/zcsaqueeb/BeatForge-AI.git
cd BeatForge-AI
pip install requests web3
```

---

### 4. Configure

Edit `config.py`:

```python
TG_BOT_TOKEN = "your_bot_token"
TG_CHAT_ID = "your_chat_id"

AUDIERA_KEYS = [
    {"key": "sk_audiera_xxx", "status": "active"},
]

EVM_ADDRESS = "0x..."  # optional
```

---

### 5. Run

```bash
python song_agent.py
```

---

## 💬 Usage

### Natural Prompts

```
"Make a dark trap beat"
"Romantic R&B with slow tempo"
"Upbeat summer EDM track"
```

### Commands

| Command        | Function         |
| -------------- | ---------------- |
| `/song <desc>` | Generate song    |
| `/custom`      | Advanced control |
| `/history`     | Past outputs     |
| `/status`      | System health    |
| `/keys`        | API key status   |
| `/balance`     | Wallet check     |

---

## 🎛 Core Features

* Natural language → music generation
* Multi-key failover system
* Duplicate request detection
* Persistent memory (200 songs)
* Wallet + token integration ($BEAT)
* Rate limit handling
* Telegram-native UX

---

## 📁 Project Structure

```
BeatForge-AI/
├── song_agent.py      # Core bot logic
├── config.py          # Config
├── memory/            # Song history
├── logs/              # Logs
└── song_agent.bat     # Windows runner
```

---

## ⚙️ Config Controls

```python
AUDIERA_MODE = "single"  # or "multi"

DEFAULT_STYLES = ["Pop", "Electronic"]
DEFAULT_ARTIST = "Kira"

SEND_WELCOME_MESSAGE = True
VERBOSE_LOGGING = False
SAVE_LOG_FILE = False
```

---

## 🛠 Debug Fast

| Issue       | Fix                     |
| ----------- | ----------------------- |
| Bot silent  | Check token + `/start`  |
| No songs    | Verify API keys `/keys` |
| Rate limit  | Wait / switch key       |
| Wallet fail | Check address           |

---

## 🔌 Architecture (Simple + Expandable)

```
User → Telegram Bot → Parser → Audiera API → Response → Memory
```

**Extendable Areas:**

* Add new music APIs
* Plug in LLM prompt optimization
* Add web UI layer
* Add async queue for scaling

---

## 🔗 Resources

* Audiera API → https://ai.audiera.fi
* $BEAT Contract → 0xcf3232b85b43bca90e51d38cc06cc8bb8c8a3e36

---

## 📜 License

MIT — Use it, break it, improve it.

---

## 🧠 Positioning Upgrade (Use This Everywhere)

> BeatForge AI = "Text → Music Engine with Telegram Control Layer"

Not a bot. A system.
