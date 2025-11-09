"""
Pre-start hook for Jellyfin.
Runs before a stopped Jellyfin container is started.
"""
from hooks.base import HookContext
from utils.logger import get_logger

logger = get_logger("mastarr.hooks.jellyfin.pre_start")


async def run(context: HookContext):
    """Execute pre-start hook for Jellyfin"""
    logger.info("=" * 60)
    logger.info("[PRE-START] Hook running BEFORE Jellyfin start")
    logger.info(f"App: {context.app_name}")
    logger.info(f"Container: {context.container_name}")
    logger.info("This hook runs before a stopped container is started")
    logger.info("Use this to verify dependencies are running")
    logger.info("=" * 60)
