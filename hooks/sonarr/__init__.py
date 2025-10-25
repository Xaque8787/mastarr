"""
Sonarr app hooks.
"""

from hooks.sonarr.post_install import run as post_install

__all__ = ["post_install"]
