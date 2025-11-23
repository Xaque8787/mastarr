"""Pre-update hook for Sonarr."""
from hooks.base import HookContext
from utils.logger import get_logger

logger = get_logger("mastarr.hooks.sonarr.pre_update")


async def run(context: HookContext):
    """Execute pre-update hook for Sonarr"""
    logger.info(f"[PRE-UPDATE] Preparing to update Sonarr: {context.app_name}")
