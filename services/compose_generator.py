import yaml
import os
from typing import Dict, Any
from datetime import datetime
from models.schemas import ComposeSchema, ServiceSchema
from models.database import App, Blueprint, GlobalSettings, get_session
from utils.logger import get_logger
from utils.path_resolver import PathResolver
from utils.compose_transforms import transform_volume_to_long_form, transform_port_to_long_form

logger = get_logger("mastarr.compose_generator")


class ComposeGenerator:
    """
    Generates Docker Compose files from blueprints and App data.
    Uses schema routing to properly separate service, compose, and metadata.
    """

    def __init__(self):
        self.db = get_session()
        self.path_resolver = PathResolver()

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

        global_settings = self.db.query(GlobalSettings).first()
        if not global_settings:
            global_settings = GlobalSettings()
            self.db.add(global_settings)
            self.db.commit()

        service_config = self._build_service_config(
            app,
            blueprint,
            global_settings
        )

        service = ServiceSchema(**service_config)

        compose_config = app.compose_data.copy() if app.compose_data else {}

        if 'networks' not in compose_config:
            compose_config['networks'] = {
                global_settings.network_name: {"external": True}
            }

        compose_config['services'] = {app.db_name: service}
        compose_config['version'] = "3.9"

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

        service_config = app.service_data.copy() if app.service_data else {}

        service_config = self._apply_transforms(service_config, blueprint, app)

        if 'image' in service_config and not service_config['image'].endswith('}'):
            service_config['image'] = f"{service_config['image']}:${{TAG:-latest}}"

        service_config = self._transform_volumes_to_long_form(service_config)
        service_config = self._transform_ports_to_long_form(service_config)

        if 'environment' not in service_config:
            service_config['environment'] = {}

        if not isinstance(service_config['environment'], dict):
            service_config['environment'] = {}

        service_config['environment']['PUID'] = global_settings.puid
        service_config['environment']['PGID'] = global_settings.pgid
        service_config['environment']['TZ'] = global_settings.timezone

        ipv4_address = service_config.pop('ipv4_address', None)

        if 'networks' not in service_config:
            service_config['networks'] = [global_settings.network_name]

        if ipv4_address:
            if isinstance(service_config['networks'], list):
                network_name = service_config['networks'][0] if service_config['networks'] else global_settings.network_name
                service_config['networks'] = {
                    network_name: {
                        "ipv4_address": ipv4_address
                    }
                }
            elif isinstance(service_config['networks'], dict):
                for net_name in service_config['networks']:
                    service_config['networks'][net_name]['ipv4_address'] = ipv4_address
                    break

        if 'restart' not in service_config:
            service_config['restart'] = "unless-stopped"

        return service_config

    def _transform_volumes_to_long_form(self, service_config: Dict[str, Any]) -> Dict[str, Any]:
        """Transform all volumes to long-form syntax with HOST_PATH"""
        if 'volumes' not in service_config or not service_config['volumes']:
            return service_config

        transformed_volumes = []
        for volume in service_config['volumes']:
            try:
                transformed_volumes.append(transform_volume_to_long_form(volume))
            except Exception as e:
                logger.warning(f"Failed to transform volume {volume}: {e}")
                transformed_volumes.append(volume)

        service_config['volumes'] = transformed_volumes
        return service_config

    def _transform_ports_to_long_form(self, service_config: Dict[str, Any]) -> Dict[str, Any]:
        """Transform all ports to long-form syntax"""
        if 'ports' not in service_config or not service_config['ports']:
            return service_config

        transformed_ports = []
        for port in service_config['ports']:
            try:
                transformed_ports.append(transform_port_to_long_form(port))
            except Exception as e:
                logger.warning(f"Failed to transform port {port}: {e}")
                transformed_ports.append(port)

        service_config['ports'] = transformed_ports
        return service_config

    def _apply_transforms(
        self,
        service_data: Dict[str, Any],
        blueprint: Blueprint,
        app: App
    ) -> Dict[str, Any]:
        """Apply compose_transform functions to convert inputs to compose format"""

        result = service_data.copy()
        transform_cache = {}

        for field_name, field_schema in blueprint.schema_json.items():
            transform_type = field_schema.get('compose_transform')
            if not transform_type:
                continue

            user_value = app.raw_inputs.get(field_name)
            if user_value is None:
                continue

            if transform_type == 'port_mapping':
                if 'port_mapping' not in transform_cache:
                    host_port = app.raw_inputs.get('host_port')
                    container_port = app.raw_inputs.get('container_port')

                    if host_port and container_port:
                        if 'ports' not in result:
                            result['ports'] = []
                        result['ports'].append(f"{host_port}:{container_port}")
                        transform_cache['port_mapping'] = True

            elif transform_type == 'volume_mapping':
                volume_target = field_schema.get('volume_target', '/data')

                if 'volumes' not in result:
                    result['volumes'] = []
                result['volumes'].append(f"{user_value}:{volume_target}")

        return result

    def generate_env_file(self, app_name: str, user_inputs: Dict[str, Any]) -> str:
        """
        Generate .env file content with HOST_PATH and TAG variables.

        Args:
            app_name: Application database name
            user_inputs: Dictionary of user-provided input values

        Returns:
            String content for .env file
        """
        host_path = self.path_resolver.get_host_stack_path(app_name)

        tag = user_inputs.get('tag', 'latest')

        lines = [
            "# Auto-generated by Mastarr",
            f"# Application: {app_name}",
            f"# Generated: {datetime.now().isoformat()}",
            "",
            "# Host path for this stack - used for volume mounts",
            f"HOST_PATH={host_path}",
            "",
            "# Docker image tag (defaults to 'latest' if not specified)",
            f"TAG={tag}",
        ]

        return '\n'.join(lines)

    def write_env_file(self, app_name: str, user_inputs: Dict[str, Any], output_path: str):
        """
        Write .env file to disk.

        Args:
            app_name: Application database name
            user_inputs: Dictionary of user-provided input values
            output_path: Path to write the .env file
        """
        env_content = self.generate_env_file(app_name, user_inputs)

        with open(output_path, 'w') as f:
            f.write(env_content)

        logger.info(f"✓ .env file written to {output_path}")

    def write_compose_file(self, compose: ComposeSchema, output_path: str):
        """
        Write ComposeSchema to YAML file.

        Args:
            compose: ComposeSchema object
            output_path: Path to write the compose file
        """
        compose_dict = compose.model_dump(exclude_none=True)

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
