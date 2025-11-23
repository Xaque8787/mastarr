"""Pre-start hook for Sonarr."""
from hooks.base import HookContext
from utils.logger import get_logger

logger = get_logger("mastarr.hooks.sonarr.pre_start")


async def run(context: HookContext):
    """Execute pre-start hook for Sonarr"""
    logger.info(f"[PRE-START] Preparing to start Sonarr: {context.app_name}")
