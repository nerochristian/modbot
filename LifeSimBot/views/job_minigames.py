# views/job_minigames.py

from __future__ import annotations

import discord
import random
import asyncio
from typing import Optional, List, Tuple
from datetime import datetime

from utils.format import money


# ============= CONSTANTS =============

MINIGAME_COLORS = {
    "memory": 0x3B82F6,      # Blue
    "reaction": 0xFBBF24,    # Yellow/Gold
    "timing": 0x9B59B6,      # Purple
    "perfect": 0x22C55E,     # Green
    "great": 0x3B82F6,       # Blue
    "good": 0xFBBF24,        # Yellow
    "poor": 0xEF4444,        # Red
    "failed": 0x991B1B,      # Dark Red
}


# ============= BASE MINIGAME =============

class BaseMinigame(discord.ui.View):
    """Base class for all job minigames."""

    def __init__(self, job_name: str, difficulty: int):
        super().__init__(timeout=45)
        self.job_name = job_name
        self.difficulty = difficulty
        self.score = 0
        self.max_score = 100
        self.completed = False
        self.failed = False
        self.user_id: Optional[int] = None
        self.start_time: Optional[float] = None
        self.message: Optional[discord.WebhookMessage] = None

    def calculate_performance(self) -> Tuple[float, str, int]:
        """Calculate performance multiplier, message, and color."""
        if self.failed:
            return 0.5, "😞 FAILED", MINIGAME_COLORS["failed"]

        pct = (self.score / self.max_score) if self.max_score > 0 else 0

        if pct >= 1.0:
            return 1.5, "🌟 PERFECT!", MINIGAME_COLORS["perfect"]
        elif pct >= 0.80:
            return 1.25, "✨ EXCELLENT!", MINIGAME_COLORS["great"]
        elif pct >= 0.60:
            return 1.0, "👍 GOOD JOB", MINIGAME_COLORS["good"]
        elif pct >= 0.40:
            return 0.75, "😐 OKAY", MINIGAME_COLORS["poor"]
        else:
            return 0.5, "😞 POOR", MINIGAME_COLORS["poor"]

    def create_progress_bar(self, current: int, total: int, length: int = 10) -> str:
        """Create a visual progress bar."""
        filled = int((current / total) * length) if total > 0 else 0
        return "🟩" * filled + "⬛" * (length - filled)

    async def on_timeout(self):
        """Handle timeout."""
        self.failed = True
        self.completed = True
        self.stop()


# ============= SEQUENCE MEMORY GAME =============

