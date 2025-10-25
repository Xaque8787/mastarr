"""
Jellyfin post-install hook.

This runs after the Jellyfin container starts successfully.
It handles:
- Waiting for Jellyfin to be ready
- Creating the admin user
- Configuring initial settings
- Adding media libraries
"""

import httpx
import asyncio
from hooks.base import HookContext
from utils.logger import get_logger

logger = get_logger("mastarr.hooks.jellyfin")


async def run(context: HookContext):
    """
    Configure Jellyfin after installation.

    Args:
        context: Hook context with app information
    """
    logger.info("Starting Jellyfin post-install configuration")

    # Extract configuration from inputs
    admin_user = context.inputs.get('admin_user')
    admin_password = context.inputs.get('admin_password')
    host_port = context.inputs.get('host_port', 8096)

    # Build Jellyfin URL
    jellyfin_url = f"http://{context.container_ip or 'localhost'}:{host_port}"
    logger.info(f"Jellyfin URL: {jellyfin_url}")

    # Wait for Jellyfin to be ready
    if not await wait_for_jellyfin(jellyfin_url):
        logger.error("Jellyfin did not become ready in time")
        raise RuntimeError("Jellyfin startup timeout")

    logger.info("Jellyfin is ready")

    # Check if initial setup is needed
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Check startup status
            response = await client.get(f"{jellyfin_url}/Startup/Configuration")

            if response.status_code == 200:
                logger.info("Jellyfin initial setup is needed")

                # Create admin user
                await create_admin_user(
                    client,
                    jellyfin_url,
                    admin_user,
                    admin_password
                )

                # Complete startup wizard
                await complete_startup_wizard(client, jellyfin_url)

                logger.info("✓ Jellyfin initial setup completed")
            else:
                logger.info("Jellyfin is already configured")

        except Exception as e:
            logger.error(f"Error during Jellyfin setup: {e}", exc_info=True)
            raise


async def wait_for_jellyfin(url: str, max_attempts: int = 30, delay: int = 2) -> bool:
    """
    Wait for Jellyfin to be ready by checking its health endpoint.

    Args:
        url: Jellyfin base URL
        max_attempts: Maximum number of attempts
        delay: Delay between attempts in seconds

    Returns:
        True if Jellyfin becomes ready, False otherwise
    """
    logger.info(f"Waiting for Jellyfin to be ready (max {max_attempts * delay}s)...")

    async with httpx.AsyncClient(timeout=10.0) as client:
        for attempt in range(max_attempts):
            try:
                response = await client.get(f"{url}/health")
                if response.status_code == 200:
                    logger.info(f"✓ Jellyfin is ready (attempt {attempt + 1})")
                    return True
            except (httpx.ConnectError, httpx.TimeoutException):
                pass

            if attempt < max_attempts - 1:
                await asyncio.sleep(delay)

    return False


async def create_admin_user(
    client: httpx.AsyncClient,
    base_url: str,
    username: str,
    password: str
):
    """
    Create the initial admin user in Jellyfin.

    Args:
        client: HTTP client
        base_url: Jellyfin base URL
        username: Admin username
        password: Admin password
    """
    logger.info(f"Creating admin user: {username}")

    try:
        # Jellyfin's startup wizard user creation endpoint
        response = await client.post(
            f"{base_url}/Startup/User",
            json={
                "Name": username,
                "Password": password
            }
        )

        if response.status_code in [200, 204]:
            logger.info(f"✓ Admin user '{username}' created")
        else:
            logger.warning(
                f"User creation returned status {response.status_code}: {response.text}"
            )

    except Exception as e:
        logger.error(f"Failed to create admin user: {e}", exc_info=True)
        raise


async def complete_startup_wizard(client: httpx.AsyncClient, base_url: str):
    """
    Complete the Jellyfin startup wizard.

    Args:
        client: HTTP client
        base_url: Jellyfin base URL
    """
    logger.info("Completing startup wizard")

    try:
        # Mark startup wizard as complete
        response = await client.post(f"{base_url}/Startup/Complete")

        if response.status_code in [200, 204]:
            logger.info("✓ Startup wizard completed")
        else:
            logger.warning(
                f"Startup completion returned status {response.status_code}"
            )

    except Exception as e:
        logger.error(f"Failed to complete startup wizard: {e}", exc_info=True)
        raise
