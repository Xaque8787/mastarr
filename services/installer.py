import yaml
from datetime import datetime
from typing import List, Dict, Set
from pathlib import Path
from python_on_whales import DockerClient
from models.database import App, Blueprint, get_session
from models.schemas import ComposeSchema
from services.compose_generator import generate_compose
from utils.logger import get_logger
from utils.path_resolver import PathResolver

logger = get_logger("mastarr.installer")


class AppInstaller:
    """Orchestrates app installation with dependency resolution"""

    def __init__(self, db=None):
        self.db = db or get_session()
        self.docker = DockerClient()
        self.path_resolver = PathResolver()

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
        app = self.db.query(App).filter(App.id == app_id).one()
        blueprint = self.db.query(Blueprint).filter(Blueprint.name == app.blueprint_name).one()

        logger.info(f"Installing {app.name} (blueprint: {app.blueprint_name})")

        app.status = "installing"
        self.db.commit()

        try:
            validated_inputs = app.inputs

            compose_obj = generate_compose(blueprint, validated_inputs)

            stack_path = self.path_resolver.ensure_stack_directory(app.db_name)
            compose_path = stack_path / "docker-compose.yml"

            compose_dict = compose_obj.model_dump(exclude_none=True)
            with open(compose_path, 'w') as f:
                yaml.dump(compose_dict, f, default_flow_style=False, sort_keys=False)

            logger.info(f"✓ Wrote compose file to {compose_path}")

            self.docker.compose.up(detach=True, project_directory=str(stack_path))
            logger.info(f"✓ Docker containers started for {app.name}")

            app.status = "running"
            app.installed_at = datetime.utcnow()
            app.compose_file_path = str(compose_path)
            app.compose_data = compose_dict
            self.db.commit()

            if blueprint.post_install_hook:
                logger.info(f"Running post-install hook: {blueprint.post_install_hook}")
                await self._run_post_install_hook(blueprint.post_install_hook, app.id)

            logger.info(f"✓ {app.name} installed successfully")

        except Exception as e:
            logger.error(f"Installation failed for {app.name}: {e}", exc_info=True)
            app.status = "error"
            app.error_message = str(e)
            self.db.commit()
            raise

    async def _run_post_install_hook(self, hook_name: str, app_id: int):
        """Execute a post-install hook"""
        try:
            module_parts = hook_name.split('_')
            if len(module_parts) > 1:
                module_name = module_parts[1]
            else:
                module_name = hook_name

            module = __import__(f"services.{module_name}", fromlist=[hook_name])
            hook_func = getattr(module, hook_name)

            await hook_func(app_id, self.db)
            logger.info(f"✓ Post-install hook completed: {hook_name}")

        except Exception as e:
            logger.error(f"Post-install hook failed: {hook_name}: {e}", exc_info=True)

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
