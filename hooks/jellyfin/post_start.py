"""
Post-start hook for Jellyfin.
Runs after a stopped Jellyfin container is started.
"""
from hooks.base import HookContext
from utils.logger import get_logger

logger = get_logger("mastarr.hooks.jellyfin.post_start")


async def run(context: HookContext):
    """Execute post-start hook for Jellyfin"""
    logger.info("=" * 60)
    logger.info("[POST-START] Hook running AFTER Jellyfin start")
    logger.info(f"App: {context.app_name}")
    logger.info(f"Container: {context.container_name}")
    logger.info("This hook runs after a stopped container is started")
    logger.info("Use this to wait for app readiness or reconnect services")
    logger.info("=" * 60)
