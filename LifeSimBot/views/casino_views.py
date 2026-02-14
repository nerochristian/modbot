# views/casino_views.py

from __future__ import annotations

import discord
import random
import asyncio
from typing import Optional, List, Dict

from utils.format import money
from views.v2_embed import apply_v2_embed_layout, iter_all_items

# ============= CONSTANTS =============

CASINO_COLORS = {
    "slots": 0xFF6B9D,
    "blackjack": 0x3B82F6,
    "coinflip": 0xFBBF24,
    "dice": 0x8B5CF6,
    "minesweeper": 0x10B981,
    "crash": 0xEF4444,
    "win": 0x22C55E,
    "lose": 0xF43F5E,
    "neutral": 0x6B7280,
}

# ============= MAIN MENU =============

CASINO_GAMES_V2: Dict[str, Dict[str, object]] = {
    "slots": {
        "label": "Slots",
        "emoji": "🎰",
        "color": CASINO_COLORS["slots"],
        "summary": "Spin the reels and match symbols for multipliers.",
    },
    "blackjack": {
        "label": "Blackjack",
        "emoji": "🃏",
        "color": CASINO_COLORS["blackjack"],
        "summary": "Get to 21 without busting. Beat the dealer.",
    },
    "coinflip": {
        "label": "Coinflip",
        "emoji": "🪙",
        "color": CASINO_COLORS["coinflip"],
        "summary": "50/50 chance. Pick heads or tails.",
    },
    "dice": {
        "label": "Dice",
        "emoji": "🎲",
        "color": CASINO_COLORS["dice"],
        "summary": "Roll against the dealer. Higher wins.",
    },
    "crash": {
        "label": "Crash",
        "emoji": "📈",
        "color": CASINO_COLORS["crash"],
        "summary": "Multiplier climbs until it crashes. Cash out in time.",
    },
    "minesweeper_easy": {
        "label": "Mines (Easy)",
        "emoji": "💣",
        "color": CASINO_COLORS["minesweeper"],
        "summary": "3x3 grid. Find safe tiles and cash out anytime.",
    },
    "minesweeper_medium": {
        "label": "Mines (Medium)",
        "emoji": "💣",
        "color": CASINO_COLORS["minesweeper"],
        "summary": "4x4 grid. Higher risk, higher multiplier.",
    },
    "minesweeper_hard": {
        "label": "Mines (Hard)",
        "emoji": "💣",
        "color": CASINO_COLORS["minesweeper"],
        "summary": "5x5 grid. Max risk, max payout.",
    },
}


async def edit_as_v2_message(
    interaction: discord.Interaction,
    *,
    embed: Optional[discord.Embed] = None,
    view: Optional[discord.ui.View] = None,
) -> None:
    """
    Edit interaction messages safely for both classic and Components V2 payloads.
    """
    if embed is not None and view is None:
        layout = discord.ui.LayoutView(timeout=None)
        apply_v2_embed_layout(layout, embed=embed)
        await interaction.response.edit_message(view=layout)
        return

    await interaction.response.edit_message(embed=embed, view=view)


class _CasinoBetModal(discord.ui.Modal, title="Change Bet"):
    amount: discord.ui.TextInput = discord.ui.TextInput(
        label="Bet Amount",
        placeholder="Enter a number (e.g. 2500)",
        required=True,
        min_length=1,
        max_length=12,
    )

    def __init__(self, view: "CasinoMenuV2View"):
        super().__init__()
        self._view = view

    async def on_submit(self, interaction: discord.Interaction):
        raw = (self.amount.value or "").strip().replace(",", "")
        try:
            new_bet = int(raw)
        except ValueError:
            return await interaction.response.send_message("❌ Please enter a valid number.", ephemeral=True)

        if new_bet < 10:
            return await interaction.response.send_message("❌ Minimum bet is $10.", ephemeral=True)
        if new_bet > 100000:
            return await interaction.response.send_message("❌ Maximum bet is $100,000.", ephemeral=True)

        db = getattr(self._view.bot, "db", None)
        if db is None:
            return await interaction.response.send_message("❌ Database not ready yet.", ephemeral=True)

        u = db.getuser(str(interaction.user.id))
        balance = int(u.get("balance", 0))
        if new_bet > balance:
            return await interaction.response.send_message(f"❌ You only have {money(balance)}.", ephemeral=True)

        self._view.bet = new_bet
        self._view.refresh()
        try:
            return await interaction.response.edit_message(view=self._view)
        except Exception:
            if getattr(self._view, "message", None):
                await self._view.message.edit(view=self._view)
            return


class _CasinoGameSelectV2(discord.ui.Select):
    def __init__(self, view: "CasinoMenuV2View"):
        self._view = view
        options: list[discord.SelectOption] = []
        for game_id, meta in CASINO_GAMES_V2.items():
            options.append(
                discord.SelectOption(
                    label=str(meta["label"]),
                    value=game_id,
                    emoji=str(meta["emoji"]),
                    description=str(meta["summary"])[:100],
                    default=(view.selected_game == game_id),
                )
            )

        placeholder = "Choose a game..."
        if view.selected_game and view.selected_game in CASINO_GAMES_V2:
            meta = CASINO_GAMES_V2[view.selected_game]
            placeholder = f"Selected: {meta['label']}"

        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=1,
            options=options[:25],
            row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        self._view.selected_game = self.values[0]
        self._view.refresh()
        await interaction.response.edit_message(view=self._view)


