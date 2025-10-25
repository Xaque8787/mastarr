"""
Sonarr post-install hook.

Similar to Radarr but for TV shows.
"""

import httpx
import asyncio
from hooks.base import HookContext
from utils.logger import get_logger
from models.database import App

logger = get_logger("mastarr.hooks.sonarr")


async def run(context: HookContext):
    """
    Configure Sonarr after installation.

    Args:
        context: Hook context with app information
    """
    logger.info("Starting Sonarr post-install configuration")

    host_port = context.inputs.get('port', 8989)
    sonarr_url = f"http://{context.container_ip or '10.21.12.12'}:{host_port}"

    logger.info(f"Sonarr URL: {sonarr_url}")

    # Wait for Sonarr to be ready
    if not await wait_for_sonarr(sonarr_url):
        logger.error("Sonarr did not become ready in time")
        raise RuntimeError("Sonarr startup timeout")

    logger.info("✓ Sonarr is ready")

    # Get Sonarr API key
    sonarr_api_key = await get_sonarr_api_key(context)

    if sonarr_api_key:
        app = context.db.query(App).filter(App.id == context.app_id).first()
        if app:
            app.inputs['api_key'] = sonarr_api_key
            app.inputs['server_url'] = sonarr_url
            context.db.commit()
            logger.info("✓ Sonarr API key stored")

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
            sonarr_url,
            sonarr_api_key
        )
    else:
        logger.info("Prowlarr not found, skipping integration")


async def wait_for_sonarr(url: str, max_attempts: int = 30, delay: int = 2) -> bool:
    """Wait for Sonarr to be ready."""
    logger.info("Waiting for Sonarr to be ready...")

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


async def get_sonarr_api_key(context: HookContext) -> str:
    """Extract API key from Sonarr's config file."""
    # TODO: Implement actual config.xml parsing
    logger.warning("API key extraction not yet implemented")
    return "placeholder-sonarr-api-key"


async def configure_prowlarr_integration(
    prowlarr_url: str,
    prowlarr_api_key: str,
    sonarr_url: str,
    sonarr_api_key: str
):
    """
    Add Sonarr as an application in Prowlarr.

    Args:
        prowlarr_url: Prowlarr base URL
        prowlarr_api_key: Prowlarr API key
        sonarr_url: Sonarr base URL
        sonarr_api_key: Sonarr API key
    """
    logger.info("Adding Sonarr to Prowlarr...")

    headers = {"X-Api-Key": prowlarr_api_key}

    payload = {
        "name": "Sonarr",
        "syncLevel": "addOnly",
        "implementation": "Sonarr",
        "configContract": "SonarrSettings",
        "fields": [
            {
                "name": "prowlarrUrl",
                "value": prowlarr_url
            },
            {
                "name": "baseUrl",
                "value": sonarr_url
            },
            {
                "name": "apiKey",
                "value": sonarr_api_key
            },
            {
                "name": "syncCategories",
                "value": [5000, 5010, 5020, 5030, 5040, 5045, 5050, 5060, 5070, 5080]
            },
            {
                "name": "animeCategories",
                "value": [5070]
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
                logger.info("✓ Sonarr added to Prowlarr successfully")
            elif response.status_code == 400:
                error = response.json()
                if "already exists" in str(error).lower():
                    logger.info("Sonarr already exists in Prowlarr")
                else:
                    logger.warning(f"Failed to add Sonarr to Prowlarr: {error}")
            else:
                logger.warning(
                    f"Unexpected response adding Sonarr to Prowlarr: "
                    f"{response.status_code} - {response.text}"
                )

        except Exception as e:
            logger.error(f"Error configuring Prowlarr integration: {e}", exc_info=True)
