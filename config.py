import os
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
KEYAUTH_SELLER_KEY = os.getenv("KEYAUTH_SELLER_KEY", "").strip()
KEYAUTH_API_URL = os.getenv("KEYAUTH_API_URL", "https://keyauth.win/api/seller/").strip()
GUILD_ID_RAW = os.getenv("GUILD_ID", "").strip()

GUILD_ID = int(GUILD_ID_RAW) if GUILD_ID_RAW.isdigit() else None

def validate_config():
    """
    Validates required environment configuration.
    Returns a list of missing or invalid variable names.
    """
    missing = []
    if not DISCORD_TOKEN or DISCORD_TOKEN == "YOUR_DISCORD_BOT_TOKEN_HERE":
        missing.append("DISCORD_TOKEN")
    if not KEYAUTH_SELLER_KEY or KEYAUTH_SELLER_KEY == "YOUR_KEYAUTH_SELLER_KEY_HERE":
        missing.append("KEYAUTH_SELLER_KEY")
    return missing
