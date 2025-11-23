"""Post-remove hook for Radarr."""
from hooks.base import HookContext
from utils.logger import get_logger

logger = get_logger("mastarr.hooks.radarr.post_remove")


async def run(context: HookContext):
    """Execute post-remove hook for Radarr"""
    logger.info(f"[POST-REMOVE] Radarr removed: {context.app_name}")
    logger.info(f"Container {context.container_name} has been removed")
