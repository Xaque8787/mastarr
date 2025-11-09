"""
Pre-install hook for Jellyfin.
Runs before Jellyfin container is created for the first time.
"""
from hooks.base import HookContext
from utils.logger import get_logger

logger = get_logger("mastarr.hooks.jellyfin.pre_install")


async def run(context: HookContext):
    """Execute pre-install hook for Jellyfin"""
    logger.info("=" * 60)
    logger.info("[PRE-INSTALL] Hook running BEFORE Jellyfin installation")
    logger.info(f"App: {context.app_name}")
    logger.info(f"Container: {context.container_name}")
    logger.info("This hook runs before the container is created")
    logger.info("=" * 60)