class CasinoMenuV2View(discord.ui.LayoutView):
    """Casino menu using Components V2 (select + buttons + rich layout)."""

    def __init__(self, bot, user: discord.User, bet: int, *, preselect: Optional[str] = None):
        super().__init__(timeout=120)
        self.bot = bot
        self.user = user
        self.bet = bet
        self.selected_game: Optional[str] = None
        self.message: Optional[discord.Message] = None

        if preselect and str(preselect) in CASINO_GAMES_V2:
            self.selected_game = str(preselect)

        self.game_select = _CasinoGameSelectV2(self)
        self.add_item(self.game_select)
        self.refresh()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "❌ This isn't your casino menu. Use `/gamble` to start your own.",
                ephemeral=True,
            )
            return False
        return True

    def refresh(self) -> None:
        db = getattr(self.bot, "db", None)
        balance_val: Optional[int] = None
        if db is not None:
            try:
                u = db.getuser(str(self.user.id))
                balance_val = int(u.get("balance", 0))
            except Exception:
                balance_val = None

        selected = CASINO_GAMES_V2.get(self.selected_game or "")
        accent = int(selected.get("color")) if selected else int(discord.Color.gold().value)

        # Keep select placeholder/defaults in sync with selection.
        try:
            if getattr(self, "game_select", None) is not None:
                if self.selected_game and self.selected_game in CASINO_GAMES_V2:
                    meta = CASINO_GAMES_V2[self.selected_game]
                    self.game_select.placeholder = f"Selected: {meta['label']}"
                else:
                    self.game_select.placeholder = "Choose a game..."

                for opt in self.game_select.options:
                    opt.default = (opt.value == self.selected_game)
        except Exception:
            pass

        title_line = "🎰 Casino"
        if selected:
            title_line = f"{selected['emoji']} {selected['label']}"

        header = (
            f"# {title_line}\n"
            f"**Bet:** {money(self.bet)}\n"
            + (f"**Balance:** {money(balance_val)}\n" if isinstance(balance_val, int) else "")
            + "\n"
        ).strip()

        details = (
            f"{selected['summary']}\n\nPress **Play** when you're ready."
            if selected
            else "Pick a game from the dropdown, then press **Play**."
        )

        body_items: list[discord.ui.Item] = []
        try:
            body_items.append(
                discord.ui.Section(
                    discord.ui.TextDisplay(content=f"{header}\n{details}".strip()),
                    accessory=discord.ui.Thumbnail(self.user.display_avatar.url),
                )
            )
        except Exception:
            body_items.append(discord.ui.TextDisplay(content=f"{header}\n{details}".strip()))

        if not selected:
            body_items.append(
                discord.ui.TextDisplay(
                    content="## Games\n"
                    + "\n".join(
                        f"- {meta['emoji']} **{meta['label']}**"
                        for meta in list(CASINO_GAMES_V2.values())[:8]
                    )
                )
            )

        apply_v2_embed_layout(self, body_items=body_items, accent_color=accent)

    async def _charge_bet(self, interaction: discord.Interaction) -> bool:
        db = getattr(self.bot, "db", None)
        if db is None:
            await interaction.response.send_message("❌ Database not ready yet.", ephemeral=True)
            return False

        userid = str(self.user.id)
        u = db.getuser(userid)
        balance = int(u.get("balance", 0))
        if self.bet > balance:
            await interaction.response.send_message(f"❌ You only have {money(balance)}.", ephemeral=True)
            return False

        db.removebalance(userid, self.bet)
        try:
            db.increment_stat(userid, "casino_total_bet", self.bet)
        except Exception:
            pass
        return True

    @discord.ui.button(label="Play", style=discord.ButtonStyle.success, emoji="▶️", row=1)
    async def play_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.selected_game or self.selected_game not in CASINO_GAMES_V2:
            return await interaction.response.send_message("❌ Select a game first.", ephemeral=True)

        ok = await self._charge_bet(interaction)
        if not ok:
            return

        game_id = str(self.selected_game)
        try:
            if game_id == "slots":
                game = SlotsGame(self.bot, self.user, self.bet)
                await game.start(interaction)
                self.stop()
                return

            if game_id == "blackjack":
                game = BlackjackGame(self.bot, self.user, self.bet)
                await game.start(interaction)
                self.stop()
                return

            if game_id == "coinflip":
                game = CoinflipGame(self.bot, self.user, self.bet)
                await game.start(interaction)
                self.stop()
                return

            if game_id == "dice":
                game = DiceGame(self.bot, self.user, self.bet)
                await game.start(interaction)
                self.stop()
                return

            if game_id == "crash":
                game = CrashGame(self.bot, self.user, self.bet)
                await game.start(interaction)
                self.stop()
                return

            if game_id.startswith("minesweeper_"):
                difficulty = game_id.split("_", 1)[1]
                game = MinesweeperGame(self.user, self.bet, self.bot, difficulty)
                embed = game.create_embed()
                apply_v2_embed_layout(game, embed=embed)
                await interaction.response.edit_message(view=game)
                self.stop()
                return

            raise RuntimeError(f"Unknown casino game: {game_id}")
        except Exception:
            # Refund bet if game launch fails after charging.
            try:
                db = getattr(self.bot, "db", None)
                if db is not None:
                    db.addbalance(str(self.user.id), self.bet)
            except Exception:
                pass

            try:
                await interaction.response.send_message("❌ Casino error while starting the game. Your bet was refunded.", ephemeral=True)
            except Exception:
                pass
            self.stop()
            return

    @discord.ui.button(label="Change Bet", style=discord.ButtonStyle.secondary, emoji="✏️", row=1)
    async def change_bet_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(_CasinoBetModal(self))

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, emoji="❌", row=1)
    async def close_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🎰 Casino",
            description="Closed the casino menu.",
            color=CASINO_COLORS["neutral"],
        )
        await edit_as_v2_message(interaction, embed=embed, view=None)
        self.stop()


