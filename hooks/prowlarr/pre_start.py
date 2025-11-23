"""Pre-start hook for Prowlarr."""
from hooks.base import HookContext
from utils.logger import get_logger

logger = get_logger("mastarr.hooks.prowlarr.pre_start")


async def run(context: HookContext):
    """Execute pre-start hook for Prowlarr"""
    logger.info(f"[PRE-START] Preparing to start Prowlarr: {context.app_name}")
