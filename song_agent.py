#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              🎵  Audiera AI Song Agent  —  v3.1.0  🎵                       ║
║                                                                              ║
║  Natural language song creation powered by Audiera + Claude AI.             ║
║  Just describe what you want — Audiera handles the rest.                    ║
║                                                                              ║
║  Usage:                                                                      ║
║    python song_agent.py              → Interactive Telegram bot              ║
║    python song_agent.py --once       → Generate one song and exit           ║
║    python song_agent.py --loop       → Auto-generate on a schedule          ║
║    python song_agent.py --menu       → Open interactive CLI menu            ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

# ─── WINDOWS I/O FIX (must run first) ────────────────────────────────────────
import sys as _sys, os as _os, io as _io

def _fix_windows_io():
    if _sys.platform != "win32":
        return
    _os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    for _name in ("stdout", "stderr"):
        _s = getattr(_sys, _name, None)
        if isinstance(_s, _io.TextIOWrapper) and getattr(_s, "encoding", "") == "utf-8":
            continue
        try:
            _buf = getattr(_s, "buffer", None)
            if _buf:
                setattr(_sys, _name, _io.TextIOWrapper(_buf, encoding="utf-8", errors="replace"))
        except Exception:
            pass

_fix_windows_io()

# ─── STANDARD IMPORTS ────────────────────────────────────────────────────────
import json, time, signal, threading, argparse, traceback, hashlib, re, random
import logging as _logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
import requests
import sys

# Windows keyboard detection
try:
    import msvcrt
    WINDOWS = True
except ImportError:
    import select
    WINDOWS = False

# Optional web3 for wallet
try:
    from web3 import Web3
    HAS_WEB3 = True
except ImportError:
    Web3 = None
    HAS_WEB3 = False

# ─── CONFIGURATION ───────────────────────────────────────────────────────────
try:
    import config as CFG
except ImportError:
    print("\n  ✖  ERROR: config.py not found!\n")
    print("  ➤  Please create config.py in the same folder as this script.")
    print("  ➤  Use the provided config.py template and fill in your keys.\n")
    _sys.exit(1)

# ─── PATHS ───────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
OUT_DIR  = BASE_DIR / "output"
MEM_DIR  = BASE_DIR / "memory"
LOG_DIR  = BASE_DIR / "logs"
for _d in [OUT_DIR, MEM_DIR, LOG_DIR]:
    _d.mkdir(parents=True, exist_ok=True)

# ─── TIME HELPERS ────────────────────────────────────────────────────────────
def now_utc():
    return datetime.now(timezone.utc)

def ts():
    return now_utc().strftime("%Y-%m-%d %H:%M:%S UTC")

# ─── LOGGING ─────────────────────────────────────────────────────────────────
log = _logging.getLogger("AUDIERA")
log.setLevel(_logging.WARNING)
_lh = _logging.StreamHandler()
_lh.setFormatter(_logging.Formatter("%(levelname)-7s  %(message)s"))
log.addHandler(_lh)

if getattr(CFG, "VERBOSE_LOGGING", False) or getattr(CFG, "SAVE_LOG_FILE", False):
    try:
        _fh = _logging.FileHandler(
            LOG_DIR / f"song_agent_{datetime.now().strftime('%Y%m%d')}.log",
            encoding="utf-8"
        )
        _fh.setFormatter(_logging.Formatter("%(asctime)s  %(levelname)-7s  %(message)s", datefmt="%H:%M:%S"))
        log.addHandler(_fh)
        if getattr(CFG, "VERBOSE_LOGGING", False):
            log.setLevel(_logging.DEBUG)
    except Exception:
        pass

