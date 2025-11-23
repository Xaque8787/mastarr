"""Pre-stop hook for Radarr."""
from hooks.base import HookContext
from utils.logger import get_logger

logger = get_logger("mastarr.hooks.radarr.pre_stop")


async def run(context: HookContext):
    """Execute pre-stop hook for Radarr"""
    logger.info(f"[PRE-STOP] Preparing to stop Radarr: {context.app_name}")
