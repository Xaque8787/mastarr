"""Pre-stop hook for Prowlarr."""
from hooks.base import HookContext
from utils.logger import get_logger

logger = get_logger("mastarr.hooks.prowlarr.pre_stop")


async def run(context: HookContext):
    """Execute pre-stop hook for Prowlarr"""
    logger.info(f"[PRE-STOP] Preparing to stop Prowlarr: {context.app_name}")