# ─── COLORS ──────────────────────────────────────────────────────────────────
class C:
    """ANSI color codes. Call C.disable() for plain terminals."""
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    ITALIC  = "\033[3m"
    UL      = "\033[4m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN    = "\033[96m"
    WHITE   = "\033[97m"
    ORANGE  = "\033[38;5;214m"
    PINK    = "\033[38;5;213m"
    TEAL    = "\033[38;5;51m"
    GRAY    = "\033[38;5;245m"
    BG_DARK = "\033[48;5;235m"

    # Semantic shortcuts
    OK      = "\033[92m"   # success
    WARN    = "\033[93m"   # warning
    ERR     = "\033[91m"   # error
    INFO    = "\033[96m"   # info
    ACCENT  = "\033[95m"   # highlight

    @classmethod
    def disable(cls):
        for attr in vars(cls):
            if not attr.startswith("_") and isinstance(getattr(cls, attr), str):
                setattr(cls, attr, "")

def p(*args, **kwargs):
    """Safe print with encoding fallback."""
    try:
        print(*args, **kwargs)
    except Exception:
        try:
            _os.write(1, (" ".join(str(a) for a in args) + "\n").encode("utf-8", "replace"))
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
#  CLI BANNER & STATUS
# ══════════════════════════════════════════════════════════════════════════════
# ── shared visual helpers ─────────────────────────────────────────────────────
def _ansi_len(s: str) -> int:
    """Return visual length of a string, ignoring ANSI escape codes."""
    return len(re.sub(r'\033\[[^m]*m', '', s))

def _pad(s: str, width: int) -> str:
    """Right-pad s to visual width, accounting for ANSI codes."""
    return s + " " * max(0, width - _ansi_len(s))

def _tstamp() -> str:
    return datetime.now().strftime("%H:%M:%S")

# Log-level icon+color key — colors read dynamically so --no-color works
_LOG_LEVEL_KEYS = {
    "ok":   ("✔", "OK"),
    "info": ("◆", "INFO"),
    "warn": ("▲", "WARN"),
    "err":  ("✖", "ERR"),
    "gen":  ("♫", "MAGENTA"),
    "auto": ("⚡", "PINK"),
    "wait": ("◌", "GRAY"),
}

def log_line(level: str, msg: str, detail: str = ""):
    """
    Print a modern, structured log line:
      HH:MM:SS  ✔  OK    message   detail
    Colors are read at call-time so --no-color takes effect.
    """
    icon, color_attr = _LOG_LEVEL_KEYS.get(level.lower(), ("·", "WHITE"))
    col      = getattr(C, color_attr, "")
    label    = level.upper().ljust(4)
    ts_part  = f"{C.GRAY}{_tstamp()}{C.RESET}"
    ico_part = f"{col}{icon}{C.RESET}"
    lbl_part = f"{col}{C.BOLD}{label}{C.RESET}"
    msg_part = f"{C.WHITE}{msg}{C.RESET}"
    det_part = f"  {C.DIM}{detail}{C.RESET}" if detail else ""
    p(f"  {ts_part}  {ico_part}  {lbl_part}  {msg_part}{det_part}")


def banner():
    """Print the premium startup banner with modern design."""
    W = 72
    accent   = C.CYAN
    hi       = C.MAGENTA
    dim      = C.DIM
    rst      = C.RESET
    bold     = C.BOLD
    white    = C.WHITE

    title    = "  🎵  AUDIERA  —  AI Song Agent  🎵  "
    subtitle = f"v{CFG.AGENT_VERSION}  ·  Natural Language Song Creation  ·  Powered by AI"

    p()
    p(f"{accent}╭{'─'*W}╮{rst}")
    p(f"{accent}│{rst}{' '*W}{accent}│{rst}")

    # Title row — centered, bold magenta highlight on keyword
    t_pad = (W - len(re.sub(r'\033\[[^m]*m', '', title))) // 2
    colored_title = (
        f"{bold}{white}  🎵  {rst}"
        f"{bold}{hi}AUDIERA{rst}"
        f"{bold}{white}  —  AI Song Agent  🎵  {rst}"
    )
    raw_t = _ansi_len(colored_title)
    t_left = (W - raw_t) // 2
    p(f"{accent}│{rst}{' '*t_left}{colored_title}{' '*(W - t_left - raw_t)}{accent}│{rst}")

    # Subtitle row
    s_left = (W - len(subtitle)) // 2
    p(f"{accent}│{rst}{dim}{' '*s_left}{subtitle}{' '*(W - s_left - len(subtitle))}{rst}{accent}│{rst}")
    p(f"{accent}│{rst}{' '*W}{accent}│{rst}")

    # Bottom accent bar
    bar = "─" * (W // 3) + "  ◆ ONLINE ◆  " + "─" * (W // 3)
    bar = bar[:W]
    b_left = (W - len(bar)) // 2
    p(f"{accent}│{rst}{hi}{' '*b_left}{bar}{' '*(W - b_left - len(bar))}{rst}{accent}│{rst}")
    p(f"{accent}│{rst}{' '*W}{accent}│{rst}")
    p(f"{accent}╰{'─'*W}╯{rst}")
    p()


def print_status_bar(agent=None):
    """Print a rich dashboard-style status strip."""
    W = 72
    accent = C.CYAN
    rst    = C.RESET

    if agent is None:
        ts = _tstamp()
        p(f"\n  {accent}◆{rst} {C.BOLD}{C.WHITE}Audiera{rst} {C.DIM}v{CFG.AGENT_VERSION}{rst}"
          f"  {C.DIM}│{rst}  {C.YELLOW}● initializing…{rst}  {C.GRAY}{ts}{rst}")
        return

    keys_ok = agent.audiera.active_count
    songs   = agent.state.song_count
    mode    = "MULTI" if CFG.AUDIERA_MODE == "multi" else "SINGLE"
    wallet  = (CFG.EVM_ADDRESS[:10] + "…") if CFG.EVM_ADDRESS and len(CFG.EVM_ADDRESS) > 12 else "—"
    auto_s  = (f"{C.PINK}● AUTO{rst}" if agent.auto_engine.active else f"{C.GRAY}○ AUTO{rst}")
    ts      = _tstamp()

    sep = f"  {C.DIM}│{rst}  "
    p()
    p(f"  {accent}╭{'─'*W}╮{rst}")
    row = (
        f"  {C.BOLD}{C.WHITE}Audiera{rst} {C.DIM}v{CFG.AGENT_VERSION}{rst}"
        + sep + f"{C.OK}● ONLINE{rst}"
        + sep + f"{C.YELLOW}⚿ {keys_ok} key{'s' if keys_ok!=1 else ''}{rst}"
        + sep + f"{C.WHITE}♫ {songs} songs{rst}"
        + sep + f"{C.DIM}{mode}{rst}"
        + sep + auto_s
        + sep + f"{C.DIM}wallet {wallet}{rst}"
        + sep + f"{C.GRAY}{ts}{rst}"
    )
    inner = f" {row}  "
    raw   = _ansi_len(inner)
    pad   = max(0, W - raw)
    p(f"  {accent}│{rst}{inner}{' '*pad}{accent}│{rst}")
    hint = "Ctrl+C to quit  ·  /help in Telegram  ·  /auto_mode on for autonomous mode"
    h_pad = max(0, W - len(hint) - 1)
    p(f"  {accent}│{rst}  {C.DIM}{hint}{' '*h_pad}{rst}{accent}│{rst}")
    p(f"  {accent}╰{'─'*W}╯{rst}")
    p()


def print_section(title: str, width: int = 58):
    """Print a modern rounded section header."""
    inner = f"  {C.BOLD}{C.WHITE}{title}{C.RESET}"
    raw   = _ansi_len(inner)
    right = max(0, width - raw - 1)
    p()
    p(f"{C.CYAN}╭{'─'*width}╮{C.RESET}")
    p(f"{C.CYAN}│{C.RESET}{inner}{' '*right}{C.CYAN}│{C.RESET}")
    p(f"{C.CYAN}╰{'─'*width}╯{C.RESET}")


def print_info_box(lines: List[Tuple[str,str]], width: int = 58):
    """Print a modern rounded key-value card."""
    p(f"{C.CYAN}╭{'─'*width}╮{C.RESET}")
    for i, (key, val) in enumerate(lines):
        # alternate row tint for readability
        key_s = f"{C.DIM}{key:<15}{C.RESET}"
        val_s = f"{C.BOLD}{C.WHITE}{val}{C.RESET}"
        inner = f"  {key_s}{val_s}"
        raw   = _ansi_len(inner)
        pad   = max(0, width - raw)
        p(f"{C.CYAN}│{C.RESET}{inner}{' '*pad}{C.CYAN}│{C.RESET}")
        # subtle separator between rows except the last
        if i < len(lines) - 1:
            p(f"{C.CYAN}│{C.RESET}{C.DIM}{'·'*width}{C.RESET}{C.CYAN}│{C.RESET}")
    p(f"{C.CYAN}╰{'─'*width}╯{C.RESET}")


class Spinner:
    """Modern CLI spinner with elapsed-time counter."""
    FRAMES = [
        "⠋","⠙","⠸","⠴","⠦","⠧","⠇","⠏",
        "⠋","⠙","⠸","⠼","⠴","⠦","⠧","⠇","⠏",
    ]
    DOTS = ["   ","·  ","·· ","···","·· ","·  "]

    def __init__(self, label: str = "Working"):
        self.label    = label
        self._stop    = threading.Event()
        self._thread  = None
        self._started = 0.0

    def start(self):
        self._stop.clear()
        self._started = time.time()
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def stop(self, final: str = ""):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1)
        sys.stdout.write(f"\r{' '*80}\r")
        sys.stdout.flush()
        if final:
            p(final)

    def _spin(self):
        i = 0
        while not self._stop.is_set():
            frame   = self.FRAMES[i % len(self.FRAMES)]
            dots    = self.DOTS[i % len(self.DOTS)]
            elapsed = int(time.time() - self._started)
            mins, secs = divmod(elapsed, 60)
            elapsed_s = f"{mins:02d}:{secs:02d}"
            line = (
                f"\r  {C.CYAN}{frame}{C.RESET}  "
                f"{C.BOLD}{C.WHITE}{self.label}{C.RESET}"
                f"{C.MAGENTA}{dots}{C.RESET}  "
                f"{C.GRAY}[{elapsed_s}]{C.RESET}  "
                f"{C.DIM}(this may take 1–3 min){C.RESET}   "
            )
            sys.stdout.write(line)
            sys.stdout.flush()
            time.sleep(0.12)
            i += 1


# ══════════════════════════════════════════════════════════════════════════════
#  CONFIG VALIDATOR  — guides user through broken setups
# ══════════════════════════════════════════════════════════════════════════════
class ConfigValidator:
    """Validates config.py and prints human-friendly guidance on problems."""

    GUIDES = {
        "no_token": (
            "Telegram Bot Token is missing or still set to the placeholder.",
            [
                "Open Telegram and search for @BotFather",
                "Send /newbot and follow the prompts",
                "Copy the token (looks like 1234567890:AABBccDD…)",
                "Paste it into config.py  →  TG_BOT_TOKEN = \"your_token\"",
            ]
        ),
        "no_chat_id": (
            "Telegram Chat ID is missing or still a placeholder.",
            [
                "Open Telegram and search for @userinfobot",
                "Send /start — it replies with your numeric ID",
                "Paste it into config.py  →  TG_CHAT_ID = \"your_id\"",
            ]
        ),
        "no_api_key": (
            "No active Audiera API key found.",
            [
                "Visit https://ai.audiera.fi and log in",
                "Go to API Keys → Create New Key",
                "Copy the key (starts with sk_audiera_…)",
                "Paste it into config.py  →  AUDIERA_KEYS = [{\"key\": \"sk_audiera_…\", \"status\": \"active\"}]",
            ]
        ),
        "bad_key_format": (
            "An Audiera key does not have the expected format.",
            [
                "All Audiera keys must start with  sk_audiera_",
                "Check for copy-paste errors (extra spaces, missing characters)",
                "Get a fresh key from  https://ai.audiera.fi",
            ]
        ),
        "no_web3": (
            "web3 library is not installed — wallet features will be unavailable.",
            [
                "Run:  pip install web3",
                "Or to skip wallet features, leave EVM_ADDRESS empty in config.py",
            ]
        ),
    }

    @classmethod
    def validate(cls) -> Tuple[bool, List[str]]:
        """
        Check all required config values. Returns (ok, list_of_error_codes).
        Prints detailed, colour-coded guidance for every problem found.
        """
        errors = []

        # Telegram token
        tok = getattr(CFG, "TG_BOT_TOKEN", "")
        if not tok or "YOUR_TELEGRAM" in tok or len(tok) < 20:
            errors.append("no_token")

        # Telegram chat ID
        cid = str(getattr(CFG, "TG_CHAT_ID", ""))
        if not cid or "YOUR_TELEGRAM" in cid or not cid.strip("-").isdigit():
            errors.append("no_chat_id")

        # Audiera keys
        keys = getattr(CFG, "AUDIERA_KEYS", [])
        active = [k for k in keys if k.get("status") == "active"]
        if not active:
            errors.append("no_api_key")
        elif any(not k.get("key","").startswith("sk_audiera_") for k in active):
            errors.append("bad_key_format")

        # web3 (optional)
        if not HAS_WEB3 and getattr(CFG, "EVM_ADDRESS", ""):
            errors.append("no_web3")

        if errors:
            cls._print_errors(errors)

        return len(errors) == 0, errors

    @classmethod
    def _print_errors(cls, codes: List[str]):
        W = 68
        p()
        p(f"{C.ERR}╭{'─'*W}╮{C.RESET}")
        hdr = f"  {C.BOLD}{C.WHITE}⚠  Configuration Problems Detected{C.RESET}"
        p(f"{C.ERR}│{C.RESET}{_pad(hdr, W)}{C.ERR}│{C.RESET}")
        ts_hdr = f"  {C.DIM}{_tstamp()}{C.RESET}"
        p(f"{C.ERR}│{C.RESET}{_pad(ts_hdr, W)}{C.ERR}│{C.RESET}")
        p(f"{C.ERR}├{'─'*W}┤{C.RESET}")
        for i, code in enumerate(codes, 1):
            title, steps = cls.GUIDES.get(code, (f"Unknown error: {code}", []))
            prob = f"  {C.WARN}▲  [{i}/{len(codes)}]{C.RESET}  {C.WHITE}{title}{C.RESET}"
            p(f"{C.ERR}│{C.RESET}{_pad(prob, W)}{C.ERR}│{C.RESET}")
            p(f"{C.ERR}│{C.RESET}{' '*W}{C.ERR}│{C.RESET}")
            for j, step in enumerate(steps, 1):
                step_s = f"      {C.CYAN}{j}.{C.RESET}  {C.DIM}{step}{C.RESET}"
                p(f"{C.ERR}│{C.RESET}{_pad(step_s, W)}{C.ERR}│{C.RESET}")
            if i < len(codes):
                p(f"{C.ERR}│{C.RESET}{C.DIM}{'·'*W}{C.RESET}{C.ERR}│{C.RESET}")
        p(f"{C.ERR}╰{'─'*W}╯{C.RESET}")
        p()


# ══════════════════════════════════════════════════════════════════════════════
#  INTERACTIVE CLI MENU
# ══════════════════════════════════════════════════════════════════════════════
class InteractiveMenu:
    """
    Arrow-key (or number-key) navigable CLI menu.
    Works on Windows (msvcrt) and Unix (select).
    """

    def __init__(self):
        self.items:    List[dict] = []
        self.selected: int        = 0
        self.scroll:   int        = 0
        self.MAX_VISIBLE          = 18

    def add(self, key: str, icon: str, title: str, subtitle: str = "", action=None):
        self.items.append({"key": key, "icon": icon, "title": title,
                           "subtitle": subtitle, "action": action})

    def run(self) -> bool:
        if not self.items:
            return False
        self._draw()
        while True:
            k = self._get_key()
            if k == "up":
                self.selected = max(0, self.selected - 1)
                if self.selected < self.scroll:
                    self.scroll = self.selected
            elif k == "down":
                self.selected = min(len(self.items) - 1, self.selected + 1)
                if self.selected >= self.scroll + self.MAX_VISIBLE:
                    self.scroll = self.selected - self.MAX_VISIBLE + 1
            elif k == "enter":
                self._clear()
                item = self.items[self.selected]
                if item["action"]:
                    return item["action"]()
                return False
            elif k in ("escape", "q", "Q"):
                self._clear()
                return False
            elif k.isdigit():
                idx = int(k) - 1
                if 0 <= idx < len(self.items):
                    self.selected = idx
                    self._clear()
                    item = self.items[idx]
                    if item["action"]:
                        return item["action"]()
                    return False
            if k:
                self._draw()

    # ── drawing ──────────────────────────────────────────────────────────────
    def _draw(self):
        self._clear()
        W   = 66
        ac  = C.CYAN
        rst = C.RESET
        ts  = _tstamp()

        # ── header ──────────────────────────────────────────────────
        p(f"{ac}╭{'─'*W}╮{rst}")
        # Logo row
        logo = f"  {C.BOLD}{C.WHITE}🎵  AUDIERA{rst}  {C.DIM}AI Song Agent{rst}"
        ver  = f"{C.DIM}v{CFG.AGENT_VERSION}  {ts}{rst}"
        logo_raw = _ansi_len(logo); ver_raw = _ansi_len(ver)
        gap = max(1, W - logo_raw - ver_raw - 2)
        p(f"{ac}│{rst} {logo}{' '*gap}{ver} {ac}│{rst}")
        p(f"{ac}├{'─'*W}┤{rst}")

        # ── menu items ──────────────────────────────────────────────
        visible = self.items[self.scroll : self.scroll + self.MAX_VISIBLE]
        for i, item in enumerate(visible):
            idx      = i + self.scroll
            selected = idx == self.selected
            if selected:
                # Highlighted row: filled accent
                num    = f"{C.BOLD}{C.YELLOW}[{item['key']}]{rst}"
                icon   = f"{C.YELLOW}{item['icon']}{rst}"
                title  = f"{C.BOLD}{C.WHITE}{item['title']}{rst}"
                sub    = f"  {C.CYAN}{item['subtitle']}{rst}" if item["subtitle"] else ""
                cursor = f"{C.MAGENTA}❯{rst}"
                bg     = f"{C.CYAN}│{rst}"
                inner  = f" {cursor} {num} {icon} {title}{sub}"
            else:
                num    = f"{C.DIM}[{item['key']}]{rst}"
                icon   = item["icon"]
                title  = f"{C.WHITE}{item['title']}{rst}"
                sub    = f"  {C.DIM}{item['subtitle']}{rst}" if item["subtitle"] else ""
                cursor = " "
                bg     = f"{ac}│{rst}"
                inner  = f"   {num} {icon} {title}{sub}"

            pad = max(0, W - _ansi_len(inner))
            p(f"{bg}{inner}{' '*pad}{bg}")

        # ── footer ──────────────────────────────────────────────────
        p(f"{ac}├{'─'*W}┤{rst}")
        hint = "  ↑ ↓  move    ↵  select    0-9  jump    Q  quit"
        h_pad = max(0, W - len(hint))
        p(f"{ac}│{rst}{C.DIM}{hint}{' '*h_pad}{rst}{ac}│{rst}")
        p(f"{ac}╰{'─'*W}╯{rst}")

    def _clear(self):
        try:
            _os.system("cls" if _os.name == "nt" else "clear")
        except Exception:
            print("\033[2J\033[H", end="")

    # ── key reading ──────────────────────────────────────────────────────────
    def _get_key(self) -> str:
        try:
            if WINDOWS:
                if msvcrt.kbhit():
                    ch = msvcrt.getch()
                    if ch == b"\xe0":
                        ch2 = msvcrt.getch()
                        if ch2 == b"H": return "up"
                        if ch2 == b"P": return "down"
                    elif ch in (b"\r", b" "): return "enter"
                    elif ch == b"\x1b":       return "escape"
                    elif ch == b"q":          return "q"
                    elif ch.isdigit():        return ch.decode()
            else:
                r, _, _ = select.select([sys.stdin], [], [], 0.05)
                if r:
                    ch = sys.stdin.read(1)
                    if ch == "\x1b":
                        extra = sys.stdin.read(2) if r else ""
                        if extra == "[A": return "up"
                        if extra == "[B": return "down"
                        return "escape"
                    elif ch in ("\n", " "): return "enter"
                    elif ch in ("q", "Q"): return "q"
                    elif ch.isdigit():     return ch
        except Exception:
            pass
        return ""


# ══════════════════════════════════════════════════════════════════════════════
#  MENU ACTIONS  (standalone helpers used by the interactive menu)
# ══════════════════════════════════════════════════════════════════════════════
def _pause():
    input(f"\n  {C.DIM}Press ENTER to return to the menu…{C.RESET}")

def menu_generate_one(agent) -> bool:
    """Interactive single-song generation from the CLI."""
    print_section("🎵  Generate One Song")
    theme   = input(f"\n  {C.CYAN}Theme / description:{C.RESET}  ").strip() or "beautiful dreams"
    sraw    = input(f"  {C.CYAN}Styles (comma-sep, blank = default):{C.RESET}  ").strip()
    styles  = [s.strip() for s in sraw.split(",")] if sraw else CFG.DEFAULT_STYLES
    artist  = input(f"  {C.CYAN}Artist (blank = {CFG.DEFAULT_ARTIST}):{C.RESET}  ").strip() or CFG.DEFAULT_ARTIST

    p(f"\n  {C.YELLOW}Starting generation…{C.RESET}")
    agent.state.last_song_params = {"theme": theme, "styles": styles, "artist": artist}
    t = threading.Thread(target=agent._generate_song_async, args=(theme, styles, artist), daemon=True)
    t.start()
    spin = Spinner("Generating")
    spin.start()
    t.join()
    spin.stop(f"  {C.OK}✔  Done!{C.RESET}")
    _pause()
    return False

def menu_auto_loop(agent) -> bool:
    """Start the autonomous generation loop from the CLI."""
    print_section("🔄  Autonomous Loop")
    try:
        interval = int(input(f"\n  {C.CYAN}Interval in minutes (default 30):{C.RESET}  ") or "30")
    except ValueError:
        interval = 30

    log_line("ok", f"Loop started — {interval} min interval", "Ctrl+C to stop")
    p()
    cycle = 0
    while True:
        try:
            cycle += 1
            mood   = random.choice(["happy","sad","energetic","chill","romantic","dark"])
            theme  = f"{mood.capitalize()} moments"
            styles = CFG.MOOD_TO_STYLES.get(mood, CFG.DEFAULT_STYLES)
            artist = random.choice(list(CFG.ARTISTS.keys()))
            agent.state.last_song_params = {"theme": theme, "styles": styles, "artist": artist, "mood": mood}

            log_line("gen", f"Cycle {cycle}  ·  {theme}", f"{', '.join(styles)}  ·  {artist}")
            t = threading.Thread(target=agent._generate_song_async, args=(theme, styles, artist), daemon=True)
            t.start(); t.join()
            log_line("ok", f"Cycle {cycle} done", f"total songs: {agent.state.song_count}")
            log_line("wait", f"Sleeping {interval} min…")
            time.sleep(interval * 60)
        except KeyboardInterrupt:
            p()
            log_line("warn", "Loop stopped by user", f"completed {cycle} cycle(s)")
            break
    _pause()
    return False

def menu_auto_mode(agent) -> bool:
    """Start the intelligent autonomous generation engine from the CLI."""
    print_section("🧠  Auto Mode — Fully Autonomous Generation")
    p(f"\n  {C.DIM}Mood  ← time-of-day  │  Style ← day-of-week  │  Artist ← round-robin  │  Interval ← adaptive{C.RESET}\n")
    try:
        interval = int(input(f"  {C.CYAN}Interval in minutes (default {agent.auto_engine.current_interval}):{C.RESET}  ")
                       or str(agent.auto_engine.current_interval))
    except ValueError:
        interval = agent.auto_engine.current_interval
    try:
        songs_pc = int(input(f"  {C.CYAN}Songs per cycle (default 1):{C.RESET}  ") or "1")
    except ValueError:
        songs_pc = 1

    agent.auto_engine.configure(interval=interval, songs=songs_pc)
    p()
    log_line("auto", "Auto Mode engine starting",
             f"{interval} min  ·  {songs_pc} song(s)/cycle")
    log_line("info", "Intelligence active",
             "time-of-day mood  ·  day-of-week style  ·  adaptive interval")
    p()

    agent.auto_engine.start()
    try:
        prev_cycle = -1
        while agent.auto_engine.active:
            ae = agent.auto_engine
            if ae.cycle_count != prev_cycle:
                prev_cycle = ae.cycle_count
                if ae.cycle_count > 0:
                    log_line("auto",
                             f"Cycle {ae.cycle_count} complete",
                             f"songs={agent.state.song_count}  interval={ae.current_interval}min  "
                             f"streak={'✔'+str(ae.success_streak) if ae.success_streak else '✖'+str(ae.fail_streak)}")
            time.sleep(2)
    except KeyboardInterrupt:
        agent.auto_engine.stop()
        p()
        log_line("warn", "Auto Mode stopped by user",
                 f"cycles={agent.auto_engine.cycle_count}  songs={agent.state.song_count}")
    _pause()
    return False


def menu_show_status(agent) -> bool:
    """Display a detailed system status box."""
    print_section("📊  System Status")
    uptime_s = int((now_utc() - agent.state.session_start).total_seconds())
    h, rem = divmod(uptime_s, 3600); m = rem // 60
    wallet_s = (CFG.EVM_ADDRESS[:14] + "…") if CFG.EVM_ADDRESS and len(CFG.EVM_ADDRESS) > 14 else "not set"
    p()
    print_info_box([
        ("Agent",     CFG.AGENT_NAME),
        ("Version",   CFG.AGENT_VERSION),
        ("Model",     CFG.AGENT_MODEL),
        ("Uptime",    f"{h}h {m}m"),
        ("Songs Made",str(agent.state.song_count)),
        ("API Keys",  f"{agent.audiera.active_count} active"),
        ("Key Mode",  CFG.AUDIERA_MODE.upper()),
        ("Wallet",    wallet_s),
        ("web3",      "✔ installed" if HAS_WEB3 else "✖ not installed"),
        ("Notify",    "ON" if agent.bot.enabled else "OFF"),
    ])
    _pause()
    return False

def menu_manage_keys(agent) -> bool:
    """CLI key management sub-menu."""
    print_section("🔑  API Key Management")
    p()
    for i, k in enumerate(agent.audiera.keys, 1):
        st  = f"{C.OK}ACTIVE{C.RESET}" if k.get("status") == "active" else f"{C.ERR}INACTIVE{C.RESET}"
        key = k["key"]
        display = f"{key[:18]}…{key[-6:]}" if len(key) > 25 else key
        p(f"  {C.DIM}[{i}]{C.RESET}  {display}  {st}")
    p(f"\n  {C.DIM}A{C.RESET} Add key   {C.DIM}R{C.RESET} Remove key   {C.DIM}Q{C.RESET} Back")
    choice = input(f"\n  Choice: ").strip().lower()

    if choice == "a":
        key = input(f"  {C.CYAN}Paste API key:{C.RESET}  ").strip()
        ok, msg = agent.audiera.add_key(key)
        p(f"  {C.OK if ok else C.ERR}{'✔' if ok else '✖'}  {msg}{C.RESET}")
    elif choice == "r":
        raw = input(f"  {C.CYAN}Index to remove:{C.RESET}  ").strip()
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(agent.audiera.keys):
                removed = agent.audiera.keys.pop(idx)
                agent.audiera._save_keys()
                p(f"  {C.OK}✔  Removed key [{idx+1}]{C.RESET}")
            else:
                p(f"  {C.ERR}✖  Index out of range{C.RESET}")
        except ValueError:
            p(f"  {C.ERR}✖  Invalid number{C.RESET}")
    _pause()
    return False

def menu_manage_wallet(agent) -> bool:
    """CLI wallet sub-menu."""
    print_section("💳  Wallet Management")
    p()
    print_info_box([
        ("Address",  CFG.EVM_ADDRESS or "—"),
        ("Contract", CFG.BEAT_CONTRACT),
        ("web3",     "installed" if HAS_WEB3 else "not installed — run: pip install web3"),
    ])
    p(f"\n  {C.DIM}S{C.RESET} Set address   {C.DIM}B{C.RESET} Check balance   {C.DIM}Q{C.RESET} Back")
    choice = input(f"\n  Choice: ").strip().lower()

    if choice == "s":
        addr = input(f"  {C.CYAN}EVM address (0x…):{C.RESET}  ").strip()
        if addr.startswith("0x") and len(addr) == 42:
            CFG.EVM_ADDRESS = addr
            p(f"  {C.OK}✔  Wallet set to {addr[:14]}…{C.RESET}")
        else:
            p(f"  {C.ERR}✖  Invalid address — must start with 0x and be 42 characters long{C.RESET}")
    elif choice == "b":
        if not HAS_WEB3:
            p(f"  {C.WARN}⚠  web3 not installed. Run: pip install web3{C.RESET}")
        elif not CFG.EVM_ADDRESS:
            p(f"  {C.WARN}⚠  No wallet set. Choose S first.{C.RESET}")
        else:
            p(f"  {C.DIM}Checking balance…{C.RESET}")
            # delegate to agent's Telegram handler logic (reuse same RPC code)
            agent._cli_check_balance()
    _pause()
    return False

def menu_open_config(_=None) -> bool:
    """Open config.py in the system editor."""
    config_path = str(BASE_DIR / "config.py")
    p(f"\n  {C.DIM}Opening: {config_path}{C.RESET}")
    import subprocess
    if _os.name == "nt":
        subprocess.Popen(["notepad", config_path])
    else:
        editor = _os.environ.get("EDITOR", "nano")
        try:
            subprocess.call([editor, config_path])
        except FileNotFoundError:
            subprocess.call(["vi", config_path])
    return False

def run_interactive_menu(agent) -> bool:
    """Build and run the main CLI menu."""
    banner()
    print_status_bar(agent)
    menu = InteractiveMenu()
    menu.add("1", "🤖", "Start Bot",        "Run the Telegram bot (default mode)",          lambda: False)
    menu.add("2", "🎵", "Generate Song",    "Create a single song now",                     lambda: menu_generate_one(agent))
    menu.add("3", "🔄", "Auto Loop",        "Generate songs on a schedule",                 lambda: menu_auto_loop(agent))
    menu.add("4", "🧠", "Auto Mode",        "Fully autonomous AI-driven generation loop",   lambda: menu_auto_mode(agent))
    menu.add("5", "📊", "System Status",    "View uptime, keys, wallet info",               lambda: menu_show_status(agent))
    menu.add("6", "🔑", "API Keys",         "Add / remove Audiera keys",                    lambda: menu_manage_keys(agent))
    menu.add("7", "💳", "Wallet",           "Set EVM address or check $BEAT balance",       lambda: menu_manage_wallet(agent))
    menu.add("8", "⚙️", "Edit Config",      "Open config.py in your editor",               menu_open_config)
    menu.add("9", "❌", "Exit",             "Quit Audiera",                                  None)
    return menu.run()


# ══════════════════════════════════════════════════════════════════════════════
#  STATE MANAGER
# ══════════════════════════════════════════════════════════════════════════════
class StateManager:
    def __init__(self):
        self.session_start     = now_utc()
        self.run_count         = 0
        self.song_count        = self._load_song_count()
        self.skipped_count     = 0
        self.last_request      = ""
        self.conversation_history: List[dict] = []
        self.user_preferences  = self._load_preferences()
        self.last_song_params: Optional[dict] = None
        self.pending_confirmation = None

    # ── persistence ──────────────────────────────────────────────────────────
    def _load_song_count(self) -> int:
        f = MEM_DIR / "song_count.json"
        try:
            return json.loads(f.read_text("utf-8")).get("count", 0) if f.exists() else 0
        except Exception:
            return 0

    def _save_song_count(self):
        try:
            (MEM_DIR / "song_count.json").write_text(
                json.dumps({"count": self.song_count}), encoding="utf-8"
            )
        except Exception:
            pass

    def _load_preferences(self) -> dict:
        pf = MEM_DIR / "preferences.json"
        try:
            return json.loads(pf.read_text("utf-8")) if pf.exists() else {}
        except Exception:
            return {}

    def save_preferences(self):
        try:
            (MEM_DIR / "preferences.json").write_text(
                json.dumps(self.user_preferences, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except Exception:
            pass

    def add_conversation(self, role: str, content: str):
        self.conversation_history.append({"role": role, "content": content, "ts": ts()})
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]

    def clear_all(self):
        self.conversation_history = []
        self.user_preferences     = {"preferred_styles": [], "preferred_artists": [], "mood_history": []}
        self.last_song_params     = None
        self.pending_confirmation = None
        self.song_count           = 0
        self.save_preferences()
        self._save_song_count()
        for f in MEM_DIR.glob("*.json"):
            try: f.unlink()
            except Exception: pass
        log.info("All memory cleared")


# ══════════════════════════════════════════════════════════════════════════════
#  AUTO MODE ENGINE  — fully autonomous, self-directing song generation
# ══════════════════════════════════════════════════════════════════════════════
class AutoModeEngine:
    """
    Autonomous song generation loop that runs with zero human interaction.

    Intelligence features:
      • Time-of-day mood mapping (morning uplift → late-night dark/chill)
      • Day-of-week style selection (Monday grind → Friday party → Sunday soul)
      • Round-robin artist cycling so every artist gets used
      • Dynamic interval: speeds up on successes, slows down after failures
      • Seasonal & trend-aware theme pools that avoid recent duplicates
      • Periodic self-reports sent to Telegram every N cycles
      • Self-healing: auto-retry on failure, auto key-rotation in multi mode
      • Configurable on-the-fly via Telegram subcommands
    """

    # ── theme pools by mood ────────────────────────────────────────────────
    THEME_POOLS = {
        "happy":     ["joy of dancing","sunshine moments","celebration vibes",
                      "golden afternoon","summer laughs","bright horizons",
                      "winning streak","carnival lights","rainbow after rain"],
        "sad":       ["lost in thoughts","rainy day reflections","missing you",
                      "empty room","fading photographs","letters unread",
                      "broken compass","ocean of tears","ghost of us"],
        "energetic": ["high voltage","unstoppable energy","alive and wild",
                      "ignite the night","power surge","adrenaline rush",
                      "blazing trail","fierce momentum","champion rise"],
        "chill":     ["peaceful mornings","quiet moments","flowing streams",
                      "lazy sunday drive","coffee and clouds","midnight ease",
                      "soft focus","velvet hours","gentle tide"],
        "romantic":  ["love's embrace","forever together","heart's desire",
                      "first kiss","starlit dance","whisper your name",
                      "crimson roses","moonlit promises","eternal us"],
        "dark":      ["shadow dance","midnight whispers","unknown depths",
                      "void between stars","crimson eclipse","fallen angel",
                      "haunted corridors","black mirror","silent storm"],
        "nostalgic": ["memory lane","yesterday's dreams","timeless echoes",
                      "childhood summers","analog warmth","old polaroids",
                      "vintage radio","sepia evenings","forgotten arcade"],
        "angry":     ["breaking free","fight for change","standing strong",
                      "burning bridges","war cry","no surrender",
                      "rebel signal","storm front","iron will"],
    }

    # ── time-of-day → mood weights {mood: weight} ─────────────────────────
    TIME_MOOD_MAP = {
        range(5,  9):  {"happy": 3, "energetic": 2, "nostalgic": 1},
        range(9,  12): {"energetic": 3, "happy": 2, "chill": 1},
        range(12, 15): {"chill": 2, "happy": 2, "romantic": 1},
        range(15, 18): {"energetic": 2, "happy": 2, "dark": 1},
        range(18, 21): {"romantic": 3, "chill": 2, "nostalgic": 1},
        range(21, 24): {"dark": 2, "chill": 3, "sad": 1},
        range(0,  5):  {"dark": 3, "sad": 2, "chill": 2},
    }

    # ── day-of-week style boosts (0=Mon … 6=Sun) ──────────────────────────
    DOW_STYLES = {
        0: ["Electronic","Hip-Hop"],          # Monday
        1: ["Pop","R&B"],                      # Tuesday
        2: ["Rock","Indie"],                   # Wednesday
        3: ["Dance","EDM"],                    # Thursday
        4: ["Dance","Pop","Electronic"],        # Friday
        5: ["House","Techno","EDM"],            # Saturday
        6: ["Soul","Jazz","Ambient"],           # Sunday
    }

    def __init__(self, agent: "SongAgent"):
        self.agent            = agent
        self._stop            = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.active           = False

        # intelligence state
        self.cycle_count      = 0
        self.success_streak   = 0
        self.fail_streak      = 0
        self._artist_idx      = 0
        self._mood_history: List[str] = []

        # configurable settings
        self.min_interval     = 15    # minutes
        self.max_interval     = 90    # minutes
        self.current_interval = getattr(CFG, "DEFAULT_INTERVAL_MINUTES", 30)
        self.songs_per_cycle  = getattr(CFG, "SONGS_PER_LOOP", 1)
        self.report_every     = 5     # send status report every N cycles
        self.paused           = False

    # ── public control ─────────────────────────────────────────────────────
    def start(self):
        if self.active:
            return False
        self._stop.clear()
        self.active = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="AutoMode")
        self._thread.start()
        return True

    def stop(self):
        if not self.active:
            return False
        self._stop.set()
        self.active = False
        return True

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

    def configure(self, **kwargs):
        if "interval" in kwargs:
            v = max(self.min_interval, min(self.max_interval, int(kwargs["interval"])))
            self.current_interval = v
        if "songs" in kwargs:
            self.songs_per_cycle = max(1, min(5, int(kwargs["songs"])))
        if "report_every" in kwargs:
            self.report_every = max(1, int(kwargs["report_every"]))

    def status_text(self) -> str:
        if not self.active:
            return "🔴 *AUTO MODE is OFF*"
        state = "⏸ _paused_" if self.paused else "🟢 _running_"
        next_mood = self._smart_mood()
        return (
            f"🤖 *AUTO MODE* — {state}\n\n"
            f"  🔄 Cycle:       `{self.cycle_count}`\n"
            f"  ⏱ Interval:    `{self.current_interval} min`\n"
            f"  🎵 Per cycle:   `{self.songs_per_cycle}` song(s)\n"
            f"  ✅ Successes:   `{self.success_streak}` streak\n"
            f"  ❌ Failures:    `{self.fail_streak}` streak\n"
            f"  🎭 Next mood:   `{next_mood}`\n"
            f"  📢 Report every:`{self.report_every}` cycles\n\n"
            f"Commands:\n"
            f"  `/auto_mode off` — stop\n"
            f"  `/auto_mode pause` — pause loop\n"
            f"  `/auto_mode resume` — resume loop\n"
            f"  `/auto_mode set interval=20` — change interval\n"
            f"  `/auto_mode set songs=2` — songs per cycle\n"
            f"  `/auto_mode set report=3` — report frequency"
        )

    # ── main loop ──────────────────────────────────────────────────────────
    def _loop(self):
        bot = self.agent.bot
        bot.send(
            f"🤖 *AUTO MODE Activated!*\n\n"
            f"  I'll now generate songs autonomously every `{self.current_interval}` min.\n"
            f"  I'll adapt my mood, artist, and style based on the time of day and what's working.\n\n"
            f"  Send `/auto_mode status` to check progress.\n"
            f"  Send `/auto_mode off` to stop at any time."
        )

        while not self._stop.is_set():
            if self.paused:
                time.sleep(10)
                continue

            self.cycle_count += 1

            # periodic status report
            if self.cycle_count > 1 and (self.cycle_count % self.report_every) == 0:
                self._send_cycle_report()

            # generate songs for this cycle
            for _ in range(self.songs_per_cycle):
                if self._stop.is_set():
                    break
                self._run_one_generation()

            # adaptive sleep
            if self._stop.is_set():
                break
            self._stop.wait(self.current_interval * 60)

        if not self._stop.is_set():
            bot.send("🤖 *AUTO MODE* — loop ended unexpectedly. Use `/auto_mode on` to restart.")

    def _run_one_generation(self):
        mood   = self._smart_mood()
        theme  = self._smart_theme(mood)
        styles = self._smart_styles(mood)
        artist = self._smart_artist()

        self.agent.state.last_song_params = {
            "theme": theme, "styles": styles,
            "artist": artist, "mood": mood
        }
        self._mood_history.append(mood)
        if len(self._mood_history) > 20:
            self._mood_history = self._mood_history[-20:]

        log.info(f"[AutoMode] cycle={self.cycle_count} mood={mood} theme='{theme}'")
        log_line("auto", f"Cycle {self.cycle_count}  ·  {mood}  ·  {theme}",
                 f"{', '.join(styles)}  ·  {artist}")

        t = threading.Thread(
            target=self._generate_and_track,
            args=(theme, styles, artist),
            daemon=True
        )
        t.start()
        t.join(timeout=400)   # max 6.5 min per song

    def _generate_and_track(self, theme: str, styles: list, artist: str):
        prev_count = self.agent.state.song_count
        try:
            self.agent._generate_song_async(theme, styles, artist)
            new_count = self.agent.state.song_count
            if new_count > prev_count:
                self.success_streak += 1
                self.fail_streak    = 0
                self._adapt_interval(success=True)
                log_line("ok", f"Song generated  ·  total {new_count}",
                         f"next cycle in {self.current_interval} min")
            else:
                self._on_fail()
        except Exception as e:
            log.warning(f"[AutoMode] generation error: {e}")
            log_line("err", "Generation error", str(e)[:80])
            self._on_fail()

    def _on_fail(self):
        self.fail_streak    += 1
        self.success_streak  = 0
        self._adapt_interval(success=False)
        # try to rotate key automatically if in multi mode
        if self.agent.audiera.mode == "multi" and self.fail_streak % 2 == 0:
            if self.agent.audiera.rotate():
                self.agent.bot.send(
                    f"🔄 *AUTO MODE* — Auto-rotated API key due to `{self.fail_streak}` consecutive failures."
                )

    def _adapt_interval(self, success: bool):
        if success:
            # gradually speed up (min floor)
            self.current_interval = max(self.min_interval,
                                        int(self.current_interval * 0.85))
        else:
            # back off on failure
            self.current_interval = min(self.max_interval,
                                        int(self.current_interval * 1.3))

    # ── intelligence helpers ───────────────────────────────────────────────
    def _smart_mood(self) -> str:
        hour = datetime.now().hour
        weights: dict = {}
        for h_range, w_map in self.TIME_MOOD_MAP.items():
            if hour in h_range:
                weights = w_map
                break

        # avoid repeating the same mood twice in a row
        last = self._mood_history[-1] if self._mood_history else None
        pool = []
        for mood, w in (weights.items() if weights else {m: 1 for m in self.THEME_POOLS}.items()):
            count = w if mood != last else max(1, w - 2)
            pool.extend([mood] * count)

        return random.choice(pool) if pool else random.choice(list(self.THEME_POOLS.keys()))

    def _smart_theme(self, mood: str) -> str:
        pool   = self.THEME_POOLS.get(mood, ["electric dreams","digital horizon"])
        used   = set(self.agent.dedup_themes.get("themes", []))
        fresh  = [t for t in pool if t.lower() not in used]
        base   = random.choice(fresh) if fresh else random.choice(pool)
        # add a unique suffix so dupes never block generation
        variants = ["", " — reborn", " — echoes", " — chapter 2",
                    " — tonight", " — redux", " — vol.2"]
        suffix = random.choice(variants)
        return base + suffix

    def _smart_styles(self, mood: str) -> list:
        dow_boost = self.DOW_STYLES.get(datetime.now().weekday(), [])
        mood_base = CFG.MOOD_TO_STYLES.get(mood, CFG.DEFAULT_STYLES)
        combined  = list(dict.fromkeys(dow_boost + mood_base))  # preserve order, dedupe
        return combined[:2] if len(combined) >= 2 else combined or CFG.DEFAULT_STYLES

    def _smart_artist(self) -> str:
        artists = list(self.agent.artist_ids.keys())
        artist  = artists[self._artist_idx % len(artists)]
        self._artist_idx += 1
        return artist

    # ── reporting ──────────────────────────────────────────────────────────
    def _send_cycle_report(self):
        recent = self.agent.history[:3]
        recent_lines = ""
        for s in recent:
            recent_lines += f"  • *{s.get('theme','?')}* — _{s.get('artist','?')}_\n"

        self.agent.bot.send(
            f"🤖 *AUTO MODE Report* — Cycle `{self.cycle_count}`\n\n"
            f"  🎵 Songs total: `{self.agent.state.song_count}`\n"
            f"  ✅ Success streak: `{self.success_streak}`\n"
            f"  ⏱ Current interval: `{self.current_interval} min`\n\n"
            f"*Recent generations:*\n{recent_lines}\n"
            f"_Type_ `/auto_mode status` _for full details._"
        )


# ══════════════════════════════════════════════════════════════════════════════
#  NATURAL LANGUAGE INTENT DETECTOR
# ══════════════════════════════════════════════════════════════════════════════
class IntentDetector:
    """Detects song creation intent, mood, genre, and artist from free text."""

    CREATE_TRIGGERS = [
        "make a song", "create a song", "generate a song", "write a song",
        "compose a song", "produce a song", "play a song",
        "make music", "create music", "generate music",
        "i want a song", "i need a song", "i want music", "i need music",
        "can you make", "can you create", "can you generate",
        "मुझे एक गाना", "गाना बनाओ", "song banana hai",
        "quiero una canción", "hazme una canción",
        "fais-moi une chanson", "crée une chanson",
    ]

    GENRE_KEYWORDS = {
        "pop":        ["pop"],
        "electronic": ["electronic","edm","techno","house","dance music"],
        "rock":       ["rock","hard rock"],
        "hip-hop":    ["hip-hop","hip hop","rap"],
        "r&b":        ["r&b","rnb","rn b"],
        "soul":       ["soul","soulful"],
        "jazz":       ["jazz"],
        "classical":  ["classical","orchestra"],
        "ambient":    ["ambient","relaxing","meditation"],
        "indie":      ["indie"],
        "folk":       ["folk","acoustic"],
        "metal":      ["metal","heavy metal"],
        "dance":      ["dance","dancefloor"],
        "funk":       ["funk"],
        "blues":      ["blues"],
        "romantic":   ["romantic","love song","romance"],
        "sad":        ["sad","melancholy","upset","sad song"],
        "happy":      ["happy","joyful","cheerful","happy song"],
        "energetic":  ["energetic","powerful","intense"],
        "chill":      ["chill","laid back","relaxed","chill vibes"],
        "dark":       ["dark","moody","gloomy"],
        "nostalgic":  ["nostalgic","retro","throwback"],
    }

    MOOD_KEYWORDS = {
        "happy":     ["happy","joy","excited","great","amazing","wonderful"],
        "sad":       ["sad","depressed","lonely","heartbroken","upset"],
        "angry":     ["angry","furious","rage","mad","annoyed"],
        "romantic":  ["love","romantic","heart","kiss","together"],
        "chill":     ["relax","chill","peaceful","calm","zen"],
        "energetic": ["energy","power","pump","hyped","pumped"],
        "nostalgic": ["remember","memory","past","childhood","old times"],
        "dark":      ["dark","shadow","void","empty","hollow"],
    }

    ARTIST_KEYWORDS = {
        "Kira":          ["soft","gentle","melodic","emotional","female","girl"],
        "Ray":           ["electronic","synth","modern","tech","futuristic"],
        "Jason Miller":  ["rock","hard","raw","powerful","male"],
        "Dylan Cross":   ["dark","moody","atmospheric","mysterious"],
        "Rhea Monroe":   ["soul","warm","love","r&b"],
        "Trevor Knox":   ["hip-hop","rap","urban","edgy"],
        "Kayden West":   ["experimental","unique","innovative","fresh"],
        "Talia Brooks":  ["soft","flowing","gentle","melody"],
        "Sienna Blake":  ["dynamic","versatile","powerful"],
        "Briana Rose":   ["gospel","soul","powerful vocals","church"],
        "Leo Martin":    ["classical","orchestral","elegant","refined"],
        "Amelia Clarke": ["indie","folk","acoustic","singer-songwriter"],
    }

    def __init__(self):
        self.last_intent = None

    def detect_intent(self, text: str) -> dict:
        tl = text.lower().strip()
        result = {
            "intent": "unknown", "theme": None, "mood": "neutral",
            "genre": None, "artist": None, "confidence": 0.0,
            "raw_text": text, "needs_clarification": False,
            "clarification_needed": []
        }

        # Explicit triggers
        for trigger in self.CREATE_TRIGGERS:
            if trigger in tl:
                result["intent"] = "create_song"
                result["confidence"] = 0.9
                break

        # Implicit: "song" + request verb
        if result["intent"] == "unknown":
            song_words   = ["song","music","beat","track","melody","गाना","संगीत"]
            request_verbs= ["want","need","make","create","generate","give"]
            for sw in song_words:
                if sw in tl:
                    for rv in request_verbs:
                        if rv in tl:
                            result["intent"] = "create_song"
                            result["confidence"] = 0.7
                            break

        # Detect mood
        for mood, kws in self.MOOD_KEYWORDS.items():
            for kw in kws:
                if kw in tl:
                    result["mood"] = mood
                    result["confidence"] = max(result["confidence"], 0.6)
                    break

        # Detect genre
        for genre, kws in self.GENRE_KEYWORDS.items():
            for kw in kws:
                if kw in tl:
                    result["genre"] = genre
                    result["confidence"] = max(result["confidence"], 0.7)
                    break

        # Detect artist
        for artist, kws in self.ARTIST_KEYWORDS.items():
            for kw in kws:
                if kw in tl:
                    result["artist"] = artist
                    result["confidence"] = max(result["confidence"], 0.5)
                    break

        result["theme"] = self._extract_theme(text)

        if result["intent"] == "create_song":
            if not result["theme"]:
                result["clarification_needed"].append("What should the song be about?")
            if not result["genre"] and result["mood"] == "neutral":
                result["clarification_needed"].append("What style or mood? (e.g., pop, chill, rock)")

        self.last_intent = result
        return result

    def _extract_theme(self, text: str) -> Optional[str]:
        patterns = [
            r"^(make|create|generate|write|i want|i need|can you|could you)\s+(a\s+)?(song|music|track)\s+(about|on|with)?\s*",
            r"^(give me|want|need)\s+(a\s+)?(song|music|track)\s*",
        ]
        theme = text.lower()
        for pat in patterns:
            theme = re.sub(pat, "", theme, flags=re.IGNORECASE)
        theme = theme.strip(" .,!?")
        return theme if len(theme) > 2 else None

    def suggest_alternatives(self, current: dict) -> List[str]:
        sug = []
        if not current.get("genre"):
            sug.append("Would you like it in Pop or Electronic style?")
        if not current.get("artist"):
            sug.append("Any preference for male or female vocals?")
        return sug


# ══════════════════════════════════════════════════════════════════════════════
#  AUDIERA API MANAGER
# ══════════════════════════════════════════════════════════════════════════════
class AudieraManager:
    """Handles all Audiera REST calls with key rotation and error recovery."""

    LYRICS_URL = "https://ai.audiera.fi/api/skills/lyrics"
    MUSIC_URL  = "https://ai.audiera.fi/api/skills/music"

    def __init__(self, keys: list, mode: str = "single"):
        self.keys    = keys.copy()
        self.idx     = 0
        self.mode    = mode
        self.metrics = {"requests": 0, "successes": 0, "failures": 0, "rotations": 0}
        self._load_keys()

    # ── key persistence ───────────────────────────────────────────────────────
    def _load_keys(self):
        kf = MEM_DIR / "audiera_keys.json"
        if kf.exists():
            try:
                d = json.loads(kf.read_text("utf-8"))
                self.keys = d.get("keys", self.keys)
                self.idx  = min(d.get("active_idx", 0), max(0, len(self.keys)-1))
                self.mode = d.get("mode", self.mode)
            except Exception:
                pass
        self._save_keys()

    def _save_keys(self):
        try:
            (MEM_DIR / "audiera_keys.json").write_text(
                json.dumps({"keys": self.keys, "active_idx": self.idx, "mode": self.mode}, indent=2),
                encoding="utf-8"
            )
        except Exception:
            pass

    # ── properties ────────────────────────────────────────────────────────────
    @property
    def current_key(self) -> str:
        if not self.keys: return ""
        return self.keys[min(self.idx, len(self.keys)-1)].get("key","")

    @property
    def current_short(self) -> str:
        k = self.current_key
        return f"{k[:18]}…{k[-6:]}" if len(k) > 25 else (k or "none")

    @property
    def active_count(self) -> int:
        return len([k for k in self.keys if k.get("status") == "active"])

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.current_key}", "Content-Type": "application/json"}

    # ── key management ────────────────────────────────────────────────────────
    def rotate(self) -> bool:
        if self.mode != "multi" or len(self.keys) <= 1:
            return False
        active = [i for i, k in enumerate(self.keys) if k.get("status") == "active"]
        if len(active) <= 1: return False
        pos      = active.index(self.idx) if self.idx in active else 0
        self.idx = active[(pos + 1) % len(active)]
        self.metrics["rotations"] += 1
        self._save_keys()
        return True

    def add_key(self, key: str) -> Tuple[bool, str]:
        key = key.strip()
        if not key.startswith("sk_audiera_"):
            return False, "Key must start with 'sk_audiera_' — check https://ai.audiera.fi"
        if any(k["key"] == key for k in self.keys):
            return False, "Key already exists in the list"
        self.keys.append({"key": key, "status": "active"})
        self._save_keys()
        return True, f"✔  Added key #{len(self.keys)}"

    # ── HTTP helpers ──────────────────────────────────────────────────────────
    def _post(self, url: str, payload: dict, timeout: int = 15) -> Tuple[Optional[dict], Optional[str]]:
        self.metrics["requests"] += 1
        try:
            r = requests.post(url, json=payload, headers=self._headers(), timeout=timeout)
            if r.status_code == 429:
                return None, "rate_limit"
            if r.status_code == 401:
                return None, "invalid_key"
            if r.status_code == 403:
                return None, "forbidden"
            if r.status_code != 200:
                try:    msg = r.json().get("message", f"HTTP {r.status_code}")
                except: msg = f"HTTP {r.status_code}"
                return None, msg
            self.metrics["successes"] += 1
            return r.json(), None
        except requests.exceptions.Timeout:
            self.metrics["failures"] += 1
            return None, "timeout"
        except requests.exceptions.ConnectionError:
            self.metrics["failures"] += 1
            return None, "connection_error"
        except Exception as e:
            self.metrics["failures"] += 1
            return None, str(e)

    # ── generation ────────────────────────────────────────────────────────────
    def generate_lyrics(self, inspiration: str, memory_hint: str = "") -> Tuple[Optional[str], Optional[str]]:
        prompt = f"{inspiration}. {memory_hint}" if memory_hint else inspiration
        log.info(f"generate_lyrics: '{inspiration[:60]}'")
        data, err = self._post(self.LYRICS_URL, {"inspiration": prompt})
        if err:
            return None, err
        try:
            lyrics = data["data"]["lyrics"]
            log.info(f"Lyrics OK: {len(lyrics)} chars")
            return lyrics, None
        except (KeyError, TypeError):
            return None, "api_response_error"

    def generate_music(self, styles: list, artist_id: str,
                       lyrics: Optional[str] = None) -> Tuple[Optional[dict], Optional[str]]:
        """
        Submit music generation job and poll until complete.
        Returns (result_dict, error_code) — always a 2-tuple.
        """
        payload = {"styles": styles, "artistId": artist_id}
        if lyrics:
            payload["lyrics"] = lyrics
        log.info(f"generate_music: {styles}, artist={artist_id}")

        data, err = self._post(self.MUSIC_URL, payload)
        if err:
            return None, err
        if not data or not data.get("success"):
            return None, "api_response_error"

        task_id = data["data"]["taskId"]
        log.info(f"Polling task {task_id}")

        for attempt in range(60):   # 5 min max
            time.sleep(5)
            try:
                r  = requests.get(f"{self.MUSIC_URL}/{task_id}", headers=self._headers(), timeout=10)
                pd = r.json()
                if pd and pd.get("success"):
                    status = pd["data"].get("status","?")
                    log.info(f"Poll {attempt+1}/60: {status}")
                    if status == "completed":
                        songs = pd["data"].get("musics") or []
                        log.info(f"Music ready: {len(songs)} tracks")
                        return {"taskId": task_id, "songs": songs}, None
                    if status == "failed":
                        return None, "generation_failed"
            except Exception as e:
                log.warning(f"Poll error: {e}")

        return None, "timeout"


