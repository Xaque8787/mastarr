"""
Pre-update hook for Jellyfin.
Runs before Jellyfin configuration is updated.
"""
from hooks.base import HookContext
from utils.logger import get_logger

logger = get_logger("mastarr.hooks.jellyfin.pre_update")


async def run(context: HookContext):
    """Execute pre-update hook for Jellyfin"""
    logger.info("=" * 60)
    logger.info("[PRE-UPDATE] Hook running BEFORE Jellyfin update")
    logger.info(f"App: {context.app_name}")
    logger.info(f"Container: {context.container_name}")
    logger.info("This hook runs before configuration changes are applied")
    logger.info("Use this to backup current config or validate new settings")
    logger.info("=" * 60)
