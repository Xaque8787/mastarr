"""Pre-remove hook for Sonarr."""
from hooks.base import HookContext
from utils.logger import get_logger

logger = get_logger("mastarr.hooks.sonarr.pre_remove")


async def run(context: HookContext):
    """Execute pre-remove hook for Sonarr"""
    logger.info(f"[PRE-REMOVE] Preparing to remove Sonarr: {context.app_name}")
    logger.info(f"Container: {context.container_name}")
