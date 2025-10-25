"""
Radarr post-install hook.

Handles:
- Waiting for Radarr to be ready
- Getting Radarr API key
- Auto-configuring Prowlarr connection (if Prowlarr is installed)
"""

import httpx
import asyncio
from hooks.base import HookContext
from utils.logger import get_logger
from models.database import App

logger = get_logger("mastarr.hooks.radarr")


async def run(context: HookContext):
    """
    Configure Radarr after installation.

    Args:
        context: Hook context with app information
    """
    logger.info("Starting Radarr post-install configuration")

    host_port = context.inputs.get('port', 7878)
    radarr_url = f"http://{context.container_ip or '10.21.12.11'}:{host_port}"

    logger.info(f"Radarr URL: {radarr_url}")

    # Wait for Radarr to be ready
    if not await wait_for_radarr(radarr_url):
        logger.error("Radarr did not become ready in time")
        raise RuntimeError("Radarr startup timeout")

    logger.info("✓ Radarr is ready")

    # Get Radarr API key
    radarr_api_key = await get_radarr_api_key(context)

    if radarr_api_key:
        app = context.db.query(App).filter(App.id == context.app_id).first()
        if app:
            app.inputs['api_key'] = radarr_api_key
            app.inputs['server_url'] = radarr_url
            context.db.commit()
            logger.info("✓ Radarr API key stored")

    # Check if Prowlarr is installed
    prowlarr_app = context.db.query(App).filter(
        App.blueprint_name == "prowlarr",
        App.status == "running"
    ).first()

    if prowlarr_app and prowlarr_app.inputs.get('api_key'):
        logger.info("Found Prowlarr, configuring integration...")
        await configure_prowlarr_integration(
            prowlarr_app.inputs['server_url'],
            prowlarr_app.inputs['api_key'],
            radarr_url,
            radarr_api_key
        )
    else:
        logger.info("Prowlarr not found, skipping integration")


async def wait_for_radarr(url: str, max_attempts: int = 30, delay: int = 2) -> bool:
    """Wait for Radarr to be ready."""
    logger.info("Waiting for Radarr to be ready...")

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


async def get_radarr_api_key(context: HookContext) -> str:
    """Extract API key from Radarr's config file."""
    # TODO: Implement actual config.xml parsing
    logger.warning("API key extraction not yet implemented")
    return "placeholder-radarr-api-key"


async def configure_prowlarr_integration(
    prowlarr_url: str,
    prowlarr_api_key: str,
    radarr_url: str,
    radarr_api_key: str
):
    """
    Add Radarr as an application in Prowlarr.

    This allows Prowlarr to automatically sync indexers to Radarr.

    Args:
        prowlarr_url: Prowlarr base URL
        prowlarr_api_key: Prowlarr API key
        radarr_url: Radarr base URL
        radarr_api_key: Radarr API key
    """
    logger.info("Adding Radarr to Prowlarr...")

    headers = {"X-Api-Key": prowlarr_api_key}

    payload = {
        "name": "Radarr",
        "syncLevel": "addOnly",
        "implementation": "Radarr",
        "configContract": "RadarrSettings",
        "fields": [
            {
                "name": "prowlarrUrl",
                "value": prowlarr_url
            },
            {
                "name": "baseUrl",
                "value": radarr_url
            },
            {
                "name": "apiKey",
                "value": radarr_api_key
            },
            {
                "name": "syncCategories",
                "value": [2000, 2010, 2020, 2030, 2040, 2045, 2050, 2060, 2070, 2080]
            }
        ]
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{prowlarr_url}/api/v1/applications",
                json=payload,
                headers=headers
            )

            if response.status_code == 201:
                logger.info("✓ Radarr added to Prowlarr successfully")
            elif response.status_code == 400:
                # Check if already exists
                error = response.json()
                if "already exists" in str(error).lower():
                    logger.info("Radarr already exists in Prowlarr")
                else:
                    logger.warning(f"Failed to add Radarr to Prowlarr: {error}")
            else:
                logger.warning(
                    f"Unexpected response adding Radarr to Prowlarr: "
                    f"{response.status_code} - {response.text}"
                )

        except Exception as e:
            logger.error(f"Error configuring Prowlarr integration: {e}", exc_info=True)
