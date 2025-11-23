"""Post-start hook for Sonarr."""
from hooks.base import HookContext
from utils.logger import get_logger

logger = get_logger("mastarr.hooks.sonarr.post_start")


async def run(context: HookContext):
    """Execute post-start hook for Sonarr"""
    logger.info(f"[POST-START] Sonarr started: {context.app_name}")
