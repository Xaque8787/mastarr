"""
App-specific hooks system.

Each app can have its own directory with hook files:
- post_install.py: Runs after container starts
- pre_uninstall.py: Runs before container stops
- health_check.py: Custom health checks
- configure.py: Additional configuration logic

Hook functions receive:
- app_id: The database ID of the installed app
- db: Database session
- context: Additional context (container info, etc.)
"""

from hooks.base import AppHook, HookContext

__all__ = ["AppHook", "HookContext"]