class CasinoGameSelector(discord.ui.LayoutView):
    """Main casino menu."""

    def __init__(self, bot, user: discord.User, bet: int):
        super().__init__(timeout=60)
        self.bot = bot
        self.user = user
        self.bet = bet

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "❌ This isn't your game! Start your own with `/gamble`",
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Slots", style=discord.ButtonStyle.primary, emoji="🎰", row=0)
    async def slots_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        game = SlotsGame(self.bot, self.user, self.bet)
        await game.start(interaction)
        self.stop()

    @discord.ui.button(label="Blackjack", style=discord.ButtonStyle.primary, emoji="🃏", row=0)
    async def blackjack_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        game = BlackjackGame(self.bot, self.user, self.bet)
        await game.start(interaction)
        self.stop()

    @discord.ui.button(label="Coinflip", style=discord.ButtonStyle.primary, emoji="🪙", row=0)
    async def coinflip_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        game = CoinflipGame(self.bot, self.user, self.bet)
        await game.start(interaction)
        self.stop()

    @discord.ui.button(label="Dice", style=discord.ButtonStyle.success, emoji="🎲", row=1)
    async def dice_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        game = DiceGame(self.bot, self.user, self.bet)
        await game.start(interaction)
        self.stop()

    @discord.ui.button(label="Minesweeper", style=discord.ButtonStyle.success, emoji="💣", row=1)
    async def minesweeper_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Show difficulty selector
        view = MinesweeperDifficultySelector(self.bot, self.user, self.bet)
        embed = discord.Embed(
            title="💣 Minesweeper - Select Difficulty",
            description="Choose your difficulty level:",
            color=CASINO_COLORS["minesweeper"]
        )
        apply_v2_embed_layout(view, embed=embed)
        await interaction.response.edit_message(view=view)
        self.stop()

    @discord.ui.button(label="Crash", style=discord.ButtonStyle.danger, emoji="📈", row=1)
    async def crash_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        game = CrashGame(self.bot, self.user, self.bet)
        await game.start(interaction)
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌", row=2)
    async def cancel_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        db = self.bot.db
        userid = str(self.user.id)
        db.addbalance(userid, self.bet)

        embed = discord.Embed(
            title="🎰 Casino - Cancelled",
            description=f"Bet refunded: **{money(self.bet)}**",
            color=CASINO_COLORS["neutral"]
        )
        await edit_as_v2_message(interaction, embed=embed, view=None)
        self.stop()

# ============= MINESWEEPER DIFFICULTY SELECTOR =============

class MinesweeperDifficultySelector(discord.ui.LayoutView):
    """Select minesweeper difficulty."""

    def __init__(self, bot, user: discord.User, bet: int):
        super().__init__(timeout=60)
        self.bot = bot
        self.user = user
        self.bet = bet

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user.id

    @discord.ui.button(label="Easy (3x3, 3 mines)", style=discord.ButtonStyle.success, emoji="🟢", row=0)
    async def easy_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        game = MinesweeperGame(self.user, self.bet, self.bot, "easy")
        embed = game.create_embed()
        apply_v2_embed_layout(game, embed=embed)
        await interaction.response.edit_message(view=game)
        self.stop()

    @discord.ui.button(label="Medium (4x4, 6 mines)", style=discord.ButtonStyle.primary, emoji="🟡", row=0)
    async def medium_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        game = MinesweeperGame(self.user, self.bet, self.bot, "medium")
        embed = game.create_embed()
        apply_v2_embed_layout(game, embed=embed)
        await interaction.response.edit_message(view=game)
        self.stop()

    @discord.ui.button(label="Hard (5x5, 10 mines)", style=discord.ButtonStyle.danger, emoji="🔴", row=0)
    async def hard_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        game = MinesweeperGame(self.user, self.bet, self.bot, "hard")
        embed = game.create_embed()
        apply_v2_embed_layout(game, embed=embed)
        await interaction.response.edit_message(view=game)
        self.stop()

    @discord.ui.button(label="Back", style=discord.ButtonStyle.secondary, emoji="◀️", row=1)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = CasinoMenuV2View(self.bot, self.user, self.bet)
        try:
            view.message = interaction.message
        except Exception:
            pass
        await interaction.response.edit_message(view=view)
        self.stop()

# ============= PLAY AGAIN VIEW =============

