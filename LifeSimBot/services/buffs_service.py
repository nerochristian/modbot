# services/buffs_service.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any

from services.family_service import calculate_family_bonus
from services.relationships_service import RelationshipsService
from data.properties_advanced import PROPERTY_TYPES
# if you have pets_service later, we can plug it here too


@dataclass
class UserBuffs:
    xp_mult: float = 1.0
    money_mult: float = 1.0
    work_success_mult: float = 1.0
    crime_success_mult: float = 1.0
    happiness_regen: int = 0
    energy_regen: int = 0

    def as_dict(self) -> Dict[str, Any]:
        return {
            "xp_mult": self.xp_mult,
            "money_mult": self.money_mult,
            "work_success_mult": self.work_success_mult,
            "crime_success_mult": self.crime_success_mult,
            "happiness_regen": self.happiness_regen,
            "energy_regen": self.energy_regen,
        }


class BuffsService:
    """Aggregate buffs from family, relationships, housing, pets, etc."""

    def __init__(self, db):
        self.db = db
        self.relationships = RelationshipsService(db)

    def _family_bonuses(self, user_data: Dict[str, Any]) -> Dict[str, int]:
        """Wrap existing family bonus logic."""
        return calculate_family_bonus(user_data)

    def _relationship_bonuses(self, user_id: str, user_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Simple relationship buffs:
        - Partner gives small global XP/money buffs.
        - High affection with partner can buff work & crime success a bit.
        """
        spouse_id = user_data.get("spouse")
        if not spouse_id:
            return {
                "xp_mult": 1.0,
                "money_mult": 1.0,
                "work_success_mult": 1.0,
                "crime_success_mult": 1.0,
            }

        rel = self.relationships.get_relationship(user_id, spouse_id)
        affection = rel.affection

        xp_mult = 1.0
        money_mult = 1.0
        work_mult = 1.0
        crime_mult = 1.0

        if rel.status == "partner":
            if affection >= 60:
                xp_mult += 0.05
                money_mult += 0.05
            if affection >= 120:
                xp_mult += 0.05
                money_mult += 0.05
                work_mult += 0.05
            if affection >= 160:
                crime_mult += 0.05

        return {
            "xp_mult": xp_mult,
            "money_mult": money_mult,
            "work_success_mult": work_mult,
            "crime_success_mult": crime_mult,
        }

    def _properties_bonuses(self, user_id: str) -> Dict[str, int]:
        """
        Housing buffs:
        - Sum comfort and energy_bonus from all owned properties.
        """
        total_comfort = 0
        total_energy = 0

        props = self.db.get_user_properties(user_id)
        for prop in props:
            ptype = PROPERTY_TYPES.get(prop["property_type"])
            if not ptype:
                continue
            total_comfort += int(ptype.get("comfort", 0))
            total_energy += int(ptype.get("energy_bonus", 0))

        return {
            "happiness_regen": total_comfort,
            "energy_regen": total_energy,
        }

    # def _pets_bonuses(...):  # later

    def get_user_buffs(self, user_id: str) -> UserBuffs:
        """
        Returns final buffs for a user. You call this inside work/crime/etc.
        """
        u = self.db.getuser(user_id)

        buffs = UserBuffs()

        # Family bonuses → convert to multipliers
        fam = self._family_bonuses(u)
        # +xp_bonus% and +money_bonus% from family
        buffs.xp_mult += fam.get("xp_bonus", 0) / 100.0
        buffs.money_mult += fam.get("money_bonus", 0) / 100.0
        buffs.happiness_regen += fam.get("happiness_bonus", 0)

        # Relationship bonuses with spouse
        rel_b = self._relationship_bonuses(user_id, u)
        buffs.xp_mult *= rel_b["xp_mult"]
        buffs.money_mult *= rel_b["money_mult"]
        buffs.work_success_mult *= rel_b["work_success_mult"]
        buffs.crime_success_mult *= rel_b["crime_success_mult"]

        # Property bonuses
        prop_b = self._properties_bonuses(user_id)
        buffs.happiness_regen += prop_b["happiness_regen"]
        buffs.energy_regen += prop_b["energy_regen"]

        # Pets buffs can be folded in here later

        return buffs
