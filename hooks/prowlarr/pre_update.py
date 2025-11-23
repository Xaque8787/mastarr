"""Pre-update hook for Prowlarr."""
from hooks.base import HookContext
from utils.logger import get_logger

logger = get_logger("mastarr.hooks.prowlarr.pre_update")


async def run(context: HookContext):
    """Execute pre-update hook for Prowlarr"""
    logger.info(f"[PRE-UPDATE] Preparing to update Prowlarr: {context.app_name}")