class PlayAgainView(discord.ui.LayoutView):
    """Reusable play again button."""

    def __init__(self, bot, user: discord.User, bet: int):
        super().__init__(timeout=120)
        self.bot = bot
        self.user = user
        self.bet = bet

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user.id

    @discord.ui.button(label="Play Again", style=discord.ButtonStyle.success, emoji="🔄")
    async def play_again(self, interaction: discord.Interaction, button: discord.ui.Button):
        db = self.bot.db
        userid = str(self.user.id)
        u = db.getuser(userid)
        balance = int(u.get("balance", 0))

        if balance < self.bet:
            return await interaction.response.send_message(
                f"❌ Not enough money! Need {money(self.bet)}, you have {money(balance)}",
                ephemeral=True
            )

        view = CasinoMenuV2View(self.bot, self.user, self.bet)
        try:
            view.message = interaction.message
        except Exception:
            pass
        await interaction.response.edit_message(view=view)
        self.stop()

    @discord.ui.button(label="Close", style=discord.ButtonStyle.secondary, emoji="❌")
    async def close_menu(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(view=None)
        self.stop()
# ============= SLOTS GAME =============

class SlotsGame:
    """🎰 Slot machine game."""

    SYMBOLS = ["🍒", "🍋", "🍊", "🍇", "💎", "7️⃣"]
    PAYOUTS = {
        "🍒🍒🍒": 2,
        "🍋🍋🍋": 3,
        "🍊🍊🍊": 4,
        "🍇🍇🍇": 5,
        "💎💎💎": 10,
        "7️⃣7️⃣7️⃣": 50,
    }

    def __init__(self, bot, user: discord.User, bet: int):
        self.bot = bot
        self.user = user
        self.bet = bet

    async def start(self, interaction: discord.Interaction):
        # Spinning animation
        await interaction.response.edit_message(
            embed=self._create_spinning_embed(),
            view=None
        )
        await asyncio.sleep(1.5)

        # Spin
        result = [random.choice(self.SYMBOLS) for _ in range(3)]
        result_str = "".join(result)

        # Check win
        payout_mult = self.PAYOUTS.get(result_str, 0)
        winnings = self.bet * payout_mult if payout_mult > 0 else 0

        # Update database
        db = self.bot.db
        userid = str(self.user.id)

        if winnings > 0:
            db.addbalance(userid, winnings)
            try:
                db.increment_stat(userid, "casino_total_won", winnings)
            except:
                pass
        
        try:
            db.increment_stat(userid, "casino_games_played", 1)
        except:
            pass

        u = db.getuser(userid)
        balance = int(u.get("balance", 0))

        embed = self._create_result_embed(result, payout_mult, winnings, balance)
        view = PlayAgainView(self.bot, self.user, self.bet)

        apply_v2_embed_layout(view, embed=embed)
        await interaction.edit_original_response(view=view)

    def _create_spinning_embed(self) -> discord.Embed:
        return discord.Embed(
            title="🎰 Slot Machine",
            description="# 🔄 🔄 🔄\n\n*Spinning...*",
            color=CASINO_COLORS["slots"]
        )

    def _create_result_embed(
        self,
        result: List[str],
        multiplier: int,
        winnings: int,
        balance: int
    ) -> discord.Embed:
        is_win = winnings > 0
        
        embed = discord.Embed(
            title="🎰 Slot Machine" + (" - JACKPOT!" if multiplier >= 10 else " - WIN!" if is_win else ""),
            color=CASINO_COLORS["win"] if is_win else CASINO_COLORS["lose"]
        )

        embed.description = f"# {' '.join(result)}\n\n"

        if is_win:
            profit = winnings - self.bet
            if multiplier >= 10:
                embed.description += f"🎉 **{multiplier}x MEGA WIN!** 🎉\n\n"
            else:
                embed.description += f"✨ **{multiplier}x Multiplier!** ✨\n\n"
            embed.description += f"💰 **Won:** {money(winnings)}\n"
            embed.description += f"📈 **Profit:** +{money(profit)}"
        else:
            embed.description += f"💸 **Lost:** {money(self.bet)}"

        embed.add_field(
            name="💎 Payout Table",
            value=(
                "7️⃣7️⃣7️⃣ = 50x  |  💎💎💎 = 10x\n"
                "🍇🍇🍇 = 5x  |  🍊🍊🍊 = 4x\n"
                "🍋🍋🍋 = 3x  |  🍒🍒🍒 = 2x"
            ),
            inline=False
        )

        embed.set_footer(text=f"Balance: {money(balance)} | Bet: {money(self.bet)}")
        
        return embed

# ============= BLACKJACK GAME =============

class BlackjackGame(discord.ui.LayoutView):
    """🃏 Blackjack game."""

    def __init__(self, bot, user: discord.User, bet: int):
        super().__init__(timeout=120)
        self.bot = bot
        self.user = user
        self.bet = bet

        # Create deck
        self.deck = self._create_deck()
        random.shuffle(self.deck)

        # Deal cards
        self.player_hand = [self.deck.pop(), self.deck.pop()]
        self.dealer_hand = [self.deck.pop(), self.deck.pop()]
        
        self.game_over = False
        self.player_stood = False
        self.doubled = False

    def _create_deck(self) -> List[str]:
        values = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        suits = ['♠️', '♥️', '♦️', '♣️']
        return [f"{v}{s}" for v in values for s in suits]

    def _card_value(self, card: str) -> int:
        value = card[:-2] if len(card) == 3 else card[0]
        if value in ['J', 'Q', 'K']:
            return 10
        elif value == 'A':
            return 11
        else:
            return int(value)

    def _hand_value(self, hand: List[str]) -> int:
        value = sum(self._card_value(card) for card in hand)
        aces = sum(1 for card in hand if card[0] == 'A')

        while value > 21 and aces:
            value -= 10
            aces -= 1

        return value

    def create_embed(self) -> discord.Embed:
        player_value = self._hand_value(self.player_hand)
        dealer_value = self._hand_value(self.dealer_hand)

        if not self.player_stood:
            dealer_display = f"{self.dealer_hand[0]} 🂠"
            dealer_value_display = "?"
        else:
            dealer_display = " ".join(self.dealer_hand)
            dealer_value_display = str(dealer_value)

        embed = discord.Embed(
            title="🃏 Blackjack",
            color=CASINO_COLORS["blackjack"]
        )

        embed.add_field(
            name=f"🎩 Dealer ({dealer_value_display})",
            value=f"`{dealer_display}`",
            inline=False
        )

        embed.add_field(
            name=f"👤 You ({player_value})",
            value=f"`{' '.join(self.player_hand)}`",
            inline=False
        )

        if not self.game_over:
            embed.add_field(
                name="💡 Goal",
                value="Get 21 or closer than dealer without going over!",
                inline=False
            )

        embed.set_footer(text=f"Bet: {money(self.bet)}")

        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ Not your game!", ephemeral=True)
            return False
        return True

    async def start(self, interaction: discord.Interaction):
        player_value = self._hand_value(self.player_hand)

        if player_value == 21:
            await self._end_game(interaction, "blackjack")
            return

        apply_v2_embed_layout(self, embed=self.create_embed())
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.primary, emoji="👆")
    async def hit_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.player_hand.append(self.deck.pop())
        player_value = self._hand_value(self.player_hand)

        # Disable double after first hit
        for item in iter_all_items(self):
            if hasattr(item, "label") and item.label == "Double":
                item.disabled = True

        if player_value > 21:
            await self._end_game(interaction, "bust")
        elif player_value == 21:
            await self._end_game(interaction, "stand")
        else:
            apply_v2_embed_layout(self, embed=self.create_embed())
            await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.success, emoji="✋")
    async def stand_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._end_game(interaction, "stand")

    @discord.ui.button(label="Double", style=discord.ButtonStyle.secondary, emoji="2️⃣")
    async def double_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if len(self.player_hand) != 2:
            return await interaction.response.send_message(
                "❌ Can only double on first turn!",
                ephemeral=True
            )

        db = self.bot.db
        userid = str(self.user.id)
        u = db.getuser(userid)
        balance = int(u.get("balance", 0))

        if balance < self.bet:
            return await interaction.response.send_message(
                f"❌ Need {money(self.bet)} to double down!",
                ephemeral=True
            )

        db.removebalance(userid, self.bet)
        try:
            db.increment_stat(userid, "casino_total_bet", self.bet)
        except:
            pass
        
        self.bet *= 2
        self.doubled = True

        self.player_hand.append(self.deck.pop())
        await self._end_game(interaction, "double")

    async def _end_game(self, interaction: discord.Interaction, reason: str):
        self.player_stood = True
        self.game_over = True
        self.clear_items()

        player_value = self._hand_value(self.player_hand)
        dealer_value = self._hand_value(self.dealer_hand)

        # Dealer draws to 17+
        while dealer_value < 17 and player_value <= 21:
            self.dealer_hand.append(self.deck.pop())
            dealer_value = self._hand_value(self.dealer_hand)

        db = self.bot.db
        userid = str(self.user.id)

        # Determine winner
        if reason == "blackjack":
            winnings = int(self.bet * 2.5)
            db.addbalance(userid, winnings)
            result = "🎉 BLACKJACK!"
            result_desc = f"💰 Won {money(winnings)}\n📈 Profit: +{money(int(self.bet * 1.5))}"
            color = CASINO_COLORS["win"]
            try:
                db.increment_stat(userid, "casino_total_won", winnings)
            except:
                pass
        elif reason == "bust":
            result = "💥 BUST!"
            result_desc = f"💸 Lost {money(self.bet)}"
            color = CASINO_COLORS["lose"]
        elif dealer_value > 21:
            winnings = self.bet * 2
            db.addbalance(userid, winnings)
            result = "🎉 DEALER BUST!"
            result_desc = f"💰 Won {money(winnings)}\n📈 Profit: +{money(self.bet)}"
            color = CASINO_COLORS["win"]
            try:
                db.increment_stat(userid, "casino_total_won", winnings)
            except:
                pass
        elif player_value > dealer_value:
            winnings = self.bet * 2
            db.addbalance(userid, winnings)
            result = "✅ YOU WIN!"
            result_desc = f"💰 Won {money(winnings)}\n📈 Profit: +{money(self.bet)}"
            color = CASINO_COLORS["win"]
            try:
                db.increment_stat(userid, "casino_total_won", winnings)
            except:
                pass
        elif player_value < dealer_value:
            result = "❌ DEALER WINS"
            result_desc = f"💸 Lost {money(self.bet)}"
            color = CASINO_COLORS["lose"]
        else:
            db.addbalance(userid, self.bet)
            result = "🤝 PUSH"
            result_desc = f"Bet returned: {money(self.bet)}"
            color = CASINO_COLORS["neutral"]

        embed = self.create_embed()
        embed.add_field(name=result, value=result_desc, inline=False)
        embed.color = color

        try:
            db.increment_stat(userid, "casino_games_played", 1)
        except:
            pass

        u = db.getuser(userid)
        balance = int(u.get("balance", 0))
        embed.set_footer(text=f"Balance: {money(balance)} | Bet: {money(self.bet)}")

        original_bet = self.bet // 2 if self.doubled else self.bet
        play_again_view = PlayAgainView(self.bot, self.user, original_bet)

        apply_v2_embed_layout(play_again_view, embed=embed)
        await interaction.response.edit_message(view=play_again_view)
        self.stop()

