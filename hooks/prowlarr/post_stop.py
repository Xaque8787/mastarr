"""Post-stop hook for Prowlarr."""
from hooks.base import HookContext
from utils.logger import get_logger

logger = get_logger("mastarr.hooks.prowlarr.post_stop")


async def run(context: HookContext):
    """Execute post-stop hook for Prowlarr"""
    logger.info(f"[POST-STOP] Prowlarr stopped: {context.app_name}")
