"""Post-stop hook for Sonarr."""
from hooks.base import HookContext
from utils.logger import get_logger

logger = get_logger("mastarr.hooks.sonarr.post_stop")


async def run(context: HookContext):
    """Execute post-stop hook for Sonarr"""
    logger.info(f"[POST-STOP] Sonarr stopped: {context.app_name}")
