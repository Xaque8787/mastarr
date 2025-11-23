"""Pre-install hook for Sonarr."""
from hooks.base import HookContext
from utils.logger import get_logger

logger = get_logger("mastarr.hooks.sonarr.pre_install")


async def run(context: HookContext):
    """Execute pre-install hook for Sonarr"""
    logger.info(f"[PRE-INSTALL] Preparing to install Sonarr: {context.app_name}")
    logger.info(f"Container: {context.container_name}")
