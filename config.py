import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
KEYAUTH_SELLER_KEY = os.getenv("KEYAUTH_SELLER_KEY", "bot_br_live_8c874050bd20af61e0126617")
KEYAUTH_API_URL = os.getenv("KEYAUTH_API_URL", "https://br-auth-all-panels.vercel.app")
