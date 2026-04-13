# 🎵 Audiera - AI Song Agent

Create songs using natural language. Just tell Audiera what you want!

**Developer:** Saqueeb

---

## 🚀 Quick Setup

### Prerequisites
- Python 3.8+
- Telegram account

### Step 1: Get Credentials

| Service | How to Get |
|---------|-----------|
| Telegram Bot | Message @BotFather on Telegram |
| Chat ID | Message @userinfobot on Telegram |
| Audiera API | https://ai.audiera.fi |

### Step 2: Configure

Edit `config.py`:

```python
# Telegram
TG_BOT_TOKEN = "your_bot_token"
TG_CHAT_ID = "your_chat_id"

# Audiera API Keys
AUDIERA_KEYS = [
    {"key": "sk_audiera_xxx", "status": "active"},
]

# Wallet (optional)
EVM_ADDRESS = "0x..."
```

### Step 3: Run

```bash
# Install dependencies
pip install requests web3

# Run bot
python song_agent.py

# Or use batch file
song_agent.bat
```

---

## 💬 How to Use

### Natural Language

```
You: "Make a happy pop song"
You: "I want romantic R&B"
You: "Create dance music about summer"
```

### Commands

| Command | Description |
|---------|------------|
| `/song <desc>` | Create song |
| `/custom about=X /artist=Y /bpm=120` | Custom song |
| `/history` | View past songs |
| `/help` | All commands |
| `/status` | System status |
| `/keys` | API keys |
| `/wallet` | Wallet info |
| `/balance` | Check $BEAT |

---

## 🎛️ Features

- Natural language song creation
- Custom songs with BPM, lyrics, artist
- Automatic duplicate detection
- Song history (200 songs)
- Multiple API keys support
- EVM wallet integration
- Rate limit handling

---

## 📁 Files

```
SONG_AGENT/
├── song_agent.py    # Main bot
├── config.py      # Configuration
├── song_agent.bat # Windows launcher
├── memory/      # Saved data
└── logs/        # Log files
```

---

## ⚙️ Configuration

Edit `config.py` to customize:

```python
# Bot Settings
TG_BOT_TOKEN = "..."
TG_CHAT_ID = "..."

# API Keys
AUDIERA_KEYS = [...]
AUDIERA_MODE = "single"  # or "multi"

# Wallet
EVM_ADDRESS = "0x..."
BEAT_CONTRACT = "0x..."

# Defaults
DEFAULT_STYLES = ["Pop", "Electronic"]
DEFAULT_ARTIST = "Kira"

# Features
SEND_WELCOME_MESSAGE = True
VERBOSE_LOGGING = False
SAVE_LOG_FILE = False
```

---

## 🛠️ Troubleshooting

### Bot not responding
- Check token and chat ID
- Run `/start` in Telegram

### Song creation fails
- Check API key: `/keys`
- Try `/balance` for wallet
- Wait if rate limited

### Check status
```bash
/status   # System status
/keys    # API keys
/debug   # Debug info
```

---

## 📜 Commands List

### Song
- `/song` - Create song
- `/custom` - Custom song
- `/rewrite` - Regenerate
- `/history` - Past songs

### Info
- `/genres` - Music styles
- `/artists` - Artists
- `/status` - Status

### Keys
- `/keys` - View keys
- `/addkey` - Add key
- `/removekey` - Remove key

### Wallet
- `/wallet` - Wallet info
- `/setwallet` - Set address
- `/balance` - Check $BEAT

---

## 🔗 Links

- Audiera API: https://ai.audiera.fi
- $BEAT Contract: 0xcf3232b85b43bca90e51d38cc06cc8bb8c8a3e36

---

MIT License - Free to use!