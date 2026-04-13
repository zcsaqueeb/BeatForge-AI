#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    🎵 Audiera - AI Song Agent 🎵                   ║
║                                                                              ║
║  The ultimate AI song creation agent with natural language understanding.  ║
║  Just tell me what kind of song you want, and I'll create it!              ║
║                                                                              ║
║  Usage:                                                                     ║
║    python song_agent.py                    # Start the bot                  ║
║    python song_agent.py --once             # Generate one song and exit      ║
║    python song_agent.py --loop --interval 30  # Auto-generate every 30 min ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

# ═══════════════════════════════════════════════════════════════════════════════
#  WINDOWS I/O FIX - MUST BE FIRST
# ═══════════════════════════════════════════════════════════════════════════════
from calendar import c
import sys as _sys
import os as _os
import io as _io

def _fix_windows_io():
    """Fix Windows I/O encoding issues."""
    if _sys.platform != "win32":
        return
    _os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    for name in ("stdout", "stderr"):
        s = getattr(_sys, name, None)
        if isinstance(s, _io.TextIOWrapper) and getattr(s, "encoding", "") == "utf-8":
            continue
        try:
            buf = getattr(s, "buffer", None)
            if buf is not None:
                setattr(_sys, name, _io.TextIOWrapper(buf, encoding="utf-8", errors="replace"))
                continue
        except Exception:
            pass
        try:
            setattr(_sys, name, _io.TextIOWrapper(_io.BytesIO(), encoding="utf-8", errors="replace"))
        except Exception:
            pass

_fix_windows_io()

# ═══════════════════════════════════════════════════════════════════════════════
#  STANDARD IMPORTS
# ═══════════════════════════════════════════════════════════════════════════════
import json, time, signal, threading, argparse, traceback, hashlib, re
import logging as _logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
import requests
import sys
import select

try:
    from web3 import Web3
except ImportError:
    Web3 = None

try:
    import msvcrt
    WINDOWS = True
except ImportError:
    WINDOWS = False

# ═══════════════════════════════════════════════════════════════════════════════
#  CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════
try:
    import config as CFG
except ImportError:
    print("ERROR: config.py not found! Please create config.py with your settings.")
    print("See the config.py file in this directory for the required settings.")
    _sys.exit(1)

# ═══════════════════════════════════════════════════════════════════════════════
#  PATHS & LOGGING SETUP
# ═══════════════════════════════════════════════════════════════════════════════
BASE_DIR = Path(__file__).parent
OUT_DIR  = BASE_DIR / "output"
MEM_DIR  = BASE_DIR / "memory"
LOG_DIR  = BASE_DIR / "logs"

