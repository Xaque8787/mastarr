"""Post-remove hook for Prowlarr."""
from hooks.base import HookContext
from utils.logger import get_logger

logger = get_logger("mastarr.hooks.prowlarr.post_remove")


async def run(context: HookContext):
    """Execute post-remove hook for Prowlarr"""
    logger.info(f"[POST-REMOVE] Prowlarr removed: {context.app_name}")
    logger.info(f"Container {context.container_name} has been removed")
