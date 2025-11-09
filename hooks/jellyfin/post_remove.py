"""
Post-remove hook for Jellyfin.
Runs after Jellyfin is removed.
"""
from hooks.base import HookContext
from utils.logger import get_logger

logger = get_logger("mastarr.hooks.jellyfin.post_remove")


async def run(context: HookContext):
    """Execute post-remove hook for Jellyfin"""
    logger.info("=" * 60)
    logger.info("[POST-REMOVE] Hook running AFTER Jellyfin removal")
    logger.info(f"App: {context.app_name}")
    logger.info(f"Container: {context.container_name}")
    logger.info("This hook runs after the app is removed")
    logger.info("Use this to clean up external resources or notify services")
    logger.info("=" * 60)
