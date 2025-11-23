"""Pre-remove hook for Radarr."""
from hooks.base import HookContext
from utils.logger import get_logger

logger = get_logger("mastarr.hooks.radarr.pre_remove")


async def run(context: HookContext):
    """Execute pre-remove hook for Radarr"""
    logger.info(f"[PRE-REMOVE] Preparing to remove Radarr: {context.app_name}")
    logger.info(f"Container: {context.container_name}")
