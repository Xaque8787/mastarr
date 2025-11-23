"""Pre-remove hook for Prowlarr."""
from hooks.base import HookContext
from utils.logger import get_logger

logger = get_logger("mastarr.hooks.prowlarr.pre_remove")


async def run(context: HookContext):
    """Execute pre-remove hook for Prowlarr"""
    logger.info(f"[PRE-REMOVE] Preparing to remove Prowlarr: {context.app_name}")
    logger.info(f"Container: {context.container_name}")