class SequenceMemoryGame(BaseMinigame):
    """Remember and repeat a sequence - Used for Cashier, Electrician, etc."""

    def __init__(self, job_name: str, difficulty: int, emojis: List[str]):
        super().__init__(job_name, difficulty)
        self.emojis = emojis
        self.sequence: List[str] = []
        self.user_sequence: List[str] = []
        self.sequence_length = min(3 + difficulty, 8)
        self.max_score = self.sequence_length * 10
        self.attempts = 0
        self.max_attempts = 3

        # Generate random sequence
        self.sequence = random.choices(emojis, k=self.sequence_length)

    def create_start_embed(self) -> discord.Embed:
        """Create the initial embed showing the sequence."""
        sequence_display = "  ".join(self.sequence)

        embed = discord.Embed(
            title=f"🧠 {self.job_name} - Memory Test",
            description=(
                f"**📋 Memorize this sequence:**\n\n"
                f"# {sequence_display}\n\n"
                f"⏰ **Memorizing... 5 seconds**"
            ),
            color=MINIGAME_COLORS["memory"]
        )

        embed.add_field(
            name="📖 Instructions",
            value=(
                f"1️⃣ Memorize the {self.sequence_length} emojis above\n"
                f"2️⃣ Repeat them in the exact same order\n"
                f"3️⃣ Click Reset if you make a mistake"
            ),
            inline=False
        )

        embed.set_footer(text=f"Difficulty: {self.sequence_length} emojis • Focus!")
        return embed

    def create_game_embed(self) -> discord.Embed:
        """Create the game embed with buttons."""
        progress = len(self.user_sequence)
        total = self.sequence_length
        progress_bar = self.create_progress_bar(progress, total)

        # Build user sequence display
        if self.user_sequence:
            user_display = "  ".join(self.user_sequence)
        else:
            user_display = "➡️ *Click the buttons below!*"

        embed = discord.Embed(
            title=f"🧠 {self.job_name} - Repeat the Sequence",
            description=f"**Your sequence:**\n# {user_display}",
            color=MINIGAME_COLORS["memory"]
        )

        embed.add_field(
            name="📊 Progress",
            value=f"{progress_bar} **{progress}/{total}**",
            inline=False
        )

        embed.add_field(
            name="🎯 Attempts Left",
            value=f"{'❤️' * (self.max_attempts - self.attempts)}{'🖤' * self.attempts}",
            inline=True
        )

        embed.add_field(
            name="💯 Score",
            value=f"**{self.score}/{self.max_score}**",
            inline=True
        )

        embed.set_footer(text="💡 Select emojis in the correct order • Use Reset to try again")
        return embed

    async def start_game(self, interaction: discord.Interaction):
        """Start the minigame sequence."""
        self.user_id = interaction.user.id
        self.start_time = asyncio.get_event_loop().time()

        # Show sequence for 5 seconds
        self.message = await interaction.followup.send(embed=self.create_start_embed())
        await asyncio.sleep(5)

        # Show game buttons
        self.clear_items()

        # Get unique emojis from sequence + extras as distractors
        unique_in_sequence = list(set(self.sequence))
        extra_emojis = [e for e in self.emojis if e not in unique_in_sequence]
        random.shuffle(extra_emojis)

        # Show sequence emojis + 1-2 distractors (max 5 buttons)
        buttons_to_show = unique_in_sequence + extra_emojis[:max(1, 5 - len(unique_in_sequence))]
        random.shuffle(buttons_to_show)

        for emoji in buttons_to_show[:5]:
            button = SequenceButton(emoji, self)
            self.add_item(button)

        # Add reset button
        reset_btn = discord.ui.Button(
            style=discord.ButtonStyle.danger,
            emoji="🔄",
            label="Reset",
            row=1
        )
        reset_btn.callback = self.reset_sequence
        self.add_item(reset_btn)

        await self.message.edit(embed=self.create_game_embed(), view=self)

    async def reset_sequence(self, interaction: discord.Interaction):
        """Reset user's sequence."""
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message(
                "❌ This isn't your work shift!",
                ephemeral=True
            )

        self.user_sequence = []
        self.attempts += 1
        self.score = max(0, self.score - 10)

        if self.attempts >= self.max_attempts:
            self.failed = True
            self.completed = True
            self.stop()
            await self.end_game(interaction)
        else:
            await interaction.response.edit_message(embed=self.create_game_embed(), view=self)

    def check_answer(self, emoji: str) -> bool:
        """Check if the emoji is correct for current position."""
        current_pos = len(self.user_sequence)
        if current_pos >= len(self.sequence):
            return False

        correct = self.sequence[current_pos] == emoji
        if correct:
            self.user_sequence.append(emoji)
            self.score += 10
        else:
            # Wrong answer
            self.attempts += 1
            if self.attempts >= self.max_attempts:
                self.failed = True
                self.completed = True
                self.stop()
            else:
                # Let them try again
                self.user_sequence = []
            return False

        # Check if complete
        if len(self.user_sequence) == len(self.sequence):
            self.completed = True
            self.stop()

        return correct

    async def end_game(self, interaction: discord.Interaction):
        """End the game and show results."""
        self.clear_items()

        elapsed = asyncio.get_event_loop().time() - self.start_time
        multiplier, msg, color = self.calculate_performance()

        embed = discord.Embed(
            title=f"{'✅ Work Complete!' if not self.failed else '❌ Work Failed!'}",
            description=f"**Performance: {msg}**",
            color=color
        )

        # Stats
        embed.add_field(
            name="📊 Results",
            value=(
                f"**Score:** {self.score}/{self.max_score}\n"
                f"**Time:** {elapsed:.1f}s\n"
                f"**Attempts Used:** {self.attempts}/{self.max_attempts}"
            ),
            inline=True
        )

        embed.add_field(
            name="💰 Pay Multiplier",
            value=f"**{multiplier:.0%}**\n{'⭐' * int(multiplier * 2)}",
            inline=True
        )

        if self.failed:
            correct_sequence = "  ".join(self.sequence)
            embed.add_field(
                name="❌ Failed",
                value=f"**Correct sequence was:**\n{correct_sequence}",
                inline=False
            )

        embed.set_footer(text=f"Job: {self.job_name} • Difficulty: {self.sequence_length}")

        await interaction.response.edit_message(embed=embed, view=None)


