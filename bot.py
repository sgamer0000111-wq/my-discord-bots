import sys
import logging
import discord
from discord import app_commands
from discord.ext import commands

import config
from keyauth_api import KeyAuthSellerAPI

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("KeyAuthBot")

# Validate configuration
missing_vars = config.validate_config()
if missing_vars:
    logger.warning(
        f"Missing or default environment variables found: {', '.join(missing_vars)}. "
        "Please fill in .env file before executing."
    )

# Instantiate KeyAuth API Client
keyauth = KeyAuthSellerAPI(seller_key=config.KEYAUTH_SELLER_KEY, api_url=config.KEYAUTH_API_URL)

# Initialize Bot with default intents (No privileged intents required)
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Helper function to generate standardized Embeds
def create_embed(title: str, description: str = "", color: discord.Color = discord.Color.blue()) -> discord.Embed:
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text="X CHEAT SILENT MAX • BR AUTH Manager", icon_url="https://br-auth-all-panels.vercel.app/favicon.ico")
    return embed


@bot.event
async def on_ready():
    logger.info(f"Bot logged in as {bot.user} (ID: {bot.user.id})")
    
    try:
        # Clear previous per-guild overrides to reset Discord permissions cache
        for guild in bot.guilds:
            try:
                bot.tree.clear_commands(guild=guild)
                await bot.tree.sync(guild=guild)
            except Exception:
                pass

        synced_global = await bot.tree.sync()
        logger.info(f"Synced {len(synced_global)} global slash command(s).")

        for guild in bot.guilds:
            try:
                bot.tree.copy_global_to(guild=guild)
                synced_guild = await bot.tree.sync(guild=guild)
                logger.info(f"Instantly synced {len(synced_guild)} command(s) to server: {guild.name} (ID: {guild.id})")
            except Exception as ge:
                logger.warning(f"Could not sync to server {guild.id}: {ge}")

    except Exception as e:
        logger.error(f"Failed to sync slash commands: {e}")

    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="X CHEAT SILENT MAX | /createkey"
        )
    )


@bot.event
async def on_guild_join(guild: discord.Guild):
    logger.info(f"Bot joined new server: {guild.name} (ID: {guild.id})")
    try:
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)
        logger.info(f"Instantly synced {len(synced)} command(s) to new server: {guild.name}")
    except Exception as e:
        logger.error(f"Failed to sync on guild join: {e}")


# Role / Permission Check Helper
def check_user_access(interaction_or_user) -> bool:
    user = getattr(interaction_or_user, "user", interaction_or_user)
    if not isinstance(user, discord.Member):
        return True
    if user.guild_permissions.administrator:
        return True
    
    # Flexible role checking for BOT ACCESS or any role containing bot/access/seller/reseller/staff
    for r in getattr(user, "roles", []):
        name = r.name.lower().strip()
        if any(keyword in name for keyword in ["bot", "access", "seller", "reseller", "manager", "admin", "staff"]):
            return True
    return False


def has_bot_access():
    async def predicate(interaction: discord.Interaction) -> bool:
        return check_user_access(interaction)
    return app_commands.check(predicate)


# Tree error handler for permission checks
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, (app_commands.MissingPermissions, app_commands.CheckFailure)):
        embed = create_embed(
            title="⛔ Permission Denied",
            description="Is command ko run karne ke liye aapke paas **`BOT ACCESS`** Role ya Administrator permission honi chahiye.",
            color=discord.Color.red()
        )
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=False)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=False)
    else:
        logger.error(f"Command error: {error}")
        embed = create_embed(
            title="⚠️ Command Error",
            description=f"An unexpected error occurred: `{str(error)}`",
            color=discord.Color.gold()
        )
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)


# --- SLASH COMMANDS ---

