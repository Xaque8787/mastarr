"""Post-update hook for Prowlarr."""
from hooks.base import HookContext
from utils.logger import get_logger

logger = get_logger("mastarr.hooks.prowlarr.post_update")


async def run(context: HookContext):
    """Execute post-update hook for Prowlarr"""
    logger.info(f"[POST-UPDATE] Prowlarr updated: {context.app_name}")
