"""
Radarr app hooks.
"""

from hooks.radarr.post_install import run as post_install

__all__ = ["post_install"]
