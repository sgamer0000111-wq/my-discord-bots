import asyncio
import logging
import sys
import discord
from discord.ext import commands

import config
from keyauth_api import KeyAuthSellerAPI
from bot import create_embed, has_bot_access, check_user_access, DAYS_CHOICES, _handle_genkey, ControlPanelView

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("MultiBotRunner")

# List of configured bots
BOTS_CONFIG = [
    {
        "name": "X CHEAT SILENT MAX",
        "token": "MTQwMjEyNTYwMDgwOTgxNjA3NA.Gj976k.qzvJnn3Ik4sBM3l7npbTFmxWsX660UBe8Ibgc0",
        "seller_key": "bot_br_live_8c874050bd20af61e0126617"
    },
    {
        "name": "X CHEAT COVER SILENT",
        "token": "MTU0ODIwOTg0MTE5MTc4ODU3NA.GzE6DL.Q_cFC2uH50bJm8lEgeeV0lxtuBpOa7WauqFX-Q",
        "seller_key": "bot_br_live_1017ee6a4b8ea826564f58f4"
    },
    {
        "name": "X CHEAT INTERNAL",
        "token": "MTU0ODIxMjg4NDg0MzI3NDI0MA.G4k4S9.yNLPRHdU0BS28jHwYz_1q0qlirTjltwoF0-PJ0",
        "seller_key": "bot_br_live_ea8e146eeeb0e3f97192aa9c"
    }
]


def create_bot_instance(bot_info: dict):
    token = bot_info["token"]
    name = bot_info["name"]
    seller_key = bot_info["seller_key"]

    intents = discord.Intents.default()
    bot = commands.Bot(command_prefix="!", intents=intents)
    api_client = KeyAuthSellerAPI(seller_key=seller_key, api_url=config.KEYAUTH_API_URL)

    @bot.event
    async def on_ready():
        logger.info(f"[{name}] Logged in as {bot.user} (ID: {bot.user.id})")
        try:
            synced_global = await bot.tree.sync()
            logger.info(f"[{name}] Synced {len(synced_global)} global slash command(s).")
            for guild in bot.guilds:
                try:
                    bot.tree.copy_global_to(guild=guild)
                    synced_guild = await bot.tree.sync(guild=guild)
                    logger.info(f"[{name}] Synced {len(synced_guild)} command(s) to server: {guild.name}")
                except Exception as ge:
                    logger.warning(f"[{name}] Guild sync error: {ge}")
        except Exception as e:
            logger.error(f"[{name}] Sync error: {e}")

        await bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{name} | /createkey"
            )
        )

    # Slash command setup
    @bot.tree.command(name="createkey", description=f"Create key via {name}")
    @discord.app_commands.describe(
        days="Select Duration (1 Day, 7 Days, 30 Days, Lifetime)"
    )
    @discord.app_commands.choices(days=DAYS_CHOICES)
    @has_bot_access()
    async def createkey(
        interaction: discord.Interaction,
        days: discord.app_commands.Choice[int]
    ):
        await interaction.response.defer(ephemeral=False)
        note_str = f"Created via Discord by {interaction.user}"
        res = await api_client.add_key(expiry=days.value, mask="XXXXXX-XXXXXX-XXXXXX", level=1, amount=1, note=note_str)

        if res.get("success"):
            key_data = res.get("key") or res.get("keys") or res.get("message")
            embed = create_embed(title=f"🔑 {name} License Key Created!", color=discord.Color.green())
            if isinstance(key_data, list):
                embed.add_field(name="Generated Keys", value="\n".join([f"`{k}`" for k in key_data]), inline=False)
            else:
                embed.add_field(name="License Key", value=f"```\n{key_data}\n```", inline=False)
            
            expiry_label = "Lifetime (Unlimited)" if days.value >= 9999 else f"{days.value} Days"
            embed.add_field(name="Duration", value=expiry_label, inline=True)
            embed.add_field(name="Created By", value=interaction.user.mention, inline=False)
            await interaction.followup.send(embed=embed, ephemeral=False)
        else:
            msg = res.get("message", "Failed to generate key.")
            embed = create_embed(title="❌ Key Generation Failed", description=msg, color=discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=False)

    @bot.tree.command(name="panel", description=f"Open Control Panel for {name}")
    @has_bot_access()
    async def panel(interaction: discord.Interaction):
        embed = create_embed(
            title=f"🛠️ {name} Control Panel",
            description="Niche diye gaye buttons se direct keys create karein:",
            color=discord.Color.dark_theme()
        )
        await interaction.response.send_message(embed=embed, view=ControlPanelView(), ephemeral=False)

    return bot, token


import os
from aiohttp import web

async def start_web_health_server():
    port = int(os.environ.get("PORT", 8080))
    app = web.Application()
    
    async def health_check(request):
        return web.Response(text="OK - 3 Discord Bots Running 24/7", status=200)

    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Health check HTTP server running on port {port}")


async def main():
    logger.info("Starting Multi-Bot Runner for all 3 Discord Bots...")
    
    # Start Web Health Server for Cloud Platforms (Render/Railway/etc.)
    try:
        await start_web_health_server()
    except Exception as e:
        logger.warning(f"Could not start web server: {e}")

    tasks = []
    for b_config in BOTS_CONFIG:
        bot_obj, token = create_bot_instance(b_config)
        tasks.append(bot_obj.start(token))

    await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Multi-Bot Runner stopped.")
