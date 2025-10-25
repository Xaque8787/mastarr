"""
Blueprint loader utility.

Loads blueprint JSON files from the blueprints/ directory into the database.
"""

import json
from pathlib import Path
from models.database import Blueprint, get_session
from utils.logger import get_logger

logger = get_logger("mastarr.blueprint_loader")


def load_blueprints_from_directory(directory: str = "blueprints"):
    """
    Load all JSON blueprint files from directory into database.

    This function:
    - Scans the blueprints/ directory for .json files
    - Creates new blueprints or updates existing ones
    - Handles errors gracefully

    Args:
        directory: Directory containing blueprint JSON files

    Returns:
        Tuple of (loaded_count, error_count)
    """
    blueprint_dir = Path(directory)

    if not blueprint_dir.exists():
        logger.error(f"Blueprints directory not found: {directory}")
        return 0, 0

    db = get_session()
    loaded_count = 0
    error_count = 0

    try:
        blueprint_files = list(blueprint_dir.glob("*.json"))

        if not blueprint_files:
            logger.warning(f"No blueprint files found in {directory}")
            return 0, 0

        logger.info(f"Found {len(blueprint_files)} blueprint file(s)")

        for blueprint_file in blueprint_files:
            try:
                logger.info(f"Loading blueprint: {blueprint_file.name}")

                with open(blueprint_file, 'r') as f:
                    data = json.load(f)

                existing = db.query(Blueprint).filter(
                    Blueprint.name == data['name']
                ).first()

                if existing:
                    logger.info(f"Updating existing blueprint: {data['name']}")
                    for key, value in data.items():
                        if key == 'schema':
                            setattr(existing, 'schema_json', value)
                        else:
                            setattr(existing, key, value)
                else:
                    logger.info(f"Creating new blueprint: {data['name']}")
                    blueprint_data = {**data}
                    blueprint_data['schema_json'] = blueprint_data.pop('schema')

                    blueprint = Blueprint(**blueprint_data)
                    db.add(blueprint)

                db.commit()
                logger.info(f"✓ Loaded blueprint: {data['name']}")
                loaded_count += 1

            except Exception as e:
                logger.error(f"Failed to load {blueprint_file.name}: {e}")
                db.rollback()
                error_count += 1

    finally:
        db.close()

    logger.info(f"Blueprint loading complete: {loaded_count} loaded, {error_count} errors")
    return loaded_count, error_count


def get_blueprint_count():
    """
    Get the number of blueprints in the database.

    Returns:
        Number of blueprints
    """
    db = get_session()
    try:
        count = db.query(Blueprint).count()
        return count
    finally:
        db.close()
