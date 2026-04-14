#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                         SONG AGENT - CONFIGURATION                          ║
║                                                                              ║
║  Edit this file to configure your AI Song Agent.                            ║
║  All sensitive data (API keys, tokens) go here - NEVER share this file!    ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

# ═══════════════════════════════════════════════════════════════════════════
#  TELEGRAM CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════
# Get your bot token from @BotFather on Telegram
TG_BOT_TOKEN = "YOUR_BOT_TOKEN"
TG_CHAT_ID   = "YOUR_CHAT_ID"

# ═══════════════════════════════════════════════════════════════════════════
#  AUDIERA API KEYS
# ═══════════════════════════════════════════════════════════════════════════
# Get your API keys from https://ai.audiera.fi
AUDIERA_KEYS = [
    {
        "key": "ENTER_YOUR_AUDIERA_API_KEYS",
        "status": "active"
    },
    # Add more keys here for multi-key rotation:
    # {"key": "sk_audiera_second_key_here", "status": "active"},
]

# Mode: "single" (use one key) or "multi" (rotate on errors)
AUDIERA_MODE = "single"

# ═══════════════════════════════════════════════════════════════════════════
#  WALLET CONFIGURATION  —  BNB Chain BEP-20
# ═══════════════════════════════════════════════════════════════════════════
# Your BEP-20 wallet address for receiving $BEAT tokens (BNB Chain / BSC)
# Get MetaMask or Trust Wallet — ensure BNB Chain network is selected
EVM_ADDRESS   = "ENTER_YOUR_EVM_ADDRESS"

# $BEAT token contract address on BNB Chain (BEP-20)
# Contract: https://bscscan.com/token/0xcf3232b85b43bca90e51d38cc06cc8bb8c8a3e36
BEAT_CONTRACT = "0xcf3232b85b43bca90e51d38cc06cc8bb8c8a3e36"

# BNB Chain (BSC) RPC endpoints — used for on-chain balance checks
# Primary:  https://bsc-dataseed1.binance.org
# Fallback: https://rpc.ankr.com/bsc  |  https://bsc.publicnode.com
BSC_RPC_ENDPOINTS = [
    "https://bsc-dataseed1.binance.org",
    "https://bsc-dataseed2.binance.org",
    "https://bsc-dataseed3.binance.org",
    "https://rpc.ankr.com/bsc",
    "https://bsc.publicnode.com",
]

# ═══════════════════════════════════════════════════════════════════════════
#  EARNINGS SYSTEM  (v3.4.0)  —  $BEAT on BNB Chain (BEP-20)
# ═══════════════════════════════════════════════════════════════════════════
# $BEAT tokens earned per song generated
BEAT_PER_SONG = 1.0

# Milestone song counts that trigger a celebration alert
EARNINGS_MILESTONES = [10, 25, 50, 100, 250, 500, 1000, 2500, 5000]

# Show earnings summary in every song result message
SHOW_EARNINGS_IN_RESULTS = True

# ═══════════════════════════════════════════════════════════════════════════
#  AGENT IDENTITY
# ═══════════════════════════════════════════════════════════════════════════
AGENT_NAME    = "🎵 Audiera"
AGENT_VERSION = "3.4.0"
AGENT_MODEL   = "claude-sonnet-4-20250514"

# Bot display name in messages
BOT_DISPLAY_NAME = "Audiera"

# ═══════════════════════════════════════════════════════════════════════════
#  NOTIFICATION SETTINGS
# ═══════════════════════════════════════════════════════════════════════════
# Enable/disable Telegram notifications by default
NOTIFICATIONS_DEFAULT = True

# Send welcome message on startup (set False to disable)
SEND_WELCOME_MESSAGE = True

# ═══════════════════════════════════════════════════════════════════════════
#  SONG GENERATION DEFAULTS
# ═══════════════════════════════════════════════════════════════════════════
# Default interval between autonomous loops (minutes)
DEFAULT_INTERVAL_MINUTES = 30

# Default music styles (can be overridden by user)
DEFAULT_STYLES = ["Pop", "Electronic"]

# Default artist
DEFAULT_ARTIST = "Kira"

# Default preferred style for natural language generation (user can set via /setstyle)
# Leave empty "" to use DEFAULT_STYLES
PREFERRED_STYLE = ""

# ═══════════════════════════════════════════════════════════════════════════
#  EMOTION ENGINE SETTINGS
# ═══════════════════════════════════════════════════════════════════════════
# How fast emotions fade (0-1, higher = faster decay)
EMOTION_MEMORY_DECAY = 0.15

# Interactions before next evolution stage
EVOLUTION_THRESHOLD = 10

# ═══════════════════════════════════════════════════════════════════════════
#  DEATH MODE SETTINGS
# ═══════════════════════════════════════════════════════════════════════════
# Days of inactivity before death mode activates
DEATH_MODE_INACTIVITY_DAYS = 7

# ═══════════════════════════════════════════════════════════════════════════
#  LOGGING SETTINGS
# ═══════════════════════════════════════════════════════════════════════════
# Enable verbose logging (shows all debug info)
VERBOSE_LOGGING = False

