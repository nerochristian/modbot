import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
import discord
from core import Config
import aiohttp

from components_v2 import branded_panel_container, branded_notice_view

log = logging.getLogger(__name__)

async def call_deepseek(system_prompt: str, user_prompt: str) -> str:
    url = "https://modbot-app-u3zsw.ondigitalocean.app/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {Config.LLM_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "response_format": {"type": "json_object"}
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise RuntimeError(f"API Error {resp.status}: {text}")
            data = await resp.json()
            return data["choices"][0]["message"]["content"]

class SetupQuestion:
    def __init__(self, question: str, options: Optional[List[str]] = None):
        self.question = question
        self.options = options  # If None, open-ended

class SetupQuestionView(discord.ui.View):
    def __init__(self, options: List[str]):
        super().__init__(timeout=300)
        self.value = None
        for opt in options:
            btn = discord.ui.Button(label=opt, style=discord.ButtonStyle.primary, custom_id=opt)
            btn.callback = self.make_callback(opt)
            self.add_item(btn)

    def make_callback(self, opt: str):
        async def callback(interaction: discord.Interaction):
            self.value = opt
            await interaction.response.defer()
            self.stop()
        return callback

QUESTIONS = [
    SetupQuestion("How strict do you want the AutoMod to be overall?", ["Relaxed", "Standard", "Strict"]),
    SetupQuestion("Do you want to automatically timeout users for severe violations (like scams or dangerous links)?", ["Yes, timeout", "No, just warn"]),
    SetupQuestion("Should AutoMod filter out common profanity and bad words?", ["Yes", "No"]),
    SetupQuestion("What should happen if someone spams messages?", ["Timeout", "Warn", "Nothing"]),
    SetupQuestion("Any specific words or phrases you want to strictly ban? (Type them out, or type 'none')", None),
    SetupQuestion("Do you want to restrict links? If so, describe how (e.g. 'block all links except youtube', or 'block dangerous links only', or 'none').", None),
]

async def start_setup_wizard(cog, interaction: discord.Interaction) -> None:
    guild = interaction.guild
    
    await interaction.response.defer(ephemeral=True)

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }

    try:
        channel = await guild.create_text_channel("automod-setup", overwrites=overwrites)
    except discord.Forbidden:
        await interaction.followup.send("I don't have permission to create channels!")
        return

    await interaction.followup.send(f"Setup started in {channel.mention}!")

    intro_embed = discord.Embed(
        title="AutoMod Setup Wizard",
        description="Hello! Welcome to your server's AutoMod setup!\nI will ask you a series of questions to configure AutoMod perfectly for your server.",
        color=Config.COLOR_INFO
    )
    await channel.send(embed=intro_embed)

    answers = []

    def check(m):
        return m.author == interaction.user and m.channel == channel

    for q in QUESTIONS:
        embed = discord.Embed(description=q.question, color=0x2b2d31)
        
        if q.options:
            view = SetupQuestionView(q.options)
            msg = await channel.send(embed=embed, view=view)
            await view.wait()
            if view.value is None:
                await channel.send("Setup timed out.")
                return
            answers.append({"question": q.question, "answer": view.value})
            await msg.edit(view=None)
            await channel.send(f"**Selected:** {view.value}")
        else:
            await channel.send(embed=embed)
            try:
                msg = await cog.bot.wait_for("message", check=check, timeout=300)
                answers.append({"question": q.question, "answer": msg.content})
            except asyncio.TimeoutError:
                await channel.send("Setup timed out.")
                return

    await channel.send("Thank you! Generating your AutoMod configuration using AI...")

    system_prompt = """You are an expert Discord AutoMod configuration AI.
Based on the user's answers, generate a JSON object representing the exact AutoMod settings dictionary.
Return ONLY valid JSON.

Available settings keys:
automod_enabled (bool)
automod_links_mode ("dangerous", "allowlist", or null)
automod_punishment ("warn", "timeout", "kick", "ban")
automod_security_punishment ("warn", "timeout", "kick", "ban")
automod_mute_duration (int, seconds)
automod_badwords (list of strings)
automod_spam_threshold (int)
automod_spam_window (int)
automod_duplicate_threshold (int)
automod_duplicate_window (int)
automod_max_mentions (int)
automod_caps_percentage (int)
automod_caps_min_length (int)
automod_newaccount_days (int)

Produce a JSON object mapping these keys to the ideal values based on the questionnaire. Ensure you include all relevant keys."""

    user_prompt = "User's Answers:\n" + "\n".join([f"Q: {a['question']}\nA: {a['answer']}" for a in answers])

    try:
        response = await call_deepseek(system_prompt, user_prompt)
        settings_update = json.loads(response)
        
        def apply_update(settings: dict) -> None:
            settings.update(settings_update)
            settings["automod_enabled"] = True

        await cog._edit_settings(guild.id, apply_update)
        
        await channel.send("AutoMod setup complete! This channel will be deleted in 10 seconds.")
        await asyncio.sleep(10)
        await channel.delete()
        
    except Exception as e:
        log.exception("Error in automod setup")
        await channel.send("An error occurred while generating the setup. Please try again.")

async def handle_automod_change(cog, interaction: discord.Interaction, request: str) -> None:
    await interaction.response.defer(ephemeral=False, thinking=True)
    
    current_settings = await cog._get_settings(interaction.guild_id)
    safe_settings = {k: v for k, v in current_settings.items() if k.startswith("automod_")}

    system_prompt = """You are an expert Discord AutoMod configuration AI.
The user wants to change their AutoMod settings via natural language.
You will be provided the CURRENT settings JSON and the user's request.
Return a JSON object containing ONLY the keys that need to be updated and their new values.
Return ONLY valid JSON.

Available keys:
automod_enabled, automod_links_mode, automod_punishment, automod_security_punishment,
automod_mute_duration, automod_badwords, automod_spam_threshold, automod_spam_window,
automod_duplicate_threshold, automod_duplicate_window, automod_max_mentions,
automod_caps_percentage, automod_caps_min_length, automod_newaccount_days"""

    user_prompt = f"Current Settings:\n{json.dumps(safe_settings, indent=2)}\n\nUser Request: {request}"

    try:
        response = await call_deepseek(system_prompt, user_prompt)
        changes = json.loads(response)
        
        if not changes:
            await interaction.followup.send("I couldn't understand what to change.")
            return

        def apply_changes(settings: dict) -> None:
            settings.update(changes)

        await cog._edit_settings(interaction.guild_id, apply_changes)
        
        embed = discord.Embed(
            title="AutoMod Updated",
            description=f"Applied the following changes:\n```json\n{json.dumps(changes, indent=2)}\n```",
            color=Config.COLOR_SUCCESS
        )
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        log.exception("Error modifying automod settings")
        await interaction.followup.send("An error occurred while modifying the settings. Please try again.")