class SequenceButton(discord.ui.Button):
    """Button for sequence minigame."""

    def __init__(self, emoji: str, game: SequenceMemoryGame):
        super().__init__(
            style=discord.ButtonStyle.primary,
            emoji=emoji,
            row=0
        )
        self.game = game
        self.emoji_str = emoji

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.game.user_id:
            return await interaction.response.send_message(
                "❌ This isn't your work shift!",
                ephemeral=True
            )

        correct = self.game.check_answer(self.emoji_str)

        if not self.game.completed:
            await interaction.response.edit_message(
                embed=self.game.create_game_embed(),
                view=self.view
            )
        else:
            await self.game.end_game(interaction)


# ============= REACTION TIME GAME =============

class ReactionTimeGame(BaseMinigame):
    """Click buttons as fast as possible - Used for Lifeguard, Pilot, etc."""

    def __init__(self, job_name: str, difficulty: int, emojis: List[str]):
        super().__init__(job_name, difficulty)
        self.target_emoji = random.choice(emojis)
        self.avoid_emojis = [e for e in emojis if e != self.target_emoji]
        self.clicks_needed = 5 + difficulty
        self.clicks_done = 0
        self.wrong_clicks = 0
        self.max_score = self.clicks_needed * 10
        self.time_limit = 25

    def create_game_embed(self) -> discord.Embed:
        """Create game embed."""
        progress_bar = self.create_progress_bar(self.clicks_done, self.clicks_needed)

        embed = discord.Embed(
            title=f"⚡ {self.job_name} - Speed Test",
            description=(
                f"**🎯 Click ONLY the {self.target_emoji} emoji!**\n"
                f"❌ Avoid all others or lose points!\n"
            ),
            color=MINIGAME_COLORS["reaction"]
        )

        embed.add_field(
            name="📊 Progress",
            value=f"{progress_bar} **{self.clicks_done}/{self.clicks_needed}**",
            inline=False
        )

        embed.add_field(
            name="✅ Correct Clicks",
            value=f"**{self.clicks_done}**",
            inline=True
        )

        embed.add_field(
            name="❌ Wrong Clicks",
            value=f"**{self.wrong_clicks}**\n(-5 points each)",
            inline=True
        )

        embed.add_field(
            name="💯 Score",
            value=f"**{self.score}/{self.max_score}**",
            inline=True
        )

        embed.set_footer(text=f"⏰ {self.time_limit}s time limit • Click fast and accurately!")
        return embed

    async def start_game(self, interaction: discord.Interaction):
        """Start reaction game."""
        self.user_id = interaction.user.id
        self.start_time = asyncio.get_event_loop().time()

        # Add buttons in grid (3 rows x 5 columns = 15 buttons)
        button_count = 15
        target_count = max(6, self.clicks_needed + 1)

        # Create button list with mix of target and avoid emojis
        buttons = []
        for _ in range(target_count):
            buttons.append(self.target_emoji)

        while len(buttons) < button_count:
            buttons.append(random.choice(self.avoid_emojis))

        random.shuffle(buttons)

        for i, emoji in enumerate(buttons):
            button = ReactionButton(emoji, self)
            button.row = i // 5  # 5 buttons per row
            self.add_item(button)

        self.message = await interaction.followup.send(
            embed=self.create_game_embed(),
            view=self
        )

    def handle_click(self, emoji: str) -> bool:
        """Handle button click."""
        if emoji == self.target_emoji:
            self.clicks_done += 1
            self.score += 10

            if self.clicks_done >= self.clicks_needed:
                self.completed = True
                self.stop()
                return True
        else:
            # Wrong click, penalty
            self.wrong_clicks += 1
            self.score = max(0, self.score - 5)

        return False


