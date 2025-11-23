"""Post-update hook for Radarr."""
from hooks.base import HookContext
from utils.logger import get_logger

logger = get_logger("mastarr.hooks.radarr.post_update")


async def run(context: HookContext):
    """Execute post-update hook for Radarr"""
    logger.info(f"[POST-UPDATE] Radarr updated: {context.app_name}")
