# services/social_service.py
from services.base_service import BaseService

class SocialService(BaseService):
    def __init__(self):
        super().__init__("social")

    async def get_relationship(self, user1: int, user2: int):
        """Checks if two users have a relationship."""
        # Normalize: user1 is always smaller ID to prevent duplicates
        u1, u2 = sorted([user1, user2])
        
        row = await self.db.fetch_one(
            "SELECT * FROM relationships WHERE user_id_1 = ? AND user_id_2 = ?",
            u1, u2
        )
        return dict(row) if row else None

    async def modify_affection(self, user1: int, user2: int, amount: int):
        """
        Changes affection level. 
        Triggers breakup/divorce if too low, or dating option if high.
        """
        if user1 == user2: return
        
        rel = await self.get_relationship(user1, user2)
        u1, u2 = sorted([user1, user2])

        if not rel:
            # Create acquaintance
            await self.db.execute(
                "INSERT INTO relationships (user_id_1, user_id_2, type, affection) VALUES (?, ?, 'acquaintance', 50)",
                u1, u2
            )
            current_aff = 50
        else:
            current_aff = rel['affection']

        new_aff = max(0, min(100, current_aff + amount))
        
        await self.db.execute(
            "UPDATE relationships SET affection = ? WHERE user_id_1 = ? AND user_id_2 = ?",
            new_aff, u1, u2
        )
        return new_aff

    async def marry(self, user1: int, user2: int):
        """Sets status to married."""
        rel = await self.get_relationship(user1, user2)
        if not rel or rel['affection'] < 80:
            return {"success": False, "error": "Affection too low."}
            
        u1, u2 = sorted([user1, user2])
        await self.db.execute(
            "UPDATE relationships SET type = 'married' WHERE user_id_1 = ? AND user_id_2 = ?",
            u1, u2
        )
        return {"success": True}

social_service = SocialService()