class ReactionButton(discord.ui.Button):
    """Button for reaction game."""

    def __init__(self, emoji: str, game: ReactionTimeGame):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            emoji=emoji
        )
        self.game = game
        self.emoji_str = emoji
        self.clicked = False

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.game.user_id:
            return await interaction.response.send_message(
                "❌ This isn't your work shift!",
                ephemeral=True
            )

        if self.clicked:
            return await interaction.response.defer()

        self.clicked = True

        # Visual feedback
        if self.emoji_str == self.game.target_emoji:
            self.style = discord.ButtonStyle.success
        else:
            self.style = discord.ButtonStyle.danger

        self.disabled = True

        finished = self.game.handle_click(self.emoji_str)

        if not finished:
            await interaction.response.edit_message(
                embed=self.game.create_game_embed(),
                view=self.view
            )
        else:
            await self.finish_game(interaction)

    async def finish_game(self, interaction: discord.Interaction):
        """Finish the reaction game."""
        self.view.clear_items()

        elapsed = asyncio.get_event_loop().time() - self.game.start_time
        multiplier, msg, color = self.game.calculate_performance()

        embed = discord.Embed(
            title=f"✅ Work Complete!",
            description=f"**Performance: {msg}**",
            color=color
        )

        embed.add_field(
            name="📊 Results",
            value=(
                f"**Score:** {self.game.score}/{self.game.max_score}\n"
                f"**Time:** {elapsed:.1f}s\n"
                f"**Speed:** {self.game.clicks_done / elapsed:.1f} clicks/sec"
            ),
            inline=True
        )

        embed.add_field(
            name="🎯 Accuracy",
            value=(
                f"**Correct:** {self.game.clicks_done}\n"
                f"**Wrong:** {self.game.wrong_clicks}\n"
                f"**Rate:** {(self.game.clicks_done / (self.game.clicks_done + self.game.wrong_clicks) * 100):.0f}%"
            ),
            inline=True
        )

        embed.add_field(
            name="💰 Pay Multiplier",
            value=f"**{multiplier:.0%}**\n{'⭐' * int(multiplier * 2)}",
            inline=True
        )

        embed.set_footer(text=f"Job: {self.game.job_name} • Great reflexes!")

        await interaction.response.edit_message(embed=embed, view=None)


# ============= TIMING GAME =============

class TimingGame(BaseMinigame):
    """Click at the perfect moment - Used for Chef, Surgeon, etc."""

    def __init__(self, job_name: str, difficulty: int, emojis: List[str]):
        super().__init__(job_name, difficulty)
        self.target_emoji = emojis[0]
        self.stages = 3 + difficulty // 2
        self.current_stage = 0
        self.max_score = self.stages * 30
        self.perfect_clicks = 0
        self.good_clicks = 0

    def create_game_embed(self) -> discord.Embed:
        """Create game embed."""
        progress_bar = self.create_progress_bar(self.current_stage, self.stages)

        embed = discord.Embed(
            title=f"⏰ {self.job_name} - Timing Challenge",
            description=(
                f"**Stage {self.current_stage + 1}/{self.stages}**\n\n"
                f"🎯 Wait for the button to turn **GREEN**, then click immediately!\n"
            ),
            color=MINIGAME_COLORS["timing"]
        )

        embed.add_field(
            name="📊 Progress",
            value=f"{progress_bar} **{self.current_stage}/{self.stages}**",
            inline=False
        )

        embed.add_field(
            name="🌟 Perfect Clicks",
            value=f"**{self.perfect_clicks}**",
            inline=True
        )

        embed.add_field(
            name="👍 Good Clicks",
            value=f"**{self.good_clicks}**",
            inline=True
        )

        embed.add_field(
            name="💯 Score",
            value=f"**{self.score}/{self.max_score}**",
            inline=True
        )

        embed.set_footer(text="⚠️ Too early = penalty • Perfect timing = max points!")
        return embed

    async def start_game(self, interaction: discord.Interaction):
        """Start timing game."""
        self.user_id = interaction.user.id
        self.start_time = asyncio.get_event_loop().time()

        button = TimingButton(self.target_emoji, self)
        self.add_item(button)

        self.message = await interaction.followup.send(
            embed=self.create_game_embed(),
            view=self
        )

        # Start timing sequence
        asyncio.create_task(button.timing_loop())

    def handle_click(self, was_perfect: bool) -> int:
        """Handle timing click, return points earned."""
        if was_perfect:
            points = 30
            self.perfect_clicks += 1
        else:
            points = 15
            self.good_clicks += 1

        self.score += points
        self.current_stage += 1

        if self.current_stage >= self.stages:
            self.completed = True
            self.stop()

        return points


