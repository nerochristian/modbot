# views/pet_views.py
from __future__ import annotations

import discord
from typing import List, Dict, Any
import math

from data.items import PET_TYPES
from utils.format import money, progress_bar
from services.pets_service import calculate_pet_level_from_xp, get_pet_buffs


class PetSelector(discord.ui.LayoutView):
    """Select a pet to interact with."""
    
    def __init__(self, bot, user: discord.User, pets: List[Dict[str, Any]], action: str):
        super().__init__(timeout=60)
        self.bot = bot
        self.user = user
        self.pets = pets
        self.action = action
        
        # Add pet selection buttons
        for i, pet in enumerate(pets[:5]):  # Max 5 pets shown
            pet_data = PET_TYPES.get(pet["pet_type"], {})
            emoji = pet_data.get("emoji", "🐾")
            
            button = discord.ui.Button(
                style=discord.ButtonStyle.primary,
                emoji=emoji,
                label=pet["name"][:20],
                custom_id=f"pet_{i}"
            )
            button.callback = lambda inter, p=pet: self.select_pet(inter, p)
            self.add_item(button)
    
    async def select_pet(self, interaction: discord.Interaction, pet: Dict[str, Any]):
        """Handle pet selection."""
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("❌ Not your pets!", ephemeral=True)
        
        # Execute action
        if self.action == "feed":
            await self.feed_pet(interaction, pet)
        elif self.action == "play":
            await self.play_pet(interaction, pet)
        elif self.action == "train":
            await self.train_pet(interaction, pet)
    
    async def feed_pet(self, interaction: discord.Interaction, pet: Dict[str, Any]):
        """Feed the selected pet."""
        db = self.bot.db
        pet_id = pet["pet_id"]
        
        # Restore hunger
        new_hunger = min(100, int(pet.get("hunger", 0)) + 30)
        db.updatepet(pet_id, "hunger", new_hunger)
        
        pet_data = PET_TYPES.get(pet["pet_type"], {})
        
        embed = discord.Embed(
            title=f"{pet_data.get('emoji', '🐾')} Fed {pet['name']}!",
            description=f"**Hunger:** {progress_bar(new_hunger, 100, length=10)} +30",
            color=discord.Color.green()
        )
        
        await interaction.response.edit_message(embed=embed, view=None)
    
    async def play_pet(self, interaction: discord.Interaction, pet: Dict[str, Any]):
        """Play with the selected pet."""
        db = self.bot.db
        pet_id = pet["pet_id"]
        
        # Boost happiness
        new_happiness = min(100, int(pet.get("happiness", 0)) + 20)
        db.updatepet(pet_id, "happiness", new_happiness)
        
        # Small XP gain
        new_xp = int(pet.get("xp", 0)) + 5
        db.updatepet(pet_id, "xp", new_xp)
        
        level, curr_xp, needed_xp = calculate_pet_level_from_xp(new_xp)
        old_level = int(pet.get("level", 1))
        
        leveled_up = level > old_level
        if leveled_up:
            db.updatepet(pet_id, "level", level)
        
        pet_data = PET_TYPES.get(pet["pet_type"], {})
        
        embed = discord.Embed(
            title=f"{pet_data.get('emoji', '🐾')} Played with {pet['name']}!",
            description=(
                f"**Happiness:** {progress_bar(new_happiness, 100, length=10)} +20\n"
                f"**XP:** +5\n"
                f"{'🎉 **Level Up!**' if leveled_up else ''}"
            ),
            color=discord.Color.gold() if leveled_up else discord.Color.green()
        )
        
        if leveled_up:
            embed.add_field(
                name="Level Up!",
                value=f"**{pet['name']}** is now level {level}!",
                inline=False
            )
        
        await interaction.response.edit_message(embed=embed, view=None)
    
    async def train_pet(self, interaction: discord.Interaction, pet: Dict[str, Any]):
        """Train the selected pet."""
        db = self.bot.db
        userid = str(interaction.user.id)
        pet_id = pet["pet_id"]
        
        # Training costs energy (user) and hunger (pet)
        u = db.getuser(userid)
        user_energy = int(u.get("energy", 100))
        pet_hunger = int(pet.get("hunger", 100))
        
        if user_energy < 20:
            return await interaction.response.send_message(
                "❌ You need at least 20 energy to train your pet!",
                ephemeral=True
            )
        
        if pet_hunger < 30:
            return await interaction.response.send_message(
                f"❌ {pet['name']} is too hungry to train! Feed them first.",
                ephemeral=True
            )
        
        # Drain stats
        db.updatestat(userid, "energy", user_energy - 20)
        db.updatepet(pet_id, "hunger", pet_hunger - 20)
        
        # Give XP
        xp_gain = 15
        new_xp = int(pet.get("xp", 0)) + xp_gain
        db.updatepet(pet_id, "xp", new_xp)
        
        level, curr_xp, needed_xp = calculate_pet_level_from_xp(new_xp)
        old_level = int(pet.get("level", 1))
        
        leveled_up = level > old_level
        if leveled_up:
            db.updatepet(pet_id, "level", level)
        
        pet_data = PET_TYPES.get(pet["pet_type"], {})
        
        embed = discord.Embed(
            title=f"{pet_data.get('emoji', '🐾')} Trained {pet['name']}!",
            description=(
                f"**Pet XP:** +{xp_gain}\n"
                f"**Progress:** {progress_bar(curr_xp, needed_xp, length=10)}\n"
                f"**Level:** {level}\n\n"
                f"{'🎉 **Level Up!** Buffs increased!' if leveled_up else ''}"
            ),
            color=discord.Color.gold() if leveled_up else discord.Color.blue()
        )
        
        embed.set_footer(text="Training costs 20 energy (you) and 20 hunger (pet)")
        
        await interaction.response.edit_message(embed=embed, view=None)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user.id
