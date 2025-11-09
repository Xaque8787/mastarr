"""
Base classes and utilities for app hooks.
"""

import importlib
import inspect
from pathlib import Path
from typing import Optional, Callable, Any, Dict
from dataclasses import dataclass
from utils.logger import get_logger

logger = get_logger("mastarr.hooks")


@dataclass
class HookContext:
    """
    Context passed to hook functions.

    Contains all information the hook might need:
    - App database record
    - Blueprint definition
    - Container information
    - Docker client
    """
    app_id: int
    app_name: str
    blueprint_name: str
    container_name: str
    container_ip: Optional[str] = None

    # Full app object with service_data, compose_data, metadata_data, raw_inputs
    app: Any = None

    # Will be populated by hook executor
    db: Any = None
    docker_client: Any = None


class AppHook:
    """
    Base class for app-specific hooks.

    App hooks should inherit from this and implement the methods they need.
    Each hook is called at a specific point in the app's lifecycle.
    """

    def __init__(self, context: HookContext):
        self.context = context
        self.logger = get_logger(f"mastarr.hooks.{context.blueprint_name}")

    async def pre_install(self):
        """
        Called before the app's container is created/started for the first time.

        Use this to:
        - Validate prerequisites
        - Prepare directories or configuration files
        - Check system requirements
        """
        self.logger.info(f"[PRE-INSTALL] This hook will run before {self.context.app_name} is installed")

    async def post_install(self):
        """
        Called after the app's container starts successfully for the first time.

        Use this to:
        - Wait for app to be ready (health checks)
        - Configure the app via its API
        - Create default settings
        - Initialize databases
        """
        self.logger.info(f"[POST-INSTALL] This hook will run after {self.context.app_name} is installed")

    async def pre_update(self):
        """
        Called before an app's configuration is updated.

        Use this to:
        - Backup current configuration
        - Validate new configuration
        - Notify dependent services
        """
        self.logger.info(f"[PRE-UPDATE] This hook will run before {self.context.app_name} is updated")

    async def post_update(self):
        """
        Called after an app's configuration is updated and container restarted.

        Use this to:
        - Verify new configuration is working
        - Update dependent services
        - Clear caches
        """
        self.logger.info(f"[POST-UPDATE] This hook will run after {self.context.app_name} is updated")

    async def pre_start(self):
        """
        Called before a stopped container is started.

        Use this to:
        - Verify dependencies are running
        - Check disk space
        - Prepare runtime environment
        """
        self.logger.info(f"[PRE-START] This hook will run before {self.context.app_name} is started")

    async def post_start(self):
        """
        Called after a stopped container is started.

        Use this to:
        - Wait for app to be ready
        - Reconnect to services
        - Resume operations
        """
        self.logger.info(f"[POST-START] This hook will run after {self.context.app_name} is started")

    async def pre_stop(self):
        """
        Called before a running container is stopped.

        Use this to:
        - Gracefully close connections
        - Save state
        - Notify dependent services
        """
        self.logger.info(f"[PRE-STOP] This hook will run before {self.context.app_name} is stopped")

    async def post_stop(self):
        """
        Called after a container is stopped.

        Use this to:
        - Clean up temporary files
        - Update monitoring systems
        - Log the stop event
        """
        self.logger.info(f"[POST-STOP] This hook will run after {self.context.app_name} is stopped")

    async def pre_remove(self):
        """
        Called before the app is completely removed.

        Use this to:
        - Backup data
        - Export configurations
        - Notify administrators
        """
        self.logger.info(f"[PRE-REMOVE] This hook will run before {self.context.app_name} is removed")

    async def post_remove(self):
        """
        Called after the app is removed.

        Use this to:
        - Clean up external resources
        - Update dependent services
        - Remove database entries in other systems
        """
        self.logger.info(f"[POST-REMOVE] This hook will run after {self.context.app_name} is removed")

    async def health_check(self) -> bool:
        """
        Custom health check for the app.

        Returns:
            True if app is healthy, False otherwise
        """
        return True