@bot.tree.command(name="ping", description="Check bot latency and connectivity")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    embed = create_embed(
        title="🏓 Pong!",
        description=f"Bot Latency: **{latency}ms**",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


async def _handle_genkey(
    interaction: discord.Interaction,
    days: int
):
    await interaction.response.defer(ephemeral=False)
    note_str = f"Created via Discord by {interaction.user}"
    res = await keyauth.add_key(expiry=days, mask="XXXXXX-XXXXXX-XXXXXX", level=1, amount=1, note=note_str)

    if res.get("success"):
        key_data = res.get("key") or res.get("keys") or res.get("message")
        
        embed = create_embed(
            title="🔑 BR AUTH License Key Created!",
            color=discord.Color.green()
        )
        if isinstance(key_data, list):
            keys_str = "\n".join([f"`{k}`" for k in key_data])
            embed.add_field(name=f"Generated Keys ({len(key_data)})", value=keys_str, inline=False)
        else:
            embed.add_field(name="License Key", value=f"```\n{key_data}\n```", inline=False)

        expiry_label = "Lifetime (Unlimited)" if days >= 9999 else f"{days} Days"
        embed.add_field(name="Duration", value=expiry_label, inline=True)
        embed.add_field(name="Created By", value=interaction.user.mention, inline=False)

        await interaction.followup.send(embed=embed, ephemeral=False)
    else:
        msg = res.get("message", "Failed to generate key.")
        embed = create_embed(title="❌ Key Generation Failed", description=msg, color=discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=False)


DAYS_CHOICES = [
    app_commands.Choice(name="1 Day", value=1),
    app_commands.Choice(name="7 Days", value=7),
    app_commands.Choice(name="30 Days", value=30),
    app_commands.Choice(name="Lifetime", value=9999),
]

@bot.tree.command(name="createkey", description="Create a new BR AUTH license key")
@app_commands.describe(
    days="Select Duration (1 Day, 7 Days, 30 Days, Lifetime)"
)
@app_commands.choices(days=DAYS_CHOICES)
@has_bot_access()
async def createkey(
    interaction: discord.Interaction,
    days: app_commands.Choice[int]
):
    await _handle_genkey(interaction, days.value)


@bot.tree.command(name="genkey", description="Create a new BR AUTH license key")
@app_commands.describe(
    days="Select Duration (1 Day, 7 Days, 30 Days, Lifetime)"
)
@app_commands.choices(days=DAYS_CHOICES)
@has_bot_access()
async def genkey(
    interaction: discord.Interaction,
    days: app_commands.Choice[int]
):
    await _handle_genkey(interaction, days.value)


@bot.tree.command(name="generatekey", description="Create a new BR AUTH license key")
@app_commands.describe(
    days="Select Duration (1 Day, 7 Days, 30 Days, Lifetime)"
)
@app_commands.choices(days=DAYS_CHOICES)
@has_bot_access()
async def generatekey(
    interaction: discord.Interaction,
    days: app_commands.Choice[int]
):
    await _handle_genkey(interaction, days.value)


@bot.tree.command(name="keyinfo", description="Check details of a BR AUTH license key")
@app_commands.describe(key="The license key to inspect")
@has_bot_access()
async def keyinfo(interaction: discord.Interaction, key: str):
    await interaction.response.defer(ephemeral=True)
    res = await keyauth.get_key_info(key=key)

    if res.get("success"):
        embed = create_embed(title="🔍 License Key Information", color=discord.Color.blue())
        embed.add_field(name="Key", value=f"`{key}`", inline=False)
        
        for k, v in res.items():
            if k not in ["success", "message"]:
                embed.add_field(name=k.capitalize(), value=str(v) if v else "N/A", inline=True)
                
        await interaction.followup.send(embed=embed, ephemeral=True)
    else:
        msg = res.get("message", "Key not found or invalid.")
        embed = create_embed(title="❌ Key Search Failed", description=msg, color=discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=True)


@bot.tree.command(name="delkey", description="Delete a license key from BR AUTH")
@app_commands.describe(key="The license key to delete")
@has_bot_access()
async def delkey(interaction: discord.Interaction, key: str):
    await interaction.response.defer(ephemeral=True)
    res = await keyauth.delete_key(key=key)

    if res.get("success"):
        embed = create_embed(
            title="🗑️ Key Deleted",
            description=f"Key `{key}` has been successfully removed.",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
    else:
        msg = res.get("message", "Unable to delete key.")
        embed = create_embed(title="❌ Deletion Failed", description=msg, color=discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=True)


@bot.tree.command(name="resethwid", description="Reset Hardware ID (HWID) for a user")
@app_commands.describe(username="Username to reset HWID for")
@has_bot_access()
async def resethwid(interaction: discord.Interaction, username: str):
    await interaction.response.defer(ephemeral=True)
    res = await keyauth.reset_hwid(username=username)

    if res.get("success"):
        embed = create_embed(
            title="🔄 HWID Reset Successful",
            description=f"User **{username}** ka Hardware ID (HWID) reset kar diya gaya hai.",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
    else:
        msg = res.get("message", "Failed to reset HWID.")
        embed = create_embed(title="❌ HWID Reset Failed", description=msg, color=discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=True)


@bot.tree.command(name="userinfo", description="Get detailed user profile from BR AUTH")
@app_commands.describe(username="Username")
@has_bot_access()
async def userinfo(interaction: discord.Interaction, username: str):
    await interaction.response.defer(ephemeral=True)
    res = await keyauth.get_user_info(username=username)

    if res.get("success"):
        embed = create_embed(title=f"👤 User Profile: {username}", color=discord.Color.purple())
        for k, v in res.items():
            if k not in ["success", "message"]:
                embed.add_field(name=k.capitalize(), value=str(v) if v else "N/A", inline=True)
        await interaction.followup.send(embed=embed, ephemeral=True)
    else:
        msg = res.get("message", "User not found.")
        embed = create_embed(title="❌ User Not Found", description=msg, color=discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=True)


@bot.tree.command(name="banuser", description="Ban a BR AUTH user")
@app_commands.describe(username="Username to ban", reason="Reason for banning")
@has_bot_access()
async def banuser(interaction: discord.Interaction, username: str, reason: str = "Banned via Discord Bot"):
    await interaction.response.defer(ephemeral=True)
    res = await keyauth.ban_user(username=username, reason=reason)

    if res.get("success"):
        embed = create_embed(
            title="🔨 User Banned",
            description=f"User **{username}** ko ban kar diya gaya hai.\n**Reason:** {reason}",
            color=discord.Color.dark_red()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
    else:
        msg = res.get("message", "Failed to ban user.")
        embed = create_embed(title="❌ Ban Failed", description=msg, color=discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=True)


@bot.tree.command(name="unbanuser", description="Unban a BR AUTH user")
@app_commands.describe(username="Username to unban")
@has_bot_access()
async def unbanuser(interaction: discord.Interaction, username: str):
    await interaction.response.defer(ephemeral=True)
    res = await keyauth.unban_user(username=username)

    if res.get("success"):
        embed = create_embed(
            title="🔓 User Unbanned",
            description=f"User **{username}** ka ban remove kar diya gaya hai.",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
    else:
        msg = res.get("message", "Failed to unban user.")
        embed = create_embed(title="❌ Unban Failed", description=msg, color=discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=True)


# --- INTERACTIVE MODAL & PANEL ---

class CreateKeyModal(discord.ui.Modal, title="🔑 Create BR AUTH License Key"):
    days_input = discord.ui.TextInput(
        label="Duration Days (1, 7, 30, 9999=Lifetime)",
        default="30",
        placeholder="1, 7, 30, or 9999",
        required=True,
        max_length=5
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            days = int(self.days_input.value.strip())
        except ValueError:
            embed = create_embed(title="❌ Invalid Duration", description="Duration Days me valid number enter karein (1, 7, 30, 9999).", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await _handle_genkey(
            interaction=interaction,
            days=days
        )


class ControlPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔑 Create Key", style=discord.ButtonStyle.success, custom_id="btn_create_key")
    async def btn_create_key(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not check_user_access(interaction):
            embed = create_embed(title="⛔ Permission Denied", description="Is action ke liye Administrator permission ya **`BOT ACCESS`** Role honi chahiye.", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        await interaction.response.send_modal(CreateKeyModal())

    @discord.ui.button(label="📊 App Stats", style=discord.ButtonStyle.primary, custom_id="btn_stats")
    async def btn_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not check_user_access(interaction):
            embed = create_embed(title="⛔ Permission Denied", description="Is action ke liye Administrator permission ya **`BOT ACCESS`** Role honi chahiye.", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        res = await keyauth.get_stats()
        if res.get("success"):
            embed = create_embed(title="📊 BR AUTH Statistics", color=discord.Color.gold())
            for k, v in res.items():
                if k not in ["success", "message"]:
                    embed.add_field(name=k.replace('_', ' ').title(), value=str(v), inline=True)
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            msg = res.get("message", "Failed to fetch stats.")
            embed = create_embed(title="❌ Stats Unavailable", description=msg, color=discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)


@bot.tree.command(name="panel", description="Open interactive Admin Control Panel with buttons")
@has_bot_access()
async def panel(interaction: discord.Interaction):
    embed = create_embed(
        title="🛠️ BR AUTH Admin Control Panel",
        description="Niche diye gaye buttons se direct keys create karein aur statistics dekhein:",
        color=discord.Color.dark_theme()
    )
    await interaction.response.send_message(embed=embed, view=ControlPanelView(), ephemeral=False)


if __name__ == "__main__":
    if not config.DISCORD_TOKEN or config.DISCORD_TOKEN == "YOUR_DISCORD_BOT_TOKEN_HERE":
        logger.error("Error: DISCORD_TOKEN is missing or not configured in .env file.")
        sys.exit(1)
    
    logger.info("Starting KeyAuth Discord Bot...")
    bot.run(config.DISCORD_TOKEN)
