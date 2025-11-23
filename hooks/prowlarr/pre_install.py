"""Pre-install hook for Prowlarr."""
from hooks.base import HookContext
from utils.logger import get_logger

logger = get_logger("mastarr.hooks.prowlarr.pre_install")


async def run(context: HookContext):
    """Execute pre-install hook for Prowlarr"""
    logger.info(f"[PRE-INSTALL] Preparing to install Prowlarr: {context.app_name}")
    logger.info(f"Container: {context.container_name}")