# ============= COINFLIP GAME =============

class CoinflipGame(discord.ui.LayoutView):
    """🪙 Coinflip game."""

    def __init__(self, bot, user: discord.User, bet: int):
        super().__init__(timeout=60)
        self.bot = bot
        self.user = user
        self.bet = bet

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ Not your game!", ephemeral=True)
            return False
        return True

    async def start(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🪙 Coinflip",
            description="Choose **Heads** or **Tails**!\n\n**Win:** 2x your bet\n**Odds:** 50/50",
            color=CASINO_COLORS["coinflip"]
        )
        embed.set_footer(text=f"Bet: {money(self.bet)}")
        apply_v2_embed_layout(self, embed=embed)
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Heads", style=discord.ButtonStyle.primary, emoji="🪙")
    async def heads_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._flip_coin(interaction, "Heads")

    @discord.ui.button(label="Tails", style=discord.ButtonStyle.primary, emoji="🪙")
    async def tails_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._flip_coin(interaction, "Tails")

    async def _flip_coin(self, interaction: discord.Interaction, choice: str):
        self.clear_items()

        embed = discord.Embed(
            title="🪙 Coinflip",
            description=f"You chose: **{choice}**\n\n# 🔄\n*Flipping...*",
            color=CASINO_COLORS["coinflip"]
        )
        await edit_as_v2_message(interaction, embed=embed, view=None)
        await asyncio.sleep(1.5)

        result = random.choice(["Heads", "Tails"])
        won = result == choice

        db = self.bot.db
        userid = str(self.user.id)

        if won:
            winnings = self.bet * 2
            db.addbalance(userid, winnings)
            try:
                db.increment_stat(userid, "casino_total_won", winnings)
            except:
                pass
            
            embed = discord.Embed(
                title=f"🪙 {result}!",
                description=f"You chose: **{choice}**\n\n✅ **YOU WIN!**\n\n💰 **Won:** {money(winnings)}\n📈 **Profit:** +{money(self.bet)}",
                color=CASINO_COLORS["win"]
            )
        else:
            embed = discord.Embed(
                title=f"🪙 {result}!",
                description=f"You chose: **{choice}**\n\n❌ **YOU LOSE!**\n\n💸 **Lost:** {money(self.bet)}",
                color=CASINO_COLORS["lose"]
            )

        try:
            db.increment_stat(userid, "casino_games_played", 1)
        except:
            pass

        u = db.getuser(userid)
        balance = int(u.get("balance", 0))
        embed.set_footer(text=f"Balance: {money(balance)} | Bet: {money(self.bet)}")

        view = PlayAgainView(self.bot, self.user, self.bet)
        apply_v2_embed_layout(view, embed=embed)
        await interaction.edit_original_response(view=view)
        self.stop()

