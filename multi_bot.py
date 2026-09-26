import asyncio
import logging
import sys
import os
import shutil
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
    },
    {
        "name": "SILENT KILLER",
        "token": clean_val(os.environ.get("BOT4_TOKEN", "")),
        "seller_key": clean_val(os.environ.get("BOT4_SELLER_KEY", "bot_br_live_6b917f44fde2f98eb2180746"))
    },
    {
        "name": "X CHEAT AUTH SYSTEM",
        "token": clean_val(os.environ.get("BOT5_TOKEN", "")),
        "seller_key": clean_val(os.environ.get("BOT5_SELLER_KEY", "bot_br_live_99de43b1a40523205cde54f0"))
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
    elif bot_id == 1551051243542151299:
        return clean_val(os.environ.get("BOT4_SELLER_KEY", "bot_br_live_6b917f44fde2f98eb2180746"))
    elif bot_id == 1548191060268941415:
        return clean_val(os.environ.get("BOT5_SELLER_KEY", "bot_br_live_99de43b1a40523205cde54f0"))

    uname = getattr(bot_user, "name", "").upper()
    if "INTERNAL" in uname:
        return clean_val(os.environ.get("BOT3_SELLER_KEY", "bot_br_live_ea8e146eeeb0e3f97192aa9c"))
    elif "COVER" in uname:
        return clean_val(os.environ.get("BOT2_SELLER_KEY", "bot_br_live_1017ee6a4b8ea826564f58f4"))
    elif "KILLER" in uname:
        return clean_val(os.environ.get("BOT4_SELLER_KEY", "bot_br_live_6b917f44fde2f98eb2180746"))
    elif "AUTH SYSTEM" in uname or "AUTH" in uname:
        return clean_val(os.environ.get("BOT5_SELLER_KEY", "bot_br_live_99de43b1a40523205cde54f0"))
    elif "SILENT" in uname or "MAX" in uname:
        return clean_val(os.environ.get("BOT1_SELLER_KEY", "bot_br_live_8c874050bd20af61e0126617"))
    elif "BOT 4" in uname or "BOT4" in uname:
        return clean_val(os.environ.get("BOT4_SELLER_KEY", "bot_br_live_6b917f44fde2f98eb2180746"))
    elif "BOT 5" in uname or "BOT5" in uname:
        return clean_val(os.environ.get("BOT5_SELLER_KEY", "bot_br_live_99de43b1a40523205cde54f0"))
    return fallback_key


def load_opus_lib():
    if discord.opus.is_loaded():
        return True
    import ctypes.util
    possible_paths = []
    try:
        discord_bin = os.path.join(os.path.dirname(discord.__file__), 'bin')
        possible_paths.append(os.path.join(discord_bin, 'libopus-0.x64.dll'))
        possible_paths.append(os.path.join(discord_bin, 'libopus-0.x86.dll'))
    except Exception:
        pass
    for name in ['opus', 'libopus', 'libopus.so.0', 'libopus.so', 'libopus-0', 'opus.dll']:
        found = ctypes.util.find_library(name)
        if found:
            possible_paths.append(found)
        possible_paths.append(name)
    for path in possible_paths:
        try:
            if path and (os.path.exists(path) or not os.path.isabs(path)):
                discord.opus.load_opus(path)
                if discord.opus.is_loaded():
                    logger.info(f"Successfully loaded Opus library from: {path}")
                    return True
        except Exception:
            continue
    logger.warning("Could not load Opus library! Voice audio playback may fail.")
    return False

load_opus_lib()

GLOBAL_BOT_INSTANCES = {}
SPEECH_LOCK = asyncio.Lock()

def ensure_tts_audio_files():
    try:
        if not os.path.exists("audio_internal.mp3") or not os.path.exists("audio_cover.mp3") or not os.path.exists("audio_silent.mp3"):
            import edge_tts
            async def _gen():
                if not os.path.exists("audio_internal.mp3"):
                    await edge_tts.Communicate("Welcome sir, how can I help you?", "en-US-AvaNeural").save("audio_internal.mp3")
                if not os.path.exists("audio_cover.mp3"):
                    await edge_tts.Communicate("Should I call any staff?", "en-US-EmmaNeural").save("audio_cover.mp3")
                if not os.path.exists("audio_silent.mp3"):
                    await edge_tts.Communicate("If you want to buy anything, I can call the owner.", "en-GB-SoniaNeural").save("audio_silent.mp3")
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(_gen())
                else:
                    asyncio.run(_gen())
            except Exception:
                asyncio.run(_gen())
    except Exception:
        try:
            from gtts import gTTS
            if not os.path.exists("audio_internal.mp3"):
                gTTS("Welcome sir, how can I help you?", lang="en", tld="co.uk").save("audio_internal.mp3")
            if not os.path.exists("audio_cover.mp3"):
                gTTS("Should I call any staff?", lang="en", tld="co.uk").save("audio_cover.mp3")
            if not os.path.exists("audio_silent.mp3"):
                gTTS("If you want to buy anything, I can call the owner.", lang="en", tld="co.uk").save("audio_silent.mp3")
        except Exception as e:
            logger.warning(f"Could not generate TTS files: {e}")

FFMPEG_EXECUTABLE_PATH = None

def get_ffmpeg_executable() -> str:
    global FFMPEG_EXECUTABLE_PATH
    if FFMPEG_EXECUTABLE_PATH and os.path.exists(FFMPEG_EXECUTABLE_PATH):
        return FFMPEG_EXECUTABLE_PATH
    sys_ffmpeg = shutil.which("ffmpeg")
    if sys_ffmpeg:
        FFMPEG_EXECUTABLE_PATH = sys_ffmpeg
        return FFMPEG_EXECUTABLE_PATH
    try:
        import static_ffmpeg.run
        ffmpeg_exe, _ = static_ffmpeg.run.get_or_fetch_platform_executables_else_raise()
        if ffmpeg_exe and os.path.exists(ffmpeg_exe):
            FFMPEG_EXECUTABLE_PATH = ffmpeg_exe
            return FFMPEG_EXECUTABLE_PATH
    except Exception as e:
        logger.warning(f"Could not resolve static_ffmpeg path: {e}")
    return "ffmpeg"


def find_bot_for_keyword(keyword: str):
    for b_id, b_inst in GLOBAL_BOT_INSTANCES.items():
        if b_inst and b_inst.user and keyword.upper() in b_inst.user.name.upper():
            return b_inst
    return None

async def play_audio_for_bot_keyword(keyword: str, guild: discord.Guild, audio_file: str, target_channel: Optional[discord.VoiceChannel] = None):
    if not os.path.exists(audio_file):
        logger.warning(f"Audio file missing: {audio_file}")
        return
    
    load_opus_lib()
    
    bot_inst = find_bot_for_keyword(keyword)
    if not bot_inst:
        for b_id, b_inst in GLOBAL_BOT_INSTANCES.items():
            if b_inst:
                g = b_inst.get_guild(guild.id)
                if g and g.voice_client and g.voice_client.is_connected():
                    bot_inst = b_inst
                    break

    if not bot_inst:
        logger.warning(f"No active bot found for keyword '{keyword}'")
        return

    g = bot_inst.get_guild(guild.id)
    if not g:
        logger.warning(f"Bot {bot_inst.user} not found in guild {guild.name}")
        return

    vc = g.voice_client
    if not vc or not vc.is_connected():
        if target_channel:
            try:
                logger.info(f"[{bot_inst.user.name}] Connecting to VC: {target_channel.name}")
                vc = await target_channel.connect(reconnect=True, self_deaf=False)
                bot_inst.saved_vc_id = target_channel.id
            except Exception as e:
                logger.warning(f"[{bot_inst.user.name}] Could not connect to VC: {e}")
                return
        else:
            logger.warning(f"Bot {bot_inst.user} is not in VC for guild {guild.name}")
            return

    try:
        logger.info(f"[{bot_inst.user.name}] Playing audio file: {audio_file}")
        if vc.is_playing():
            vc.stop()

        ffmpeg_exe = get_ffmpeg_executable()
        audio_source = discord.FFmpegPCMAudio(audio_file, executable=ffmpeg_exe)
        vc.play(audio_source)

        while vc.is_playing():
            await asyncio.sleep(0.3)
        await asyncio.sleep(0.6)
    except Exception as ex:
        logger.error(f"Audio playback error for bot {bot_inst.user}: {ex}")

async def handle_vc_welcome_sequence(guild: discord.Guild, channel: discord.VoiceChannel):
    async with SPEECH_LOCK:
        logger.info(f"Triggering Girl Voice Welcome Dialogue in VC: {channel.name}")
        ensure_tts_audio_files()
        await asyncio.sleep(0.6)

        # 1. Bot 3 (INTERNAL) speaks: "Welcome sir, how can I help you?"
        await play_audio_for_bot_keyword("INTERNAL", guild, "audio_internal.mp3", target_channel=channel)

        # 2. Bot 2 (COVER) speaks: "Should I call any staff?"
        await play_audio_for_bot_keyword("COVER", guild, "audio_cover.mp3", target_channel=channel)

        # 3. Bot 1 (SILENT MAX) speaks: "If you want to buy anything, I can call the owner."
        await play_audio_for_bot_keyword("SILENT", guild, "audio_silent.mp3", target_channel=channel)


async def vc_auto_reconnect_loop(bot, bot_name: str):
    await asyncio.sleep(10)
    while not bot.is_closed():
        await asyncio.sleep(15)
        vc_id = getattr(bot, "saved_vc_id", None) or os.environ.get("VC_CHANNEL_ID")
        if vc_id:
            try:
                ch_id = int(vc_id)
                channel = bot.get_channel(ch_id)
                if not channel:
                    for g in bot.guilds:
                        ch = g.get_channel(ch_id)
                        if ch:
                            channel = ch
                            break
                
                if channel and isinstance(channel, (discord.VoiceChannel, discord.StageChannel)):
                    guild = channel.guild
                    voice_client = guild.voice_client
                    if not voice_client or not voice_client.is_connected():
                        logger.info(f"[{bot_name}] Auto-reconnecting 24/7 to VC: {channel.name}")
                        await channel.connect(reconnect=True, self_deaf=False)
            except Exception as ex:
                logger.debug(f"[{bot_name}] VC Auto-Reconnect error: {ex}")


def create_bot_instance(bot_info: dict):
    token = bot_info["token"]
    name = bot_info["name"]
    seller_key = bot_info["seller_key"]

    intents = discord.Intents.default()
    bot = commands.Bot(command_prefix="!", intents=intents)

    @bot.event
    async def on_ready():
        logger.info(f"[{name}] Logged in as {bot.user} (ID: {bot.user.id})")
        if bot.user:
            GLOBAL_BOT_INSTANCES[bot.user.id] = bot
            
        if not getattr(bot, "auto_vc_task_started", False):
            bot.auto_vc_task_started = True
            asyncio.create_task(vc_auto_reconnect_loop(bot, name))

        try:
            for guild in bot.guilds:
                try:
                    bot.tree.copy_global_to(guild=guild)
                    await bot.tree.sync(guild=guild)
                except Exception as ex:
                    logger.debug(f"[{name}] Guild sync warning: {ex}")

            synced_global = await bot.tree.sync()
            logger.info(f"[{name}] Synced {len(synced_global)} slash command(s) for guild and global.")
        except Exception as e:
            logger.error(f"[{name}] Sync error: {e}")

        await bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{bot.user.name if bot.user else name} | /createkey"
            )
        )

    @bot.event
    async def on_voice_state_update(member, before, after):
        if not member.bot and before.channel != after.channel and after.channel is not None:
            if bot.user:
                GLOBAL_BOT_INSTANCES[bot.user.id] = bot
            
            uname = bot.user.name.upper() if bot.user else ""
            has_internal_bot = any("INTERNAL" in (b.user.name.upper() if b.user else "") for b in GLOBAL_BOT_INSTANCES.values())
            
            should_trigger = False
            if has_internal_bot and ("INTERNAL" in uname or bot.user.id == 1548212884843274240):
                should_trigger = True
            elif not has_internal_bot and GLOBAL_BOT_INSTANCES and list(GLOBAL_BOT_INSTANCES.keys())[0] == bot.user.id:
                should_trigger = True

            if should_trigger:
                logger.info(f"[{bot.user.name if bot.user else name}] Voice state update: {member.display_name} joined {after.channel.name}")
                asyncio.create_task(handle_vc_welcome_sequence(member.guild, after.channel))

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

    @bot.tree.command(name="joinvc", description=f"Make {name} join a Voice Channel 24/7")
    @discord.app_commands.describe(channel="Select Voice Channel (Optional if you are currently sitting in VC)")
    async def joinvc(interaction: discord.Interaction, channel: Optional[discord.VoiceChannel] = None):
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

        target_channel = None

        if channel and interaction.guild:
            resolved = interaction.guild.get_channel(channel.id)
            if isinstance(resolved, (discord.VoiceChannel, discord.StageChannel)):
                target_channel = resolved

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
                    bot.saved_vc_id = target_channel.id
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
                await target_channel.connect(reconnect=True, self_deaf=False)

            bot.saved_vc_id = target_channel.id
            bot_display_name = interaction.client.user.name if interaction.client.user else name
            embed = create_embed(
                title=f"🔊 {bot_display_name} Joined Voice Channel!",
                description=f"Bot successfully **{target_channel.mention}** me join ho gaya hai aur **24/7** connected rahega!",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed, ephemeral=False)

            if bot.user and ("INTERNAL" in bot.user.name.upper() or bot.user.id == 1548212884843274240):
                asyncio.create_task(handle_vc_welcome_sequence(guild, target_channel))
        except Exception as e:
            embed = create_embed(
                title="❌ VC Join Failed",
                description=f"Voice channel join karte waqt error aaya: `{str(e)}`\nMake sure bot has `Connect` & `Speak` permissions in VC!",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=False)

    @bot.tree.command(name="speakwelcome", description=f"Manually trigger Girl Voice Welcome Dialogue in VC")
    async def speakwelcome(interaction: discord.Interaction):
        try:
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=False)
        except Exception:
            pass

        if not check_user_access(interaction):
            embed = create_embed(title="⛔ Permission Denied", description="Is command ke liye **`BOT ACCESS`** Role ya Admin permission honi chahiye.", color=discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=False)
            return

        guild = interaction.guild
        if not guild:
            return

        vc = guild.voice_client
        if vc and vc.channel:
            bot_display_name = interaction.client.user.name if interaction.client.user else name
            embed = create_embed(
                title="🎙️ Girl Voice Dialogue Started",
                description=f"Teeno bots **{vc.channel.mention}** me 3-step sequential dialogue bol rahe hain!",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed, ephemeral=False)
            asyncio.create_task(handle_vc_welcome_sequence(guild, vc.channel))
        else:
            embed = create_embed(title="❌ Not Connected in VC", description="Pehle bot ko `/joinvc` se Voice Channel me join karayein.", color=discord.Color.red())
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
            bot.saved_vc_id = None
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
        return web.Response(text="OK - 5 Discord Bots Running 24/7", status=200)

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
            await asyncio.sleep(240)
            for u in urls_to_ping:
                try:
                    async with session.get(u, timeout=10) as resp:
                        pass
                except Exception:
                    pass


async def main():
    logger.info("Starting Multi-Bot Runner for Discord Bots...")
    
    try:
        await start_web_health_server()
    except Exception as e:
        logger.warning(f"Could not start web server: {e}")

    asyncio.create_task(self_ping_keep_alive())

    tasks = []
    for b_config in BOTS_CONFIG:
        if not b_config["token"]:
            logger.warning(f"[{b_config['name']}] Token not set in Environment Variables.")
            continue
        bot_obj, token = create_bot_instance(b_config)
        tasks.append(bot_obj.start(token))

    if tasks:
        logger.info(f"Successfully launched {len(tasks)} bot instance(s). Running 24/7...")
        await asyncio.gather(*tasks)
    else:
        logger.warning("No bot tokens set in Environment Variables. Web Health Server is running 24/7 on port 8080. Please add BOT1_TOKEN .. BOT5_TOKEN in Render Environment tab.")
        await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Multi-Bot Runner stopped.")
