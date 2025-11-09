"""
Post-update hook for Jellyfin.
Runs after Jellyfin configuration is updated and container restarted.
"""
from hooks.base import HookContext
from utils.logger import get_logger

logger = get_logger("mastarr.hooks.jellyfin.post_update")


async def run(context: HookContext):
    """Execute post-update hook for Jellyfin"""
    logger.info("=" * 60)
    logger.info("[POST-UPDATE] Hook running AFTER Jellyfin update")
    logger.info(f"App: {context.app_name}")
    logger.info(f"Container: {context.container_name}")
    logger.info("This hook runs after configuration is updated and container restarted")
    logger.info("Use this to verify new configuration is working")
    logger.info("=" * 60)