class TimingButton(discord.ui.Button):
    """Button for timing game."""

    def __init__(self, emoji: str, game: TimingGame):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            emoji=emoji,
            label="⏳ WAIT..."
        )
        self.game = game
        self.ready = False
        self.ready_time = None
        self.loop_running = False

    async def timing_loop(self):
        """Run the timing loop."""
        if self.loop_running:
            return

        self.loop_running = True

        # Wait random time then turn green
        wait_time = random.uniform(2.0, 4.0)
        await asyncio.sleep(wait_time)

        if not self.game.completed:
            self.ready = True
            self.ready_time = asyncio.get_event_loop().time()
            self.style = discord.ButtonStyle.success
            self.label = "✨ CLICK NOW!"

            try:
                await self.game.message.edit(view=self.view)
            except:
                pass

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.game.user_id:
            return await interaction.response.send_message(
                "❌ This isn't your work shift!",
                ephemeral=True
            )

        # Check if clicked at right time
        was_perfect = self.ready

        if not self.ready:
            # Too early! Penalty
            self.game.score = max(0, self.game.score - 10)

        points = self.game.handle_click(was_perfect)

        if not self.game.completed:
            # Reset for next stage
            self.ready = False
            self.loop_running = False
            self.style = discord.ButtonStyle.secondary
            self.label = "⏳ WAIT..."

            await interaction.response.edit_message(
                embed=self.game.create_game_embed(),
                view=self.view
            )

            # Start next timing loop
            asyncio.create_task(self.timing_loop())
        else:
            # Game complete
            await self.finish_game(interaction)

    async def finish_game(self, interaction: discord.Interaction):
        """Finish timing game."""
        self.view.clear_items()

        elapsed = asyncio.get_event_loop().time() - self.game.start_time
        multiplier, msg, color = self.game.calculate_performance()

        embed = discord.Embed(
            title=f"✅ All Stages Complete!",
            description=f"**Performance: {msg}**",
            color=color
        )

        embed.add_field(
            name="📊 Results",
            value=(
                f"**Score:** {self.game.score}/{self.game.max_score}\n"
                f"**Time:** {elapsed:.1f}s\n"
                f"**Stages:** {self.game.stages}"
            ),
            inline=True
        )

        embed.add_field(
            name="🎯 Timing Stats",
            value=(
                f"**Perfect:** {self.game.perfect_clicks} 🌟\n"
                f"**Good:** {self.game.good_clicks} 👍\n"
                f"**Accuracy:** {(self.game.perfect_clicks / self.game.stages * 100):.0f}%"
            ),
            inline=True
        )

        embed.add_field(
            name="💰 Pay Multiplier",
            value=f"**{multiplier:.0%}**\n{'⭐' * int(multiplier * 2)}",
            inline=True
        )

        embed.set_footer(text=f"Job: {self.game.job_name} • Perfect timing!")

        await interaction.response.edit_message(embed=embed, view=None)


# ============= MULTIPLE CHOICE GAME =============

