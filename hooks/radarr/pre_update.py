"""Pre-update hook for Radarr."""
from hooks.base import HookContext
from utils.logger import get_logger

logger = get_logger("mastarr.hooks.radarr.pre_update")


async def run(context: HookContext):
    """Execute pre-update hook for Radarr"""
    logger.info(f"[PRE-UPDATE] Preparing to update Radarr: {context.app_name}")
