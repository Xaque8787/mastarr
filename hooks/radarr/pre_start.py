"""Pre-start hook for Radarr."""
from hooks.base import HookContext
from utils.logger import get_logger

logger = get_logger("mastarr.hooks.radarr.pre_start")


async def run(context: HookContext):
    """Execute pre-start hook for Radarr"""
    logger.info(f"[PRE-START] Preparing to start Radarr: {context.app_name}")