# Save logs to file (set False to disable)
SAVE_LOG_FILE = False

# Log file retention days
LOG_RETENTION_DAYS = 30

# ═══════════════════════════════════════════════════════════════════════════
#  FEATURE FLAGS (Advanced Settings)
# ═══════════════════════════════════════════════════════════════════════════
# Enable conversation memory (remembers previous requests)
ENABLE_CONVERSATION_MEMORY = True

# Enable smart suggestions based on history
ENABLE_SMART_SUGGESTIONS = True

# Enable auto-retry on failure
ENABLE_AUTO_RETRY = True

# Max retry attempts for failed generations
MAX_RETRY_ATTEMPTS = 3

# Enable learning from user preferences
ENABLE_PREFERENCE_LEARNING = True

# ═══════════════════════════════════════════════════════════════════════════
#  LANGUAGE SETTINGS
# ═══════════════════════════════════════════════════════════════════════════
# Primary language for bot responses
PRIMARY_LANGUAGE = "en"

# Supported languages
SUPPORTED_LANGUAGES = ["en", "hi", "es", "fr", "de"]

# ═══════════════════════════════════════════════════════════════════════════
#  AUTONOMOUS MODE SETTINGS
# ═══════════════════════════════════════════════════════════════════════════
# Enable autonomous song generation loop
AUTONOMOUS_MODE = False

# How many songs to generate per autonomous loop
SONGS_PER_LOOP = 1

# ═══════════════════════════════════════════════════════════════════════════
#  STYLE AND GENRE DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════
# Available music styles/genres
AVAILABLE_STYLES = [
    "Pop", "Electronic", "R&B", "Soul", "Rock", "Hip-Hop",
    "Jazz", "Classical", "Ambient", "Indie", "Folk", "Metal",
    "Dance", "Funk", "Punk", "Gospel", "Blues", "Country",
    "Reggae", "Latin", "EDM", "House", "Techno", "Trance"
]

# Mood to style mapping
MOOD_TO_STYLES = {
    "happy": ["Pop", "Dance", "Funk"],
    "sad": ["R&B", "Soul", "Indie"],
    "angry": ["Rock", "Metal", "Punk"],
    "romantic": ["R&B", "Soul", "Pop"],
    "chill": ["Ambient", "Indie", "Folk"],
    "energetic": ["EDM", "Dance", "Hip-Hop"],
    "nostalgic": ["Soul", "Funk", "R&B"],
    "dark": ["Metal", "Electronic", "Ambient"],
    "uplifting": ["Pop", "Dance", "Electronic"]
}

# ═══════════════════════════════════════════════════════════════════════════
#  ARTIST DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════
# Available artists with their Audiera IDs
ARTISTS = {
    "Kira":         "osipvytdvxuzci9pn2nz1",
    "Ray":          "jyjcnj6t3arzzb5dnzk4p",
    "Jason Miller": "i137z0bj0cwsbzrzd8m0c",
    "Dylan Cross":  "xa6h1wjowcyvo1r87x1np",
    "Rhea Monroe":   "yinjs025l733tttxgy2w5",
    "Trevor Knox":  "woujl3ws7l9z6df4p0y03",
    "Kayden West":  "lwyap77qryxy4xz8vo11m",
    "Talia Brooks": "hcqa005jz02ikis7xt2q4",
    "Sienna Blake": "yk5reyqu4ko46k5knx4w9",
    "Briana Rose":  "tzuww7dbsh4enwifaptfl",
    "Leo Martin":   "udst8rsngyccqh3e2y80a",
    "Amelia Clarke": "9j282m4kbg1dukqabas3h",
}

# Artist descriptions for better matching
ARTIST_DESCRIPTIONS = {
    "Kira": "Soft, melodic vocals - great for emotional songs",
    "Ray": "Electronic, synth-based - perfect for modern beats",
    "Jason Miller": "Raw, powerful - ideal for rock and intense tracks",
    "Dylan Cross": "Dark, moody - suits atmospheric music",
    "Rhea Monroe": "Soulful, warm - excellent for R&B and love songs",
    "Trevor Knox": "Edgy, bold - great for hip-hop and rap",
    "Kayden West": "Experimental, unique - perfect for innovative sounds",
    "Talia Brooks": "Gentle, flowing - ideal for soft melodies",
    "Sienna Blake": "Dynamic, versatile - works with many genres",
    "Briana Rose": "Powerful vocals - great for gospel and soul",
    "Leo Martin": "Classical training - perfect for orchestral elements",
    "Amelia Clarke": "Indie, folk-inspired - suits acoustic tracks",
}

# ═══════════════════════════════════════════════════════════════════════════
#  COMMAND ALIASES
# ═══════════════════════════════════════════════════════════════════════════
# Alternative command names
COMMAND_ALIASES = {
    "reset": ["reset", "restart", "clear"],
    "help": ["help", "commands", "menu"],
    "status": ["status", "stats", "info"],
    "create": ["create", "make", "generate", "song"],
    "genres": ["genres", "styles", "types"],
    "artists": ["artists", "singers", "vocalists"],
    "earnings": ["earnings", "earn", "money", "beat", "rewards"],
}
