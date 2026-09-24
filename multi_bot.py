import asyncio
import logging
import sys
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

from typing import Optional, Union
import config
from keyauth_api import KeyAuthSellerAPI
from bot import create_embed, has_bot_access, check_user_access, DAYS_CHOICES, _handle_genkey, ControlPanelView

# Load .env file
load_dotenv()

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("MultiBotRunner")

def clean_val(val: str) -> str:
    if not val:
        return ""
    val = val.strip().strip("'\"")
    if "Value:" in val:
        val = val.split("Value:")[-1]
    if "|" in val:
        val = val.split("|")[-1]
    return val.strip()

# List of configured bots with Environment Variable support
BOTS_CONFIG = [
    {
        "name": "X CHEAT SILENT MAX",
        "token": clean_val(os.environ.get("BOT1_TOKEN", "")),
        "seller_key": clean_val(os.environ.get("BOT1_SELLER_KEY", "bot_br_live_8c874050bd20af61e0126617"))
    },
    {
        "name": "X CHEAT COVER SILENT",
        "token": clean_val(os.environ.get("BOT2_TOKEN", "")),
        "seller_key": clean_val(os.environ.get("BOT2_SELLER_KEY", "bot_br_live_1017ee6a4b8ea826564f58f4"))
    },
    {
        "name": "X CHEAT INTERNAL",
        "token": clean_val(os.environ.get("BOT3_TOKEN", "")),
        "seller_key": clean_val(os.environ.get("BOT3_SELLER_KEY", "bot_br_live_ea8e146eeeb0e3f97192aa9c"))
    }
]


def get_seller_key_for_bot(bot_user, fallback_key: str) -> str:
    if not bot_user:
        return fallback_key
    bot_id = getattr(bot_user, "id", 0)
    if bot_id == 1402125600809816074:
        return clean_val(os.environ.get("BOT1_SELLER_KEY", "bot_br_live_8c874050bd20af61e0126617"))
    elif bot_id == 1548209841191788574:
        return clean_val(os.environ.get("BOT2_SELLER_KEY", "bot_br_live_1017ee6a4b8ea826564f58f4"))
    elif bot_id == 1548212884843274240:
        return clean_val(os.environ.get("BOT3_SELLER_KEY", "bot_br_live_ea8e146eeeb0e3f97192aa9c"))

    uname = getattr(bot_user, "name", "").upper()
    if "INTERNAL" in uname:
        return clean_val(os.environ.get("BOT3_SELLER_KEY", "bot_br_live_ea8e146eeeb0e3f97192aa9c"))
    elif "COVER" in uname:
        return clean_val(os.environ.get("BOT2_SELLER_KEY", "bot_br_live_1017ee6a4b8ea826564f58f4"))
    elif "SILENT" in uname or "MAX" in uname:
        return clean_val(os.environ.get("BOT1_SELLER_KEY", "bot_br_live_8c874050bd20af61e0126617"))
    return fallback_key


