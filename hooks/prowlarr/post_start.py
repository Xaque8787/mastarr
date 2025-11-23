"""Post-start hook for Prowlarr."""
from hooks.base import HookContext
from utils.logger import get_logger

logger = get_logger("mastarr.hooks.prowlarr.post_start")


async def run(context: HookContext):
    """Execute post-start hook for Prowlarr"""
    logger.info(f"[POST-START] Prowlarr started: {context.app_name}")
