"""
Jellyfin app hooks.
"""

from hooks.jellyfin.post_install import run as post_install

__all__ = ["post_install"]