class HookExecutor:
    """
    Discovers and executes app-specific hooks.
    """

    def __init__(self):
        self.hooks_dir = Path(__file__).parent
        self.logger = get_logger("mastarr.hook_executor")

    def get_hook_module(self, blueprint_name: str, hook_name: str) -> Optional[Callable]:
        """
        Dynamically import a hook function from an app's hooks directory.

        Args:
            blueprint_name: Name of the blueprint (e.g., "jellyfin")
            hook_name: Name of the hook file (e.g., "post_install")

        Returns:
            The hook function if found, None otherwise

        Example:
            For jellyfin's post_install hook:
            - Looks for: hooks/jellyfin/post_install.py
            - Imports: hooks.jellyfin.post_install
            - Calls: post_install.run(context)
        """
        module_path = f"hooks.{blueprint_name}.{hook_name}"

        try:
            module = importlib.import_module(module_path)

            # Look for a 'run' function in the module
            if hasattr(module, 'run'):
                return module.run

            # Or look for a class that inherits from AppHook
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, AppHook) and obj != AppHook:
                    return obj

            self.logger.warning(
                f"Hook module {module_path} found but has no 'run' function or AppHook class"
            )
            return None

        except ModuleNotFoundError:
            # Hook doesn't exist, which is fine
            self.logger.debug(f"No hook found: {module_path}")
            return None

        except Exception as e:
            self.logger.error(f"Error loading hook {module_path}: {e}", exc_info=True)
            return None

    async def execute_hook(
        self,
        blueprint_name: str,
        hook_name: str,
        context: HookContext
    ) -> bool:
        """
        Execute a specific hook for an app.

        Args:
            blueprint_name: App blueprint name
            hook_name: Hook to execute (post_install, pre_uninstall, etc.)
            context: Hook context with app info

        Returns:
            True if hook executed successfully, False otherwise
        """
        self.logger.info(f"Executing {hook_name} hook for {blueprint_name}")

        hook = self.get_hook_module(blueprint_name, hook_name)

        if not hook:
            self.logger.debug(f"No {hook_name} hook defined for {blueprint_name}")
            return True  # Not having a hook is not a failure

        try:
            # If hook is a class (inherits from AppHook)
            if inspect.isclass(hook):
                hook_instance = hook(context)
                method = getattr(hook_instance, hook_name, None)

                if method and callable(method):
                    await method()
                else:
                    self.logger.warning(
                        f"Hook class {hook} has no method '{hook_name}'"
                    )
                    return False

            # If hook is a function
            elif callable(hook):
                # Check if function expects context parameter
                sig = inspect.signature(hook)
                if len(sig.parameters) > 0:
                    await hook(context)
                else:
                    await hook()

            else:
                self.logger.error(f"Hook {hook} is not callable")
                return False

            self.logger.info(f"✓ {hook_name} hook completed for {blueprint_name}")
            return True

        except Exception as e:
            self.logger.error(
                f"Hook {hook_name} failed for {blueprint_name}: {e}",
                exc_info=True
            )
            return False

    def list_available_hooks(self, blueprint_name: str) -> list[str]:
        """
        List all available hooks for a blueprint.

        Args:
            blueprint_name: Blueprint to check

        Returns:
            List of hook names (without .py extension)
        """
        app_hooks_dir = self.hooks_dir / blueprint_name

        if not app_hooks_dir.exists():
            return []

        hooks = []
        for hook_file in app_hooks_dir.glob("*.py"):
            if hook_file.name != "__init__.py":
                hooks.append(hook_file.stem)

        return hooks


# Singleton instance
_hook_executor = None

def get_hook_executor() -> HookExecutor:
    """Get the global hook executor instance"""
    global _hook_executor
    if _hook_executor is None:
        _hook_executor = HookExecutor()
    return _hook_executor
