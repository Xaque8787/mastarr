"""
Post-stop hook for Jellyfin.
Runs after Jellyfin container is stopped.
"""
from hooks.base import HookContext
from utils.logger import get_logger

logger = get_logger("mastarr.hooks.jellyfin.post_stop")


async def run(context: HookContext):
    """Execute post-stop hook for Jellyfin"""
    logger.info("=" * 60)
    logger.info("[POST-STOP] Hook running AFTER Jellyfin stop")
    logger.info(f"App: {context.app_name}")
    logger.info(f"Container: {context.container_name}")
    logger.info("This hook runs after the container is stopped")
    logger.info("Use this to clean up temporary files or update monitoring")
    logger.info("=" * 60)
