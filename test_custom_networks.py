#!/usr/bin/env python3
"""
Test script for custom networks feature with dry-run mode.
Tests the transform registry and custom_networks_array transform.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from models.database import get_session, App, Blueprint
from services.compose_generator import ComposeGenerator
from utils.logger import get_logger

logger = get_logger("test_custom_networks")


def test_custom_networks():
    """Test custom networks transform with dry-run mode"""

    logger.info("="*80)
    logger.info("TESTING CUSTOM NETWORKS FEATURE")
    logger.info("="*80)

    db = get_session()

    try:
        # Get jellyfin blueprint
        blueprint = db.query(Blueprint).filter(Blueprint.name == "jellyfin").first()

        if not blueprint:
            logger.error("Jellyfin blueprint not found! Run load_blueprints.py first.")
            return

        logger.info(f"\nFound blueprint: {blueprint.name}")
        logger.info(f"Blueprint has {len(blueprint.schema_json)} fields")

        # Check if custom_networks field exists
        if 'custom_networks' in blueprint.schema_json:
            logger.info("\n✓ custom_networks field found in blueprint")
            field = blueprint.schema_json['custom_networks']
            logger.info(f"  - Type: {field.get('type')}")
            logger.info(f"  - UI Component: {field.get('ui_component')}")
            logger.info(f"  - Transform: {field.get('compose_transform')}")
        else:
            logger.error("\n✗ custom_networks field NOT found in blueprint")
            return

        # Get an existing jellyfin app (if any)
        app = db.query(App).filter(App.blueprint_name == "jellyfin").first()

        if not app:
            logger.warning("\nNo existing Jellyfin app found.")
            logger.info("Creating a test scenario with mock data...")

            # Create mock app for testing
            from models.schemas import AppSchema

            mock_app = App(
                name="test-jellyfin",
                db_name="test_jellyfin",
                blueprint_name="jellyfin",
                raw_inputs={
                    "custom_networks": [
                        {"network_name": "vpn_test", "mode": "create"},
                        {"network_name": "monitoring_test", "mode": "existing"}
                    ],
                    "host_port": {"host": 8096, "container": 8096, "protocol": "tcp"},
                    "config_volume": {"source": "./config", "target": "/config", "type": "bind"}
                },
                service_data={
                    "image": "jellyfin/jellyfin",
                    "container_name": "test_jellyfin"
                },
                compose_data={},
                metadata_data={}
            )

            logger.info("\nMock app created with custom_networks:")
            logger.info(f"  - vpn_test (mode: create)")
            logger.info(f"  - monitoring_test (mode: existing)")

        else:
            mock_app = app
            logger.info(f"\nUsing existing app: {app.name}")
            logger.info(f"Current raw_inputs keys: {list(app.raw_inputs.keys())}")

        # Test with dry-run mode
        logger.info("\n" + "="*80)
        logger.info("GENERATING COMPOSE FILE (DRY RUN MODE)")
        logger.info("="*80 + "\n")

        generator = ComposeGenerator(dry_run=True)
        compose = generator.generate(mock_app, blueprint)

        # Write to console (dry-run will print it)
        output_path = f"/tmp/{mock_app.db_name}/docker-compose.yml"
        generator.write_compose_file(compose, output_path)

        logger.info("\n" + "="*80)
        logger.info("TEST COMPLETED")
        logger.info("="*80)
        logger.info("\nCheck the output above to verify:")
        logger.info("1. Service-level networks includes custom networks")
        logger.info("2. Compose-level networks section has custom networks marked as external")
        logger.info("3. Existing network_config functionality still works")

    except Exception as e:
        logger.error(f"Error during test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    test_custom_networks()
