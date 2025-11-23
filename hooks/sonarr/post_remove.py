"""Post-remove hook for Sonarr."""
from hooks.base import HookContext
from utils.logger import get_logger

logger = get_logger("mastarr.hooks.sonarr.post_remove")


async def run(context: HookContext):
    """Execute post-remove hook for Sonarr"""
    logger.info(f"[POST-REMOVE] Sonarr removed: {context.app_name}")
    logger.info(f"Container {context.container_name} has been removed")
