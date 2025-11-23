"""Pre-stop hook for Sonarr."""
from hooks.base import HookContext
from utils.logger import get_logger

logger = get_logger("mastarr.hooks.sonarr.pre_stop")


async def run(context: HookContext):
    """Execute pre-stop hook for Sonarr"""
    logger.info(f"[PRE-STOP] Preparing to stop Sonarr: {context.app_name}")