for d in [OUT_DIR, MEM_DIR, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

def now_utc():
    return datetime.now(timezone.utc)

def ts():
    return now_utc().strftime("%Y-%m-%d %H:%M:%S UTC")

# Logger
log = _logging.getLogger("SONG_MASTER")
log.setLevel(_logging.WARNING)
_log_handler = _logging.StreamHandler()
_log_handler.setFormatter(_logging.Formatter(
    "%(levelname)-7s  %(message)s"))
log.addHandler(_log_handler)

if CFG.VERBOSE_LOGGING or CFG.SAVE_LOG_FILE:
    try:
        _fh = _logging.FileHandler(LOG_DIR / f"song_agent_{datetime.now().strftime('%Y%m%d')}.log", encoding="utf-8")
        _fh.setFormatter(_logging.Formatter(
            "%(asctime)s  %(levelname)-7s  %(message)s", datefmt="%H:%M:%S"))
        log.addHandler(_fh)
        if CFG.VERBOSE_LOGGING:
            log.setLevel(_logging.DEBUG)
    except Exception:
        pass

def safe_print(*args, **kwargs):
    """Safe print that handles encoding errors."""
    try:
        print(*args, **kwargs)
    except Exception:
        try:
            _os.write(1, (" ".join(str(a) for a in args) + "\n").encode("utf-8", "replace"))
        except Exception:
            pass

# ═══════════════════════════════════════════════════════════════════════════════
#  COLORS & UI CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════
class Colors:
    """ANSI color codes for terminal output."""
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"
    RED    = "\033[91m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    BLUE   = "\033[94m"
    MAGENTA= "\033[95m"
    CYAN   = "\033[96m"
    WHITE  = "\033[97m"

    @classmethod
    def disable(cls):
        cls.RESET = cls.BOLD = cls.DIM = cls.RED = cls.GREEN = ""
        cls.YELLOW = cls.BLUE = cls.MAGENTA = cls.CYAN = cls.WHITE = ""

# ═══════════════════════════════════════════════════════════════════════════════
#  UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════
def p(*args, **kwargs):
    """Print with colors."""
    try:
        print(*args, **kwargs)
    except Exception:
        pass

def banner():
    """Display startup banner."""
    width = 72
    c = Colors
    print()
    p(f"{c.CYAN}╔{'═' * width}╗{c.RESET}")
    p(f"{c.CYAN}║{c.RESET}{c.BOLD}{c.WHITE}{' 🎵 Audiera - AI Song Agent ':^{width}}{c.RESET}{c.CYAN}║{c.RESET}")
    p(f"{c.CYAN}╠{'═' * width}╣{c.RESET}")
    p(f"{c.CYAN}║{c.RESET}  {c.GREEN}v{CFG.AGENT_VERSION}{c.RESET}  •  Natural Language Song Creation  •  AI-Powered{c.CYAN}║{c.RESET}")
    p(f"{c.CYAN}╚{'═' * width}╝{c.RESET}")
    print()

# ═══════════════════════════════════════════════════════════════════════
#  INTERACTIVE CLI MENU
# ═══════════════════════════════════════════════════════════════════════
class InteractiveMenu:
    """Modern interactive CLI menu with keyboard navigation."""

    def __init__(self):
        self.items = []
        self.selected = 0
        self.scroll = 0
        self.old_settings = None

    def add_item(self, icon: str, title: str, subtitle: str = "", action=None):
        self.items.append({"icon": icon, "title": title, "subtitle": subtitle, "action": action})

    def run(self) -> bool:
        if not self.items:
            return False
        self._draw()
        while True:
            key = self._get_key()
            if key == "up":
                self.selected = max(0, self.selected - 1)
                if self.selected < self.scroll:
                    self.scroll = self.selected
            elif key == "down":
                self.selected = min(len(self.items) - 1, self.selected + 1)
                if self.selected >= self.scroll + 20:
                    self.scroll = self.selected - 19
            elif key == "enter":
                self._clear()
                if self.items[self.selected]["action"]:
                    return self.items[self.selected]["action"]()
                return True
            elif key == "escape":
                self._clear()
                return False
            elif key in ["q", "Q"]:
                self._clear()
                return False
            self._draw()

    def _get_key(self) -> str:
        try:
            if WINDOWS:
                if msvcrt.kbhit():
                    ch = msvcrt.getch()
                    if ch == b"\xe0":
                        ch = msvcrt.getch()
                        if ch == b"H":
                            return "up"
                        elif ch == b"P":
                            return "down"
                    elif ch == b"\r":
                        return "enter"
                    elif ch == b" ":
                        return "enter"
                    elif ch == b"\x1b":
                        return "escape"
                return ""
            else:
                dr, dw, de = select.select([sys.stdin], [], [], 0)
                if dr:
                    ch = sys.stdin.read(1)
                    if ch == "\x1b":
                        return "escape"
                    elif ch == "\n":
                        return "enter"
                    elif ch == " ":
                        return "enter"
                    elif ch == "q":
                        return "q"
                return ""
        except:
            return ""

    def _draw(self):
        self._clear()
        c = Colors
        width = 60

        p(f"{c.CYAN}╔{'═' * width}╗{c.RESET}")
        p(f"{c.CYAN}║{c.RESET}{c.BOLD}{c.WHITE}{' 🎵 Audiera MENU ':^{width}}{c.RESET}{c.CYAN}║{c.RESET}")
        p(f"{c.CYAN}╠{'═' * width}╣{c.RESET}")

        for i, item in enumerate(self.items[self.scroll:self.scroll + 20]):
            idx = i + self.scroll
            prefix = " ➤ " if idx == self.selected else " ○ "
            icon = f"{c.YELLOW}{item['icon']}{c.RESET}" if idx == self.selected else item['icon']
            title = f"{c.BOLD}{c.WHITE}{item['title']}{c.RESET}" if idx == self.selected else item['title']
            subtitle = f"{c.DIM}{item['subtitle']}{c.RESET}" if item['subtitle'] else ""

            line = f"{c.CYAN}║{c.RESET} {prefix}{icon} {title}"
            if subtitle:
                line += f" {c.DIM}-{c.RESET} {subtitle}"
            line = line.ljust(width + 4) + f"{c.CYAN}║{c.RESET}"
            p(line)

        p(f"{c.CYAN}╚{'═' * width}╝{c.RESET}")
        p(f"\n{c.YELLOW}↑↓ Select | ENTER Choose | ESC/Q Exit{c.RESET}")

    def _clear(self):
        try:
            import os
            os.system('cls' if os.name == 'nt' else 'clear')
        except:
            print("\033[2J\033[H", end="")

def run_interactive_menu(agent=None):
    """Run the interactive menu."""
    c = Colors
    menu = InteractiveMenu()

    def start_bot():
        main()
        return False

    menu.add_item("🚀", "Start Bot", "Run the Telegram bot", start_bot)
    menu.add_item("🎵", "Generate Song", "Create a single song", lambda: generate_one(agent))
    menu.add_item("🔄", "Auto Loop", "Generate songs automatically", lambda: run_loop(agent))
    menu.add_item("📊", "Status", "View system status", lambda: show_status(agent))
    menu.add_item("🔑", "API Keys", "Manage Audiera keys", lambda: manage_keys(agent))
    menu.add_item("💳", "Wallet", "Manage EVM wallet", lambda: manage_wallet(agent))
    menu.add_item("⚙️", "Config", "Edit configuration", lambda: open_config())
    menu.add_item("❌", "Exit", "Exit the application", None)

    return menu.run()

def generate_one(agent):
    if not agent:
        p(f"{c.RED}Agent not initialized!{c.RESET}")
        return False
    theme = input(f"\n{c.CYAN}Song Theme: {c.RESET}") or "beautiful dreams"
    styles_input = input(f"{c.CYAN}Styles (comma-separated): {c.RESET}")
    styles = [s.strip() for s in styles_input.split(",")] if styles_input else CFG.DEFAULT_STYLES
    artist = input(f"{c.CYAN}Artist: {c.RESET}") or CFG.DEFAULT_ARTIST

    p(f"\n{c.YELLOW}Generating: {theme} ({', '.join(styles)})...{c.RESET}")
    agent.state.last_song_params = {"theme": theme, "styles": styles, "artist": artist}
    threading.Thread(target=agent._generate_song_async, args=(theme, styles, artist)).start()

    p(f"{c.GREEN}Song generation started!{c.RESET}")
    input(f"\n{c.DIM}Press ENTER to continue...{c.RESET}")
    return False

def run_loop(agent):
    if not agent:
        p(f"{c.RED}Agent not initialized!{c.RESET}")
        return False
    try:
        interval = int(input(f"\n{c.CYAN}Interval (minutes): {c.RESET}") or "30")
    except:
        interval = 30
    p(f"\n{c.GREEN}Auto loop started! Press Ctrl+C to stop.{c.RESET}")
    while True:
        try:
            import random
            moods = ["happy", "sad", "energetic", "chill", "romantic", "dark"]
            mood = random.choice(moods)
            theme = f"{mood.capitalize()} moments"
            styles = CFG.MOOD_TO_STYLES.get(mood, CFG.DEFAULT_STYLES)
            artist = random.choice(list(CFG.ARTISTS.keys()))
            agent.state.last_song_params = {"theme": theme, "styles": styles, "artist": artist, "mood": mood}
            p(f"\n{c.CYAN}Generating: {theme} ({', '.join(styles)}){c.RESET}")
            threading.Thread(target=agent._generate_song_async, args=(theme, styles, artist)).start()
            time.sleep(interval * 60)
        except KeyboardInterrupt:
            break
    return False

def show_status(agent):
    if not agent:
        return False
    p(f"\n{c.CYAN}╔{'═' * 50}╗{c.RESET}")
    p(f"{c.CYAN}║{c.RESET}  📊 SYSTEM STATUS{c.RESET}".ljust(54) + f"{c.CYAN}║{c.RESET}")
    p(f"{c.CYAN}╠{'═' * 50}╣{c.RESET}")
    p(f"{c.CYAN}║{c.RESET}  Agent:    {c.WHITE}{CFG.AGENT_NAME}{c.RESET}".ljust(54) + f"{c.CYAN}║{c.RESET}")
    p(f"{c.CYAN}║{c.RESET}  Version:  {c.WHITE}{CFG.AGENT_VERSION}{c.RESET}".ljust(54) + f"{c.CYAN}║{c.RESET}")
    p(f"{c.CYAN}║{c.RESET}  Songs:    {c.WHITE}{agent.state.song_count}{c.RESET}".ljust(54) + f"{c.CYAN}║{c.RESET}")
    p(f"{c.CYAN}║{c.RESET}  Keys:     {c.WHITE}{agent.audiera.active_count}{c.RESET} active".ljust(54) + f"{c.CYAN}║{c.RESET}")
    p(f"{c.CYAN}║{c.RESET}  Wallet:   {c.WHITE}{CFG.EVM_ADDRESS[:12]}...{c.RESET}".ljust(54) + f"{c.CYAN}║{c.RESET}")
    p(f"{c.CYAN}╚{'═' * 50}╝{c.RESET}")
    input(f"\n{c.DIM}Press ENTER to continue...{c.RESET}")
    return False

def manage_keys(agent):
    if not agent:
        return False
    p(f"\n{c.CYAN}🔑 API Key Management{c.RESET}\n")
    for i, k in enumerate(agent.audiera.keys):
        status = f"{c.GREEN}ACTIVE{c.RESET}" if k.get("status") == "active" else f"{c.RED}INACTIVE{c.RESET}"
        p(f"  {i+1}. {k['key'][:15]}...{k['key'][-6:]} {status}")
    p(f"\n{c.YELLOW}[A] Add Key | [R] Remove Key | [Q] Quit{c.RESET}")

    choice = input(f"\n{c.CYAN}Choice: {c.RESET}").strip().lower()
    if choice == "a":
        key = input(f"{c.CYAN}Enter API key: {c.RESET}").strip()
        success, msg = agent.audiera.add_key(key)
        p(f"{c.GREEN if success else c.RED}{msg}{c.RESET}")
    elif choice == "r":
        idx = input(f"{c.CYAN}Enter index to remove: {c.RESET}").strip()
        try:
            idx = int(idx) - 1
            if 0 <= idx < len(agent.audiera.keys):
                removed = agent.audiera.keys.pop(idx)
                p(f"{c.GREEN}Removed: {removed['key'][:15]}...{c.RESET}")
        except:
            p(f"{c.RED}Invalid index{c.RESET}")
    input(f"\n{c.DIM}Press ENTER to continue...{c.RESET}")
    return False

def manage_wallet(agent):
    p(f"\n{c.CYAN}💳 Wallet Management{c.RESET}\n")
    p(f"  Address: {CFG.EVM_ADDRESS}")
    p(f"  Contract: {CFG.BEAT_CONTRACT}\n")
    p(f"{c.YELLOW}[S] Set Address | [B] Check Balance | [Q] Quit{c.RESET}")

    choice = input(f"\n{c.CYAN}Choice: {c.RESET}").strip().lower()
    if choice == "s":
        addr = input(f"{c.CYAN}Enter EVM address: {c.RESET}").strip()
        if addr.startswith("0x") and len(addr) == 42:
            CFG.EVM_ADDRESS = addr
            p(f"{c.GREEN}Wallet set!{c.RESET}")
        else:
            p(f"{c.RED}Invalid address{c.RESET}")
    elif choice == "b":
        p(f"{c.YELLOW}Checking balance...{c.RESET}")
    input(f"\n{c.DIM}Press ENTER to continue...{c.RESET}")
    return False

def open_config():
    import subprocess
    subprocess.run(["notepad", str(BASE_DIR / "config.py")])
    return False

# ═══════════════════════════════════════════════════════════════════════════════
#  STATE MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════
class StateManager:
    """Manages persistent state for the agent."""

    def __init__(self):
        self.session_start = now_utc()
        self.run_count = 0
        self.song_count = 0
        self.skipped_count = 0
        self.last_request = ""
        self.conversation_history = []
        self.user_preferences = self._load_preferences()
        self.last_song_params = None
        self.pending_confirmation = None

    def _load_preferences(self) -> dict:
        """Load user preferences from disk."""
        pfile = MEM_DIR / "preferences.json"
        if pfile.exists():
            try:
                return json.loads(pfile.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"preferred_styles": [], "preferred_artists": [], "mood_history": []}

    def save_preferences(self):
        """Save user preferences to disk."""
        pfile = MEM_DIR / "preferences.json"
        try:
            pfile.write_text(json.dumps(self.user_preferences, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def add_conversation(self, role: str, content: str):
        """Add to conversation history."""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "ts": ts()
        })
        # Keep only last 20 messages
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]

    def clear_all(self):
        """Clear all memory and state."""
        self.conversation_history = []
        self.user_preferences = {"preferred_styles": [], "preferred_artists": [], "mood_history": []}
        self.last_song_params = None
        self.pending_confirmation = None
        self.save_preferences()
        # Clear all memory files
        for f in MEM_DIR.glob("*.json"):
            try:
                f.unlink()
            except Exception:
                pass
        log.info("All memory cleared")

# ═══════════════════════════════════════════════════════════════════════════════
#  NATURAL LANGUAGE INTENT DETECTOR
# ═══════════════════════════════════════════════════════════════════════════════
class IntentDetector:
    """
    Advanced natural language intent detection for song creation.
    Understands various ways users express their song needs.
    """

    # Song creation triggers
    CREATE_TRIGGERS = [
        "make a song", "create a song", "generate a song", "write a song",
        "compose a song", "produce a song", "sing a song", "play a song",
        "make music", "create music", "generate music", "write music",
        "i want a song", "i need a song", "i want music", "i need music",
        "can you make", "can you create", "can you generate",
        "मुझे एक गाना", "गाना बनाओ", "song banana hai",  # Hindi
        "quiero una canción", "hazme una canción",  # Spanish
        "fais-moi une chanson", "crée une chanson",  # French
    ]

    # Genre/style keywords
    GENRE_KEYWORDS = {
        "pop": ["pop", "पॉप", "पॉप संगीत"],
        "electronic": ["electronic", "edm", "techno", "house", "dance music", "इलेक्ट्रॉनिक"],
        "rock": ["rock", "रॉक", "hard rock"],
        "hip-hop": ["hip-hop", "hip hop", "rap", "रैप"],
        "r&b": ["r&b", "rnb", "rn b", "आर एंड बी"],
        "soul": ["soul", "सोल", "soulful"],
        "jazz": ["jazz", "जैज़"],
        "classical": ["classical", "क्लासिकल", "orchestra"],
        "ambient": ["ambient", "चिल", "relaxing", "meditation"],
        "indie": ["indie", "इंडी"],
        "folk": ["folk", "फोक", "acoustic"],
        "metal": ["metal", "मेटल", "heavy metal"],
        "dance": ["dance", "डांस", "dancefloor"],
        "funk": ["funk", "फंक"],
        "blues": ["blues", "ब्लूज़"],
        "romantic": ["romantic", "love song", "रोमांटिक", "लव सॉन्ग", "romance"],
        "sad": ["sad", "melancholy", "upset", "दुखी", "sad song"],
        "happy": ["happy", "joyful", "cheerful", "खुश", "happy song"],
        "energetic": ["energetic", "powerful", "intense", "ऊर्जावान"],
        "chill": ["chill", "laid back", "relaxed", "chill vibes"],
        "dark": ["dark", "moody", "gloomy", "डार्क"],
        "nostalgic": ["nostalgic", "retro", "throwback", "पुराना"],
    }

    # Mood detection
    MOOD_KEYWORDS = {
        "happy": ["happy", "joy", "excited", "great", "amazing", "wonderful", "love", "खुश", "मस्त"],
        "sad": ["sad", "depressed", "lonely", "heartbroken", "upset", "दुखी", "उदास"],
        "angry": ["angry", "furious", "rage", "mad", "annoyed", "गुस्सा"],
        "romantic": ["love", "romantic", "heart", "kiss", "together", "प्यार", "लव"],
        "chill": ["relax", "chill", "peaceful", "calm", "zen", "आराम"],
        "energetic": ["energy", "power", "pump", " hyped", "pumped", "जोश"],
        "nostalgic": ["remember", "memory", "past", "childhood", "old times", "याद"],
        "dark": ["dark", "shadow", "void", "empty", "hollow", "अंधेरा"],
    }

    # Artist matching keywords
    ARTIST_KEYWORDS = {
        "Kira": ["soft", "gentle", "melodic", "emotional", "female", "girl"],
        "Ray": ["electronic", "synth", "modern", "tech", "futuristic"],
        "Jason Miller": ["rock", "hard", "raw", "powerful", "male"],
        "Dylan Cross": ["dark", "moody", "atmospheric", "mysterious"],
        "Rhea Monroe": ["soul", "warm", "love", "r&b", "female"],
        "Trevor Knox": ["hip-hop", "rap", "urban", "edgy", "male"],
        "Kayden West": ["experimental", "unique", "innovative", "fresh"],
        "Talia Brooks": ["soft", "flowing", "gentle", "melody"],
        "Sienna Blake": ["dynamic", "versatile", "powerful"],
        "Briana Rose": ["gospel", "soul", "powerful vocals", "church"],
        "Leo Martin": ["classical", "orchestral", "elegant", "refined"],
        "Amelia Clarke": ["indie", "folk", "acoustic", "singer-songwriter"],
    }

    def __init__(self):
        self.last_intent = None

    def detect_intent(self, text: str) -> dict:
        """
        Detect user intent from natural language.
        Returns dict with: intent, theme, mood, genre, artist, confidence
        """
        text_lower = text.lower().strip()
        result = {
            "intent": "unknown",
            "theme": None,
            "mood": "neutral",
            "genre": None,
            "artist": None,
            "confidence": 0.0,
            "raw_text": text,
            "needs_clarification": False,
            "clarification_needed": []
        }

        # Check if this is a song creation request
        for trigger in self.CREATE_TRIGGERS:
            if trigger in text_lower:
                result["intent"] = "create_song"
                result["confidence"] = 0.9
                break

        # If no explicit trigger, check for indirect requests
        if result["intent"] == "unknown":
            song_words = ["song", "music", "beat", "track", "melody", "गाना", "संगीत", "canción", "chanson"]
            for word in song_words:
                if word in text_lower:
                    # Check if it's a request (want, need, make, create, etc.)
                    request_words = ["want", "need", "make", "create", "generate", "give", " चाहिए", "चाहता", "quiero", "fais"]
                    for req in request_words:
                        if req in text_lower:
                            result["intent"] = "create_song"
                            result["confidence"] = 0.7
                            break
                    break

        # Detect mood
        for mood, keywords in self.MOOD_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    result["mood"] = mood
                    result["confidence"] = max(result["confidence"], 0.6)
                    break

        # Detect genre/style
        for genre, keywords in self.GENRE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    result["genre"] = genre
                    result["confidence"] = max(result["confidence"], 0.7)
                    break

        # Detect suggested artist
        for artist, keywords in self.ARTIST_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    result["artist"] = artist
                    result["confidence"] = max(result["confidence"], 0.5)
                    break

        # Extract theme from the text
        result["theme"] = self._extract_theme(text)

        # Determine if we need clarification
        if result["intent"] == "create_song":
            if not result["theme"]:
                result["clarification_needed"].append("What should the song be about?")
            if not result["genre"] and not result["mood"]:
                result["clarification_needed"].append("What style or mood? (e.g., pop, rock, chill)")

        self.last_intent = result
        return result

    def _extract_theme(self, text: str) -> Optional[str]:
        """Extract the main theme/topic from the request."""
        text_lower = text.lower()

        # Patterns to remove
        patterns_to_remove = [
            r"^(make|create|generate|write|i want|i need|can you|could you)\s+(a\s+)?(song|music|track)\s+(about|on|with)?\s*",
            r"^(give me|want|need)\s+(a\s+)?(song|music|track)\s*",
            r"मुझे\s+",
            r"गाना\s*",
            r"चाहिए\s*",
            r"quiero\s+",
            r"hazme\s+",
            r"fais[- ]moi\s+",
        ]

        theme = text_lower
        for pattern in patterns_to_remove:
            theme = re.sub(pattern, "", theme, flags=re.IGNORECASE)

        theme = theme.strip(" .,!?।।¡¿")
        return theme if len(theme) > 2 else None

    def suggest_alternatives(self, current: dict) -> List[str]:
        """Suggest alternative song parameters."""
        suggestions = []

        if not current.get("genre"):
            suggestions.append("Would you like it in Pop style?")
            suggestions.append("Maybe something Electronic or Dance?")

        if not current.get("mood"):
            if current.get("genre") in ["rock", "metal"]:
                suggestions.append("Want it energetic and powerful?")
            elif current.get("genre") in ["pop", "dance"]:
                suggestions.append("Should it be happy and uplifting?")

        if not current.get("artist"):
            suggestions.append("Any preference for male or female vocals?")

        return suggestions

# ═══════════════════════════════════════════════════════════════════════════════
#  AUDIERA API MANAGER
# ═══════════════════════════════════════════════════════════════════════════════
class AudieraManager:
    """Manages Audiera API interactions with multi-key support."""

    LYRICS_URL = "https://ai.audiera.fi/api/skills/lyrics"
    MUSIC_URL  = "https://ai.audiera.fi/api/skills/music"

    def __init__(self, keys: list, mode: str = "single"):
        self.keys = keys.copy()
        self.idx = 0
        self.mode = mode
        self.metrics = {"requests": 0, "successes": 0, "failures": 0, "rotations": 0}
        self._load_keys()

    def _load_keys(self):
        """Load keys from config."""
        keys_file = MEM_DIR / "audiera_keys.json"
        if keys_file.exists():
            try:
                data = json.loads(keys_file.read_text(encoding="utf-8"))
                self.keys = data.get("keys", self.keys)
                self.idx = min(data.get("active_idx", 0), len(self.keys) - 1)
                self.mode = data.get("mode", self.mode)
            except Exception:
                pass
        self._save_keys()

    def _save_keys(self):
        """Save keys state."""
        keys_file = MEM_DIR / "audiera_keys.json"
        try:
            keys_file.write_text(json.dumps({
                "keys": self.keys,
                "active_idx": self.idx,
                "mode": self.mode
            }, indent=2), encoding="utf-8")
        except Exception:
            pass

    @property
    def current_key(self) -> str:
        if not self.keys:
            return ""
        return self.keys[min(self.idx, len(self.keys) - 1)]["key"]

    @property
    def current_short(self) -> str:
        k = self.current_key
        return f"{k[:15]}...{k[-6:]}" if k else "none"

    @property
    def active_count(self) -> int:
        return len([k for k in self.keys if k.get("status") == "active"])

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.current_key}", "Content-Type": "application/json"}

    def rotate(self) -> bool:
        """Rotate to next key."""
        if self.mode != "multi" or len(self.keys) <= 1:
            return False
        active = [i for i, k in enumerate(self.keys) if k.get("status") == "active"]
        if len(active) <= 1:
            return False
        curr_pos = active.index(self.idx) if self.idx in active else 0
        self.idx = active[(curr_pos + 1) % len(active)]
        self.metrics["rotations"] += 1
        self._save_keys()
        log.info(f"Rotated to key [{self.idx}]")
        return True

    def add_key(self, key: str) -> Tuple[bool, str]:
        """Add a new API key."""
        key = key.strip()
        if not key.startswith("sk_audiera_"):
            return False, "Key must start with 'sk_audiera_'"
        if any(k["key"] == key for k in self.keys):
            return False, "Key already exists"
        self.keys.append({"key": key, "status": "active"})
        self._save_keys()
        return True, f"Added key at index {len(self.keys) - 1}"

    def _post(self, url: str, payload: dict, timeout: int = 15) -> tuple:
        """Make POST request with error handling. Returns (data, error_msg)."""
        self.metrics["requests"] += 1
        try:
            r = requests.post(url, json=payload, headers=self._headers(), timeout=timeout)
            
            # Rate limited
            if r.status_code == 429:
                try:
                    err_data = r.json()
                    msg = err_data.get("message", "Rate limited")
                except:
                    msg = "Rate limited"
                log.warning(f"Rate limited: {msg}")
                return None, "rate_limit"
            
            # Invalid API key
            if r.status_code == 401:
                log.error("Invalid API key")
                return None, "invalid_key"
            
            # Forbidden
            if r.status_code == 403:
                log.error("Forbidden - check API scopes")
                return None, "forbidden"
            
            # Other errors
            if r.status_code != 200:
                try:
                    err_data = r.json()
                    msg = err_data.get("message", f"HTTP {r.status_code}")
                except:
                    msg = f"HTTP {r.status_code}"
                log.error(f"API error: {msg}")
                return None, msg
            
            self.metrics["successes"] += 1
            return r.json(), None
            
        except requests.exceptions.Timeout:
            log.error("Request timeout")
            return None, "timeout"
        except Exception as e:
            log.error(f"Request failed: {e}")
            self.metrics["failures"] += 1
            return None, str(e)

    def generate_lyrics(self, inspiration: str, memory_hint: str = "") -> tuple:
        """Generate lyrics from inspiration. Returns (lyrics, error_msg)."""
        prompt = inspiration
        if memory_hint:
            prompt = f"{inspiration}. {memory_hint}"
        log.info(f"Generating lyrics: '{inspiration[:50]}'")
        data, err = self._post(self.LYRICS_URL, {"inspiration": prompt})
        
        if err:
            return None, err
        
        if data and data.get("success") and data.get("data", {}).get("lyrics"):
            lyrics = data["data"]["lyrics"]
            log.info(f"Lyrics generated: {len(lyrics)} chars")
            return lyrics, None
        
        log.error("Lyrics generation failed")
        return None, "api_error"

    def generate_music(self, styles: list, artist_id: str, lyrics: str = None) -> tuple:
        """Generate music with styles and artist. Returns (result, error_msg)."""
        payload = {"styles": styles, "artistId": artist_id}
        if lyrics:
            payload["lyrics"] = lyrics
        log.info(f"Generating music: {styles} with {artist_id}")

        data, err = self._post(self.MUSIC_URL, payload)
        
        if err:
            return None, err
        
        if not data or not data.get("success"):
            log.error("Music generation failed")
            return None, "api_error"

        task_id = data["data"]["taskId"]
        log.info(f"Polling task: {task_id}")

        # Poll for completion (up to 5 minutes)
        for i in range(60):
            time.sleep(5)
            try:
                r = requests.get(f"{self.MUSIC_URL}/{task_id}", headers=self._headers(), timeout=5)
                pd = r.json()
                if pd and pd.get("success"):
                    status = pd["data"].get("status", "?")
                    log.info(f"Poll {i+1}/60: {status}")
                    if status == "completed":
                        songs = pd["data"].get("musics") or []
                        log.info(f"Generated {len(songs)} songs")
                        return {"taskId": task_id, "songs": songs}
            except Exception as e:
                log.warning(f"Poll error: {e}")

        log.error("Music generation timed out")
        return None

