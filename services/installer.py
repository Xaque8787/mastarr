import yaml
import docker
import subprocess
import os
from datetime import datetime
from typing import List, Dict, Set
from pathlib import Path
from python_on_whales import DockerClient
from models.database import App, Blueprint, get_session
from models.schemas import ComposeSchema
from services.compose_generator import generate_compose, ComposeGenerator
from hooks.base import HookContext, get_hook_executor
from utils.logger import get_logger
from utils.path_resolver import PathResolver

logger = get_logger("mastarr.installer")


class AppInstaller:
    """Orchestrates app installation with dependency resolution"""

    def __init__(self, db=None):
        self.db = db or get_session()
        self.docker = DockerClient()
        self.docker_client = docker.from_env()
        self.path_resolver = PathResolver()
        self.hook_executor = get_hook_executor()

    async def install_apps_batch(self, app_ids: List[int]):
        """
        Install multiple apps in correct order, respecting dependencies.

        Args:
            app_ids: List of app IDs to install

        Raises:
            ValueError: If missing prerequisites
            RuntimeError: If installation fails
        """
        logger.info(f"Starting batch installation for {len(app_ids)} apps")

        apps = self._get_apps(app_ids)
        blueprints = self._get_blueprints([app.blueprint_name for app in apps])

        missing_prereqs = self._check_missing_prerequisites(apps, blueprints)
        if missing_prereqs:
            raise ValueError(
                f"Missing required apps: {', '.join(missing_prereqs)}. "
                f"Please install these first or add them to your selection."
            )

        install_order = self._resolve_install_order(apps, blueprints)
        logger.info(f"Installation order: {[app.name for app in install_order]}")

        for app in install_order:
            try:
                await self.install_single_app(app.id)
            except Exception as e:
                logger.error(f"Failed to install {app.name}: {e}")
                app.status = "error"
                app.error_message = str(e)
                self.db.commit()
                raise RuntimeError(f"Installation halted due to failure in {app.name}")

        logger.info("✓ Batch installation completed successfully")

    def _check_missing_prerequisites(
        self,
        apps: List[App],
        blueprints: Dict[str, Blueprint]
    ) -> Set[str]:
        """Check if any selected apps have prerequisites that aren't installed or selected"""
        installed_blueprints = {
            app.blueprint_name
            for app in self.db.query(App).filter(App.status.in_(["running", "stopped"])).all()
        }

        selected_blueprints = {app.blueprint_name for app in apps}
        available_blueprints = installed_blueprints | selected_blueprints

        missing = set()
        for app in apps:
            blueprint = blueprints[app.blueprint_name]
            for prereq in blueprint.prerequisites:
                if prereq not in available_blueprints:
                    missing.add(prereq)

        return missing

    def _resolve_install_order(
        self,
        apps: List[App],
        blueprints: Dict[str, Blueprint]
    ) -> List[App]:
        """Sort apps for installation using topological sort + install_order"""
        graph = {}
        in_degree = {}

        for app in apps:
            blueprint = blueprints[app.blueprint_name]
            graph[app.blueprint_name] = blueprint.prerequisites
            in_degree[app.blueprint_name] = len(blueprint.prerequisites)

        sorted_names = []
        queue = [name for name, degree in in_degree.items() if degree == 0]
        queue.sort(key=lambda name: blueprints[name].install_order)

        while queue:
            current = queue.pop(0)
            sorted_names.append(current)

            for app_name, deps in graph.items():
                if current in deps:
                    in_degree[app_name] -= 1
                    if in_degree[app_name] == 0:
                        queue.append(app_name)

            queue.sort(key=lambda name: blueprints[name].install_order)

        if len(sorted_names) != len(apps):
            remaining = set(graph.keys()) - set(sorted_names)
            raise ValueError(f"Circular dependency detected: {remaining}")

        app_map = {app.blueprint_name: app for app in apps}
        return [app_map[name] for name in sorted_names]

    async def install_single_app(self, app_id: int, is_initial_install: bool = None):
        """
        Install or start a single app.

        Args:
            app_id: ID of the app to install
            is_initial_install: If True, runs install hooks. If False, runs start hooks.
                               If None (default), determines based on app.installed_at
        """
        from services.compose_generator import ComposeGenerator

        app = self.db.query(App).filter(App.id == app_id).one()
        blueprint = self.db.query(Blueprint).filter(Blueprint.name == app.blueprint_name).one()

        # Determine if this is the initial install or a subsequent start
        if is_initial_install is None:
            is_initial_install = app.installed_at is None

        operation = "Installing" if is_initial_install else "Starting"
        logger.info(f"{operation} {app.name} (blueprint: {app.blueprint_name})")

        # Run pre-install or pre-start hook
        if is_initial_install:
            await self._execute_app_hook(app, blueprint, "pre_install")
        else:
            await self._execute_app_hook(app, blueprint, "pre_start")

        app.status = "installing"
        self.db.commit()

        try:
            generator = ComposeGenerator()

            compose_obj = generator.generate(app, blueprint)

            # Use container paths for all operations
            # The docker compose command runs inside this container, so it needs container paths
            stack_path = self.path_resolver.ensure_stack_directory(app.db_name)
            compose_path = stack_path / "docker-compose.yml"
            env_path = stack_path / ".env"

            generator.write_env_file(app.db_name, app.raw_inputs, blueprint, str(env_path))

            compose_dict = compose_obj.model_dump(exclude_none=True)

            # Remove empty strings, empty dicts, and empty lists
            compose_dict = self._clean_empty_values(compose_dict)

            if 'services' in compose_dict:
                for service_name, service_config in compose_dict['services'].items():
                    if 'environment' in service_config and isinstance(service_config['environment'], dict):
                        service_config['environment'] = [
                            f"{k}={v}" for k, v in service_config['environment'].items()
                        ]

            with open(compose_path, 'w') as f:
                yaml.dump(compose_dict, f, default_flow_style=False, sort_keys=False)

            logger.info(f"✓ Wrote compose file to {compose_path}")

            generator.close()

            # Check if dry-run mode is enabled
            dry_run = os.getenv('DRY_RUN', 'false').lower() in ('true', '1', 'yes')

            if dry_run:
                logger.info(f"🔍 DRY RUN MODE: Skipping container startup for {app.name}")
                logger.info(f"   Compose file written to: {compose_path}")
                logger.info(f"   To actually start the container, set DRY_RUN=false in .env")
            else:
                try:
                    # Use container paths for docker compose command
                    # The docker compose CLI runs inside this container, so it needs container paths
                    # The Docker daemon will handle volume mounts for the services being created
                    result = subprocess.run(
                        [
                            "docker", "compose",
                            "--project-directory", str(stack_path),
                            "-f", str(compose_path),
                            "up", "-d"
                        ],
                        check=True,
                        capture_output=True,
                        text=True
                    )
                    logger.info(f"✓ Docker containers started for {app.name}")
                    if result.stdout:
                        logger.debug(f"Docker output: {result.stdout}")
                except subprocess.CalledProcessError as e:
                    logger.error(f"Docker compose failed: {e.stderr}")
                    raise Exception(f"Failed to start containers: {e.stderr}")

            app.status = "running"
            if is_initial_install:
                app.installed_at = datetime.utcnow()
            app.compose_file_path = str(compose_path)
            self.db.commit()

            # Run post-install or post-start hook
            if is_initial_install:
                await self._execute_app_hook(app, blueprint, "post_install")
            else:
                await self._execute_app_hook(app, blueprint, "post_start")

            logger.info(f"✓ {app.name} {operation.lower()} successfully")

        except Exception as e:
            logger.error(f"{operation} failed for {app.name}: {e}", exc_info=True)
            app.status = "error"
            app.error_message = str(e)
            self.db.commit()
            raise

    async def _execute_app_hook(self, app: App, blueprint: Blueprint, hook_name: str):
        """
        Execute an app-specific hook using the new hooks system.

        Args:
            app: App database record
            blueprint: Blueprint definition
            hook_name: Name of hook to execute (post_install, pre_uninstall, etc.)
        """
        try:
            # Get container info from service_data
            container_name = app.service_data.get('container_name', app.db_name)
            container_ip = None

            try:
                container = self.docker_client.containers.get(container_name)
                networks = container.attrs.get('NetworkSettings', {}).get('Networks', {})

                # Try to get IP from mastarr_net
                if 'mastarr_net' in networks:
                    container_ip = networks['mastarr_net'].get('IPAddress')

                logger.info(f"Container {container_name} IP: {container_ip}")
            except docker.errors.NotFound:
                logger.warning(f"Container {container_name} not found")

            # Build hook context with full app object
            context = HookContext(
                app_id=app.id,
                app_name=app.name,
                blueprint_name=blueprint.name,
                container_name=container_name,
                container_ip=container_ip,
                app=app,
                db=self.db,
                docker_client=self.docker_client
            )

            # Execute hook
            success = await self.hook_executor.execute_hook(
                blueprint.name,
                hook_name,
                context
            )

            if success:
                logger.info(f"✓ {hook_name} hook completed for {app.name}")
            else:
                logger.warning(f"{hook_name} hook had issues for {app.name}")

        except Exception as e:
            logger.error(f"Failed to execute {hook_name} hook for {app.name}: {e}", exc_info=True)
            # Don't fail the installation if hook fails
            # The app is running, just post-config didn't complete

    def _get_apps(self, app_ids: List[int]) -> List[App]:
        """Fetch apps from database"""
        return self.db.query(App).filter(App.id.in_(app_ids)).all()

    def _get_blueprints(self, names: List[str]) -> Dict[str, Blueprint]:
        """Fetch blueprints from database"""
        blueprints = self.db.query(Blueprint).filter(Blueprint.name.in_(names)).all()
        return {bp.name: bp for bp in blueprints}

    def _clean_empty_values(self, data):
        """
        Recursively remove empty strings, empty dicts, and empty lists from data.
        Keeps False and 0 as they are valid values.

        Args:
            data: Dictionary, list, or other value to clean

        Returns:
            Cleaned data structure
        """
        if isinstance(data, dict):
            cleaned = {}
            for key, value in data.items():
                # Recursively clean nested structures
                cleaned_value = self._clean_empty_values(value)

                # Skip empty strings, empty dicts, empty lists
                # But keep False and 0 as they are valid values
                if cleaned_value == '' or \
                   (isinstance(cleaned_value, dict) and len(cleaned_value) == 0) or \
                   (isinstance(cleaned_value, list) and len(cleaned_value) == 0):
                    continue

                cleaned[key] = cleaned_value
            return cleaned
        elif isinstance(data, list):
            # Clean each item in the list
            return [self._clean_empty_values(item) for item in data if item not in ('', None)]
        else:
            return data

    def close(self):
        """Close database session"""
        self.db.close()
