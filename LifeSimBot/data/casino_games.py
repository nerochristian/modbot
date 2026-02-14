# data/casino_games.py
from __future__ import annotations

CASINO_GAMES = {
    "slots": {
        "name": "🎰 Slot Machine",
        "description": "Spin the reels and match symbols",
        "min_bet": 10,
        "max_bet": 10000,
        "house_edge": 0.05,  # 5% house edge
        "multipliers": {
            "🍒🍒🍒": 10,
            "🍋🍋🍋": 15,
            "🍊🍊🍊": 20,
            "🍇🍇🍇": 30,
            "💎💎💎": 50,
            "7️⃣7️⃣7️⃣": 100
        },
        "emoji": "🎰"
    },
    "blackjack": {
        "name": "🃏 Blackjack",
        "description": "Beat the dealer without going over 21",
        "min_bet": 20,
        "max_bet": 5000,
        "house_edge": 0.03,
        "payout": 2.0,  # 2:1 for win
        "blackjack_payout": 2.5,  # 5:2 for blackjack
        "emoji": "🃏"
    },
    "roulette": {
        "name": "🎡 Roulette",
        "description": "Bet on red, black, or numbers",
        "min_bet": 10,
        "max_bet": 10000,
        "house_edge": 0.027,
        "payouts": {
            "color": 2,      # red/black pays 2:1
            "even_odd": 2,   # even/odd pays 2:1
            "number": 36,    # single number pays 36:1
            "dozen": 3,      # dozen pays 3:1
            "column": 3      # column pays 3:1
        },
        "emoji": "🎡"
    },
    "coinflip": {
        "name": "🪙 Coin Flip",
        "description": "Simple 50/50 chance",
        "min_bet": 5,
        "max_bet": 50000,
        "house_edge": 0.02,
        "payout": 2.0,
        "emoji": "🪙"
    },
    "dice": {
        "name": "🎲 Dice Roll",
        "description": "Roll higher than the dealer",
        "min_bet": 10,
        "max_bet": 25000,
        "house_edge": 0.03,
        "payout": 2.0,
        "emoji": "🎲"
    },
    "mines": {
        "name": "💣 Mines",
        "description": "Reveal safe tiles and cash out",
        "min_bet": 20,
        "max_bet": 10000,
        "house_edge": 0.04,
        "grid_size": 25,  # 5x5 grid
        "mine_count": 5,
        "multiplier_per_reveal": 1.2,
        "emoji": "💣"
    },
    "crash": {
        "name": "🚀 Crash",
        "description": "Cash out before it crashes",
        "min_bet": 10,
        "max_bet": 20000,
        "house_edge": 0.03,
        "max_multiplier": 10.0,
        "emoji": "🚀"
    },
    "poker": {
        "name": "🂡 Video Poker",
        "description": "Make the best 5-card hand",
        "min_bet": 25,
        "max_bet": 5000,
        "house_edge": 0.04,
        "payouts": {
            "royal_flush": 800,
            "straight_flush": 50,
            "four_kind": 25,
            "full_house": 9,
            "flush": 6,
            "straight": 4,
            "three_kind": 3,
            "two_pair": 2,
            "jacks_better": 1
        },
        "emoji": "🂡"
    }
}

# VIP Tier benefits
VIP_TIERS = {
    0: {
        "name": "Bronze",
        "required_wagered": 0,
        "perks": [],
        "emoji": "🥉",
        "color": 0xCD7F32
    },
    1: {
        "name": "Silver",
        "required_wagered": 10000,
        "perks": ["5% rakeback", "+5% better odds"],
        "emoji": "🥈",
        "color": 0xC0C0C0
    },
    2: {
        "name": "Gold",
        "required_wagered": 50000,
        "perks": ["10% rakeback", "+10% better odds", "Daily bonus"],
        "emoji": "🥇",
        "color": 0xFFD700
    },
    3: {
        "name": "Platinum",
        "required_wagered": 250000,
        "perks": ["15% rakeback", "+15% better odds", "Daily bonus", "Free spins"],
        "emoji": "💎",
        "color": 0xE5E4E2
    },
    4: {
        "name": "Diamond",
        "required_wagered": 1000000,
        "perks": ["20% rakeback", "+20% better odds", "Daily bonus", "Free spins", "VIP lounge"],
        "emoji": "💠",
        "color": 0xB9F2FF
    }
}
