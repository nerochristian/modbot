from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Literal


INTERACTION_COOLDOWN = timedelta(minutes=5)

RelationshipStatus = Literal["stranger", "friend", "partner", "ex"]
InteractionType = Literal["talk", "hangout", "flirt"]


@dataclass
class Relationship:
    user_id: str
    target_id: str
    affection: int
    status: RelationshipStatus
    last_interaction: str | None = None

    @classmethod
    def from_row(cls, row: dict) -> "Relationship":
        return cls(
            user_id=row["user_id"],
            target_id=row["target_id"],
            affection=int(row["affection"]),
            status=row["status"],
            last_interaction=row.get("last_interaction"),
        )

    def can_interact(self) -> tuple[bool, int]:
        """Return (can_interact, seconds_remaining)."""
        if not self.last_interaction:
            return True, 0

        try:
            last = datetime.fromisoformat(self.last_interaction)
            # FIX: make sure stored time is timezone-aware
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
        except Exception:
            return True, 0

        now = datetime.now(timezone.utc)
        delta = now - last
        if delta >= INTERACTION_COOLDOWN:
            return True, 0

        remaining = int((INTERACTION_COOLDOWN - delta).total_seconds())
        return False, max(0, remaining)


class RelationshipsService:
    def __init__(self, db):
        self.db = db

    def get_relationship(self, user_id: str, target_id: str) -> Relationship:
        row = self.db.get_relationship(user_id, target_id)
        if not row:
            row = self.db.upsert_relationship(user_id, target_id, 0)
        return Relationship.from_row(row)

    def list_relationships(self, user_id: str) -> list[Relationship]:
        rows = self.db.get_relationships_for_user(user_id)
        return [Relationship.from_row(r) for r in rows]

    def interaction_affection_delta(self, interaction_type: InteractionType) -> int:
        if interaction_type == "talk":
            return 3
        if interaction_type == "hangout":
            return 6
        if interaction_type == "flirt":
            return 10
        return 0

    def apply_interaction(
        self,
        user_id: str,
        target_id: str,
        interaction_type: InteractionType,
    ) -> tuple[Relationship, int]:
        rel = self.get_relationship(user_id, target_id)
        can, remaining = rel.can_interact()
        if not can:
            return rel, remaining

        delta = self.interaction_affection_delta(interaction_type)

        new_status: RelationshipStatus = rel.status
        new_affection = rel.affection + delta

        if new_affection >= 80 and rel.status in ("stranger", "friend"):
            new_status = "friend"
        if new_affection >= 130 and rel.status == "friend":
            new_status = "partner"

        row = self.db.upsert_relationship(
            user_id=user_id,
            target_id=target_id,
            affection_delta=delta,
            status=new_status,
            touch_interaction=True,
        )
        return Relationship.from_row(row), 0

    def apply_gift(
        self,
        user_id: str,
        target_id: str,
        value: int,
    ) -> Relationship:
        if value <= 0:
            return self.get_relationship(user_id, target_id)

        # 1 affection per 500 money, capped per gift
        delta = max(1, min(40, value // 500))

        rel = self.get_relationship(user_id, target_id)
        new_status: RelationshipStatus = rel.status
        new_affection = rel.affection + delta

        if new_affection >= 80 and rel.status in ("stranger", "friend"):
            new_status = "friend"
        if new_affection >= 130 and rel.status == "friend":
            new_status = "partner"

        row = self.db.upsert_relationship(
            user_id=user_id,
            target_id=target_id,
            affection_delta=delta,
            status=new_status,
            touch_interaction=True,
        )
        return Relationship.from_row(row)

    def askout(
        self,
        user_id: str,
        target_id: str,
    ) -> tuple[bool, Relationship, str]:
        rel = self.get_relationship(user_id, target_id)

        if rel.status == "partner":
            return False, rel, "You are already partners."
        if rel.status == "ex":
            return False, rel, "This relationship has already ended."

        if rel.affection < 120:
            return False, rel, "Affection is too low to ask them out."

        row = self.db.upsert_relationship(
            user_id=user_id,
            target_id=target_id,
            affection_delta=5,
            status="partner",
            touch_interaction=True,
        )
        return True, Relationship.from_row(row), "They said yes!"

    def breakup(
        self,
        user_id: str,
        target_id: str,
    ) -> Relationship:
        rel = self.get_relationship(user_id, target_id)
        row = self.db.upsert_relationship(
            user_id=user_id,
            target_id=target_id,
            affection_delta=-40,
            status="ex",
            touch_interaction=True,
        )
        return Relationship.from_row(row)