JOB_QUESTIONS: dict[str, list[dict]] = {
    # Quiz-style questions for jobs - each job gets themed questions
    "delivery": [
        {
            "question": "A customer needs a package ASAP. Which route is fastest?",
            "options": ["Highway (tolled)", "Backstreets (many lights)", "Scenic route (longer)", "Detour (roadwork)"],
            "answer": 0,
        }
    ],
    "barista": [
        {
            "question": "A latte needs espresso + steamed milk. What's the missing step?",
            "options": ["Foam the milk properly", "Add ketchup", "Freeze it", "Add motor oil"],
            "answer": 0,
        }
    ],
    "mechanic": [
        {
            "question": "The car won't start, but the lights turn on. Most likely issue?",
            "options": ["Dead starter", "Flat tire", "Empty washer fluid", "Broken mirror"],
            "answer": 0,
        }
    ],
    "paramedic": [
        {
            "question": "Patient not breathing. First action?",
            "options": ["Start CPR immediately", "Wait and watch", "Give them water", "Call their family first"],
            "answer": 0,
        }
    ],
    "teacher": [
        {
            "question": "Quick math: 12 × 3 = ?",
            "options": ["36", "24", "48", "18"],
            "answer": 0,
        }
    ],
    "nurse": [
        {
            "question": "A patient feels dizzy after standing up quickly. Best first action?",
            "options": ["Have them sit/lie down", "Tell them to sprint", "Give spicy food", "Turn off the lights"],
            "answer": 0,
        }
    ],
    "programmer": [
        {
            "question": "Bug: `if x = 5:` in Python. What's the fix?",
            "options": ["Use `==` for comparison", "Remove the colon", "Use `=>`", "Replace with `:=`"],
            "answer": 0,
        }
    ],
    "accountant": [
        {
            "question": "Invoice check: $120 subtotal + 10% tax = ?",
            "options": ["$132", "$130", "$140", "$120"],
            "answer": 0,
        }
    ],
    "architect": [
        {
            "question": "Pattern: ▢ ▢ △ ▢ ▢ △ ... What comes next?",
            "options": ["▢", "△", "○", "☆"],
            "answer": 0,
        }
    ],
    "realtor": [
        {
            "question": "Client wants 3 bed, 2 bath under $300k. Which do you show?",
            "options": ["3 bed, 2 bath, $285k", "2 bed, 2 bath, $250k", "4 bed, 3 bath, $400k", "1 bed, 1 bath, $150k"],
            "answer": 0,
        }
    ],
    "lawyer": [
        {
            "question": "In court, what's the strongest approach?",
            "options": ["Use evidence + clear argument", "Yell loudly", "Ignore the judge", "Make up facts"],
            "answer": 0,
        }
    ],
    "doctor": [
        {
            "question": "Symptoms: sore throat + fever. Most likely common cause?",
            "options": ["Infection", "Broken toe", "Sunburn", "Sprained wrist"],
            "answer": 0,
        }
    ],
    "scientist": [
        {
            "question": "Experiment safety: what's required first?",
            "options": ["Wear PPE", "Taste chemicals", "Turn off ventilation", "Remove goggles"],
            "answer": 0,
        }
    ],
    "trader": [
        {
            "question": "A stock spikes 30% in 5 minutes on hype. Best move?",
            "options": ["Be cautious / take profits", "All-in with leverage", "Ignore risk completely", "Buy random penny stocks"],
            "answer": 0,
        }
    ],
    "hacker": [
        {
            "question": "Which is the safest password practice?",
            "options": ["Use a password manager + unique passwords", "Reuse one password everywhere", "Share passwords in DMs", "Use 'password123'"],
            "answer": 0,
        }
    ],
    "ceo": [
        {
            "question": "Revenue is flat. What's the best first step?",
            "options": ["Analyze costs + customer feedback", "Fire everyone", "Double prices overnight", "Ignore the numbers"],
            "answer": 0,
        }
    ],
    "president": [
        {
            "question": "In a debate, what's most persuasive?",
            "options": ["Clear plan + calm delivery", "Interrupt constantly", "Insults only", "Avoid questions"],
            "answer": 0,
        }
    ],
    "detective": [
        {
            "question": "Clue pattern: red, red, blue, red, red, blue... What color is next?",
            "options": ["Red", "Blue", "Green", "Yellow"],
            "answer": 0,
        }
    ],
}


