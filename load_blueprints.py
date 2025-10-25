#!/usr/bin/env python3
"""
Manual blueprint loader script.

NOTE: Blueprints are automatically loaded on first startup!
This script is only needed for:
- Manually reloading/updating blueprints
- Forcing a reload of modified blueprint files
- Testing blueprint changes

For normal operation, blueprints load automatically when Mastarr starts.
"""

from models.database import init_db
from utils.logger import setup_logging
from utils.blueprint_loader import load_blueprints_from_directory, get_blueprint_count

logger = setup_logging()


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Manual Blueprint Loader")
    logger.info("=" * 60)

    logger.info("Initializing database...")
    init_db()

    current_count = get_blueprint_count()
    logger.info(f"Current blueprints in database: {current_count}")

    logger.info("Loading/updating blueprints from blueprints/ directory...")
    loaded, errors = load_blueprints_from_directory()

    logger.info("=" * 60)
    logger.info(f"Results: {loaded} loaded, {errors} errors")
    logger.info("=" * 60)
