# views/crime_views.py

from __future__ import annotations

import discord
import random
import asyncio
from typing import Optional

from utils.format import money
from views.v2_embed import apply_v2_embed_layout


# ============= CONSTANTS =============

CRIME_COLORS = {
    "lockpick": 0xF59E0B,    # Amber
    "success": 0x22C55E,     # Green
    "fail": 0xEF4444,        # Red
    "progress": 0x3B82F6,    # Blue
}


# ============= LOCKPICK GAME =============

class LockpickGame(discord.ui.LayoutView):
    """Interactive lockpick minigame for robberies."""

    def __init__(
        self,
        attacker: discord.User,
        victim: discord.User,
        potential_steal: int,
        difficulty: int = 3
    ):
        super().__init__(timeout=30)
        self.attacker = attacker
        self.victim = victim
        self.potential_steal = potential_steal
        self.difficulty = difficulty

        # Generate random code (1-5 for each digit)
        self.code = [random.randint(1, 5) for _ in range(difficulty)]
        self.user_code = []
        self.attempts = 0
        self.max_attempts = difficulty + 2

        self.success = False
        self.failed = False
        self.start_time = None

        # Create buttons
        self._create_buttons()

    def _create_buttons(self):
        """Create number buttons."""
        for num in range(1, 6):
            button = LockpickButton(num, self)
            self.add_item(button)

        # Add reset button
        reset_btn = discord.ui.Button(
            style=discord.ButtonStyle.secondary,
            emoji="🔄",
            label="Reset",
            row=1
        )
        reset_btn.callback = self.reset_code
        self.add_item(reset_btn)

        # Add hint button
        hint_btn = discord.ui.Button(
            style=discord.ButtonStyle.secondary,
            emoji="💡",
            label="Hint",
            row=1
        )
        hint_btn.callback = self.get_hint
        self.add_item(hint_btn)

    def _get_digit_emoji(self, digit: int) -> str:
        """Get emoji for digit."""
        emojis = {
            1: "1️⃣",
            2: "2️⃣",
            3: "3️⃣",
            4: "4️⃣",
            5: "5️⃣"
        }
        return emojis.get(digit, "❓")

    def _create_progress_bar(self) -> str:
        """Create visual progress bar."""
        filled = len(self.user_code)
        empty = self.difficulty - filled
        return "🟦" * filled + "⬜" * empty

    def create_game_embed(self) -> discord.Embed:
        """Create the game embed."""
        # Build visual display with better formatting
        display_code = []
        hints = []

        for i in range(self.difficulty):
            if i < len(self.user_code):
                digit = self.user_code[i]
                digit_emoji = self._get_digit_emoji(digit)
                
                if digit == self.code[i]:
                    display_code.append(f"🟢 {digit_emoji}")
                    hints.append("✅")
                else:
                    display_code.append(f"🔴 {digit_emoji}")
                    hints.append("❌")
            else:
                display_code.append("⬜ ❓")
                hints.append("⏳")

        # Calculate progress percentage
        progress_pct = (len(self.user_code) / self.difficulty) * 100

        embed = discord.Embed(
            title="🔓 Lockpick Challenge",
            description=(
                f"**Target:** {self.victim.mention}\n"
                f"**Potential Steal:** 💰 {money(self.potential_steal)}\n"
                f"**Difficulty:** {self.difficulty} digits\n"
            ),
            color=CRIME_COLORS["lockpick"]
        )

        # Code display
        embed.add_field(
            name="🔐 Lock Combination",
            value=f"``````",
            inline=False
        )

        # Progress info
        embed.add_field(
            name="📊 Progress",
            value=(
                f"{self._create_progress_bar()} **{len(self.user_code)}/{self.difficulty}**\n"
                f"**Attempts Left:** {self.max_attempts - self.attempts}\n"
                f"**Progress:** {progress_pct:.0f}%"
            ),
            inline=False
        )

        # Instructions
        embed.add_field(
            name="💡 How to Play",
            value=(
                "• Click numbers to enter code\n"
                "• 🟢 = Correct position\n"
                "• 🔴 = Wrong digit\n"
                "• Click **Reset** to try again\n"
                "• Click **Hint** for a clue (costs attempt)"
            ),
            inline=False
        )

        embed.set_footer(
            text=f"⏰ Time limit: 30s | Robbing {self.victim.display_name}"
        )
        embed.set_thumbnail(url=self.victim.display_avatar.url)

        return embed

    async def reset_code(self, interaction: discord.Interaction):
        """Reset the current attempt."""
        if interaction.user.id != self.attacker.id:
            return await interaction.response.send_message(
                "❌ This isn't your robbery!",
                ephemeral=True
            )

        if not self.user_code:
            return await interaction.response.send_message(
                "❌ Nothing to reset!",
                ephemeral=True
            )

        self.user_code = []
        self.attempts += 1

        if self.attempts >= self.max_attempts:
            self.failed = True
            self.stop()
            await self.end_game(interaction)
        else:
            apply_v2_embed_layout(self, embed=self.create_game_embed())
            await interaction.response.edit_message(
                view=self
            )

    async def get_hint(self, interaction: discord.Interaction):
        """Give a hint (costs an attempt)."""
        if interaction.user.id != self.attacker.id:
            return await interaction.response.send_message(
                "❌ This isn't your robbery!",
                ephemeral=True
            )

        if self.attempts >= self.max_attempts - 1:
            return await interaction.response.send_message(
                "❌ Can't afford a hint! You need attempts left.",
                ephemeral=True
            )

        # Cost an attempt
        self.attempts += 1

        # Reveal one random correct digit
        unrevealed_positions = [
            i for i in range(self.difficulty)
            if i >= len(self.user_code)
        ]

        if not unrevealed_positions:
            return await interaction.response.send_message(
                "❌ No more hints available!",
                ephemeral=True
            )

        hint_pos = random.choice(unrevealed_positions)
        hint_digit = self.code[hint_pos]

        hint_msg = f"💡 **Hint:** Position {hint_pos + 1} is **{self._get_digit_emoji(hint_digit)}**"

        await interaction.response.send_message(hint_msg, ephemeral=True)

    def check_digit(self, number: int) -> bool:
        """Check if the digit is correct."""
        current_pos = len(self.user_code)

        if current_pos >= self.difficulty:
            return False

        self.user_code.append(number)

        # Check if complete
        if len(self.user_code) == self.difficulty:
            # Check if all correct
            if self.user_code == self.code:
                self.success = True
            else:
                self.attempts += 1

                # Check if out of attempts
                if self.attempts >= self.max_attempts:
                    self.failed = True

            self.stop()
            return True

        return False

    async def end_game(self, interaction: discord.Interaction):
        """End the game and show results."""
        self.clear_items()

        elapsed = 0
        if self.start_time:
            elapsed = asyncio.get_event_loop().time() - self.start_time

        code_display = " ".join(self._get_digit_emoji(d) for d in self.code)

        if self.success:
            embed = discord.Embed(
                title="🎉 Robbery Successful!",
                description=f"**{self.attacker.mention}** cracked the lock!",
                color=CRIME_COLORS["success"]
            )

            embed.add_field(
                name="🔓 Code Cracked",
                value=f"``````",
                inline=False
            )

            embed.add_field(
                name="💰 Loot",
                value=f"**Stolen:** {money(self.potential_steal)}",
                inline=True
            )

            embed.add_field(
                name="📊 Stats",
                value=(
                    f"**Time:** {elapsed:.1f}s\n"
                    f"**Attempts:** {self.attempts + 1}/{self.max_attempts}"
                ),
                inline=True
            )

            embed.set_footer(text=f"{self.victim.display_name} got robbed! 💸")

        else:
            fine = self.potential_steal // 2

            embed = discord.Embed(
                title="🚨 Robbery Failed!",
                description=f"**{self.attacker.mention}** got caught red-handed!",
                color=CRIME_COLORS["fail"]
            )

            embed.add_field(
                name="🔒 The Code Was",
                value=f"``````",
                inline=False
            )

            embed.add_field(
                name="💸 Consequences",
                value=f"**Fine:** {money(fine)}",
                inline=True
            )

            embed.add_field(
                name="📊 Stats",
                value=(
                    f"**Time:** {elapsed:.1f}s\n"
                    f"**Attempts:** {self.attempts}/{self.max_attempts}"
                ),
                inline=True
            )

            if self.user_code:
                your_code = " ".join(self._get_digit_emoji(d) for d in self.user_code)
                embed.add_field(
                    name="❌ Your Last Attempt",
                    value=f"``````",
                    inline=False
                )

            embed.set_footer(text=f"{self.victim.display_name} is safe!")

        embed.set_thumbnail(url=self.attacker.display_avatar.url)

        try:
            await interaction.response.edit_message(embed=embed, view=None)
        except:
            await interaction.edit_original_response(embed=embed, view=None)

    async def on_timeout(self):
        """Handle timeout."""
        self.failed = True

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.attacker.id:
            await interaction.response.send_message(
                "❌ This isn't your robbery!",
                ephemeral=True
            )
            return False
        return True


# ============= LOCKPICK BUTTON =============

class LockpickButton(discord.ui.Button):
    """Button for lockpick numbers."""

    def __init__(self, number: int, game: LockpickGame):
        emoji_map = {
            1: "1️⃣",
            2: "2️⃣",
            3: "3️⃣",
            4: "4️⃣",
            5: "5️⃣"
        }

        super().__init__(
            style=discord.ButtonStyle.primary,
            label=str(number),
            emoji=emoji_map[number],
            row=0
        )
        self.number = number
        self.game = game

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.game.attacker.id:
            return await interaction.response.send_message(
                "❌ This isn't your robbery!",
                ephemeral=True
            )

        # Show feedback
        await interaction.response.defer()

        finished = self.game.check_digit(self.number)

        if not finished:
            # Update display
            apply_v2_embed_layout(self.view, embed=self.game.create_game_embed())
            await interaction.edit_original_response(
                view=self.view
            )
        else:
            # Game over - wait a moment for suspense
            await asyncio.sleep(0.5)
            await self.game.end_game(interaction)