class MultipleChoiceGame(BaseMinigame):
    """One-question multiple-choice minigame used for quiz-like jobs (code, diagnosis, strategy, etc)."""

    def __init__(self, job_name: str, difficulty: int, questions: list[dict]):
        super().__init__(job_name, difficulty)
        self.questions = questions or [
            {"question": "Pick the best answer.", "options": ["A", "B", "C", "D"], "answer": 0}
        ]
        self.q = random.choice(self.questions)
        self.max_score = 100
        self.attempts = 0
        self.max_attempts = 1
        self._answered = False

    def create_game_embed(self) -> discord.Embed:
        letters = ["A", "B", "C", "D"]
        opts = list(self.q.get("options") or [])[:4]
        lines = [f"**{letters[i]}.** {opt}" for i, opt in enumerate(opts)]

        embed = discord.Embed(
            title=f"🧠 {self.job_name} - Quick Challenge",
            description=f"**{self.q.get('question', 'Pick the best answer.')}**\n\n" + "\n".join(lines),
            color=MINIGAME_COLORS.get("memory", 0x3B82F6),
        )
        embed.set_footer(text="Choose carefully — one attempt!")
        return embed

    async def start_game(self, interaction: discord.Interaction):
        self.user_id = interaction.user.id
        self.start_time = asyncio.get_event_loop().time()

        self.clear_items()
        options = list(self.q.get("options") or [])[:4]
        for idx, label in enumerate(options):
            self.add_item(_ChoiceButton(idx, str(label), self))

        self.message = await interaction.followup.send(embed=self.create_game_embed(), view=self)

    async def finish(self, interaction: discord.Interaction, *, correct: bool):
        if self._answered:
            return
        self._answered = True
        self.attempts = 1

        elapsed = (asyncio.get_event_loop().time() - (self.start_time or asyncio.get_event_loop().time()))
        if correct:
            self.score = 100 if elapsed <= 15 else 80
        else:
            self.score = 30

        self.completed = True
        self.stop()

        multiplier, msg, color = self.calculate_performance()
        result = "Correct!" if correct else "Wrong!"

        embed = discord.Embed(
            title="✅ Work Complete!" if correct else "⚠️ Work Complete (with mistakes)",
            description=f"**{result}**\n**Performance:** {msg}\n**Time:** {elapsed:.1f}s",
            color=color,
        )
        embed.add_field(name="Score", value=f"**{self.score}/{self.max_score}**", inline=True)
        embed.add_field(name="Pay Multiplier", value=f"**{multiplier:.0%}**", inline=True)

        await interaction.response.edit_message(embed=embed, view=None)


class _ChoiceButton(discord.ui.Button):
    def __init__(self, index: int, label: str, game: MultipleChoiceGame):
        super().__init__(style=discord.ButtonStyle.secondary, label=label[:80])
        self.index = index
        self.game = game

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.game.user_id:
            return await interaction.response.send_message("❌ This isn't your work shift!", ephemeral=True)

        correct = int(self.game.q.get("answer", 0)) == self.index
        await self.game.finish(interaction, correct=correct)


# ============= JOB EMOJI MAPPINGS =============

