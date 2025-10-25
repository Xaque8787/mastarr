"""
Prowlarr post-install hook.

Handles:
- Waiting for Prowlarr to be ready
- Getting API key
- Storing API key for later use by Radarr/Sonarr
"""

import httpx
import asyncio
from hooks.base import HookContext
from utils.logger import get_logger
from models.database import App

logger = get_logger("mastarr.hooks.prowlarr")


async def run(context: HookContext):
    """
    Configure Prowlarr after installation.

    Args:
        context: Hook context with app information
    """
    logger.info("Starting Prowlarr post-install configuration")

    host_port = context.inputs.get('port', 9696)
    prowlarr_url = f"http://{context.container_ip or '10.21.12.10'}:{host_port}"

    logger.info(f"Prowlarr URL: {prowlarr_url}")

    # Wait for Prowlarr to be ready
    if not await wait_for_prowlarr(prowlarr_url):
        logger.error("Prowlarr did not become ready in time")
        raise RuntimeError("Prowlarr startup timeout")

    logger.info("✓ Prowlarr is ready")

    # Get API key from config.xml
    api_key = await get_prowlarr_api_key(context)

    if api_key:
        # Store API key in app inputs for later use
        app = context.db.query(App).filter(App.id == context.app_id).first()
        if app:
            app.inputs['api_key'] = api_key
            app.inputs['server_url'] = prowlarr_url
            context.db.commit()
            logger.info("✓ Prowlarr API key stored")


async def wait_for_prowlarr(url: str, max_attempts: int = 30, delay: int = 2) -> bool:
    """Wait for Prowlarr to be ready."""
    logger.info("Waiting for Prowlarr to be ready...")

    async with httpx.AsyncClient(timeout=10.0) as client:
        for attempt in range(max_attempts):
            try:
                response = await client.get(f"{url}/ping")
                if response.status_code == 200:
                    return True
            except (httpx.ConnectError, httpx.TimeoutException):
                pass

            if attempt < max_attempts - 1:
                await asyncio.sleep(delay)

    return False


async def get_prowlarr_api_key(context: HookContext) -> str:
    """
    Extract API key from Prowlarr's config file.

    In a real implementation, this would:
    1. Find the container's config volume
    2. Read config.xml
    3. Parse and extract <ApiKey>
    """
    # TODO: Implement actual config.xml parsing
    logger.warning("API key extraction from config.xml not yet implemented")
    return "placeholder-prowlarr-api-key"