# ============= DICE GAME =============

class DiceGame:
    """🎲 Dice game."""

    def __init__(self, bot, user: discord.User, bet: int):
        self.bot = bot
        self.user = user
        self.bet = bet

    async def start(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎲 Dice Roll",
            description="# 🎲 vs 🎲\n\n*Rolling...*",
            color=CASINO_COLORS["dice"]
        )
        await edit_as_v2_message(interaction, embed=embed, view=None)
        await asyncio.sleep(1.5)

        player_roll = random.randint(1, 6)
        dealer_roll = random.randint(1, 6)

        db = self.bot.db
        userid = str(self.user.id)

        if player_roll > dealer_roll:
            winnings = self.bet * 2
            db.addbalance(userid, winnings)
            try:
                db.increment_stat(userid, "casino_total_won", winnings)
            except:
                pass
            result = f"✅ **YOU WIN!**\n\n💰 **Won:** {money(winnings)}\n📈 **Profit:** +{money(self.bet)}"
            color = CASINO_COLORS["win"]
        elif player_roll < dealer_roll:
            result = f"❌ **YOU LOSE!**\n\n💸 **Lost:** {money(self.bet)}"
            color = CASINO_COLORS["lose"]
        else:
            db.addbalance(userid, self.bet)
            result = f"🤝 **TIE!**\n\nBet returned: {money(self.bet)}"
            color = CASINO_COLORS["neutral"]

        try:
            db.increment_stat(userid, "casino_games_played", 1)
        except:
            pass

        u = db.getuser(userid)
        balance = int(u.get("balance", 0))

        embed = discord.Embed(title="🎲 Dice Roll", color=color)
        embed.add_field(name="👤 Your Roll", value=f"# {player_roll}", inline=True)
        embed.add_field(name="🎩 Dealer Roll", value=f"# {dealer_roll}", inline=True)
        embed.add_field(name="Result", value=result, inline=False)
        embed.set_footer(text=f"Balance: {money(balance)} | Bet: {money(self.bet)}")

        view = PlayAgainView(self.bot, self.user, self.bet)
        apply_v2_embed_layout(view, embed=embed)
        await interaction.edit_original_response(view=view)
# ============= MINESWEEPER GAME (FIXED) =============

