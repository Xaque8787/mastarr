"""
Pre-remove hook for Jellyfin.
Runs before Jellyfin is completely removed.
"""
from hooks.base import HookContext
from utils.logger import get_logger

logger = get_logger("mastarr.hooks.jellyfin.pre_remove")


async def run(context: HookContext):
    """Execute pre-remove hook for Jellyfin"""
    logger.info("=" * 60)
    logger.info("[PRE-REMOVE] Hook running BEFORE Jellyfin removal")
    logger.info(f"App: {context.app_name}")
    logger.info(f"Container: {context.container_name}")
    logger.info("This hook runs before the app is completely removed")
    logger.info("Use this to backup data or export configurations")
    logger.info("=" * 60)