# ══════════════════════════════════════════════════════════════════════════════
#  TELEGRAM BOT
# ══════════════════════════════════════════════════════════════════════════════
class TelegramBot:
    """Thin Telegram wrapper — long-polling listener + send helpers."""

    _BASE = "https://api.telegram.org/bot{token}/{method}"

    def __init__(self, agent: "SongAgent"):
        self.agent       = agent
        self.token       = CFG.TG_BOT_TOKEN
        self.chat_id     = str(CFG.TG_CHAT_ID)
        self.offset      = 0
        self._stop       = threading.Event()
        self.enabled     = getattr(CFG, "NOTIFICATIONS_DEFAULT", True)
        self.sent_count  = 0
        self._lock       = threading.Lock()

        if self.token and self.chat_id:
            threading.Thread(target=self._listen, daemon=True, name="TGListener").start()
            log.info("Telegram listener started")
        else:
            log.warning("Telegram not configured — set TG_BOT_TOKEN and TG_CHAT_ID")

    # ── send helpers ─────────────────────────────────────────────────────────
    def send(self, text: str, silent: bool = False,
             reply_markup: Optional[dict] = None, parse_mode: str = "Markdown") -> bool:
        if not self.enabled and not silent: return False
        if not self.token or not self.chat_id: return False
        payload: dict = {
            "chat_id": self.chat_id, "text": text,
            "parse_mode": parse_mode, "disable_notification": silent,
            "disable_web_page_preview": False,
        }
        if reply_markup:
            payload["reply_markup"] = json.dumps(reply_markup)
        try:
            r = requests.post(self._BASE.format(token=self.token, method="sendMessage"),
                              json=payload, timeout=10)
            ok = r.json().get("ok", False)
            if ok:
                self.sent_count += 1
            else:
                # If Markdown parse fails, retry as plain text
                if "parse" in r.json().get("description","").lower():
                    payload["parse_mode"] = ""
                    r2 = requests.post(self._BASE.format(token=self.token, method="sendMessage"),
                                       json=payload, timeout=10)
                    if r2.json().get("ok"): self.sent_count += 1; return True
                log.warning(f"TG send failed: {r.json().get('description','?')}")
            return ok
        except Exception as e:
            log.warning(f"TG send error: {e}")
            return False

    def send_buttons(self, text: str, button_rows: List[List[Tuple[str,str]]]) -> bool:
        """Send message with an inline keyboard.
        button_rows: [[(label, callback_data), …], …]
        """
        kb = {"inline_keyboard": [
            [{"text": b[0], "callback_data": b[1]} for b in row]
            for row in button_rows
        ]}
        return self.send(text, reply_markup=kb)

    def typing(self):
        """Show 'typing…' indicator in Telegram."""
        try:
            requests.post(
                self._BASE.format(token=self.token, method="sendChatAction"),
                json={"chat_id": self.chat_id, "action": "typing"}, timeout=5
            )
        except Exception:
            pass

    def stop(self):
        self._stop.set()

    # ── listener ─────────────────────────────────────────────────────────────
    def _listen(self):
        while not self._stop.is_set():
            try:
                r = requests.get(
                    self._BASE.format(token=self.token, method="getUpdates"),
                    params={"offset": self.offset, "timeout": 5,
                            "allowed_updates": ["message","callback_query"]},
                    timeout=12
                )
                data = r.json()
                if not data.get("ok"):
                    time.sleep(2); continue
                for upd in data.get("result", []):
                    self.offset = upd["update_id"] + 1
                    try:
                        self._dispatch(upd)
                    except Exception as e:
                        log.error(f"Dispatch error: {e}\n{traceback.format_exc()}")
            except Exception:
                time.sleep(3)

    def _dispatch(self, update: dict):
        # Normal messages
        msg  = update.get("message", {})
        text = (msg.get("text") or "").strip()
        cid  = str(msg.get("chat", {}).get("id", ""))

        # Callback queries (button taps)
        cbq = update.get("callback_query")
        if cbq:
            cid  = str(cbq.get("message", {}).get("chat", {}).get("id", ""))
            text = cbq.get("data", "")
            # Acknowledge the tap silently
            try:
                requests.post(
                    self._BASE.format(token=self.token, method="answerCallbackQuery"),
                    json={"callback_query_id": cbq["id"]}, timeout=5
                )
            except Exception:
                pass

        if cid != self.chat_id: return
        if not text: return

        log.info(f"Received: {text[:80]}")
        self.agent.handle_message(text)