class MinesweeperGame(discord.ui.LayoutView):
    """💣 Minesweeper casino game - FIXED for Discord limits."""

    def __init__(self, user: discord.User, bet: int, bot, difficulty: str = "easy"):
        super().__init__(timeout=180)
        self.user = user
        self.bet = bet
        self.bot = bot
        self.difficulty = difficulty

        # Grid configs (FIXED to respect Discord's 5x5 limit)
        self.grid_configs = {
            "easy": {"size": 3, "mines": 3, "multiplier": 1.5},
            "medium": {"size": 4, "mines": 6, "multiplier": 2.0},
            "hard": {"size": 5, "mines": 10, "multiplier": 3.0}
        }

        config = self.grid_configs[difficulty]
        self.size = config["size"]
        self.mine_count = config["mines"]
        self.max_multiplier = config["multiplier"]

        # Create grid
        self.grid = [[False for _ in range(self.size)] for _ in range(self.size)]
        self.revealed = [[False for _ in range(self.size)] for _ in range(self.size)]

        # Place mines randomly
        mines_placed = 0
        while mines_placed < self.mine_count:
            x = random.randint(0, self.size - 1)
            y = random.randint(0, self.size - 1)
            if not self.grid[x][y]:
                self.grid[x][y] = True
                mines_placed += 1

        self.safe_revealed = 0
        self.total_safe = (self.size * self.size) - self.mine_count
        self.game_over = False
        self.won = False

        # Create buttons (grid layout)
        for row in range(self.size):
            for col in range(self.size):
                button = MinesweeperButton(row, col, self)
                self.add_item(button)

        # Add cash out button on last row
        cashout = discord.ui.Button(
            style=discord.ButtonStyle.success,
            label="💰 Cash Out",
            row=4  # Always on row 4 (bottom)
        )
        cashout.callback = self.cashout
        self.add_item(cashout)

    def count_adjacent_mines(self, row: int, col: int) -> int:
        """Count mines around a cell."""
        count = 0
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                nx, ny = row + dx, col + dy
                if 0 <= nx < self.size and 0 <= ny < self.size:
                    if self.grid[nx][ny]:
                        count += 1
        return count

    def reveal_cell(self, row: int, col: int) -> bool:
        """Reveal a cell. Returns True if mine hit."""
        if self.revealed[row][col]:
            return False

        self.revealed[row][col] = True

        if self.grid[row][col]:
            # Hit mine
            self.game_over = True
            self.won = False
            return True
        else:
            # Safe cell
            self.safe_revealed += 1

            # Check win
            if self.safe_revealed >= self.total_safe:
                self.game_over = True
                self.won = True

            return False

    def get_current_multiplier(self) -> float:
        """Get current multiplier based on progress."""
        if self.safe_revealed == 0:
            return 1.0
        progress = self.safe_revealed / self.total_safe
        return 1.0 + (progress * (self.max_multiplier - 1.0))

    def create_embed(self) -> discord.Embed:
        """Create game embed."""
        if self.game_over:
            if self.won:
                winnings = int(self.bet * self.max_multiplier)
                profit = winnings - self.bet
                embed = discord.Embed(
                    title="💎 Minesweeper - CLEARED!",
                    description=f"🎉 You cleared all safe cells!\n\n💰 **Won:** {money(winnings)}\n📈 **Profit:** +{money(profit)}\n**Multiplier:** {self.max_multiplier:.2f}x",
                    color=CASINO_COLORS["win"]
                )
            else:
                embed = discord.Embed(
                    title="💣 Minesweeper - BOOM!",
                    description=f"You hit a mine!\n\n💸 **Lost:** {money(self.bet)}\n**Safe Revealed:** {self.safe_revealed}/{self.total_safe}",
                    color=CASINO_COLORS["lose"]
                )
        else:
            current_mult = self.get_current_multiplier()
            current_winnings = int(self.bet * current_mult)
            current_profit = current_winnings - self.bet

            embed = discord.Embed(
                title=f"💣 Minesweeper - {self.difficulty.title()}",
                color=CASINO_COLORS["minesweeper"]
            )

            embed.add_field(
                name="📊 Progress",
                value=f"**Safe:** {self.safe_revealed}/{self.total_safe}\n**Mines:** {self.mine_count}\n**Grid:** {self.size}x{self.size}",
                inline=True
            )

            embed.add_field(
                name="💰 Current Stats",
                value=f"**Multiplier:** {current_mult:.2f}x\n**Winnings:** {money(current_winnings)}\n**Profit:** +{money(current_profit)}",
                inline=True
            )

            embed.add_field(
                name="💡 Tip",
                value="Click cells to reveal. Avoid mines! Cash out anytime to keep your winnings.",
                inline=False
            )

        return embed

    async def cashout(self, interaction: discord.Interaction):
        """Cash out winnings."""
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("❌ Not your game!", ephemeral=True)

        if self.game_over:
            return await interaction.response.send_message("❌ Game already over!", ephemeral=True)

        if self.safe_revealed == 0:
            return await interaction.response.send_message("❌ Reveal at least one cell first!", ephemeral=True)

        current_mult = self.get_current_multiplier()
        winnings = int(self.bet * current_mult)
        profit = winnings - self.bet

        db = self.bot.db
        userid = str(interaction.user.id)
        db.addbalance(userid, winnings)
        
        try:
            db.increment_stat(userid, "casino_total_won", winnings)
            db.increment_stat(userid, "casino_games_played", 1)
        except:
            pass

        self.game_over = True
        self.won = True

        # Disable all buttons
        for item in iter_all_items(self):
            item.disabled = True

        u = db.getuser(userid)
        balance = int(u.get("balance", 0))

        embed = discord.Embed(
            title="💰 Cashed Out!",
            description=f"💵 Smart play!\n\n💰 **Won:** {money(winnings)}\n📈 **Profit:** +{money(profit)}\n**Multiplier:** {current_mult:.2f}x\n**Safe Revealed:** {self.safe_revealed}/{self.total_safe}",
            color=CASINO_COLORS["win"]
        )
        embed.set_footer(text=f"Balance: {money(balance)}")

        view = PlayAgainView(self.bot, self.user, self.bet)

        apply_v2_embed_layout(view, embed=embed)
        await interaction.response.edit_message(view=view)
        self.stop()


class MinesweeperButton(discord.ui.Button):
    """Individual minesweeper cell button."""

    def __init__(self, row: int, col: int, game: MinesweeperGame):
        super().__init__(style=discord.ButtonStyle.secondary, label="❓", row=row)
        self.row = row
        self.col = col
        self.game = game

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.game.user.id:
            return await interaction.response.send_message("❌ Not your game!", ephemeral=True)

        if self.game.game_over:
            return await interaction.response.send_message("❌ Game over!", ephemeral=True)

        # Reveal cell
        hit_mine = self.game.reveal_cell(self.row, self.col)

        # Update button
        if self.game.grid[self.row][self.col]:
            # Mine
            self.emoji = "💣"
            self.label = ""
            self.style = discord.ButtonStyle.danger
        else:
            # Safe
            adjacent = self.game.count_adjacent_mines(self.row, self.col)
            if adjacent == 0:
                self.emoji = "✅"
                self.label = ""
            else:
                self.label = str(adjacent)
                self.emoji = None
            self.style = discord.ButtonStyle.success

        self.disabled = True

        if self.game.game_over:
            # Reveal all mines
            for item in iter_all_items(self.view):
                if isinstance(item, MinesweeperButton):
                    if self.game.grid[item.row][item.col]:
                        item.emoji = "💣"
                        item.label = ""
                        item.style = discord.ButtonStyle.danger
                    item.disabled = True

            # Update database
            db = self.game.bot.db
            userid = str(interaction.user.id)

            if self.game.won:
                winnings = int(self.game.bet * self.game.max_multiplier)
                db.addbalance(userid, winnings)
                try:
                    db.increment_stat(userid, "casino_total_won", winnings)
                except:
                    pass

            try:
                db.increment_stat(userid, "casino_games_played", 1)
            except:
                pass

            u = db.getuser(userid)
            balance = int(u.get("balance", 0))

            embed = self.game.create_embed()
            embed.set_footer(text=f"Balance: {money(balance)}")

            view = PlayAgainView(self.game.bot, self.game.user, self.game.bet)

            apply_v2_embed_layout(view, embed=embed)
            await interaction.response.edit_message(view=view)
            self.view.stop()
        else:
            apply_v2_embed_layout(self.view, embed=self.game.create_embed())
            await interaction.response.edit_message(view=self.view)


