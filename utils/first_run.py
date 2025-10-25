import docker
import os
from pathlib import Path
from utils.logger import get_logger
from utils.blueprint_loader import load_blueprints_from_directory, get_blueprint_count

logger = get_logger("mastarr.first_run")


class FirstRunInitializer:
    """
    First-run initialization checks and setup.
    Ensures Docker socket access, directories, etc.
    """

    def __init__(self):
        self.client = None

    def initialize(self):
        """Run all first-run initialization checks"""
        logger.info("=" * 60)
        logger.info("Starting First-Run Initialization")
        logger.info("=" * 60)

        self._check_docker_socket()
        self._check_docker_connectivity()
        self._ensure_directories()
        self._load_blueprints()

        logger.info("=" * 60)
        logger.info("First-Run Initialization Complete")
        logger.info("=" * 60)

    def _check_docker_socket(self):
        """Verify Docker socket is mounted and accessible"""
        socket_path = "/var/run/docker.sock"

        if not os.path.exists(socket_path):
            logger.error(f"Docker socket not found at {socket_path}")
            raise RuntimeError(
                "Docker socket not mounted. "
                "Please ensure -v /var/run/docker.sock:/var/run/docker.sock is set"
            )

        logger.info(f"✓ Docker socket found at {socket_path}")

    def _check_docker_connectivity(self):
        """Test Docker connectivity"""
        try:
            self.client = docker.from_env()
            self.client.ping()
            logger.info("✓ Docker daemon is accessible")

            # Log Docker info
            info = self.client.info()
            logger.info(f"  Docker version: {info.get('ServerVersion', 'unknown')}")
            logger.info(f"  Containers running: {info.get('ContainersRunning', 0)}")

        except Exception as e:
            logger.error(f"Cannot connect to Docker daemon: {e}")
            raise RuntimeError("Docker daemon not accessible") from e

    def _ensure_directories(self):
        """Ensure required directories exist"""
        directories = [
            "/stacks",
            "/app/data",
            "/app/logs"
        ]

        for directory in directories:
            path = Path(directory)
            path.mkdir(parents=True, exist_ok=True)
            logger.info(f"✓ Directory ensured: {directory}")

    def _load_blueprints(self):
        """Load blueprints from JSON files if database is empty"""
        try:
            blueprint_count = get_blueprint_count()

            if blueprint_count == 0:
                logger.info("No blueprints found in database, loading from files...")
                loaded, errors = load_blueprints_from_directory()

                if loaded > 0:
                    logger.info(f"✓ Loaded {loaded} blueprint(s)")
                else:
                    logger.warning("No blueprints were loaded")

                if errors > 0:
                    logger.warning(f"{errors} blueprint(s) failed to load")
            else:
                logger.info(f"✓ Found {blueprint_count} blueprint(s) in database")

        except Exception as e:
            logger.error(f"Failed to load blueprints: {e}", exc_info=True)
            logger.warning("Application will continue, but no blueprints are available")

    def reload_blueprints(self):
        """Manually reload all blueprints from files (updates existing)"""
        logger.info("Manually reloading blueprints...")
        loaded, errors = load_blueprints_from_directory()
        logger.info(f"Reload complete: {loaded} loaded, {errors} errors")
        return loaded, errors

    def get_system_info(self) -> dict:
        """Get system information for display"""
        if not self.client:
            self.client = docker.from_env()

        info = self.client.info()

        return {
            "docker_version": info.get("ServerVersion", "unknown"),
            "containers_running": info.get("ContainersRunning", 0),
            "containers_total": info.get("Containers", 0),
            "images_total": info.get("Images", 0),
            "os": info.get("OperatingSystem", "unknown"),
            "architecture": info.get("Architecture", "unknown")
        }
