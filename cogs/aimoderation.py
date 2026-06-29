"""
Backward-compatibility shim for cogs.aimoderation.

All code now lives in cogs.moderation.ai.aimoderation.
Import from cogs.moderation.ai directly in new code.
"""

# Re-export everything for backward compat
from cogs.moderation.ai.aimoderation import *  # noqa: F401, F403
from cogs.moderation.ai.aimoderation import setup  # noqa: F401
