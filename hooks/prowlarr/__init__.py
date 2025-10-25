"""
Prowlarr app hooks.
"""

from hooks.prowlarr.post_install import run as post_install

__all__ = ["post_install"]
