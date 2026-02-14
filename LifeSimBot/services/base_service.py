# services/base_service.py
import logging
from db.database import db
from abc import ABC

class BaseService(ABC):
    """
    The abstract base class for all logical services.
    Provides standard access to the Database and Logger.
    """
    def __init__(self, service_name: str):
        self.db = db
        self.logger = logging.getLogger(f"bot.services.{service_name}")
        self.logger.info(f"Service '{service_name}' initialized.")

    async def _log_error(self, method: str, error: Exception):
        """Standardized error logging."""
        self.logger.error(f"[{method}] Critical Error: {error}", exc_info=True)

    async def _ensure_record(self, table: str, key_col: str, key_val: int, defaults: dict):
        """
        Generic helper to ensure a row exists in any table.
        Useful for initializing user states lazily.
        """
        exists = await self.db.fetch_one(f"SELECT 1 FROM {table} WHERE {key_col} = ?", key_val)
        if not exists:
            cols = ", ".join(defaults.keys())
            placeholders = ", ".join(["?"] * len(defaults))
            values = list(defaults.values())
            
            # Prepend the key column
            cols = f"{key_col}, {cols}"
            placeholders = f"?, {placeholders}"
            values.insert(0, key_val)
            
            await self.db.execute(
                f"INSERT INTO {table} ({cols}) VALUES ({placeholders})", 
                *values
            )
            self.logger.info(f"Created new record in {table} for ID {key_val}")
            return True
        return False