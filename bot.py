import discord
from discord import app_commands
from discord.ext import commands
import os
from dotenv import load_dotenv
import logging

load_dotenv()

DAYS_CHOICES = [
    app_commands.Choice(name="1 Day", value=1),
    app_commands.Choice(name="7 Days", value=7),
    app_commands.Choice(name="30 Days", value=30),
    app_commands.Choice(name="Lifetime", value=99999),
]

def check_user_access(interaction: discord.Interaction) -> bool:
    if not interaction.guild:
        return True
    if isinstance(interaction.user, discord.Member):
        if interaction.user.guild_permissions.administrator:
            return True
        for role in interaction.user.roles:
            if role.name.upper() == "BOT ACCESS":
                return True
    return False

def has_bot_access():
    def predicate(interaction: discord.Interaction) -> bool:
        return check_user_access(interaction)
    return app_commands.check(predicate)

def create_embed(title: str, description: str = "", color: discord.Color = discord.Color.blue()) -> discord.Embed:
    embed = discord.Embed(title=title, description=description, color=color)
    return embed

async def _handle_genkey(interaction: discord.Interaction, days: int, prefix: str):
    pass

class ControlPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Gen 1 Day Key", style=discord.ButtonStyle.green, custom_id="btn_gen_1d")
    async def gen_1d(self, interaction: discord.Interaction, button: discord.ui.Button):
        await _handle_genkey(interaction, 1, "XCHEAT")

    @discord.ui.button(label="Gen 7 Days Key", style=discord.ButtonStyle.blurple, custom_id="btn_gen_7d")
    async def gen_7d(self, interaction: discord.Interaction, button: discord.ui.Button):
        await _handle_genkey(interaction, 7, "XCHEAT")

    @discord.ui.button(label="Gen 30 Days Key", style=discord.ButtonStyle.primary, custom_id="btn_gen_30d")
    async def gen_30d(self, interaction: discord.Interaction, button: discord.ui.Button):
        await _handle_genkey(interaction, 30, "XCHEAT")

    @discord.ui.button(label="Gen Lifetime Key", style=discord.ButtonStyle.red, custom_id="btn_gen_lt")
    async def gen_lt(self, interaction: discord.Interaction, button: discord.ui.Button):
        await _handle_genkey(interaction, 99999, "XCHEAT")