def create_bot_instance(bot_info: dict):
    token = bot_info["token"]
    name = bot_info["name"]
    seller_key = bot_info["seller_key"]

    intents = discord.Intents.default()
    bot = commands.Bot(command_prefix="!", intents=intents)

    @bot.event
    async def on_ready():
        logger.info(f"[{name}] Logged in as {bot.user} (ID: {bot.user.id})")
        try:
            # Clear per-guild commands to eliminate duplicate slash command entries in Discord
            for guild in bot.guilds:
                try:
                    bot.tree.clear_commands(guild=guild)
                    await bot.tree.sync(guild=guild)
                except Exception:
                    pass

            # Sync Global commands clean
            synced_global = await bot.tree.sync()
            logger.info(f"[{name}] Synced {len(synced_global)} global slash command(s).")
        except Exception as e:
            logger.error(f"[{name}] Sync error: {e}")

        await bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{bot.user.name if bot.user else name} | /createkey"
            )
        )

    # Slash command setup
    @bot.tree.command(name="createkey", description=f"Create key via bot")
    @discord.app_commands.describe(
        days="Select Duration (1 Day, 7 Days, 30 Days, Lifetime)",
        prefix="Key Prefix (Default: XCHEAT, e.g. VIP, MYBRAND)"
    )
    @discord.app_commands.choices(days=DAYS_CHOICES)
    @has_bot_access()
    async def createkey(
        interaction: discord.Interaction,
        days: discord.app_commands.Choice[int],
        prefix: str = "XCHEAT"
    ):
        await interaction.response.defer(ephemeral=False)
        note_str = f"Created via Discord by {interaction.user}"
        active_seller_key = get_seller_key_for_bot(interaction.client.user, seller_key)
        active_api_client = KeyAuthSellerAPI(seller_key=active_seller_key, api_url=config.KEYAUTH_API_URL)
        res = await active_api_client.add_key(expiry=days.value, mask="XXXXXX-XXXXXX-XXXXXX", level=1, amount=1, note=note_str, prefix=prefix)

        if res.get("success"):
            key_data = res.get("key") or res.get("keys") or res.get("message")
            bot_display_name = interaction.client.user.name if interaction.client.user else name
            embed = create_embed(title=f"🔑 {bot_display_name} License Key Created!", color=discord.Color.green())
            embed.set_footer(text=f"{bot_display_name} • BR AUTH Manager", icon_url="https://br-auth-all-panels.vercel.app/favicon.ico")
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

    # Tree error handler for permission checks and command failures
    @bot.tree.error
    async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
        if isinstance(error, (discord.app_commands.MissingPermissions, discord.app_commands.CheckFailure)):
            embed = create_embed(
                title="⛔ Permission Denied",
                description="Is command ko chalane ke liye aapke paas **`BOT ACCESS`** Role ya Administrator permission honi chahiye.",
                color=discord.Color.red()
            )
        else:
            logger.error(f"[{name}] Command error: {error}")
            embed = create_embed(
                title="⚠️ Command Error",
                description=f"Command execute karte waqt error aaya: `{str(error)}`",
                color=discord.Color.gold()
            )
        try:
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, ephemeral=False)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=False)
        except Exception:
            pass

    # 24/7 Voice Channel Commands
    @bot.tree.command(name="joinvc", description=f"Make {name} join a Voice Channel 24/7")
    @discord.app_commands.describe(channel="Select Voice Channel (Optional if you are currently sitting in VC)")
    async def joinvc(interaction: discord.Interaction, channel: Optional[Union[discord.VoiceChannel, discord.StageChannel]] = None):
        try:
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=False)
        except Exception:
            pass

        if not check_user_access(interaction):
            embed = create_embed(
                title="⛔ Permission Denied",
                description="Is command ko chalane ke liye aapke paas **`BOT ACCESS`** Role ya Administrator permission honi chahiye.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=False)
            return

        target_channel = channel
        if not target_channel:
            if isinstance(interaction.user, discord.Member) and interaction.user.voice:
                target_channel = interaction.user.voice.channel

        if not target_channel:
            embed = create_embed(
                title="❌ Voice Channel Not Found",
                description="Kripya pehle kisi Voice Channel me join hon ya command me `channel` select karein.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=False)
            return

        try:
            guild = interaction.guild
            if not guild:
                embed = create_embed(title="❌ Server Only", description="Is command ko server me chalayein.", color=discord.Color.red())
                await interaction.followup.send(embed=embed, ephemeral=False)
                return

            voice_client = guild.voice_client
            if voice_client:
                if voice_client.channel and voice_client.channel.id == target_channel.id:
                    embed = create_embed(
                        title="🔊 Already Connected in VC",
                        description=f"Bot already **{target_channel.mention}** me connected hai (24/7 Mode).",
                        color=discord.Color.blue()
                    )
                    await interaction.followup.send(embed=embed, ephemeral=False)
                    return
                else:
                    await voice_client.move_to(target_channel)
            else:
                await target_channel.connect(reconnect=True, self_deaf=True)

            bot_display_name = interaction.client.user.name if interaction.client.user else name
            embed = create_embed(
                title=f"🔊 {bot_display_name} Joined Voice Channel!",
                description=f"Bot successfully **{target_channel.mention}** me join ho gaya hai aur **24/7** connected rahega!",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed, ephemeral=False)
        except Exception as e:
            embed = create_embed(
                title="❌ VC Join Failed",
                description=f"Voice channel join karte waqt error aaya: `{str(e)}`\nMake sure bot has `Connect` & `Speak` permissions in VC!",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=False)

    @bot.tree.command(name="leavevc", description=f"Disconnect {name} from Voice Channel")
    async def leavevc(interaction: discord.Interaction):
        try:
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=False)
        except Exception:
            pass

        if not check_user_access(interaction):
            embed = create_embed(
                title="⛔ Permission Denied",
                description="Is command ko chalane ke liye aapke paas **`BOT ACCESS`** Role ya Administrator permission honi chahiye.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=False)
            return

        guild = interaction.guild
        voice_client = guild.voice_client if guild else None

        if voice_client:
            vc_name = voice_client.channel.name if voice_client.channel else "VC"
            await voice_client.disconnect(force=True)
            bot_display_name = interaction.client.user.name if interaction.client.user else name
            embed = create_embed(
                title=f"🔇 {bot_display_name} Disconnected",
                description=f"Bot **{vc_name}** Voice Channel se disconnect ho gaya hai.",
                color=discord.Color.gold()
            )
            await interaction.followup.send(embed=embed, ephemeral=False)
        else:
            embed = create_embed(
                title="❌ Not in Voice Channel",
                description="Bot filhal kisi Voice Channel me connected nahi hai.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=False)

    return bot, token


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


async def self_ping_keep_alive():
    await asyncio.sleep(10)
    render_url = os.environ.get("RENDER_EXTERNAL_URL", "")
    port = os.environ.get("PORT", "8080")
    urls_to_ping = ["http://127.0.0.1:" + str(port) + "/health"]
    if render_url:
        urls_to_ping.append(render_url.rstrip("/") + "/health")
    
    import aiohttp
    async with aiohttp.ClientSession() as session:
        while True:
            await asyncio.sleep(240)  # Ping every 4 minutes to stay awake
            for u in urls_to_ping:
                try:
                    async with session.get(u, timeout=10) as resp:
                        pass
                except Exception:
                    pass


async def main():
    logger.info("Starting Multi-Bot Runner for all 3 Discord Bots...")
    
    # Start Web Health Server for Cloud Platforms (Render/Railway/etc.)
    try:
        await start_web_health_server()
    except Exception as e:
        logger.warning(f"Could not start web server: {e}")

    # Launch background keep-alive self ping loop
    asyncio.create_task(self_ping_keep_alive())

    tasks = []
    for b_config in BOTS_CONFIG:
        if not b_config["token"]:
            logger.error(f"Missing token for {b_config['name']}. Please set Environment Variable.")
            continue
        bot_obj, token = create_bot_instance(b_config)
        tasks.append(bot_obj.start(token))

    if tasks:
        await asyncio.gather(*tasks)
    else:
        logger.error("No bot tokens configured. Exiting.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Multi-Bot Runner stopped.")
