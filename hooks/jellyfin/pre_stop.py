"""
Pre-stop hook for Jellyfin.
Runs before Jellyfin container is stopped.
"""
from hooks.base import HookContext
from utils.logger import get_logger

logger = get_logger("mastarr.hooks.jellyfin.pre_stop")


async def run(context: HookContext):
    """Execute pre-stop hook for Jellyfin"""
    logger.info("=" * 60)
    logger.info("[PRE-STOP] Hook running BEFORE Jellyfin stop")
    logger.info(f"App: {context.app_name}")
    logger.info(f"Container: {context.container_name}")
    logger.info("This hook runs before the container is stopped")
    logger.info("Use this to gracefully close connections or save state")
    logger.info("=" * 60)
