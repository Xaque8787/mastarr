#!/usr/bin/env python3
"""
Load blueprint JSON files into the database.
Run this script to initialize blueprints from the blueprints/ directory.
"""

import json
from pathlib import Path
from models.database import Blueprint, get_session, init_db
from utils.logger import setup_logging

logger = setup_logging()


def load_blueprints_from_directory(directory: str = "blueprints"):
    """
    Load all JSON blueprint files from directory into database.

    Args:
        directory: Directory containing blueprint JSON files
    """
    blueprint_dir = Path(directory)

    if not blueprint_dir.exists():
        logger.error(f"Blueprints directory not found: {directory}")
        return

    db = get_session()

    for blueprint_file in blueprint_dir.glob("*.json"):
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

        except Exception as e:
            logger.error(f"Failed to load {blueprint_file.name}: {e}")
            db.rollback()

    db.close()
    logger.info("Blueprint loading complete")


if __name__ == "__main__":
    logger.info("Initializing database...")
    init_db()

    logger.info("Loading blueprints from blueprints/ directory...")
    load_blueprints_from_directory()