# ═══════════════════════════════════════════════════════════════════════════════
#  TELEGRAM BOT
# ═══════════════════════════════════════════════════════════════════════════════
class TelegramBot:
    """Telegram bot for interacting with users."""

    URL = "https://api.telegram.org/bot{token}/{method}"

    def __init__(self, agent: 'SongAgent'):
        self.agent = agent
        self.token = CFG.TG_BOT_TOKEN
        self.chat_id = str(CFG.TG_CHAT_ID) if CFG.TG_CHAT_ID else ""
        self.offset = 0
        self._stop = threading.Event()
        self.enabled = CFG.NOTIFICATIONS_DEFAULT
        self.sent_count = 0

        if self.token and self.chat_id:
            threading.Thread(target=self._listen, daemon=True, name="TGBot").start()
            log.info("Telegram bot started")
        else:
            log.warning("Telegram not configured - set TG_BOT_TOKEN and TG_CHAT_ID in config.py")

    def send(self, text: str, silent: bool = False, reply_markup: dict = None) -> bool:
        """Send message to Telegram."""
        if not self.enabled and not silent:
            return False
        if not self.token or not self.chat_id:
            return False

        try:
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "Markdown",
                "disable_notification": silent,
                "disable_web_page_preview": False
            }
            if reply_markup:
                payload["reply_markup"] = json.dumps(reply_markup)

            r = requests.post(
                self.URL.format(token=self.token, method="sendMessage"),
                json=payload,
                timeout=8
            )
            if r.json().get("ok"):
                self.sent_count += 1
                return True
            log.warning(f"TG error: {r.json().get('description', '?')}")
        except Exception as e:
            log.warning(f"TG send error: {e}")
        return False

    def send_with_buttons(self, text: str, buttons: list) -> bool:
        """Send message with inline keyboard buttons."""
        if not self.token or not self.chat_id:
            return False

        inline_keyboard = []
        for row in buttons:
            button_row = []
            for btn in row:
                button_row.append({"text": btn[0], "callback_data": btn[1]})
            inline_keyboard.append(button_row)

        reply_markup = {"inline_keyboard": inline_keyboard}
        return self.send(text, reply_markup=reply_markup)

    def send_typing(self):
        """Send typing indicator."""
        if not self.token or not self.chat_id:
            return
        try:
            requests.post(
                self.URL.format(token=self.token, method="sendChatAction"),
                json={"chat_id": self.chat_id, "action": "typing"},
                timeout=5
            )
        except Exception:
            pass

    def stop(self):
        """Stop the bot."""
        self._stop.set()

    def _listen(self):
        """Listen for incoming messages."""
        while not self._stop.is_set():
            try:
                r = requests.get(
                    self.URL.format(token=self.token, method="getUpdates"),
                    params={"offset": self.offset, "timeout": 5, "allowed_updates": ["message"]},
                    timeout=10
                )
                data = r.json()
                if not data.get("ok"):
                    continue
                for upd in data.get("result", []):
                    self.offset = upd["update_id"] + 1
                    try:
                        self._dispatch(upd)
                    except Exception as e:
                        log.error(f"Dispatch error: {e}")
            except Exception:
                continue

    def _dispatch(self, update: dict):
        """Handle incoming update."""
        msg = update.get("message", {})
        text = (msg.get("text") or "").strip()
        cid = str(msg.get("chat", {}).get("id", ""))

        if cid != self.chat_id:
            return
        if not text:
            return

        log.info(f"Received: {text}")
        self.agent.handle_message(text)

