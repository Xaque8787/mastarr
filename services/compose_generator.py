import yaml
from typing import Dict, Any
from models.schemas import ComposeSchema, ServiceSchema
from models.database import App, Blueprint, GlobalSettings, get_session
from utils.logger import get_logger

logger = get_logger("mastarr.compose_generator")


class ComposeGenerator:
    """
    Generates Docker Compose files from blueprints and App data.
    Uses schema routing to properly separate service, compose, and metadata.
    """

    def __init__(self):
        self.db = get_session()

    def generate(self, app: App, blueprint: Blueprint) -> ComposeSchema:
        """
        Generate a ComposeSchema object from app's separated schema data.

        Args:
            app: App instance with service_data, compose_data, metadata_data
            blueprint: Blueprint definition with field schemas

        Returns:
            ComposeSchema object ready to be written to YAML
        """
        logger.info(f"Generating compose for {app.name} ({blueprint.name})")

        # Get global settings
        global_settings = self.db.query(GlobalSettings).first()
        if not global_settings:
            global_settings = GlobalSettings()
            self.db.add(global_settings)
            self.db.commit()

        # Build service configuration from service_data and transforms
        service_config = self._build_service_config(
            app,
            blueprint,
            global_settings
        )

        # Validate service using ServiceSchema
        service = ServiceSchema(**service_config)

        # Build compose configuration from compose_data
        compose_config = app.compose_data.copy() if app.compose_data else {}

        # Add networks if not present
        if 'networks' not in compose_config:
            compose_config['networks'] = {
                global_settings.network_name: {"external": True}
            }

        # Add the service
        compose_config['services'] = {app.db_name: service}
        compose_config['version'] = "3.9"

        # Validate entire compose using ComposeSchema
        compose = ComposeSchema(**compose_config)

        logger.info(f"✓ Compose generated for {app.name}")
        return compose

    def _build_service_config(
        self,
        app: App,
        blueprint: Blueprint,
        global_settings: GlobalSettings
    ) -> Dict[str, Any]:
        """Build service configuration from service_data and apply transforms"""

        # Start with existing service_data
        service_config = app.service_data.copy() if app.service_data else {}

        # Apply transforms to convert user inputs to compose format
        service_config = self._apply_transforms(service_config, blueprint, app)

        # Add global environment variables (keep as dict for validation)
        if 'environment' not in service_config:
            service_config['environment'] = {}

        # Ensure environment is a dict
        if not isinstance(service_config['environment'], dict):
            service_config['environment'] = {}

        # Add global settings
        service_config['environment']['PUID'] = global_settings.puid
        service_config['environment']['PGID'] = global_settings.pgid
        service_config['environment']['TZ'] = global_settings.timezone

        # Ensure networks is set
        if 'networks' not in service_config:
            service_config['networks'] = [global_settings.network_name]

        # Ensure restart policy
        if 'restart' not in service_config:
            service_config['restart'] = "unless-stopped"

        return service_config

    def _apply_transforms(
        self,
        service_data: Dict[str, Any],
        blueprint: Blueprint,
        app: App
    ) -> Dict[str, Any]:
        """Apply compose_transform functions to convert inputs to compose format"""

        result = service_data.copy()
        transform_cache = {}  # Cache for multi-field transforms

        # Process each field in blueprint
        for field_name, field_schema in blueprint.schema_json.items():
            transform_type = field_schema.get('compose_transform')
            if not transform_type:
                continue

            # Get original user input
            user_value = app.raw_inputs.get(field_name)
            if user_value is None:
                continue

            # Apply transformation
            if transform_type == 'port_mapping':
                # Port mapping needs both host_port and container_port
                if 'port_mapping' not in transform_cache:
                    host_port = app.raw_inputs.get('host_port')
                    container_port = app.raw_inputs.get('container_port')

                    if host_port and container_port:
                        if 'ports' not in result:
                            result['ports'] = []
                        result['ports'].append(f"{host_port}:{container_port}")
                        transform_cache['port_mapping'] = True

            elif transform_type == 'volume_mapping':
                # Volume mapping: source path + target mount point
                volume_target = field_schema.get('volume_target', '/data')

                if 'volumes' not in result:
                    result['volumes'] = []
                result['volumes'].append(f"{user_value}:{volume_target}")

        return result

    def write_compose_file(self, compose: ComposeSchema, output_path: str):
        """
        Write ComposeSchema to YAML file.

        Args:
            compose: ComposeSchema object
            output_path: Path to write the compose file
        """
        compose_dict = compose.model_dump(exclude_none=True)

        # Convert environment dicts to list format for Docker Compose
        if 'services' in compose_dict:
            for service_name, service_config in compose_dict['services'].items():
                if 'environment' in service_config and isinstance(service_config['environment'], dict):
                    service_config['environment'] = [
                        f"{k}={v}" for k, v in service_config['environment'].items()
                    ]

        with open(output_path, 'w') as f:
            yaml.dump(compose_dict, f, default_flow_style=False, sort_keys=False)

        logger.info(f"✓ Compose file written to {output_path}")

    def close(self):
        """Close database session"""
        self.db.close()


def generate_compose(app: App, blueprint: Blueprint) -> ComposeSchema:
    """
    Convenience function to generate compose.

    Args:
        app: App instance with separated schema data
        blueprint: Blueprint definition

    Returns:
        ComposeSchema object
    """
    generator = ComposeGenerator()
    compose = generator.generate(app, blueprint)
    generator.close()
    return compose
