"""Post-stop hook for Radarr."""
from hooks.base import HookContext
from utils.logger import get_logger

logger = get_logger("mastarr.hooks.radarr.post_stop")


async def run(context: HookContext):
    """Execute post-stop hook for Radarr"""
    logger.info(f"[POST-STOP] Radarr stopped: {context.app_name}")
