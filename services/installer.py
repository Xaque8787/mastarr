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
from services.compose_generator import generate_compose
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

    async def install_single_app(self, app_id: int):
        """Install a single app"""
        from services.compose_generator import ComposeGenerator

        app = self.db.query(App).filter(App.id == app_id).one()
        blueprint = self.db.query(Blueprint).filter(Blueprint.name == app.blueprint_name).one()

        logger.info(f"Installing {app.name} (blueprint: {app.blueprint_name})")

        app.status = "installing"
        self.db.commit()

        try:
            generator = ComposeGenerator()

            compose_obj = generator.generate(app, blueprint)

            stack_path = self.path_resolver.ensure_stack_directory(app.db_name)
            compose_path = stack_path / "docker-compose.yml"
            env_path = stack_path / ".env"

            generator.write_env_file(app.db_name, app.raw_inputs, str(env_path))

            compose_dict = compose_obj.model_dump(exclude_none=True)

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

            host_stack_path = self.path_resolver.get_host_stack_path(app.db_name)
            host_compose_path = os.path.join(host_stack_path, "docker-compose.yml")

            try:
                result = subprocess.run(
                    [
                        "docker", "compose",
                        "--project-directory", host_stack_path,
                        "-f", host_compose_path,
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
            app.installed_at = datetime.utcnow()
            app.compose_file_path = str(compose_path)
            self.db.commit()

            await self._execute_app_hook(app, blueprint, "post_install")

            logger.info(f"✓ {app.name} installed successfully")

        except Exception as e:
            logger.error(f"Installation failed for {app.name}: {e}", exc_info=True)
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

    def close(self):
        """Close database session"""
        self.db.close()