# ============= CRASH GAME =============

class CrashGame(discord.ui.LayoutView):
    """📈 Crash multiplier game."""

    def __init__(self, bot, user: discord.User, bet: int):
        super().__init__(timeout=60)
        self.bot = bot
        self.user = user
        self.bet = bet
        self.multiplier = 1.0
        self.crashed = False
        self.cashed_out = False
        self.message = None

        # Random crash point (weighted towards lower)
        rand = random.random()
        if rand < 0.5:
            self.crash_point = round(random.uniform(1.1, 2.0), 2)
        elif rand < 0.8:
            self.crash_point = round(random.uniform(2.0, 5.0), 2)
        else:
            self.crash_point = round(random.uniform(5.0, 10.0), 2)

    def create_embed(self) -> discord.Embed:
        """Create game embed."""
        current_win = int(self.bet * self.multiplier)
        current_profit = current_win - self.bet

        if self.crashed:
            embed = discord.Embed(
                title="📈 Crash - CRASHED!",
                description=f"# 💥 {self.crash_point:.2f}x\n\nThe multiplier crashed!\n\n💸 **Lost:** {money(self.bet)}",
                color=CASINO_COLORS["lose"]
            )
        elif self.cashed_out:
            embed = discord.Embed(
                title="📈 Crash - Cashed Out!",
                description=f"# 💰 {self.multiplier:.2f}x\n\n✅ Successfully cashed out!\n\n💰 **Won:** {money(current_win)}\n📈 **Profit:** +{money(current_profit)}",
                color=CASINO_COLORS["win"]
            )
        else:
            embed = discord.Embed(
                title="📈 Crash Game",
                description=f"# 🚀 {self.multiplier:.2f}x\n\n📈 **Rising...**",
                color=CASINO_COLORS["crash"]
            )

            embed.add_field(
                name="💰 Current Winnings",
                value=f"**Win:** {money(current_win)}\n**Profit:** +{money(current_profit)}",
                inline=True
            )

            embed.add_field(
                name="⚡ Quick Stats",
                value=f"**Bet:** {money(self.bet)}\n**Multiplier:** {self.multiplier:.2f}x",
                inline=True
            )

        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ Not your game!", ephemeral=True)
            return False
        return True

    async def start(self, interaction: discord.Interaction):
        """Start the crash game."""
        embed = self.create_embed()
        embed.set_footer(text="💡 Cash out before it crashes!")
        apply_v2_embed_layout(self, embed=embed)
        await interaction.response.edit_message(view=self)
        self.message = await interaction.original_response()

        # Start multiplier
        asyncio.create_task(self._run_multiplier())

    async def _run_multiplier(self):
        """Increment multiplier until crash."""
        await asyncio.sleep(1)

        while not self.crashed and not self.cashed_out:
            self.multiplier = round(self.multiplier + 0.10, 2)

            if self.multiplier >= self.crash_point:
                self.crashed = True
                self.clear_items()

                db = self.bot.db
                userid = str(self.user.id)
                
                try:
                    db.increment_stat(userid, "casino_games_played", 1)
                except:
                    pass

                u = db.getuser(userid)
                balance = int(u.get("balance", 0))

                embed = self.create_embed()
                embed.set_footer(text=f"Balance: {money(balance)}")

                view = PlayAgainView(self.bot, self.user, self.bet)

                try:
                    apply_v2_embed_layout(view, embed=embed)
                    await self.message.edit(view=view)
                except:
                    pass

                self.stop()
                break

            try:
                apply_v2_embed_layout(self, embed=self.create_embed())
                await self.message.edit(view=self)
            except:
                break

            await asyncio.sleep(0.7)

    @discord.ui.button(label="Cash Out", style=discord.ButtonStyle.success, emoji="💰")
    async def cashout_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.crashed:
            return await interaction.response.send_message("❌ Already crashed!", ephemeral=True)

        if self.cashed_out:
            return await interaction.response.send_message("❌ Already cashed out!", ephemeral=True)

        self.cashed_out = True
        self.clear_items()

        winnings = int(self.bet * self.multiplier)

        db = self.bot.db
        userid = str(self.user.id)
        db.addbalance(userid, winnings)
        
        try:
            db.increment_stat(userid, "casino_total_won", winnings)
            db.increment_stat(userid, "casino_games_played", 1)
        except:
            pass

        u = db.getuser(userid)
        balance = int(u.get("balance", 0))

        embed = self.create_embed()
        embed.set_footer(text=f"Balance: {money(balance)}")

        view = PlayAgainView(self.bot, self.user, self.bet)

        apply_v2_embed_layout(view, embed=embed)
        await interaction.response.edit_message(view=view)
        self.stop()