# ══════════════════════════════════════════════════════════════════════════════
#  SONG AGENT  —  Main class
# ══════════════════════════════════════════════════════════════════════════════
class SongAgent:
    """
    Orchestrates intent detection, Audiera API calls, and Telegram responses.
    All Telegram commands and natural language messages flow through here.
    """

    def __init__(self):
        self.state        = StateManager()
        self.intent       = IntentDetector()
        self.audiera      = AudieraManager(CFG.AUDIERA_KEYS, CFG.AUDIERA_MODE)
        self.bot          = TelegramBot(self)
        self.artist_ids   = CFG.ARTISTS
        self.dedup_themes = self._load_dedup()
        self.history      = self._load_history()
        self.evolution_stage    = 0
        self.consecutive_fails  = 0
        self.generating         = False
        self._gen_lock          = threading.Lock()
        self.auto_engine        = AutoModeEngine(self)

        log.info(f"SongAgent ready  v{CFG.AGENT_VERSION}")

        if getattr(CFG, "SEND_WELCOME_MESSAGE", True):
            # Small delay so the listener has a chance to connect first
            threading.Timer(1.5, self._send_welcome).start()

    # ── persistence helpers ───────────────────────────────────────────────────
    def _load_dedup(self) -> dict:
        f = MEM_DIR / "dedup.json"
        try: return json.loads(f.read_text("utf-8")) if f.exists() else {"themes": [], "songs": []}
        except Exception: return {"themes": [], "songs": []}

    def _save_dedup(self):
        try: (MEM_DIR / "dedup.json").write_text(json.dumps(self.dedup_themes, indent=2), "utf-8")
        except Exception: pass

    def _load_history(self) -> list:
        f = MEM_DIR / "history.json"
        try: return json.loads(f.read_text("utf-8")) if f.exists() else []
        except Exception: return []

    def _save_history(self):
        try: (MEM_DIR / "history.json").write_text(json.dumps(self.history, indent=2), "utf-8")
        except Exception: pass

    def _add_to_history(self, theme: str, styles: list, artist: str, url: str = ""):
        self.history.insert(0, {
            "theme": theme, "styles": ", ".join(styles),
            "artist": artist, "url": url, "ts": ts()
        })
        if len(self.history) > 200:
            self.history = self.history[:200]
        self._save_history()

    # ── startup welcome ───────────────────────────────────────────────────────
    def _send_welcome(self):
        wallet_set = bool(CFG.EVM_ADDRESS and len(CFG.EVM_ADDRESS) == 42)
        wallet_s   = f"`{CFG.EVM_ADDRESS[:14]}…`" if wallet_set else "_not set_"

        msg  = f"🎵 *{CFG.BOT_DISPLAY_NAME}* is Online!  `v{CFG.AGENT_VERSION}`\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"📊 *Status*\n"
        msg += f"  • API keys: `{self.audiera.active_count}` active\n"
        msg += f"  • Songs made: `{self.state.song_count}`\n"
        msg += f"  • Wallet: {wallet_s}\n\n"
        msg += f"💬 *Quick Start*\n"
        msg += f"  Just type what you want, for example:\n"
        msg += f"  _\"Make a happy pop song about summer\"_\n"
        msg += f"  _\"Create a chill R&B track\"_\n\n"
        msg += f"⌨️ *Commands*\n"
        msg += f"  /song  /custom  /history  /status  /help\n\n"
        msg += f"🤖 *New!* `/auto_mode on` — let the bot generate songs on its own"

        self.bot.send_buttons(msg, [
            [("🎵 Create Song", "/song"), ("📋 Help", "/help")],
            [("📊 Status", "/status"), ("🔑 API Keys", "/keys")],
        ])

    # ══════════════════════════════════════════════════════════════════════════
    #  MESSAGE ROUTER
    # ══════════════════════════════════════════════════════════════════════════
    def handle_message(self, text: str):
        self.state.add_conversation("user", text)
        self.bot.typing()

        if text.startswith("/"):
            self._handle_command(text)
        else:
            self._handle_natural_language(text)

    # ── command dispatcher ────────────────────────────────────────────────────
    def _handle_command(self, text: str):
        parts = text.split(maxsplit=1)
        # Strip @BotName suffix if present
        raw_cmd = parts[0].lower().lstrip("/").split("@")[0]
        args    = parts[1].strip() if len(parts) > 1 else ""

        commands = {
            # Core
            "start":        self._cmd_start,
            "help":         self._cmd_help,
            "status":       self._cmd_status,
            "reset":        self._cmd_reset,
            "clear":        self._cmd_reset,
            # Songs
            "song":         lambda: self._cmd_song(args),
            "create":       lambda: self._cmd_song(args),
            "make":         lambda: self._cmd_song(args),
            "generate":     lambda: self._cmd_song(args),
            "rewrite":      self._cmd_rewrite,
            "retry":        self._cmd_retry,
            "modern":       self._cmd_modern,
            "morden":       self._cmd_modern,   # typo alias
            "custom":       lambda: self._cmd_custom(args),
            # Info
            "genres":       self._cmd_genres,
            "styles":       self._cmd_genres,
            "artists":      self._cmd_artists,
            "history":      self._cmd_history,
            "list":         self._cmd_list_all,
            # Keys
            "keys":         self._cmd_keys,
            "addkey":       lambda: self._cmd_addkey(args),
            "removekey":    lambda: self._cmd_removekey(args),
            "rotatekey":    self._cmd_rotatekey,
            # Wallet
            "wallet":       self._cmd_wallet,
            "setwallet":    lambda: self._cmd_setwallet(args),
            "setevm":       lambda: self._cmd_setwallet(args),
            "balance":      self._cmd_balance,
            # System
            "notifications":lambda: self._cmd_notifications(args),
            "notify":       lambda: self._cmd_notifications(args),
            "debug":        self._cmd_debug,
            "config":       self._cmd_config,
            # Autonomous mode
            "auto_mode":    lambda: self._cmd_auto_mode(args),
            "automode":     lambda: self._cmd_auto_mode(args),
            "auto":         lambda: self._cmd_auto_mode(args),
        }

        if raw_cmd in commands:
            try:
                commands[raw_cmd]()
            except Exception as e:
                log.error(f"Command /{raw_cmd} error: {e}\n{traceback.format_exc()}")
                self.bot.send(
                    f"❌ *Oops!* Something went wrong with `/{raw_cmd}`.\n\n"
                    f"Error: `{str(e)[:120]}`\n\n"
                    f"Try `/status` to check if the bot is healthy, or `/help` for usage."
                )
        else:
            # Unknown command — suggest closest match
            self._cmd_unknown(raw_cmd)

    # ── natural language handler ──────────────────────────────────────────────
    def _handle_natural_language(self, text: str):
        intent_data = self.intent.detect_intent(text)
        self.state.last_request = text
        log.info(f"Intent: {intent_data['intent']}, mood={intent_data['mood']}, genre={intent_data['genre']}")

        if intent_data["intent"] == "create_song":
            if intent_data["clarification_needed"]:
                self._ask_for_details(intent_data)
            else:
                self._create_song_with_params(intent_data)
        else:
            self._handle_conversation(text, intent_data)

    def _handle_conversation(self, text: str, intent_data: dict):
        """Fallback handler for messages that are not song requests."""
        greet_words = ["hi","hello","hey","hola","bonjour","नमस्ते","yo","sup"]
        tl = text.lower()
        if any(w in tl for w in greet_words):
            self.bot.send_buttons(
                f"👋 Hey! I'm *{CFG.BOT_DISPLAY_NAME}*, your AI music creator.\n\n"
                f"Just tell me what kind of song you want — I'll handle the rest!",
                [
                    [("🎵 Create a Song", "/song"), ("📋 See Commands", "/help")],
                    [("🎤 View Artists", "/artists"), ("🎸 View Genres", "/genres")],
                ]
            )
        else:
            self.bot.send(
                f"🎵 I'm a *song creation* bot — I'm not sure what you mean, but I'd love to make you music!\n\n"
                f"*Try saying:*\n"
                f"  • _\"Make me a happy pop song\"_\n"
                f"  • _\"Create a chill R\\&B track about love\"_\n"
                f"  • `/song <description>` for a direct request\n\n"
                f"Type /help to see all commands."
            )

    # ── clarification flow ────────────────────────────────────────────────────
    def _ask_for_details(self, intent_data: dict):
        questions = intent_data["clarification_needed"]
        if len(questions) == 1:
            example = self._build_example(intent_data)
            self.bot.send(
                f"🎵 Almost there! {questions[0]}\n\n"
                f"*Example:* _{example}_"
            )
        else:
            lines = "\n".join(f"  {i+1}. {q}" for i, q in enumerate(questions))
            self.bot.send(
                f"🎵 *I'd love to create your song!* Just need a little more info:\n\n"
                f"{lines}\n\n"
                f"Or describe everything at once:\n"
                f"_\"{self._build_example(intent_data)}\"_"
            )

    def _build_example(self, i: dict) -> str:
        if i.get("theme") and i.get("mood"):
            return f"Make a {i['mood']} song about {i['theme']}"
        if i.get("theme") and i.get("genre"):
            return f"Create a {i['genre']} song about {i['theme']}"
        if i.get("mood"):
            return f"I want a {i['mood']} and energetic song"
        if i.get("genre"):
            return f"Create an awesome {i['genre']} track"
        return "Make a happy pop song about dancing in the rain"

    # ── song creation ─────────────────────────────────────────────────────────
    _GENRE_STYLES: Dict[str, List[str]] = {
        "pop":        ["Pop","Dance"],
        "electronic": ["Electronic","EDM"],
        "rock":       ["Rock","Metal"],
        "hip-hop":    ["Hip-Hop","R&B"],
        "r&b":        ["R&B","Soul"],
        "soul":       ["Soul","R&B"],
        "jazz":       ["Jazz","Blues"],
        "classical":  ["Classical","Ambient"],
        "ambient":    ["Ambient","Indie"],
        "indie":      ["Indie","Folk"],
        "folk":       ["Folk"],
        "metal":      ["Metal","Rock"],
        "dance":      ["Dance","Electronic"],
        "funk":       ["Funk","Soul"],
        "romantic":   ["R&B","Soul","Pop"],
        "sad":        ["R&B","Soul"],
        "happy":      ["Pop","Dance"],
        "energetic":  ["Dance","Electronic"],
        "chill":      ["Ambient","Indie"],
        "dark":       ["Electronic","Ambient"],
        "nostalgic":  ["Soul","Funk"],
    }

    def _create_song_with_params(self, params: dict):
        g      = params.get("genre") or params.get("mood", "")
        styles = self._GENRE_STYLES.get(g, CFG.DEFAULT_STYLES)
        artist = params.get("artist") or CFG.DEFAULT_ARTIST
        if artist not in self.artist_ids:
            artist = CFG.DEFAULT_ARTIST
        theme  = params.get("theme") or self._auto_theme(params)

        self.state.last_song_params = {
            "theme": theme, "styles": styles, "artist": artist,
            "mood":  params.get("mood"), "genre": params.get("genre")
        }

        mood_tag = f"  💭 Mood: _{params['mood']}_\n" if params.get("mood") else ""
        self.bot.send(
            f"🎵 *Creating Your Song!*\n\n"
            f"  🎨 Theme:  `{theme}`\n"
            f"  🎸 Styles: `{', '.join(styles)}`\n"
            f"  🎤 Artist: `{artist}`\n"
            f"{mood_tag}\n"
            f"⏳ Generating…  _(this may take 1–3 minutes)_"
        )
        threading.Thread(
            target=self._generate_song_async,
            args=(theme, styles, artist),
            daemon=True
        ).start()

    def _auto_theme(self, params: dict) -> str:
        mood_themes = {
            "happy":     ["joy of dancing","sunshine moments","celebration vibes"],
            "sad":       ["lost in thoughts","rainy day reflections","missing you"],
            "angry":     ["breaking free","fight for change","standing strong"],
            "romantic":  ["love's embrace","forever together","heart's desire"],
            "chill":     ["peaceful mornings","quiet moments","flowing streams"],
            "energetic": ["high voltage","unstoppable energy","alive and wild"],
            "nostalgic": ["memory lane","yesterday's dreams","timeless"],
            "dark":      ["shadow dance","midnight whispers","unknown depths"],
        }
        pool = mood_themes.get(params.get("mood",""), ["electric dreams","digital horizon"])
        base = random.choice(pool)
        g = params.get("genre","")
        return f"{base} — {g} vibes" if g else base

    # ── async generation ──────────────────────────────────────────────────────
    def _generate_song_async(self, theme: str, styles: list, artist: str):
        with self._gen_lock:
            if self.generating:
                self.bot.send(
                    "⏳ *Already generating a song!*\n\n"
                    "Please wait for the current generation to finish, then try again."
                )
                return
            self.generating = True

        try:
            # Duplicate check
            tl = theme.lower()
            if tl in self.dedup_themes.get("themes", []):
                self.bot.send(
                    f"⚠️ *Duplicate Theme*\n\n"
                    f"I've already made a song about `{theme}`.\n"
                    f"Try a slightly different description, or use /rewrite for a fresh take."
                )
                return

            # Generate lyrics
            lyrics, err = self.audiera.generate_lyrics(theme)
            if err:
                self._handle_api_error("lyrics", err)
                self.consecutive_fails += 1
                return

            # Get artist ID
            artist_id = self.artist_ids.get(artist, self.artist_ids[CFG.DEFAULT_ARTIST])

            # Generate music
            result, err = self.audiera.generate_music(styles, artist_id, lyrics)
            if err:
                self._handle_api_error("music", err)
                self.consecutive_fails += 1
                return

            if not result or not result.get("songs"):
                self.bot.send(
                    "❌ *No songs returned.*\n\n"
                    "The API returned an empty result. This sometimes happens with unusual style combinations.\n"
                    "Try `/retry` or change the theme/style."
                )
                self.consecutive_fails += 1
                return

            # Success
            songs = result["songs"]
            self.consecutive_fails = 0

            # Update dedup + stats
            self.dedup_themes.setdefault("themes",[]).append(tl)
            if len(self.dedup_themes["themes"]) > 500:
                self.dedup_themes["themes"] = self.dedup_themes["themes"][-500:]
            self._save_dedup()

            self.state.song_count += len(songs)
            self.state.run_count  += 1
            self.state._save_song_count()

            if getattr(CFG, "ENABLE_PREFERENCE_LEARNING", True):
                self._learn_preference(styles, artist)

            self._send_results(songs, theme, styles, artist)

        except Exception as e:
            log.error(f"_generate_song_async error: {e}\n{traceback.format_exc()}")
            self.bot.send(
                f"❌ *Unexpected Error*\n\n"
                f"`{str(e)[:160]}`\n\n"
                f"Use `/retry` to try again, or `/status` to check the system."
            )
            self.consecutive_fails += 1
        finally:
            self.generating = False

    def _send_results(self, songs: list, theme: str, styles: list, artist: str):
        """Send song results with inline action buttons."""
        track_lines = ""
        first_url   = ""
        for i, song in enumerate(songs, 1):
            title    = song.get("title", f"Track {i}")
            url      = song.get("url", "")
            duration = song.get("duration", "?")
            if url and not first_url:
                first_url = url
                track_lines += f"  {i}. [{title}]({url})  _{duration}s_\n"
            else:
                track_lines += f"  {i}. {title}  _{duration}s_\n"
            self._add_to_history(theme, styles, artist, url)

        msg  = f"🎵 *Song Ready!*\n\n"
        msg += track_lines
        msg += f"\n  🎨 Theme:  `{theme}`\n"
        msg += f"  🎸 Styles: `{', '.join(styles)}`\n"
        msg += f"  🎤 Artist: `{artist}`\n"
        msg += f"  📊 Total:  `{self.state.song_count}` songs made"

        self.bot.send_buttons(msg, [
            [("🔄 Rewrite", "/rewrite"), ("🎵 New Song", "/song"), ("📜 History", "/history")],
        ])

    # ── preference learning ───────────────────────────────────────────────────
    def _learn_preference(self, styles: list, artist: str):
        p = self.state.user_preferences
        for s in styles:
            if s not in p.setdefault("preferred_styles", []):
                p["preferred_styles"].append(s)
        if artist not in p.setdefault("preferred_artists", []):
            p["preferred_artists"].append(artist)
        self.state.save_preferences()

    # ── CLI balance helper ────────────────────────────────────────────────────
    def _cli_check_balance(self):
        """Check $BEAT balance from CLI (no Telegram)."""
        if not HAS_WEB3:
            p(f"  {C.WARN}⚠  web3 not installed{C.RESET}")
            return
        if not CFG.EVM_ADDRESS:
            p(f"  {C.WARN}⚠  No wallet configured{C.RESET}")
            return
        rpcs = ["https://eth.llamarpc.com","https://rpc.ankr.com/eth","https://eth.public-rpc.com"]
        for rpc in rpcs:
            try:
                w3  = Web3(Web3.HTTPProvider(rpc))
                ca  = Web3.to_checksum_address(CFG.BEAT_CONTRACT)
                wa  = Web3.to_checksum_address(CFG.EVM_ADDRESS)
                abi = '[{"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"type":"function"}]'
                bal = w3.eth.contract(address=ca, abi=abi).functions.balanceOf(wa).call()
                p(f"  {C.OK}✔  $BEAT Balance: {bal/1e18:,.4f} BEAT{C.RESET}")
                return
            except Exception as e:
                if "429" in str(e): continue
                p(f"  {C.ERR}✖  RPC error: {e}{C.RESET}")
                return
        p(f"  {C.WARN}⚠  All RPC providers rate-limited. Try again later.{C.RESET}")

    # ══════════════════════════════════════════════════════════════════════════
    #  ERROR HANDLER — detailed, actionable guidance
    # ══════════════════════════════════════════════════════════════════════════
    def _handle_api_error(self, step: str, code: str):
        """
        Translate error codes into user-friendly Telegram messages
        that include the cause and a concrete fix.
        """
        MESSAGES = {
            "rate_limit": (
                "⏱ *Rate Limited*",
                "The Audiera API has temporarily limited requests.",
                ["Wait 30–60 seconds and try again.",
                 "If you have multiple API keys, use `/rotatekey` to switch.",
                 "Set AUDIERA_MODE = \"multi\" in config.py for automatic rotation."]
            ),
            "invalid_key": (
                "🔑 *Invalid API Key*",
                "The current API key was rejected by Audiera.",
                ["Check your key in `/keys` — it should start with `sk_audiera_`",
                 "Generate a new key at https://ai.audiera.fi",
                 "Add it with `/addkey sk_audiera_your_new_key`"]
            ),
            "forbidden": (
                "🚫 *Access Forbidden*",
                "The API key doesn't have the required permissions.",
                ["Visit https://ai.audiera.fi and check your key's scopes.",
                 "Make sure the key has access to both `lyrics` and `music` endpoints.",
                 "Generate a new key with full permissions if needed."]
            ),
            "timeout": (
                "⌛ *Request Timed Out*",
                f"The {step} request took too long to respond.",
                ["Check your internet connection.",
                 "The Audiera API may be under load — try again in a minute.",
                 "Use `/retry` to re-run the last generation."]
            ),
            "connection_error": (
                "📡 *Connection Error*",
                "Cannot reach the Audiera API.",
                ["Check your internet connection.",
                 "Try: `ping ai.audiera.fi` in a terminal.",
                 "If you're behind a firewall, ensure HTTPS port 443 is open."]
            ),
            "generation_failed": (
                "🎵 *Generation Failed*",
                "Audiera returned a 'failed' status for this generation job.",
                ["This sometimes happens with very unusual style combinations.",
                 "Try different styles with `/song` or a simpler theme.",
                 "Use `/modern` for a pre-tested trending combination."]
            ),
            "api_response_error": (
                "🔌 *Unexpected API Response*",
                f"The {step} API returned an unexpected data format.",
                ["This is likely a temporary Audiera issue.",
                 "Use `/retry` in 30 seconds.",
                 "If it keeps happening, check https://ai.audiera.fi for status."]
            ),
            "credits": (
                "💳 *Insufficient Credits*",
                "Your Audiera account has run out of generation credits.",
                ["Visit https://ai.audiera.fi to add more credits.",
                 "If you have multiple keys, try `/addkey` with a key that has credits.",
                 "Check current usage with `/keys`."]
            ),
        }

        title, cause, steps = MESSAGES.get(code, (
            "❌ *Generation Error*",
            f"An error occurred during {step} generation: `{code}`",
            ["Try `/retry` to try again.", "Use `/debug` for more information."]
        ))

        step_lines = "\n".join(f"  {i+1}. {s}" for i,s in enumerate(steps))
        self.bot.send(
            f"{title}\n\n"
            f"_{cause}_\n\n"
            f"*What to do:*\n{step_lines}"
        )

    # ══════════════════════════════════════════════════════════════════════════
    #  COMMAND HANDLERS
    # ══════════════════════════════════════════════════════════════════════════
    def _cmd_unknown(self, cmd: str):
        """Suggest alternatives for unknown commands."""
        all_cmds = ["start","help","status","song","create","custom","rewrite","retry",
                    "modern","genres","artists","history","keys","addkey","removekey",
                    "wallet","setwallet","balance","debug","reset","notifications",
                    "auto_mode","automode","auto"]
        # Simple prefix match suggestion
        suggestions = [c for c in all_cmds if c.startswith(cmd[:3])][:3]
        sug_line = "  " + "  ".join(f"`/{c}`" for c in suggestions) if suggestions else ""
        self.bot.send(
            f"❓ *Unknown command:* `/{cmd}`\n\n"
            f"{'*Did you mean:*' + chr(10) + sug_line + chr(10) + chr(10) if sug_line else ''}"
            f"Type `/help` to see all available commands."
        )

    def _cmd_start(self):
        self._send_welcome()

    def _cmd_help(self):
        self.bot.send(
            f"📚 *{CFG.BOT_DISPLAY_NAME} — Command Reference*\n\n"

            f"🎵 *Song Creation*\n"
            f"  `/song <description>` — Create a song in plain English\n"
            f"  `/custom` — Full custom options (theme, artist, BPM, lyrics)\n"
            f"  `/modern` — Random trending song (pre-set styles)\n"
            f"  `/rewrite` — Regenerate the last song with a fresh twist\n"
            f"  `/retry` — Retry after a failed generation\n\n"

            f"📋 *Information*\n"
            f"  `/genres` — List all available styles\n"
            f"  `/artists` — List all available artists\n"
            f"  `/history` — Last 10 songs you made\n"
            f"  `/status` — System health & stats\n\n"

            f"🔑 *API Keys*\n"
            f"  `/keys` — View current keys\n"
            f"  `/addkey sk_audiera_…` — Add a key\n"
            f"  `/removekey <index>` — Remove a key\n"
            f"  `/rotatekey` — Switch to next key (multi mode)\n\n"

            f"💳 *Wallet*\n"
            f"  `/wallet` — View wallet info\n"
            f"  `/setwallet 0x…` — Set your EVM address\n"
            f"  `/balance` — Check $BEAT token balance\n\n"

            f"⚙️ *System*\n"
            f"  `/notifications on|off` — Toggle notifications\n"
            f"  `/reset` — Clear all memory & history\n"
            f"  `/debug` — Detailed debug info\n\n"

            f"🤖 *Autonomous Mode*\n"
            f"  `/auto_mode on` — Start fully autonomous generation\n"
            f"  `/auto_mode off` — Stop\n"
            f"  `/auto_mode pause` / `resume` — Pause or continue\n"
            f"  `/auto_mode status` — Show current state & stats\n"
            f"  `/auto_mode set interval=20 songs=2` — Configure\n\n"

            f"💡 *Custom Song Example:*\n"
            f"  `/custom about=summer love /artist=Kira /bpm=120`\n"
            f"  `/custom about=midnight /lyrics=the stars shine bright /bpm=90`"
        )

    def _cmd_status(self):
        uptime_s = int((now_utc() - self.state.session_start).total_seconds())
        h, rem   = divmod(uptime_s, 3600); m = rem // 60
        wallet_s = f"`{CFG.EVM_ADDRESS[:14]}…`" if CFG.EVM_ADDRESS and len(CFG.EVM_ADDRESS) == 42 else "_not set_"
        gen_s    = "⏳ _generating right now_" if self.generating else "✅ _ready_"
        ae       = self.auto_engine
        auto_s   = (f"🟢 _ON_ (cycle `{ae.cycle_count}`, every `{ae.current_interval}` min)"
                    if ae.active else "🔴 _OFF_")

        self.bot.send(
            f"📊 *System Status*  `v{CFG.AGENT_VERSION}`\n\n"
            f"  ⏱ Uptime:     `{h}h {m}m`\n"
            f"  🎵 Songs made: `{self.state.song_count}`\n"
            f"  🔑 API keys:   `{self.audiera.active_count}` active\n"
            f"  🔄 Key mode:   `{self.audiera.mode.upper()}`\n"
            f"  💳 Wallet:     {wallet_s}\n"
            f"  🤖 Generator:  {gen_s}\n"
            f"  🤖 Auto mode:  {auto_s}\n"
            f"  📢 Notify:     `{'ON' if self.bot.enabled else 'OFF'}`\n\n"
            f"  📈 API calls:  `{self.audiera.metrics['requests']}` total  "
            f"(`{self.audiera.metrics['successes']}` OK, `{self.audiera.metrics['failures']}` failed)"
        )

    def _cmd_reset(self):
        self.state.clear_all()
        self.dedup_themes = {"themes":[], "songs":[]}
        self._save_dedup()
        self.evolution_stage    = 0
        self.consecutive_fails  = 0
        self.bot.send(
            "🔄 *Full Reset Complete!*\n\n"
            "  ✔  Conversation memory cleared\n"
            "  ✔  Song history cleared\n"
            "  ✔  Duplicate theme list cleared\n"
            "  ✔  Song counter reset\n\n"
            "_Ready for a fresh start!_  Use /song to create your first track."
        )

    def _cmd_song(self, args: str):
        if not args:
            self.bot.send_buttons(
                "🎵 *What kind of song do you want?*\n\n"
                "Just describe it in your own words — for example:\n"
                "  • _\"A sad piano ballad about leaving home\"_\n"
                "  • _\"Happy energetic pop for a workout\"_\n"
                "  • _\"Chill lo-fi hip hop with soft vocals\"_\n\n"
                "Or type `/song <description>` directly.",
                [[("🎤 View Artists", "/artists"), ("🎸 View Genres", "/genres")]]
            )
            return
        self._handle_natural_language(args)

    def _cmd_rewrite(self):
        if not self.state.last_song_params:
            self.bot.send(
                "❌ *Nothing to rewrite.*\n\n"
                "Create a song first with /song, then use /rewrite for a fresh version."
            )
            return
        params = self.state.last_song_params
        modifiers = ["redux","v2","remix","fresh take","reimagined","new chapter"]
        new_theme = f"{params['theme']} — {random.choice(modifiers)}"
        self.bot.send(f"🔄 *Rewriting:* `{params['theme']}`\n\n⏳ Generating…")
        threading.Thread(
            target=self._generate_song_async,
            args=(new_theme, params["styles"], params["artist"]),
            daemon=True
        ).start()

    def _cmd_retry(self):
        if self.consecutive_fails == 0:
            self.bot.send("✅ *No failed generation to retry!*\n\nAll looks good. Use /song to create something new.")
            return
        if not self.state.last_song_params:
            self.bot.send("❌ No previous parameters to retry. Please create a new song with /song.")
            return
        params = self.state.last_song_params
        self.bot.send(
            f"🔄 *Retrying last generation…*\n\n"
            f"  Theme:  `{params['theme']}`\n"
            f"  Styles: `{', '.join(params['styles'])}`\n"
            f"  Artist: `{params['artist']}`"
        )
        threading.Thread(
            target=self._generate_song_async,
            args=(params["theme"], params["styles"], params["artist"]),
            daemon=True
        ).start()

    def _cmd_modern(self):
        themes  = ["midnight vibes","neon dreams","digital love","city lights",
                   "summer nights","party mode","chill waves","future bass","retro future"]
        styles_pool = [
            ["Electronic","Pop"], ["EDM","Dance"], ["R&B","Hip-Hop"],
            ["Pop","Dance","Electronic"], ["Synthwave","Electronic"],
        ]
        theme  = random.choice(themes)
        styles = random.choice(styles_pool)
        artist = random.choice(list(self.artist_ids.keys()))
        self.state.last_song_params = {"theme": theme, "styles": styles, "artist": artist}
        self.bot.send(
            f"🔥 *Modern Mode!*\n\n"
            f"  🎨 Theme:  `{theme}`\n"
            f"  🎸 Styles: `{', '.join(styles)}`\n"
            f"  🎤 Artist: `{artist}`\n\n"
            f"⏳ Generating…"
        )
        threading.Thread(
            target=self._generate_song_async,
            args=(theme, styles, artist),
            daemon=True
        ).start()

    def _cmd_custom(self, args: str):
        if not args:
            self.bot.send(
                "🎵 *Custom Song Creator*\n\n"
                "*Usage:*\n"
                "`/custom about=<theme> /artist=<name> /bpm=<70-180> /lyrics=<text>`\n\n"
                "*Options:*\n"
                "  • `about=`  — Song theme or description _(required)_\n"
                "  • `artist=` — Artist name (see /artists)\n"
                "  • `bpm=`    — Tempo: 70=slow, 120=mid, 140=fast, 160=party\n"
                "  • `lyrics=` — Custom lyrics to include _(optional)_\n\n"
                "*Examples:*\n"
                "  `/custom about=summer /artist=Kira /bpm=120`\n"
                "  `/custom about=midnight rain /lyrics=the stars shine bright /bpm=90`\n"
                "  `/custom about=gym workout /artist=Ray /bpm=150`"
            )
            return

        parts  = args.split("/")
        theme  = None
        lyrics = None
        artist = CFG.DEFAULT_ARTIST
        bpm    = 120

        for part in parts:
            part = part.strip()
            if part.startswith("about="):    theme  = part[6:].strip()
            elif part.startswith("lyrics="): lyrics = part[7:].strip()
            elif part.startswith("artist="):
                a = part[7:].strip()
                artist = a if a in self.artist_ids else CFG.DEFAULT_ARTIST
                if a not in self.artist_ids:
                    self.bot.send(
                        f"⚠️ Artist `{a}` not found — using `{CFG.DEFAULT_ARTIST}` instead.\n"
                        f"See `/artists` for the full list."
                    )
            elif part.startswith("bpm="):
                try:    bpm = max(60, min(200, int(part[4:].strip())))
                except: pass

        if not theme:
            self.bot.send(
                "❌ *Missing theme.*\n\n"
                "Use `about=` to set the theme. Example:\n"
                "`/custom about=summer love /artist=Kira /bpm=120`"
            )
            return

        # BPM → styles
        if bpm < 90:   styles = ["Ambient","Indie"]
        elif bpm < 110: styles = ["R&B","Soul"]
        elif bpm < 130: styles = ["Pop","Electronic"]
        elif bpm < 150: styles = ["Dance","EDM"]
        else:           styles = ["EDM","Techno"]

        self.state.last_song_params = {"theme": theme, "styles": styles,
                                       "artist": artist, "bpm": bpm, "custom_lyrics": lyrics}

        lyrics_tag = f"  📝 Lyrics:  _custom provided_\n" if lyrics else ""
        self.bot.send(
            f"🎵 *Creating Custom Song*\n\n"
            f"  🎨 Theme:  `{theme}`\n"
            f"  🎸 Styles: `{', '.join(styles)}`\n"
            f"  🎤 Artist: `{artist}`\n"
            f"  🥁 BPM:    `{bpm}`\n"
            f"{lyrics_tag}\n"
            f"⏳ Generating…"
        )
        threading.Thread(
            target=self._generate_song_async,
            args=(theme, styles, artist),
            daemon=True
        ).start()

    def _cmd_genres(self):
        styles = getattr(CFG, "AVAILABLE_STYLES", [
            "Pop","Electronic","R&B","Soul","Rock","Hip-Hop","Jazz","Classical",
            "Ambient","Indie","Folk","Metal","Dance","Funk","Punk","Gospel",
            "Blues","Country","Reggae","Latin","EDM","House","Techno","Trance"
        ])
        cols = [styles[i::3] for i in range(3)]
        max_rows = max(len(c) for c in cols)
        rows = ""
        for r in range(max_rows):
            row = ""
            for col in cols:
                cell = col[r] if r < len(col) else ""
                row += f"  `{cell:<14}`"
            rows += row.rstrip() + "\n"
        self.bot.send(
            f"🎸 *Available Styles* ({len(styles)} total)\n\n"
            f"{rows}\n"
            f"Use them like: `/song a {random.choice(styles).lower()} track about love`"
        )

    def _cmd_artists(self):
        descs = getattr(CFG, "ARTIST_DESCRIPTIONS", {})
        lines = ""
        for name, aid in self.artist_ids.items():
            desc = descs.get(name, "")
            lines += f"  🎤 *{name}*\n"
            if desc:
                lines += f"     _{desc}_\n"
        self.bot.send(
            f"🎤 *Available Artists*\n\n"
            f"{lines}\n"
            f"Use with: `/custom about=love /artist=Rhea Monroe /bpm=100`"
        )

    def _cmd_history(self):
        if not self.history:
            self.bot.send(
                "📜 *No history yet!*\n\n"
                "Create your first song with `/song` or just describe what you want."
            )
            return
        recent = self.history[:10]
        lines  = ""
        for i, s in enumerate(recent, 1):
            url_part = f"  [▶ Play]({s['url']})" if s.get("url") else ""
            lines += f"  {i}. *{s.get('theme','?')}*{url_part}\n"
            lines += f"     _{s.get('styles','?')}  •  {s.get('artist','?')}_\n"
            lines += f"     {C.DIM}{s.get('ts','')}{C.RESET}\n"
        self.bot.send(
            f"📜 *Last {len(recent)} Songs*\n\n"
            f"{lines}\n"
            f"Total songs made: `{self.state.song_count}`"
        )

    def _cmd_list_all(self):
        self.bot.send(
            f"📋 *Everything Available*\n\n"
            f"*Styles:* {len(getattr(CFG,'AVAILABLE_STYLES',[]))} genres\n"
            f"*Artists:* {len(self.artist_ids)}\n\n"
            f"Use `/genres` and `/artists` for full details."
        )

    def _cmd_config(self):
        self.bot.send(
            f"⚙️ *Current Configuration*\n\n"
            f"  Model:    `{CFG.AGENT_MODEL}`\n"
            f"  Version:  `{CFG.AGENT_VERSION}`\n"
            f"  Key mode: `{CFG.AUDIERA_MODE}`\n"
            f"  Notify:   `{'ON' if self.bot.enabled else 'OFF'}`\n"
            f"  Default artist: `{CFG.DEFAULT_ARTIST}`\n"
            f"  Default styles: `{', '.join(CFG.DEFAULT_STYLES)}`\n\n"
            f"_Edit config.py on the server to change these values._"
        )

    def _cmd_keys(self):
        if not self.audiera.keys:
            self.bot.send(
                "🔑 *No API Keys Configured*\n\n"
                "Add a key with:\n`/addkey sk_audiera_your_key_here`\n\n"
                "Get a key from https://ai.audiera.fi"
            )
            return
        lines = ""
        for i, k in enumerate(self.audiera.keys, 1):
            key    = k.get("key","")
            short  = f"`{key[:18]}…{key[-6:]}`" if len(key) > 25 else f"`{key}`"
            status = "✅ active" if k.get("status") == "active" else "❌ inactive"
            active = " ◀ _current_" if (i-1) == self.audiera.idx else ""
            lines += f"  {i}. {short}  {status}{active}\n"
        self.bot.send(
            f"🔑 *API Keys*  (mode: `{self.audiera.mode.upper()}`)\n\n"
            f"{lines}\n"
            f"➕ `/addkey sk_audiera_…` — add new key\n"
            f"➖ `/removekey <index>` — remove key\n"
            f"🔄 `/rotatekey` — switch to next key"
        )

    def _cmd_addkey(self, args: str):
        if not args:
            self.bot.send(
                "🔑 *Add API Key*\n\n"
                "Usage: `/addkey sk_audiera_your_key_here`\n\n"
                "Get keys from: https://ai.audiera.fi"
            )
            return
        ok, msg = self.audiera.add_key(args)
        icon = "✅" if ok else "❌"
        self.bot.send(f"{icon} {msg}")

    def _cmd_removekey(self, args: str):
        if not args or not args.strip().isdigit():
            self.bot.send(
                "❌ *Usage:* `/removekey <index>`\n\n"
                "Use `/keys` to see the index of each key."
            )
            return
        idx = int(args.strip()) - 1
        if 0 <= idx < len(self.audiera.keys):
            removed = self.audiera.keys.pop(idx)
            self.audiera._save_keys()
            key_s = removed.get("key","")
            self.bot.send(f"✅ *Removed key #{idx+1}*\n`{key_s[:18]}…{key_s[-6:]}`")
        else:
            self.bot.send(
                f"❌ *Index {idx+1} not found.*\n\n"
                f"Use `/keys` to see valid indices."
            )

    def _cmd_rotatekey(self):
        if self.audiera.rotate():
            self.bot.send(f"🔄 *Rotated to key #{self.audiera.idx+1}*\n`{self.audiera.current_short}`")
        else:
            self.bot.send(
                "⚠️ *Cannot rotate.*\n\n"
                "Either you only have one key, or AUDIERA_MODE is set to `single`.\n\n"
                "To enable rotation: set `AUDIERA_MODE = \"multi\"` in config.py "
                "and add more keys with `/addkey`."
            )

    def _cmd_wallet(self):
        addr = CFG.EVM_ADDRESS
        has_addr = bool(addr and len(addr) == 42)
        self.bot.send(
            f"💳 *Wallet Info*\n\n"
            f"  Address:  {'`' + addr[:14] + '…`' if has_addr else '_not set_'}\n"
            f"  Contract: `{CFG.BEAT_CONTRACT[:14]}…`\n"
            f"  web3:     {'✅ installed' if HAS_WEB3 else '❌ run: pip install web3'}\n\n"
            f"{'Use `/balance` to check your $BEAT balance.' if has_addr else 'Set your address with `/setwallet 0x…`'}"
        )

    def _cmd_setwallet(self, args: str):
        addr = args.strip()
        if not addr:
            self.bot.send(
                "💳 *Set Wallet Address*\n\n"
                "Usage: `/setwallet 0x1234567890abcdef1234567890abcdef12345678`\n\n"
                "This is your EVM-compatible wallet address (Ethereum, Polygon, etc.)"
            )
            return
        if not addr.startswith("0x") or len(addr) != 42:
            self.bot.send(
                "❌ *Invalid Address*\n\n"
                "EVM addresses must:\n"
                "  • Start with `0x`\n"
                "  • Be exactly 42 characters long\n"
                "  • Contain only hex characters (0-9, a-f)\n\n"
                f"Your input `{addr[:50]}` doesn't match. Double-check and try again."
            )
            return
        CFG.EVM_ADDRESS = addr
        self._save_wallet_config(addr)
        self.bot.send(
            f"✅ *Wallet Set!*\n\n"
            f"  Address: `{addr[:14]}…{addr[-6:]}`\n\n"
            f"Use `/balance` to check your $BEAT balance."
        )

    def _save_wallet_config(self, addr: str):
        try:
            cfg_path = BASE_DIR / "config.py"
            content  = cfg_path.read_text("utf-8")
            content  = re.sub(r'EVM_ADDRESS\s*=\s*"[^"]*"',
                              f'EVM_ADDRESS   = "{addr}"', content)
            cfg_path.write_text(content, "utf-8")
        except Exception as e:
            log.warning(f"Could not persist wallet: {e}")

    def _cmd_balance(self):
        addr = CFG.EVM_ADDRESS
        if not addr or len(addr) != 42:
            self.bot.send(
                "❌ *No wallet set.*\n\n"
                "Set your wallet first: `/setwallet 0x…`"
            )
            return
        if not HAS_WEB3:
            self.bot.send(
                "❌ *web3 not installed.*\n\n"
                "Install it on the server:\n`pip install web3`\n\n"
                "Then restart the bot."
            )
            return

        self.bot.send(f"⏳ Checking $BEAT balance for `{addr[:14]}…`")

        rpcs = ["https://eth.llamarpc.com","https://rpc.ankr.com/eth","https://eth.public-rpc.com"]
        for rpc in rpcs:
            try:
                w3  = Web3(Web3.HTTPProvider(rpc))
                if not w3.is_address(addr):
                    self.bot.send("❌ Wallet address failed checksum. Set a valid address with `/setwallet`.")
                    return
                ca  = Web3.to_checksum_address(CFG.BEAT_CONTRACT)
                wa  = Web3.to_checksum_address(addr)
                abi = '[{"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"type":"function"}]'
                bal = w3.eth.contract(address=ca, abi=abi).functions.balanceOf(wa).call()
                self.bot.send(
                    f"💰 *$BEAT Balance*\n\n"
                    f"  Wallet: `{addr[:14]}…{addr[-6:]}`\n"
                    f"  Balance: `{bal/1e18:,.4f} $BEAT`"
                )
                return
            except Exception as e:
                if "429" in str(e) or "rate" in str(e).lower(): continue
                self.bot.send(
                    f"❌ *RPC Error*\n\n`{str(e)[:120]}`\n\n"
                    f"Try again in a moment, or check your wallet address."
                )
                return

        self.bot.send("⚠️ All RPC providers are rate-limited right now. Try again in a minute.")

    def _cmd_notifications(self, args: str):
        if args.strip().lower() in ("off","0","false","no"):
            self.bot.enabled = False
            self.bot.send("🔕 *Notifications OFF* — You'll no longer receive alerts.", silent=True)
        else:
            self.bot.enabled = True
            self.bot.send("🔔 *Notifications ON* — You'll receive all updates.")

    def _cmd_debug(self):
        metrics = self.audiera.metrics
        auto_s  = "ON" if self.auto_engine.active else "OFF"
        self.bot.send(
            f"🔧 *Debug Info*\n\n"
            f"  Agent ver:     `{CFG.AGENT_VERSION}`\n"
            f"  Model:         `{CFG.AGENT_MODEL}`\n"
            f"  Session start: `{self.state.session_start.strftime('%H:%M UTC')}`\n"
            f"  Generating:    `{self.generating}`\n"
            f"  Consec. fails: `{self.consecutive_fails}`\n"
            f"  History size:  `{len(self.history)}`\n"
            f"  Dedup themes:  `{len(self.dedup_themes.get('themes',[]))}`\n"
            f"  Auto mode:     `{auto_s}` (cycle {self.auto_engine.cycle_count})\n\n"
            f"  API requests:  `{metrics['requests']}`\n"
            f"  API successes: `{metrics['successes']}`\n"
            f"  API failures:  `{metrics['failures']}`\n"
            f"  Key rotations: `{metrics['rotations']}`\n\n"
            f"  Active key:    `{self.audiera.current_short}`\n"
            f"  Key mode:      `{self.audiera.mode}`\n"
            f"  Keys total:    `{len(self.audiera.keys)}`\n\n"
            f"  web3:          `{'installed' if HAS_WEB3 else 'NOT installed'}`"
        )

    def _cmd_auto_mode(self, args: str):
        """
        /auto_mode [on|off|pause|resume|status|set key=val]

        Starts, stops, pauses, or configures the fully autonomous generation engine.
        """
        sub = args.strip().lower() if args else "on"

        # ── STATUS ────────────────────────────────────────────────────────
        if sub in ("status", "info", "?", ""):
            self.bot.send(self.auto_engine.status_text())
            return

        # ── ON / START ────────────────────────────────────────────────────
        if sub in ("on", "start", "enable", "begin", "go"):
            if self.auto_engine.active:
                self.bot.send(
                    "🤖 *AUTO MODE is already running!*\n\n"
                    "Send `/auto_mode status` to see progress, or `/auto_mode off` to stop."
                )
                return
            self.auto_engine.start()
            self.bot.send_buttons(
                f"🤖 *AUTO MODE Started!*\n\n"
                f"  ⏱ Interval:  `{self.auto_engine.current_interval} min`\n"
                f"  🎵 Per cycle: `{self.auto_engine.songs_per_cycle}` song(s)\n"
                f"  📢 Report:   every `{self.auto_engine.report_every}` cycles\n\n"
                f"I'll pick moods by time-of-day, styles by day-of-week, "
                f"and rotate through all 12 artists automatically.\n\n"
                f"_No human input needed — I'll handle everything!_",
                [[("⏸ Pause", "/auto_mode pause"), ("🔴 Stop", "/auto_mode off"),
                  ("📊 Status", "/auto_mode status")]]
            )
            return

        # ── OFF / STOP ────────────────────────────────────────────────────
        if sub in ("off", "stop", "disable", "end", "quit"):
            if not self.auto_engine.active:
                self.bot.send("🤖 *AUTO MODE is not running.* Use `/auto_mode on` to start it.")
                return
            self.auto_engine.stop()
            ae = self.auto_engine
            self.bot.send(
                f"🔴 *AUTO MODE Stopped.*\n\n"
                f"  Cycles completed: `{ae.cycle_count}`\n"
                f"  Songs generated:  `{self.state.song_count}`\n"
                f"  Final interval:   `{ae.current_interval} min`\n\n"
                f"_Use `/auto_mode on` to start again._"
            )
            return

        # ── PAUSE ─────────────────────────────────────────────────────────
        if sub in ("pause", "hold", "wait"):
            if not self.auto_engine.active:
                self.bot.send("🤖 *AUTO MODE is not running.* Use `/auto_mode on` to start.")
                return
            self.auto_engine.pause()
            self.bot.send(
                "⏸ *AUTO MODE Paused.*\n\n"
                "Generation is on hold. Send `/auto_mode resume` to continue."
            )
            return

        # ── RESUME ────────────────────────────────────────────────────────
        if sub in ("resume", "continue", "unpause", "go"):
            if not self.auto_engine.active:
                self.bot.send("🤖 *AUTO MODE is not running.* Use `/auto_mode on` to start.")
                return
            self.auto_engine.resume()
            self.bot.send(
                f"▶️ *AUTO MODE Resumed.*\n\n"
                f"  Next cycle will start within `{self.auto_engine.current_interval} min`.\n"
                f"  Use `/auto_mode status` to monitor progress."
            )
            return

        # ── SET (configure) ───────────────────────────────────────────────
        if sub.startswith("set"):
            cfg_str = args.strip()[3:].strip()  # e.g. "interval=20 songs=2"
            if not cfg_str:
                self.bot.send(
                    "⚙️ *AUTO MODE Config — Usage:*\n\n"
                    "`/auto_mode set interval=20`    — minutes between cycles\n"
                    "`/auto_mode set songs=2`         — songs per cycle (1–5)\n"
                    "`/auto_mode set report=5`        — report every N cycles\n\n"
                    "*Example:*\n"
                    "`/auto_mode set interval=15 songs=2 report=3`"
                )
                return
            kwargs: dict = {}
            for token in cfg_str.split():
                if "=" in token:
                    k, v = token.split("=", 1)
                    k = k.strip().lower()
                    try:
                        if k in ("interval",):   kwargs["interval"] = int(v)
                        elif k in ("songs","song"): kwargs["songs"] = int(v)
                        elif k in ("report","report_every"): kwargs["report_every"] = int(v)
                    except ValueError:
                        pass
            if not kwargs:
                self.bot.send("❌ Could not parse settings. Example: `/auto_mode set interval=20 songs=2`")
                return
            self.auto_engine.configure(**kwargs)
            ae = self.auto_engine
            self.bot.send(
                f"✅ *AUTO MODE Config Updated*\n\n"
                f"  ⏱ Interval:  `{ae.current_interval} min`\n"
                f"  🎵 Per cycle: `{ae.songs_per_cycle}` song(s)\n"
                f"  📢 Report:   every `{ae.report_every}` cycles"
            )
            return

        # ── UNKNOWN SUBCOMMAND ────────────────────────────────────────────
        self.bot.send(
            "🤖 *AUTO MODE Commands:*\n\n"
            "  `/auto_mode on` — start autonomous generation\n"
            "  `/auto_mode off` — stop\n"
            "  `/auto_mode pause` — pause loop\n"
            "  `/auto_mode resume` — resume loop\n"
            "  `/auto_mode status` — show current status\n"
            "  `/auto_mode set interval=20 songs=2` — configure\n\n"
            "_When on, I pick moods, styles, themes and artists automatically._"
        )


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(
        description=f"Audiera AI Song Agent  v{CFG.AGENT_VERSION}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python song_agent.py                   Run the Telegram bot (default)
  python song_agent.py --menu            Open the interactive CLI menu
  python song_agent.py --once            Generate one song and exit
  python song_agent.py --loop            Auto-generate on a schedule
  python song_agent.py --loop --interval 15   Auto-generate every 15 minutes
        """
    )
    parser.add_argument("--once",     action="store_true",  help="Generate one song and exit")
    parser.add_argument("--loop",     action="store_true",  help="Auto-generate songs on a schedule")
    parser.add_argument("--interval", type=int, default=getattr(CFG,"DEFAULT_INTERVAL_MINUTES",30),
                                                            help="Loop interval in minutes")
    parser.add_argument("--theme",    type=str,             help="Song theme for --once / --loop")
    parser.add_argument("--styles",   nargs="+",            help="Styles e.g. Pop Electronic")
    parser.add_argument("--artist",   type=str,             help="Artist name")
    parser.add_argument("--menu",     action="store_true",  help="Open interactive CLI menu")
    parser.add_argument("--no-menu",  action="store_true",  help="Skip the menu (for .bat launcher)")
    parser.add_argument("--no-color", action="store_true",  help="Disable ANSI colors")
    args = parser.parse_args()

    if args.no_color:
        C.disable()

    # ── validate config ───────────────────────────────────────────────────────
    ok, errors = ConfigValidator.validate()
    if not ok:
        # Fatal errors (missing token / chat ID)
        fatal = {"no_token", "no_chat_id", "no_api_key"}
        if fatal & set(errors):
            p(f"\n{C.ERR}  Startup aborted — fix the errors above and try again.{C.RESET}\n")
            _sys.exit(1)
        # Non-fatal (e.g. no web3) — warn and continue
        p(f"{C.WARN}  ⚠  Some optional features are unavailable (see above).{C.RESET}\n")

    # ── init agent ────────────────────────────────────────────────────────────
    try:
        agent = SongAgent()
    except Exception as e:
        p(f"\n{C.ERR}  ✖  Failed to initialise agent: {e}{C.RESET}")
        traceback.print_exc()
        _sys.exit(1)

    # ── menu mode ─────────────────────────────────────────────────────────────
    if args.menu:
        run_interactive_menu(agent)
        return

    # ── --once mode ───────────────────────────────────────────────────────────
    if args.once:
        banner()
        print_section("🎵  Single Song Generation")
        theme  = args.theme  or input(f"\n  {C.CYAN}Song theme:{C.RESET}  ") or "beautiful dreams"
        styles = args.styles or CFG.DEFAULT_STYLES
        artist = args.artist or CFG.DEFAULT_ARTIST
        p()
        log_line("info", f"Theme   {theme}")
        log_line("info", f"Styles  {', '.join(styles)}")
        log_line("info", f"Artist  {artist}")
        p()

        spin = Spinner("Generating song")
        spin.start()
        t = threading.Thread(target=agent._generate_song_async, args=(theme, styles, artist), daemon=True)
        t.start(); t.join()
        spin.stop()
        log_line("ok", "Done!", f"total songs: {agent.state.song_count}")
        return

    # ── --loop mode ───────────────────────────────────────────────────────────
    if args.loop:
        banner()
        log_line("ok", f"Auto-loop started", f"interval: {args.interval} min  ·  Ctrl+C to stop")
        p()
        cycle = 0
        while True:
            try:
                cycle += 1
                mood   = random.choice(["happy","sad","energetic","chill","romantic","dark"])
                theme  = args.theme or f"{mood.capitalize()} moments"
                styles = args.styles or CFG.MOOD_TO_STYLES.get(mood, CFG.DEFAULT_STYLES)
                artist = args.artist or random.choice(list(CFG.ARTISTS.keys()))

                log_line("gen", f"Cycle {cycle}  ·  {theme}", f"{', '.join(styles)}  ·  {artist}")
                t = threading.Thread(target=agent._generate_song_async, args=(theme, styles, artist), daemon=True)
                t.start(); t.join()
                log_line("ok", f"Cycle {cycle} done", f"total songs: {agent.state.song_count}")
                log_line("wait", f"Sleeping {args.interval} min…")
                time.sleep(args.interval * 60)
            except KeyboardInterrupt:
                p()
                log_line("warn", "Loop stopped", f"completed {cycle} cycle(s)")
                break
            except Exception as e:
                log_line("err", "Loop error", str(e)[:80])
                time.sleep(60)
        return

    # ── default: Telegram bot ─────────────────────────────────────────────────
    banner()
    print_status_bar(agent)

    def _shutdown(sig, frame):
        p(f"\n  {C.WARN}⏹  Shutting down Audiera…{C.RESET}")
        agent.bot.stop()
        _sys.exit(0)

    signal.signal(signal.SIGINT,  _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        _shutdown(None, None)


if __name__ == "__main__":
    main()
