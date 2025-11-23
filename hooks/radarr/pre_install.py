"""Pre-install hook for Radarr."""
from hooks.base import HookContext
from utils.logger import get_logger

logger = get_logger("mastarr.hooks.radarr.pre_install")


async def run(context: HookContext):
    """Execute pre-install hook for Radarr"""
    logger.info(f"[PRE-INSTALL] Preparing to install Radarr: {context.app_name}")
    logger.info(f"Container: {context.container_name}")
