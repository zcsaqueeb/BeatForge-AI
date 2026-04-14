# 🎵 Audiera — AI Song Agent

> **Generate full songs from plain English — automatically.**

Lyrics + music → delivered to Telegram
Now with **autonomous generation engine** (zero input required)

---

## 🚀 Why This Exists

Most “AI music tools”:

* Need prompts every time
* Don’t scale
* Don’t automate

**Audiera = self-running music engine**

* Input once → runs forever
* Generates continuously
* Adapts automatically

---

## 🔗 Repository (Use This First)

👉 https://github.com/zcsaqueeb/BeatForge-AI.git

Clone + run:

```bash
git clone https://github.com/zcsaqueeb/BeatForge-AI.git
cd BeatForge-AI
pip install requests web3
python song_agent.py --menu
```

---

## ⚡ Quick Setup (Minimal Friction)

### Requirements

* Python 3.8+
* Telegram account

### Configure

```python
TG_BOT_TOKEN = "..."
TG_CHAT_ID   = "..."
AUDIERA_KEYS = [{"key": "sk_...", "status": "active"}]
```

### Run

```bash
python song_agent.py --menu
```

---

## 🎯 Core Usage

### Natural Language (Primary Mode)

```
Make a chill lo-fi song about rain
Create a dark techno track
Romantic acoustic song
```

### Commands (Control Mode)

```
/song <prompt>
/custom about=theme /artist=name /bpm=120
/modern
/rewrite
```

---

## 🤖 Autonomous Mode (Core Weapon)

```
/auto_mode on
```

### What Happens

* Chooses mood (time-based)
* Chooses style (day-based)
* Generates continuously
* Adjusts speed dynamically
* Rotates API keys on failure

### Behavior Model

* Success → faster loop
* Failure → slower + safer
* Multi-key → auto-switch

---

## 🧠 Intelligence Engine

### Time → Mood

| Time      | Output    |
| --------- | --------- |
| Morning   | Energetic |
| Afternoon | Chill     |
| Evening   | Romantic  |
| Night     | Dark      |

### Day → Style Boost

| Day      | Style       |
| -------- | ----------- |
| Fri–Sat  | EDM / Dance |
| Sun      | Soul / Jazz |
| Weekdays | Mixed       |

---

## ⚙️ CLI Modes (Execution Control)

```bash
python song_agent.py --menu     # interactive
python song_agent.py --once     # single execution
python song_agent.py --loop     # continuous engine
```

---

## 📊 System Commands (Minimal Set)

### Creation

* `/song`
* `/custom`
* `/modern`
* `/rewrite`
* `/retry`

### Automation

* `/auto_mode on|off|status`
* `/auto_mode set interval=20`
* `/auto_mode set songs=2`

### Info

* `/status`
* `/history`
* `/artists`
* `/genres`

### Keys

* `/keys`
* `/addkey`
* `/removekey`
* `/rotatekey`

---

## 🧱 Architecture (Simplified)

```
User → Telegram → Agent → Audiera API
                         ↓
                  Song Generated
                         ↓
                   Sent to Telegram
```

Auto Mode:

```
Loop → Generate → Evaluate → Adjust → Repeat
```

---

## ⚠️ Failure System (Already Solved)

| Problem    | System Response    |
| ---------- | ------------------ |
| API fails  | Retry + rotate key |
| Rate limit | Backoff            |
| Timeout    | Retry              |
| Bad config | Startup validator  |

---

## 📁 Project Structure

```
SONG_AGENT/
├── song_agent.py
├── config.py
├── memory/
├── logs/
```

---

## 🔥 What You Actually Built

Not a bot.

* It’s a **looping generation engine**
* With **adaptive intelligence**
* That can run **indefinitely**

---

## 🧨 Upgrade Path (If You’re Serious)

* Run on VPS (24/7)
* Enable multi-key mode
* Increase loop frequency
* Track output volume
* Add monetization layer

---

## 📌 Bottom Line

You built something most people don’t understand:

> A system that **creates content without needing you**

Now structure it like a product — not a script.
