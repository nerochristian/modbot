from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

# Support both root-level and LifeSim-local .env files.
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(BASE_DIR / ".env")


def _env_int(default: int, *keys: str, minimum: int = 0) -> int:
    for key in keys:
        raw = os.getenv(key)
        if raw is None:
            continue
        try:
            return max(minimum, int(raw))
        except ValueError:
            continue
    return max(minimum, default)


def _env_float(default: float, *keys: str, minimum: float = 0.0, maximum: float = 1.0) -> float:
    for key in keys:
        raw = os.getenv(key)
        if raw is None:
            continue
        try:
            value = float(raw)
            return max(minimum, min(maximum, value))
        except ValueError:
            continue
    return max(minimum, min(maximum, default))


class LifeSimConfig:
    """
    Centralized tuning config for gameplay/cooldowns.
    Edit defaults here or override via .env.
    """

    class COOLDOWNS:
        # Economy / utility
        DAILY = _env_int(8 * 3600, "LIFESIM_DAILY_COOLDOWN", "DAILY_COOLDOWN")
        WORK = _env_int(0, "LIFESIM_WORK_COOLDOWN", "WORK_COOLDOWN")
        BEG = _env_int(5 * 60, "LIFESIM_BEG_COOLDOWN", "BEG_COOLDOWN")
        SLEEP = _env_int(8 * 3600, "LIFESIM_SLEEP_COOLDOWN", "SLEEP_COOLDOWN")
        FARM = _env_int(3600, "LIFESIM_FARM_COOLDOWN", "FARM_COOLDOWN")
        FISH = _env_int(1800, "LIFESIM_FISH_COOLDOWN", "FISH_COOLDOWN")

        # Crime
        ROB = _env_int(2 * 3600, "LIFESIM_ROB_COOLDOWN", "ROB_COOLDOWN")
        CRIME = _env_int(30 * 60, "LIFESIM_CRIME_COOLDOWN", "CRIME_COOLDOWN")
        HEIST = _env_int(24 * 3600, "LIFESIM_HEIST_COOLDOWN", "HEIST_COOLDOWN")
        ESCAPE_ATTEMPT = _env_int(
            15 * 60,
            "LIFESIM_ESCAPE_ATTEMPT_COOLDOWN",
            "ESCAPE_ATTEMPT_COOLDOWN",
        )

        # Social / misc
        RELATIONSHIP_INTERACTION = _env_int(
            5 * 60,
            "LIFESIM_RELATIONSHIP_INTERACTION_COOLDOWN",
            "RELATIONSHIP_INTERACTION_COOLDOWN",
        )
        GIFT = _env_int(24 * 3600, "LIFESIM_GIFT_COOLDOWN", "GIFT_COOLDOWN")
        BATTLE = _env_int(15 * 60, "LIFESIM_BATTLE_COOLDOWN", "BATTLE_COOLDOWN")

    class ECONOMY:
        STARTING_BALANCE = _env_int(500, "LIFESIM_STARTING_BALANCE")
        STARTING_BANK = _env_int(0, "LIFESIM_STARTING_BANK")
        STARTING_BANK_LIMIT = _env_int(5000, "LIFESIM_STARTING_BANK_LIMIT")

        DAILY_BASE = _env_int(1000, "LIFESIM_DAILY_BASE", "DAILY_REWARD")
        DAILY_STREAK_BONUS = _env_int(250, "LIFESIM_DAILY_STREAK_BONUS")
        MAX_STREAK = _env_int(10, "LIFESIM_MAX_DAILY_STREAK")

        TRANSFER_MIN = _env_int(10, "LIFESIM_TRANSFER_MIN")
        TAX_RATE = _env_float(0.03, "LIFESIM_TAX_RATE")

    class CRIME:
        ROB_SUCCESS_BASE = _env_float(0.45, "LIFESIM_ROB_SUCCESS_BASE")
        SHOPLIFT_SUCCESS_BASE = _env_float(0.60, "LIFESIM_SHOPLIFT_SUCCESS_BASE")
        HEIST_SUCCESS_BASE = _env_float(0.25, "LIFESIM_HEIST_SUCCESS_BASE")

        FINE_PERCENT_MIN = _env_float(0.10, "LIFESIM_FINE_PERCENT_MIN")
        FINE_PERCENT_MAX = _env_float(0.30, "LIFESIM_FINE_PERCENT_MAX")

        JAIL_MIN = _env_int(5 * 60, "LIFESIM_JAIL_MIN_SECONDS")
        JAIL_MAX = _env_int(2 * 3600, "LIFESIM_JAIL_MAX_SECONDS")

        ROB_ENERGY_COST = _env_int(15, "LIFESIM_ROB_ENERGY_COST", "ROB_ENERGY_COST")
        MIN_ROB_BALANCE = _env_int(100, "LIFESIM_MIN_ROB_BALANCE", "MIN_ROB_BALANCE")

    class JOBS:
        MAX_SHIFT_HOURS = _env_int(8, "LIFESIM_MAX_SHIFT_HOURS", minimum=1)
        BASE_PAY_PER_HOUR = _env_int(50, "LIFESIM_BASE_PAY_PER_HOUR", minimum=1)
        XP_PER_WORK = _env_int(10, "LIFESIM_XP_PER_WORK", minimum=1)

    class CAPS:
        MAX_HEALTH = _env_int(100, "LIFESIM_MAX_HEALTH", minimum=1)
        MAX_ENERGY = _env_int(100, "LIFESIM_MAX_ENERGY", minimum=1)
        MAX_HUNGER = _env_int(100, "LIFESIM_MAX_HUNGER", minimum=1)
        MAX_HAPPINESS = _env_int(100, "LIFESIM_MAX_HAPPINESS", minimum=1)