JOB_EMOJIS = {
    # Entry level
    "waiter": ["🍝", "🥩", "🍷", "🍰", "🥗", "🍜", "🍱"],
    "cashier": ["🍎", "🍕", "🍔", "🥤", "☕", "🍩", "🥗"],
    "janitor": ["🧹", "🧽", "🧴", "🚮", "🧺", "🪣", "🧼"],
    "dogwalker": ["🐕", "🐩", "🦮", "🐕‍🦺", "🐶", "🦴", "⚽"],
    "paperboy": ["📰", "📨", "📬", "🏠", "🚲", "📦", "✉️"],
    "fastfood": ["🍔", "🍟", "🌭", "🥤", "🍕", "🌮", "🍗"],
    "receptionist": ["📞", "📋", "📅", "💼", "🖊️", "📧", "🏢"],
    
    # Skilled
    "delivery": ["📦", "🚚", "🏠", "🏢", "🏪", "📍", "🗺️"],
    "barista": ["☕", "🥤", "🍵", "🧋", "🍰", "🥐", "🧁"],
    "lifeguard": ["🏊", "🆘", "🚨", "💦", "🌊", "⛱️", "🩱"],
    "photographer": ["📸", "📷", "🎨", "🌅", "🌃", "👥", "🎬"],
    "electrician": ["🔌", "💡", "⚡", "🔋", "🔧", "⚙️", "🛠️"],
    "mechanic": ["🔧", "🔩", "⚙️", "🛠️", "🚗", "🔌", "⚡"],
    "paramedic": ["🚑", "🩺", "💉", "🆘", "❤️", "🏥", "⚡"],
    
    # Professional
    "chef": ["🍳", "🥘", "🍲", "🔥", "👨‍🍳", "🍴", "🥄"],
    "teacher": ["📚", "📖", "✏️", "📝", "🎓", "🏫", "👨‍🏫"],
    "nurse": ["💉", "🩺", "💊", "❤️", "🏥", "👨‍⚕️", "🩹"],
    "programmer": ["💻", "⌨️", "🖥️", "🐛", "✅", "❌", "🔢"],
    "accountant": ["💰", "💵", "📊", "📈", "🧮", "📉", "💼"],
    "architect": ["🏗️", "📐", "📏", "🏢", "🏛️", "🏠", "📋"],
    "musician": ["🎵", "🎤", "🎸", "🥁", "🎹", "🎶", "🎧"],
    "realtor": ["🏠", "🏢", "🔑", "💰", "📋", "🤝", "🏘️"],
    
    # Expert
    "lawyer": ["⚖️", "📜", "🏛️", "👔", "💼", "📋", "🖊️"],
    "doctor": ["🩺", "💉", "💊", "❤️", "🫀", "🧠", "🏥"],
    "pilot": ["✈️", "🛬", "🛫", "⛅", "🌤️", "⛈️", "🌍"],
    "scientist": ["🔬", "🧪", "🧬", "⚗️", "🦠", "💉", "📊"],
    "surgeon": ["💉", "🩺", "❤️", "🫀", "🧠", "✂️", "🏥"],
    "detective": ["🕵️", "🔎", "🧩", "📌", "🗂️", "🧠", "🗝️"],
    "firefighter": ["🚒", "🔥", "🧯", "⛑️", "🚨", "💪", "🪓"],
    
    # Elite
    "trader": ["📊", "📈", "📉", "💰", "💵", "💹", "📱"],
    "hacker": ["💻", "🔐", "🔓", "🛡️", "⚡", "🐛", "✅"],
    "astronaut": ["🚀", "🌍", "🌙", "⭐", "🛰️", "👨‍🚀", "🌌"],
    "ceo": ["💼", "📊", "📈", "💰", "🏢", "📱", "💵"],
    "president": ["🏛️", "🗽", "🎙️", "📜", "⚖️", "🌍", "🤝"],
}


# ============= HELPER FUNCTION =============

def get_job_minigame(job_id: str, job_data: dict, difficulty: int) -> Optional[BaseMinigame]:
    """Get appropriate minigame for job."""
    job_name = job_data.get("name", job_id)
    minigame_type = job_data.get("minigame", "sequence")
    emojis = JOB_EMOJIS.get(job_id.lower(), ["🔵", "🔴", "🟢", "🟡", "🟣", "⚫", "⚪"])

    if minigame_type in ("sequence", "memory"):
        return SequenceMemoryGame(job_name, difficulty, emojis)
    if minigame_type == "reaction":
        return ReactionTimeGame(job_name, difficulty, emojis)
    if minigame_type in ("timing", "precision"):
        return TimingGame(job_name, difficulty, emojis)

    questions = JOB_QUESTIONS.get(job_id.lower())
    if not questions:
        questions = [
            {
                "question": f"Quick task for {job_name}: pick the best option.",
                "options": ["Option A", "Option B", "Option C", "Option D"],
                "answer": 0,
            }
        ]
    return MultipleChoiceGame(job_name, difficulty, questions)
