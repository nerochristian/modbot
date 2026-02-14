# cogs/pets_cog.py
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone

from data.items import PET_TYPES
from views.pet_views import PetSelector
from services.pets_service import calculate_pet_level_from_xp, get_pet_buffs, calculate_total_buffs
from utils.format import money, progress_bar
from utils.checks import safe_defer, safe_reply
from views.v2_embed import apply_v2_embed_layout


class PetsCog(commands.Cog):
    """Pet ownership and management commands."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.command(name="adoptpet", description="🐾 Adopt a pet from the shop")
    @app_commands.describe(
        pet_type="Type of pet to adopt",
        name="Name for your pet"
    )
    @app_commands.choices(pet_type=[
        app_commands.Choice(name="🐕 Dog", value="dog"),
        app_commands.Choice(name="🐈 Cat", value="cat"),
        app_commands.Choice(name="🦜 Parrot", value="parrot"),
        app_commands.Choice(name="🐰 Rabbit", value="rabbit"),
        app_commands.Choice(name="🐹 Hamster", value="hamster"),
        app_commands.Choice(name="🐠 Fish", value="fish"),
        app_commands.Choice(name="🐉 Dragon", value="dragon"),
        app_commands.Choice(name="🔥 Phoenix", value="phoenix"),
    ])
    async def adoptpet(self, interaction: discord.Interaction, pet_type: str, name: str):
        await safe_defer(interaction)
        
        db = self.bot.db
        userid = str(interaction.user.id)
        u = db.getuser(userid)
        
        # Get pet data
        pet_data = PET_TYPES.get(pet_type)
        if not pet_data:
            return await safe_reply(interaction, content="❌ Invalid pet type!")
        
        # Check if can afford
        balance = int(u.get("balance", 0))
        price = pet_data["price"]
        
        if balance < price:
            return await safe_reply(
                interaction,
                content=f"❌ Not enough money! Need {money(price)}, you have {money(balance)}"
            )
        
        # Check name length
        if len(name) > 20:
            return await safe_reply(interaction, content="❌ Pet name must be 20 characters or less!")
        
        # Check pet limit (max 5 pets)
        current_pets = db.get_user_pets(userid)
        if len(current_pets) >= 5:
            return await safe_reply(interaction, content="❌ You already have 5 pets! (Max limit)")
        
        # Purchase pet
        db.removebalance(userid, price)
        pet_id = db.create_pet(userid, pet_type, name)
        
        # Get buffs
        buffs = get_pet_buffs(pet_type, 1)
        buff_text = []
        for buff_type, value in buffs.items():
            if value > 0:
                buff_text.append(f"• {buff_type.replace('_', ' ').title()}: +{value}%")
        
        embed = discord.Embed(
            title=f"{pet_data['emoji']} Pet Adopted!",
            description=(
                f"**Name:** {name}\n"
                f"**Type:** {pet_data['name']}\n"
                f"**Price:** {money(price)}\n\n"
                f"**Buffs:**\n" + ("\n".join(buff_text) if buff_text else "None")
            ),
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="📝 Description",
            value=pet_data["description"],
            inline=False
        )
        
        embed.set_footer(text="Use /pets to view all your pets • /feedpet, /playpet, /trainpet to interact!")
        
        await safe_reply(interaction, embed=embed)
    
    @app_commands.command(name="pets", description="🐾 View all your pets")
    async def pets(self, interaction: discord.Interaction):
        await safe_defer(interaction)
        
        db = self.bot.db
        userid = str(interaction.user.id)
        
        pets = db.get_user_pets(userid)
        
        if not pets:
            return await safe_reply(
                interaction,
                content="❌ You don't have any pets! Use `/adoptpet` to get one."
            )
        
        # Calculate total buffs
        total_buffs = calculate_total_buffs(pets)
        
        embed = discord.Embed(
            title=f"🐾 {interaction.user.display_name}'s Pets",
            description=f"**Total Pets:** {len(pets)}/5",
            color=discord.Color.blue()
        )
        
        for pet in pets:
            pet_data = PET_TYPES.get(pet["pet_type"], {})
            emoji = pet_data.get("emoji", "🐾")
            
            level = int(pet.get("level", 1))
            xp = int(pet.get("xp", 0))
            _, curr_xp, needed_xp = calculate_pet_level_from_xp(xp)
            
            hunger = int(pet.get("hunger", 100))
            happiness = int(pet.get("happiness", 100))
            is_alive = pet.get("is_alive", 1)
            
            status = "💀 Dead" if not is_alive else "✅ Alive"
            
            pet_info = (
                f"{emoji} **{pet['name']}** ({pet_data.get('name', 'Unknown')})\n"
                f"└ Level {level} | {status}\n"
                f"└ 🍗 {progress_bar(hunger, 100, 5)} {hunger}/100\n"
                f"└ 😊 {progress_bar(happiness, 100, 5)} {happiness}/100\n"
                f"└ ⭐ {progress_bar(curr_xp, needed_xp, 5)} {curr_xp}/{needed_xp}"
            )
            
            embed.add_field(
                name=f"{pet['name']}",
                value=pet_info,
                inline=False
            )
        
        # Show total buffs
        active_buffs = [f"{k.replace('_', ' ').title()}: +{v}%" for k, v in total_buffs.items() if v > 0]
        
        if active_buffs:
            embed.add_field(
                name="💎 Active Buffs",
                value="\n".join(active_buffs),
                inline=False
            )
        
        embed.set_footer(text="Use /feedpet, /playpet, /trainpet to interact with your pets!")
        
        await safe_reply(interaction, embed=embed)
    
    @app_commands.command(name="feedpet", description="🍖 Feed your pet to restore hunger")
    async def feedpet(self, interaction: discord.Interaction):
        await safe_defer(interaction)
        
        db = self.bot.db
        userid = str(interaction.user.id)
        
        pets = db.get_user_pets(userid)
        alive_pets = [p for p in pets if p.get("is_alive")]
        
        if not alive_pets:
            return await safe_reply(interaction, content="❌ You don't have any alive pets!")
        
        # Show pet selector
        view = PetSelector(self.bot, interaction.user, alive_pets, "feed")
        
        embed = discord.Embed(
            title="🍖 Feed Pet",
            description="Select a pet to feed:",
            color=discord.Color.blue()
        )
        
        apply_v2_embed_layout(view, embed=embed)
        await safe_reply(interaction, view=view)
    
    @app_commands.command(name="playpet", description="🎾 Play with your pet to boost happiness")
    async def playpet(self, interaction: discord.Interaction):
        await safe_defer(interaction)
        
        db = self.bot.db
        userid = str(interaction.user.id)
        
        pets = db.get_user_pets(userid)
        alive_pets = [p for p in pets if p.get("is_alive")]
        
        if not alive_pets:
            return await safe_reply(interaction, content="❌ You don't have any alive pets!")
        
        # Show pet selector
        view = PetSelector(self.bot, interaction.user, alive_pets, "play")
        
        embed = discord.Embed(
            title="🎾 Play with Pet",
            description="Select a pet to play with:",
            color=discord.Color.blue()
        )
        
        apply_v2_embed_layout(view, embed=embed)
        await safe_reply(interaction, view=view)
    
    @app_commands.command(name="trainpet", description="⚡ Train your pet to level it up")
    async def trainpet(self, interaction: discord.Interaction):
        await safe_defer(interaction)
        
        db = self.bot.db
        userid = str(interaction.user.id)
        
        pets = db.get_user_pets(userid)
        alive_pets = [p for p in pets if p.get("is_alive")]
        
        if not alive_pets:
            return await safe_reply(interaction, content="❌ You don't have any alive pets!")
        
        # Show pet selector
        view = PetSelector(self.bot, interaction.user, alive_pets, "train")
        
        embed = discord.Embed(
            title="⚡ Train Pet",
            description="Select a pet to train:\n\n**Training costs 20 energy (you) and 20 hunger (pet)**",
            color=discord.Color.blue()
        )
        
        apply_v2_embed_layout(view, embed=embed)
        await safe_reply(interaction, view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(PetsCog(bot))