# ═══════════════════════════════════════════════════════════════════════════════
#  SONG AGENT - MAIN CLASS
# ═══════════════════════════════════════════════════════════════════════════════
class SongAgent:
    """
    Perfect AI Song Agent with natural language understanding.
    Just tell it what kind of song you want!
    """

    def __init__(self):
        self.state = StateManager()
        self.intent = IntentDetector()
        self.audiera = AudieraManager(CFG.AUDIERA_KEYS, CFG.AUDIERA_MODE)
        self.bot = TelegramBot(self)
        self.dedup_themes = self._load_dedup()
        self.artist_ids = CFG.ARTISTS
        self.evolution_stage = 0
        self.consecutive_fails = 0
        self.generating = False
        self.history = self._load_history()

        log.info(f"Song Agent initialized v{CFG.AGENT_VERSION}")
        if CFG.SEND_WELCOME_MESSAGE:
            self._send_startup_message()

    def _load_dedup(self) -> dict:
        """Load deduplication data."""
        dedup_file = MEM_DIR / "dedup.json"
        if dedup_file.exists():
            try:
                return json.loads(dedup_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"themes": [], "songs": []}

    def _save_dedup(self):
        """Save deduplication data."""
        dedup_file = MEM_DIR / "dedup.json"
        try:
            dedup_file.write_text(json.dumps(self.dedup_themes, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _load_history(self) -> list:
        """Load song history."""
        history_file = MEM_DIR / "history.json"
        if history_file.exists():
            try:
                return json.loads(history_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return []

    def _save_history(self):
        """Save song history."""
        history_file = MEM_DIR / "history.json"
        try:
            history_file.write_text(json.dumps(self.history, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _add_to_history(self, theme: str, styles: list, artist: str, url: str = ""):
        """Add song to history."""
        self.history.insert(0, {
            "theme": theme,
            "styles": ", ".join(styles),
            "artist": artist,
            "url": url,
            "ts": ts()
        })
        # Keep only last 200
        if len(self.history) > 200:
            self.history = self.history[:200]
        self._save_history()

    def _send_startup_message(self):
        """Send startup notification - minimal clean."""
        wallet_set = CFG.EVM_ADDRESS and CFG.EVM_ADDRESS != "0x" * 42

        msg = f"🎵 *{CFG.BOT_DISPLAY_NAME}* v{CFG.AGENT_VERSION}\n"
        msg += f"Songs: {self.state.song_count} | Keys: {self.audiera.active_count}"
        if wallet_set:
            msg += f" | {CFG.EVM_ADDRESS[:14]}..."
        msg += f"\n\n📖 Quick Guide:\n"
        msg += f"• Tell me: \"Make a happy pop song\"\n"
        msg += f"• Or use: /song <description>\n"
        msg += f"• Check: /status /keys /wallet\n"
        msg += f"\n📚 All Commands:\n"
        msg += f"/help - Show all commands\n"
        msg += f"/song <desc> - Create song\n"
        msg += f"/genres - List styles\n"
        msg += f"/keys - API keys\n"
        msg += f"/wallet - Wallet info\n"
        msg += f"/balance - Check $BEAT"

        self.bot.send(msg)

    # ═══════════════════════════════════════════════════════════════════════════
    #  MESSAGE HANDLING
    # ═══════════════════════════════════════════════════════════════════════════
    def handle_message(self, text: str):
        """Main message handler."""
        self.state.add_conversation("user", text)

        # Handle commands
        if text.startswith("/"):
            self._handle_command(text)
            return

        # Natural language processing
        self._handle_natural_language(text)

    def _handle_command(self, text: str):
        """Handle slash commands."""
        parts = text.split(maxsplit=1)
        cmd = parts[0].lower().lstrip("/")
        args = parts[1] if len(parts) > 1 else ""

        commands = {
            # Core commands
            "start": self._cmd_start,
            "help": self._cmd_help,
            "status": self._cmd_status,
            "reset": self._cmd_reset,
            "clear": self._cmd_reset,

            # Song commands
            "song": lambda: self._cmd_song(args),
            "create": lambda: self._cmd_song(args),
            "make": lambda: self._cmd_song(args),
            "generate": lambda: self._cmd_song(args),
            "rewrite": self._cmd_rewrite,
            "retry": self._cmd_retry,
            "morden": self._cmd_morden,
            "custom": lambda: self._cmd_custom(args),

            # Info commands
            "genres": self._cmd_genres,
            "styles": self._cmd_genres,
            "artists": self._cmd_artists,
            "list": self._cmd_list_all,

            # Config commands
            "config": self._cmd_config,
            "set": lambda: self._cmd_set(args),

            # Key management commands
            "keys": self._cmd_keys,
            "addkey": lambda: self._cmd_addkey(args),
            "removekey": lambda: self._cmd_removekey(args),
            "rotatekey": self._cmd_rotatekey,

            # EVM Wallet commands
            "wallet": self._cmd_wallet,
            "setwallet": lambda: self._cmd_setwallet(args),
            "setevm": lambda: self._cmd_setwallet(args),
            "balance": self._cmd_balance,

            # System commands
            "notifications": lambda: self._cmd_notifications(args),
            "notify": lambda: self._cmd_notifications(args),
            "debug": self._cmd_debug,
            "history": self._cmd_history,
        }

        if cmd in commands:
            try:
                commands[cmd]()
            except Exception as e:
                log.error(f"Command error: {e}")
                self.bot.send(f"Error: {str(e)[:50]}")
        else:
            # Unknown command - show help
            self.bot.send(
                f"Unknown command: /{cmd}\n\n"
                f"Type /help for all commands\n"
                f"Or just tell me what you want naturally!"
            )

    def _handle_natural_language(self, text: str):
        """Handle natural language song requests."""
        intent_data = self.intent.detect_intent(text)

        log.info(f"Intent: {intent_data['intent']}, theme={intent_data['theme']}, "
                f"mood={intent_data['mood']}, genre={intent_data['genre']}")

        # Store detected parameters
        self.state.last_request = text

        if intent_data["intent"] == "create_song":
            # Check if we have all info
            if intent_data["clarification_needed"]:
                self._ask_for_details(intent_data)
            else:
                self._create_song_with_params(intent_data)
        else:
            # Handle other intents
            self._handle_general_conversation(text, intent_data)

    def _ask_for_details(self, intent_data: dict):
        """Ask user for missing details."""
        clarifications = intent_data["clarification_needed"]

        if len(clarifications) == 1:
            # Single question - ask directly
            self.bot.send(f"🎵 *Sure! {clarifications[0]}*\n\n"
                         f"For example: \"{self._get_example_request(intent_data)}\"")
        else:
            # Multiple questions - show options
            msg = "🎵 *I'd love to create your song!*\n\n"
            msg += "Please tell me:\n"
            for i, c in enumerate(clarifications, 1):
                msg += f"{i}. {c}\n"
            msg += "\nOr just describe what you want in one sentence!\n"
            msg += f"Example: \"{self._get_example_request(intent_data)}\""
            self.bot.send(msg)

    def _get_example_request(self, intent_data: dict) -> str:
        """Get example request based on partial intent."""
        if intent_data["theme"]:
            if intent_data["mood"]:
                return f"Make a {intent_data['mood']} song about {intent_data['theme']}"
            if intent_data["genre"]:
                return f"Create a {intent_data['genre']} song about {intent_data['theme']}"
            return f"Make a song about {intent_data['theme']}"
        if intent_data["mood"]:
            return f"I want a {intent_data['mood']} and energetic song"
        if intent_data["genre"]:
            return f"Create an awesome {intent_data['genre']} track"
        return "Make a happy pop song about dancing"

    def _create_song_with_params(self, params: dict):
        """Create song with given parameters."""
        # Map detected genre to Audiera styles
        genre_to_styles = {
            "pop": ["Pop", "Dance"],
            "electronic": ["Electronic", "EDM"],
            "rock": ["Rock", "Metal"],
            "hip-hop": ["Hip-Hop", "R&B"],
            "r&b": ["R&B", "Soul"],
            "soul": ["Soul", "R&B"],
            "jazz": ["Jazz", "Blues"],
            "classical": ["Classical", "Ambient"],
            "ambient": ["Ambient", "Indie"],
            "indie": ["Indie", "Folk"],
            "folk": ["Folk", "Acoustic"],
            "metal": ["Metal", "Rock"],
            "dance": ["Dance", "Electronic"],
            "funk": ["Funk", "Soul"],
            "romantic": ["R&B", "Soul", "Pop"],
            "sad": ["R&B", "Soul"],
            "happy": ["Pop", "Dance"],
            "energetic": ["Dance", "Electronic"],
            "chill": ["Ambient", "Indie"],
            "dark": ["Electronic", "Ambient"],
            "nostalgic": ["Soul", "Funk"],
        }

        # Get styles
        if params.get("genre"):
            styles = genre_to_styles.get(params["genre"], CFG.DEFAULT_STYLES)
        elif params.get("mood"):
            styles = genre_to_styles.get(params["mood"], CFG.DEFAULT_STYLES)
        else:
            styles = CFG.DEFAULT_STYLES

        # Get artist
        artist = params.get("artist") or CFG.DEFAULT_ARTIST
        if artist not in self.artist_ids:
            artist = CFG.DEFAULT_ARTIST

        # Get theme
        theme = params.get("theme") or self._generate_theme(params)

        # Store params for potential rewrite
        self.state.last_song_params = {
            "theme": theme,
            "styles": styles,
            "artist": artist,
            "mood": params.get("mood"),
            "genre": params.get("genre")
        }

        # Show confirmation
        msg = f"🎵 *Creating Your Song!*\n\n"
        msg += f"🎨 Theme: `{theme}`\n"
        msg += f"🎸 Styles: {', '.join(styles)}\n"
        msg += f"🎤 Artist: {artist}\n"
        if params.get("mood"):
            msg += f"💭 Mood: {params['mood']}\n"
        msg += "\n⏳ Generating..."

        self.bot.send(msg)

        # Start generation in background
        threading.Thread(target=self._generate_song_async,
                        args=(theme, styles, artist), daemon=True).start()

    def _generate_theme(self, params: dict) -> str:
        """Generate a theme based on detected parameters."""
        moods = {
            "happy": ["joy of dancing", "sunshine moments", "celebration"],
            "sad": ["lost in thoughts", "rainy day reflections", "melancholy"],
            "angry": ["breaking free", "fight for change", "standing strong"],
            "romantic": ["love's embrace", "forever together", "heart's desire"],
            "chill": ["peaceful mornings", "quiet moments", "flowing streams"],
            "energetic": ["high voltage", "unstoppable", "alive and wild"],
            "nostalgic": ["memory lane", "yesterday's dreams", "timeless"],
            "dark": ["shadow dance", "midnight whispers", "unknown depths"],
        }

        mood_list = moods.get(params.get("mood", ""), ["electric dreams", "digital horizon"])
        import random
        base = random.choice(mood_list)

        if params.get("genre"):
            return f"{base} - {params['genre']} vibes"
        return base

    def _generate_song_async(self, theme: str, styles: list, artist: str):
        """Generate song in background thread."""
        if self.generating:
            self.bot.send("Already generating, please wait...")
            return
        
        self.generating = True
        try:
            # Check duplicate
            theme_lower = theme.lower()
            
            # Check dedup themes
            if theme_lower in self.dedup_themes["themes"]:
                self.bot.send(f"⚠️ Theme already used! Try a different theme.")
                return
            
            # Check history for similar theme
            for song in self.history:
                if theme_lower in song.get("theme", "").lower():
                    self.bot.send(f"⚠️ Similar song exists: {song.get('theme')}\nUse /history to see past songs.")
                    return
            
            # Check history for same artist + styles combination
            styles_str = ", ".join(styles).lower()
            for song in self.history[:10]:
                if song.get("artist", "").lower() == artist.lower():
                    if styles_str in song.get("styles", "").lower():
                        self.bot.send(f"⚠️ Recent song with same artist/style.\nTheme: {song.get('theme')}")
                        return

            # Generate lyrics
            lyrics, err = self.audiera.generate_lyrics(theme)
            if err:
                self._handle_error("lyrics", err)
                self.consecutive_fails += 1
                return

            # Get artist ID
            artist_id = self.artist_ids.get(artist, self.artist_ids[CFG.DEFAULT_ARTIST])

            # Generate music
            result, err = self.audiera.generate_music(styles, artist_id, lyrics)
            if err:
                self._handle_error("music", err)
                self.consecutive_fails += 1
                return
            
            if not result or not result.get("songs"):
                self.bot.send("No songs generated. Try again.")
                self.consecutive_fails += 1
                return

            songs = result["songs"]
            self.consecutive_fails = 0

            # Mark theme as used
            self.dedup_themes["themes"].append(theme_lower)
            if len(self.dedup_themes["themes"]) > 500:
                self.dedup_themes["themes"] = self.dedup_themes["themes"][-500:]
            self._save_dedup()

            # Update stats
            self.state.song_count += len(songs)
            self.state.run_count += 1

            # Learn from preferences
            if CFG.ENABLE_PREFERENCE_LEARNING:
                self._learn_preference(styles, artist)

            # Send results
            self._send_song_results(songs, theme, styles, artist)

        except Exception as e:
            log.error(f"Generation error: {e}")
            self.bot.send(f"❌ Error: {e}")
            self.consecutive_fails += 1
        finally:
            self.generating = False

    def _send_song_results(self, songs: list, theme: str, styles: list, artist: str):
        """Send song results - minimal clean."""
        msg = f"🎵 *Song Created!*\n"

        for i, song in enumerate(songs, 1):
            title = song.get("title", f"Track {i}")
            url = song.get("url", "")
            duration = song.get("duration", "?")
            msg += f"{i}. {title}"
            if url:
                msg += f" [{url}]"
            msg += f" ({duration}s)\n"

        msg += f"\nTheme: {theme}\n"
        msg += f"Styles: {', '.join(styles)}\n"
        msg += f"Artist: {artist}\n"
        msg += f"Total: {self.state.song_count} songs"

        self.bot.send(msg)
        
        # Add to history
        for song in songs:
            self._add_to_history(theme, styles, artist, song.get("url", ""))

    def _learn_preference(self, styles: list, artist: str):
        """Learn from user preferences."""
        prefs = self.state.user_preferences

        # Track style preferences
        for style in styles:
            if style not in prefs["preferred_styles"]:
                prefs["preferred_styles"].append(style)

        # Track artist preferences
        if artist not in prefs["preferred_artists"]:
            prefs["preferred_artists"].append(artist)

        self.state.save_preferences()

    def _handle_error(self, step: str, err: str):
        """Handle API errors with proper messages."""
        error_messages = {
            "rate_limit": "⚠️ Rate limited. Wait a moment and try again.",
            "invalid_key": "⚠️ Invalid API key. Check /keys config.",
            "forbidden": "⚠️ API access denied. Check key permissions.",
            "timeout": "⚠️ Request timed out. Check internet and try again.",
            "credits": "⚠️ Credits depleted. Add more credits to your account.",
            "api_error": "❌ API error. Try again later."
        }
        
        msg = error_messages.get(err, f"❌ {step} failed: {err[:50]}")
        self.bot.send(msg)

    def _handle_general_conversation(self, text: str, intent_data: dict):
        """Handle general conversation."""
        text_lower = text.lower()

        # Greetings
        greetings = ["hi", "hello", "hey", "namaste", "hola", "bonjour"]
        for g in greetings:
            if g in text_lower:
                self.bot.send(
                    f"👋 *Hello!* I'm *{CFG.BOT_DISPLAY_NAME}*!\n\n"
                    f"Just tell me what kind of song you want, and I'll create it!\n\n"
                    f"Try: \"Make a happy pop song\" or \"I want a romantic R&B track\""
                )
                return

        # Help requests
        if any(w in text_lower for w in ["help", "how", "what can", "commands"]):
            self._cmd_help()
            return

        # Status requests
        if any(w in text_lower for w in ["status", "stats", "how many", "how many songs"]):
            self._cmd_status()
            return

        # List genres
        if any(w in text_lower for w in ["list genres", "show genres", "what genres"]):
            self._cmd_genres()
            return

        # List artists
        if any(w in text_lower for w in ["list artists", "show artists", "who are"]):
            self._cmd_artists()
            return

        # Default: show available commands
        self.bot.send(
            f"🎵 *I understand you're interested in music!*\n\n"
            f"Here's how to create a song:\n\n"
            f"1️⃣ *Direct Request:* \"Make a pop song about love\"\n"
            f"2️⃣ *Style Request:* \"I want an energetic electronic track\"\n"
            f"3️⃣ *Mood Request:* \"Create a chill and relaxing song\"\n\n"
            f"Just describe what you want naturally!\n\n"
            f"Type `/help` for all commands."
        )

    # ═══════════════════════════════════════════════════════════════════════════
    #  COMMANDS
    # ═══════════════════════════════════════════════════════════════════════════
    def _cmd_start(self):
        """Start/welcome command."""
        self.bot.send(
            f"🎵 *Welcome to {CFG.BOT_DISPLAY_NAME}!*\n\n"
            f"I'm an AI agent that creates songs based on your requests.\n\n"
            f"✨ *Just tell me what you want!*\n"
            f"Examples:\n"
            f"• \"Make a happy song about summer\"\n"
            f"• \"I want a romantic R&B track\"\n"
            f"• \"Create energetic dance music\"\n\n"
            f"🎛️ *Commands:* `/help` `/genres` `/artists` `/status`"
        )

    def _cmd_help(self):
        """Show commands - minimal."""
        self.bot.send(
            f"📚 Commands\n\n"
            f"Song: /song /custom /rewrite /retry /history\n"
            f"Info: /genres /artists /status\n"
            f"Keys: /keys /addkey /removekey\n"
            f"Wallet: /wallet /setwallet /balance\n"
            f"System: /config /reset /debug\n\n"
            f"🎵 *Custom Song:*\n"
            f"/custom about=<theme> /lyrics=<lyrics> /artist=<name> /bpm=<70-180>\n\n"
            f"Examples:\n"
            f"/custom about=summer /artist=Kira /bpm=120\n"
            f"/custom about=party /lyrics=love this beat /bpm=140\n\n"
            f"Or just tell me what you want!"
        )

    def _cmd_status(self):
        """Show system status - minimal."""
        uptime = int((now_utc() - self.state.session_start).total_seconds())
        hours, rem = divmod(uptime, 3600)
        minutes = rem // 60

        msg = f"📊 Status | v{CFG.AGENT_VERSION}\n"
        msg += f"Uptime: {hours}h {minutes}m | Songs: {self.state.song_count}\n"
        msg += f"Keys: {self.audiera.active_count} | Mode: {self.audiera.mode.upper()}\n"
        if CFG.EVM_ADDRESS and CFG.EVM_ADDRESS != "0x" * 42:
            msg += f"Wallet: {CFG.EVM_ADDRESS[:14]}..."
        else:
            msg += f"Wallet: Not set"
        msg += f"\nNotify: {'ON' if self.bot.enabled else 'OFF'}"

        self.bot.send(msg)

    def _cmd_reset(self):
        """Reset all memory and state."""
        self.state.clear_all()
        self.dedup_themes = {"themes": [], "songs": []}
        self._save_dedup()
        self.evolution_stage = 0
        self.bot.send(
            f"🔄 *Reset Complete!*\n\n"
            f"All memory has been cleared.\n"
            f"Ready for fresh start!"
        )

    def _cmd_song(self, args: str):
        """Create a song with given description."""
        if not args:
            self.bot.send(
                f"🎵 *What kind of song do you want?*\n\n"
                f"Tell me in your own words!\n"
                f"Examples:\n"
                f"• \"Make a happy pop song\"\n"
                f"• \"I want romantic music\"\n"
                f"• \"Create energetic dance track\""
            )
            return

        self._handle_natural_language(args)

    def _cmd_rewrite(self):
        """Rewrite the last song."""
        if not self.state.last_song_params:
            self.bot.send("❌ No previous song to rewrite. Create one first!")
            return

        params = self.state.last_song_params
        self.bot.send(f"🔄 *Rewriting last song...*")

        # Slightly modify theme for variety
        import random
        modifiers = ["again", "redux", "v2", "fresh", "new version"]
        modifier = random.choice(modifiers)
        new_theme = f"{params['theme']} - {modifier}"

        threading.Thread(
            target=self._generate_song_async,
            args=(new_theme, params["styles"], params["artist"]),
            daemon=True
        ).start()

    def _cmd_retry(self):
        """Retry last failed generation."""
        if self.consecutive_fails == 0:
            self.bot.send("✅ No failed generations to retry!")
            return

        if not self.state.last_song_params:
            self.bot.send("❌ No song parameters to retry. Please create a new song.")
            return

        params = self.state.last_song_params
        self.bot.send(f"🔄 *Retrying last generation...*")

        threading.Thread(
            target=self._generate_song_async,
            args=(params["theme"], params["styles"], params["artist"]),
            daemon=True
        ).start()

    def _cmd_morden(self):
        """Generate a modern trending song."""
        import random

        modern_themes = [
            "midnight vibes", "neon dreams", "digital love",
            "city lights", "summer nights", "party mode",
            "chill waves", "future bass", "retro future"
        ]

        modern_styles = [
            ["Electronic", "Pop"],
            ["EDM", "Dance"],
            ["R&B", "Hip-Hop"],
            ["Synthwave", "Electronic"],
            ["Pop", "Dance", "Electronic"]
        ]

        theme = random.choice(modern_themes)
        styles = random.choice(modern_styles)
        artist = random.choice(list(self.artist_ids.keys()))

        self.state.last_song_params = {
            "theme": theme,
            "styles": styles,
            "artist": artist
        }

        msg = f"🔥 *MORDEN Mode Activated!*\n\n"
        msg += f"🎨 Theme: `{theme}`\n"
        msg += f"🎸 Styles: {', '.join(styles)}\n"
        msg += f"🎤 Artist: {artist}\n\n"
        msg += f"⏳ Generating..."

        self.bot.send(msg)

        threading.Thread(
            target=self._generate_song_async,
            args=(theme, styles, artist),
            daemon=True
        ).start()

    def _cmd_custom(self, args: str):
        """Custom song with full options."""
        if not args:
            self.bot.send(
                "🎵 *Custom Song Creator*\n\n"
                "Usage: /custom <options>\n\n"
                "Options:\n"
                "• Theme: \"about love\", \"summer vibes\"\n"
                "• Lyrics: \"your custom lyrics\" (optional)\n"
                "• Artist: Kira, Ray, Jason Miller...\n"
                "• BPM: 70 (slow), 120 (fast), 140 (party)\n\n"
                "Examples:\n"
                "/custom about=summer vibes /lyrics=love is in the air /artist=Kira /bpm=120\n"
                "/custom about=dance party /artist=Ray /bpm=140"
            )
            return
        
        # Parse custom options
        parts = args.split("/")
        theme = CFG.DEFAULT_STYLES[0]
        lyrics = None
        artist = CFG.DEFAULT_ARTIST
        bpm = 120
        
        for part in parts:
            part = part.strip()
            if part.startswith("about="):
                theme = part[6:].strip()
            elif part.startswith("lyrics="):
                lyrics = part[7:].strip()
            elif part.startswith("artist="):
                artist = part[7:].strip()
            elif part.startswith("bpm="):
                try:
                    bpm = int(part[4:].strip())
                except:
                    pass
        
        # Validate artist
        if artist not in self.artist_ids:
            artist = CFG.DEFAULT_ARTIST
        
        # Set styles based on BPM
        if bpm < 90:
            styles = ["Ambient", "Chill"]
        elif bpm < 120:
            styles = ["Pop", "R&B"]
        elif bpm < 140:
            styles = ["Electronic", "Dance"]
        else:
            styles = ["EDM", "Dance"]
        
        self.state.last_song_params = {
            "theme": theme,
            "styles": styles,
            "artist": artist,
            "custom_lyrics": lyrics,
            "bpm": bpm
        }
        
        msg = f"🎵 *Creating Custom Song*\n\n"
        msg += f"Theme: {theme}\n"
        msg += f"Styles: {', '.join(styles)}\n"
        msg += f"Artist: {artist}\n"
        msg += f"BPM: {bpm}\n"
        if lyrics:
            msg += f"Lyrics: Custom\n"
        msg += f"\n⏳ Generating..."
        
        self.bot.send(msg)
        
        threading.Thread(
            target=self._generate_song_async,
            args=(theme, styles, artist),
            daemon=True
        ).start()

    def _cmd_genres(self):
        """List genres - minimal."""
        self.bot.send(
            f"Styles\n{CFG.AVAILABLE_STYLES[0]}, {CFG.AVAILABLE_STYLES[1]}, {CFG.AVAILABLE_STYLES[2]}... ({len(CFG.AVAILABLE_STYLES)} total)\n\n"
            f"Mood: Happy→Pop, Sad→R&B, Chill→Ambient, Romantic→R&B"
        )

    def _cmd_artists(self):
        """List available artists."""
        msg = f"🎤 *Available Artists*\n\n"

        for name, desc in CFG.ARTIST_DESCRIPTIONS.items():
            msg += f"• *{name}*\n  _{desc}_\n\n"

        self.bot.send(msg)

    def _cmd_list_all(self):
        """List all available options."""
        self._cmd_genres()
        time.sleep(0.5)
        self._cmd_artists()

    def _cmd_config(self):
        """Show current configuration."""
        self.bot.send(
            f"⚙️ *Configuration*\n\n"
            f"*Agent:* `{CFG.AGENT_NAME}` v{CFG.AGENT_VERSION}\n"
            f"*Model:* `{CFG.AGENT_MODEL}`\n"
            f"*Default Artist:* `{CFG.DEFAULT_ARTIST}`\n"
            f"*Default Styles:* {', '.join(CFG.DEFAULT_STYLES)}\n"
            f"*Autonomous Mode:* `{'ON' if CFG.AUTONOMOUS_MODE else 'OFF'}`\n"
            f"*Preference Learning:* `{'ON' if CFG.ENABLE_PREFERENCE_LEARNING else 'OFF'}`\n"
            f"*Smart Suggestions:* `{'ON' if CFG.ENABLE_SMART_SUGGESTIONS else 'OFF'}`"
        )

    def _cmd_set(self, args: str):
        """Set configuration value."""
        if not args:
            self.bot.send("Usage: `/set <key> <value>`\n\nExample: `/set default_artist Kira`")
            return

        parts = args.split(maxsplit=1)
        if len(parts) < 2:
            self.bot.send("Please provide both key and value.\nExample: `/set default_artist Kira`")
            return

        key, value = parts
        self.bot.send(
            f"ℹ️ *Config Update*\n\n"
            f"To update configuration, please edit `config.py` directly.\n"
            f"Key: `{key}`\n"
            f"Value: `{value}`\n\n"
            f"Restart the bot to apply changes."
        )

    def _cmd_notifications(self, args: str):
        """Toggle notifications."""
        if not args:
            self.bot.send(f"Notifications: `{'ON' if self.bot.enabled else 'OFF'}`\n\nUsage: `/notifications on` or `/notifications off`")
            return

        args_lower = args.lower()
        if args_lower in ["on", "enable", "true"]:
            self.bot.enabled = True
            self.bot.send("✅ Notifications enabled!")
        elif args_lower in ["off", "disable", "false"]:
            self.bot.enabled = False
            self.bot.send("🔕 Notifications disabled!")
        else:
            self.bot.send("Usage: `/notifications on` or `/notifications off`")

    def _cmd_debug(self):
        """Show debug information."""
        prefs = self.state.user_preferences

        self.bot.send(
            f"🔍 *Debug Info*\n\n"
            f"*Last Intent:* `{self.state.last_request[:50]}...`\n"
            f"*Last Params:* `{json.dumps(self.state.last_song_params, default=str)[:100]}...`\n"
            f"*Conversation:* `{len(self.state.conversation_history)}` messages\n"
            f"*Dedup Themes:* `{len(self.dedup_themes['themes'])}`\n"
            f"*Consecutive Fails:* `{self.consecutive_fails}`\n"
            f"*Evolution Stage:* `{self.evolution_stage}`\n\n"
            f"*Preferences:*\n"
            f"• Styles: `{prefs.get('preferred_styles', [])}`\n"
            f"• Artists: `{prefs.get('preferred_artists', [])}`"
        )

    def _cmd_history(self):
        """Show song creation history."""
        if not self.history:
            self.bot.send("No song history yet. Create some songs!")
            return
        
        msg = f"📜 *Song History* ({len(self.history)} songs)\n\n"
        
        for i, song in enumerate(self.history[:20], 1):
            theme = song.get("theme", "?")
            artist = song.get("artist", "?")
            styles = song.get("styles", "?")
            url = song.get("url", "")
            ts = song.get("ts", "")
            
            msg += f"{i}. {theme[:30]}"
            if url:
                msg += f" [link]"
            msg += f"\n"
            msg += f"   {artist} • {styles[:20]}\n"
        
        if len(self.history) > 20:
            msg += f"\n...and {len(self.history) - 20} more"
        
        self.bot.send(msg)

    # ═══════════════════════════════════════════════════════════════════════════
    #  AUDIERA KEY MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════════
    def _cmd_keys(self):
        """Show API keys - minimal."""
        keys = self.audiera.keys
        if not keys:
            self.bot.send("No API keys configured")
            return

        msg = f"🔑 Keys ({len(keys)}) | Mode: {self.audiera.mode}\n"
        for i, k in enumerate(keys):
            status = "✓" if k.get("status") == "active" else "✗"
            key_short = f"{k['key'][:14]}..."
            current = " [active]" if i == self.audiera.idx else ""
            msg += f"{i+1}. {status} {key_short}{current}\n"

        msg += f"\nStats: {self.audiera.metrics['successes']}/{self.audiera.metrics['requests']} OK"
        self.bot.send(msg)

    def _cmd_addkey(self, args: str):
        """Add a new API key."""
        if not args:
            self.bot.send(
                "📝 *Add API Key*\n\n"
                "Usage: `/addkey <your_api_key>`\n\n"
                "Example: `/addkey sk_audiera_xxxxxxxxxx`"
            )
            return

        key = args.strip()
        success, msg = self.audiera.add_key(key)

        if success:
            self.bot.send(f"✅ *Key Added!*\n\n{msg}\n\nUse `/keys` to view all keys.")
        else:
            self.bot.send(f"❌ *Error*\n\n{msg}")

    def _cmd_removekey(self, args: str):
        """Remove an API key."""
        if not args:
            self.bot.send(
                "🗑️ *Remove API Key*\n\n"
                "Usage: `/removekey <index>`\n\n"
                "Example: `/removekey 1`\n\n"
                "Use `/keys` to see key indices."
            )
            return

        try:
            idx = int(args.strip()) - 1
            if idx < 0 or idx >= len(self.audiera.keys):
                self.bot.send(f"❌ Invalid index. Use `/keys` to see available indices.")
                return

            removed_key = self.audiera.keys.pop(idx)
            self.audiera._save_keys()
            key_short = f"{removed_key['key'][:12]}...{removed_key['key'][-6:]}"
            self.bot.send(f"✅ *Key Removed!*\n\n`{key_short}` has been removed.")

        except ValueError:
            self.bot.send("❌ Invalid index. Please provide a number.\nExample: `/removekey 1`")

    def _cmd_rotatekey(self):
        """Rotate to next API key."""
        if self.audiera.mode != "multi":
            self.bot.send(
                "⚠️ *Multi-Key Mode Not Enabled*\n\n"
                f"Current mode: `{self.audiera.mode.upper()}`\n\n"
                "To enable multi-key mode, set `AUDIERA_MODE = 'multi'` in config.py"
            )
            return

        if self.audiera.rotate():
            self.bot.send(f"✅ *Key Rotated!*\n\nCurrent: `{self.audiera.current_short}`")
        else:
            self.bot.send("❌ Cannot rotate. Only one active key available.")

    # ═══════════════════════════════════════════════════════════════════════════
    #  EVM WALLET MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════
    def _cmd_wallet(self):
        """Show wallet - minimal."""
        addr = CFG.EVM_ADDRESS

        if not addr or addr == "0x" * 42:
            self.bot.send("Wallet not set. Use /setwallet 0x...")
            return

        addr_short = f"{addr[:14]}..."
        self.bot.send(f"💳 Wallet\n{addr_short}\nContract: {CFG.BEAT_CONTRACT[:14]}...\n\n/balance to check $BEAT")

    def _cmd_setwallet(self, args: str):
        """Set EVM wallet address."""
        if not args:
            self.bot.send(
                "💳 *Set Wallet*\n\n"
                "Usage: `/setwallet <address>`\n\n"
                "Example: `/setwallet 0x1234567890abcdef1234567890abcdef12345678`\n\n"
                "This is your EVM-compatible wallet address for receiving $BEAT tokens."
            )
            return

        addr = args.strip()
        if not addr.startswith("0x") or len(addr) != 42:
            self.bot.send(
                "❌ *Invalid Address*\n\n"
                "EVM addresses must:\n"
                "• Start with `0x`\n"
                "• Be 42 characters long\n\n"
                "Example: `0x1234567890abcdef1234567890abcdef12345678`"
            )
            return

        CFG.EVM_ADDRESS = addr
        self._save_config()
        addr_short = f"{addr[:10]}...{addr[-6:]}"
        self.bot.send(f"✅ *Wallet Set!*\n\nAddress: `{addr_short}`\n\nUse `/balance` to check your balance.")

    def _cmd_balance(self):
        """Check BEAT token balance with retry."""
        addr = CFG.EVM_ADDRESS

        if not addr or addr == "0x" * 42:
            self.bot.send("Wallet not set. Use /setwallet 0x...")
            return

        self.bot.send(f"Checking $BEAT...\n{addr[:14]}...")

        rpc_providers = [
            "https://eth.llamarpc.com",
            "https://rpc.ankr.com/eth",
            "https://eth.public-rpc.com"
        ]

        for rpc_url in rpc_providers:
            try:
                from web3 import Web3
                w3 = Web3(Web3.HTTPProvider(rpc_url))

                if not w3.is_address(addr):
                    self.bot.send("Invalid address format.")
                    return

                contract_addr = Web3.to_checksum_address(CFG.BEAT_CONTRACT)
                wallet_addr = Web3.to_checksum_address(addr)
                
                abi = '[{"constant":true,"inputs":[{"name":"balanceOf","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"type":"function"}]'
                contract = w3.eth.contract(address=contract_addr, abi=abi)
                balance = contract.functions.balanceOf(wallet_addr).call()

                balance_beat = balance / 10**18
                addr_short = f"{addr[:14]}..."

                self.bot.send(
                    f"💰 $BEAT Balance\n"
                    f"Wallet: {addr_short}\n"
                    f"Balance: {balance_beat:,.4f} $BEAT"
                )
                return

            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "rate" in error_msg.lower():
                    continue
                self.bot.send(f"Error: {error_msg[:80]}")
                return

        self.bot.send("Rate limited. Try again later.")

    def _save_config(self):
        """Save configuration changes."""
        try:
            config_file = BASE_DIR / "config.py"
            content = config_file.read_text(encoding="utf-8")

            if 'EVM_ADDRESS   = "' in content:
                import re
                content = re.sub(
                    r'EVM_ADDRESS   = "[^"]*"',
                    f'EVM_ADDRESS   = "{CFG.EVM_ADDRESS}"',
                    content
                )

            config_file.write_text(content, encoding="utf-8")
        except Exception as e:
            log.warning(f"Could not save config: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description=f"{CFG.BOT_DISPLAY_NAME} - AI Song Creation Agent")
    parser.add_argument("--once", action="store_true", help="Generate one song and exit")
    parser.add_argument("--loop", action="store_true", help="Auto-generate songs in loop")
    parser.add_argument("--interval", type=int, default=CFG.DEFAULT_INTERVAL_MINUTES,
                       help=f"Interval between generations (minutes, default: {CFG.DEFAULT_INTERVAL_MINUTES})")
    parser.add_argument("--theme", type=str, help="Custom theme for song")
    parser.add_argument("--styles", nargs="+", help="Custom styles (e.g., Pop Electronic)")
    parser.add_argument("--artist", type=str, help="Custom artist name")
    parser.add_argument("--menu", action="store_true", help="Open interactive menu")
    parser.add_argument("--no-menu", action="store_true", help="Skip interactive menu")
    args = parser.parse_args()

    # Validate configuration
    if not CFG.TG_BOT_TOKEN or CFG.TG_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        print(f"{Colors.RED}ERROR: Telegram bot token not configured!{Colors.RESET}")
        print(f"Please edit config.py and set TG_BOT_TOKEN")
        return

    if not CFG.TG_CHAT_ID or CFG.TG_CHAT_ID == "YOUR_TELEGRAM_CHAT_ID_HERE":
        print(f"{Colors.RED}ERROR: Telegram chat ID not configured!{Colors.RESET}")
        print(f"Please edit config.py and set TG_CHAT_ID")
        return

    # Initialize agent
    try:
        agent = SongAgent()
    except Exception as e:
        print(f"{Colors.RED}ERROR: Failed to initialize agent: {e}{Colors.RESET}")
        return

    # Show menu only if --menu is explicitly passed
    if args.menu:
        banner()
        if run_interactive_menu(agent):
            return

    # Handle --once mode
    if args.once:
        print(f"\n{Colors.GREEN}Generating single song...{Colors.RESET}")

        theme = args.theme or input("Enter song theme: ") or "beautiful dreams"
        styles = args.styles or CFG.DEFAULT_STYLES
        artist = args.artist or CFG.DEFAULT_ARTIST

        print(f"Theme: {theme}")
        print(f"Styles: {styles}")
        print(f"Artist: {artist}")

        # Create song synchronously
        agent.state.last_song_params = {"theme": theme, "styles": styles, "artist": artist}

        # Check if we should use CLI output or Telegram
        if CFG.TG_BOT_TOKEN and CFG.TG_CHAT_ID:
            agent.bot.send(f"🎵 Generating: {theme}")
            # Generate async and wait
            thread = threading.Thread(
                target=agent._generate_song_async,
                args=(theme, styles, artist)
            )
            thread.start()
            thread.join(timeout=600)  # Wait up to 10 minutes
        else:
            # CLI mode
            print(f"{Colors.YELLOW}Note: Telegram not configured. Use Telegram bot for full experience.{Colors.RESET}")

        return

    # Handle --loop mode
    if args.loop:
        print(f"\n{Colors.GREEN}Starting autonomous loop mode...{Colors.RESET}")
        print(f"Interval: {args.interval} minutes")

        while True:
            try:
                # Generate with auto-detected parameters
                import random

                # Pick random mood/theme
                moods = ["happy", "sad", "energetic", "chill", "romantic", "dark"]
                mood = random.choice(moods)

                theme = f"{mood.capitalize()} moments"
                styles = CFG.MOOD_TO_STYLES.get(mood, CFG.DEFAULT_STYLES)
                artist = random.choice(list(CFG.ARTISTS.keys()))

                agent.state.last_song_params = {
                    "theme": theme,
                    "styles": styles,
                    "artist": artist,
                    "mood": mood
                }

                print(f"\n{Colors.CYAN}Generating: {theme} ({', '.join(styles)}){Colors.RESET}")

                # Generate async
                thread = threading.Thread(
                    target=agent._generate_song_async,
                    args=(theme, styles, artist)
                )
                thread.start()
                thread.join(timeout=600)

                print(f"{Colors.GREEN}Waiting {args.interval} minutes...{Colors.RESET}")
                time.sleep(args.interval * 60)

            except KeyboardInterrupt:
                print(f"\n{Colors.YELLOW}Stopping autonomous mode...{Colors.RESET}")
                break
            except Exception as e:
                print(f"{Colors.RED}Error in loop: {e}{Colors.RESET}")
                time.sleep(60)

    else:
        # Default: Run Telegram bot - minimal clean design
        c = Colors
        print()
        print(f"{c.CYAN}▶ Audiera{c.RESET} v{CFG.AGENT_VERSION} | {c.GREEN}ONLINE{c.RESET}")
        print(f"  Songs: {agent.state.song_count} | Keys: {agent.audiera.active_count}")
        if CFG.EVM_ADDRESS and CFG.EVM_ADDRESS != "0x" * 42:
            print(f"  Wallet: {CFG.EVM_ADDRESS[:14]}...")
        print()
        print(f"{c.DIM}Ctrl+C | /help{c.RESET}")
        print()

        try:
            # Keep main thread alive
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"\n{c.YELLOW}Shutting down...{c.RESET}")
            agent.bot.stop()

if __name__ == "__main__":
    main()
