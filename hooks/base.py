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
    inputs: Dict[str, Any] = None

    # Will be populated by hook executor
    db: Any = None
    docker_client: Any = None


class AppHook:
    """
    Base class for app-specific hooks.

    App hooks should inherit from this and implement the methods they need.
    """

    def __init__(self, context: HookContext):
        self.context = context
        self.logger = get_logger(f"mastarr.hooks.{context.blueprint_name}")

    async def post_install(self):
        """
        Called after the app's container starts successfully.

        Use this to:
        - Wait for app to be ready (health checks)
        - Configure the app via its API
        - Create default settings
        - Initialize databases
        """
        pass

    async def pre_uninstall(self):
        """
        Called before the app's container is stopped/removed.

        Use this to:
        - Backup data
        - Clean up resources
        - Notify other services
        """
        pass

    async def health_check(self) -> bool:
        """
        Custom health check for the app.

        Returns:
            True if app is healthy, False otherwise
        """
        return True

    async def configure(self):
        """
        Additional configuration logic.

        Called after post_install completes successfully.
        """
        pass


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
