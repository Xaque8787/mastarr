"""Post-start hook for Radarr."""
from hooks.base import HookContext
from utils.logger import get_logger

logger = get_logger("mastarr.hooks.radarr.post_start")


async def run(context: HookContext):
    """Execute post-start hook for Radarr"""
    logger.info(f"[POST-START] Radarr started: {context.app_name}")
