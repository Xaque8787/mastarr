"""Post-update hook for Sonarr."""
from hooks.base import HookContext
from utils.logger import get_logger

logger = get_logger("mastarr.hooks.sonarr.post_update")


async def run(context: HookContext):
    """Execute post-update hook for Sonarr"""
    logger.info(f"[POST-UPDATE] Sonarr updated: {context.app_name}")
