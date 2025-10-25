import docker
import os
from pathlib import Path
from typing import Optional
from utils.logger import get_logger

logger = get_logger("mastarr.path_resolver")


class PathResolver:
    """
    Resolves container paths to host paths.
    Replicates functionality of MESS's resolve_host.sh script.
    """

    def __init__(self):
        self.client = docker.from_env()
        self.container_name = os.getenv("HOSTNAME", "mastarr")
        self._host_stacks_path: Optional[str] = None
        self._host_data_path: Optional[str] = None

    def resolve_host_path(self, container_path: str) -> str:
        """
        Given a path inside this container, resolve it to the host path.

        Args:
            container_path: Path inside the mastarr container (e.g., /stacks)

        Returns:
            Host path that corresponds to the container path
        """
        try:
            container = self.client.containers.get(self.container_name)

            for mount in container.attrs['Mounts']:
                dest = mount['Destination']
                source = mount['Source']

                if dest == container_path:
                    logger.debug(f"Resolved {container_path} -> {source}")
                    return source

                # Check if container_path is a subdirectory
                if container_path.startswith(dest + '/'):
                    relative = container_path[len(dest):].lstrip('/')
                    host_path = os.path.join(source, relative)
                    logger.debug(f"Resolved {container_path} -> {host_path}")
                    return host_path

            logger.warning(f"No mount found for {container_path}, returning as-is")
            return container_path

        except Exception as e:
            logger.error(f"Failed to resolve host path for {container_path}: {e}")
            return container_path

    def get_host_stacks_path(self) -> str:
        """Get host path for /stacks directory"""
        if not self._host_stacks_path:
            self._host_stacks_path = self.resolve_host_path("/stacks")
        return self._host_stacks_path

    def get_host_data_path(self) -> str:
        """Get host path for /app/data directory"""
        if not self._host_data_path:
            self._host_data_path = self.resolve_host_path("/app/data")
        return self._host_data_path

    def get_stack_path(self, app_name: str) -> Path:
        """
        Get the path to an app's stack directory.

        Args:
            app_name: Name of the app

        Returns:
            Path object for the stack directory
        """
        return Path("/stacks") / app_name

    def get_host_stack_path(self, app_name: str) -> str:
        """
        Get the host path for an app's stack directory.

        Args:
            app_name: Name of the app

        Returns:
            Host path to the stack directory
        """
        return os.path.join(self.get_host_stacks_path(), app_name)

    def ensure_stack_directory(self, app_name: str) -> Path:
        """
        Ensure an app's stack directory exists.

        Args:
            app_name: Name of the app

        Returns:
            Path to the created/existing directory
        """
        stack_path = self.get_stack_path(app_name)
        stack_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Ensured stack directory exists: {stack_path}")
        return stack_path
