import yaml
import os
from typing import Dict, Any
from datetime import datetime
from models.schemas import (
    ComposeSchema,
    ServiceSchema,
    ServiceBindVolumeSchema,
    ServiceNamedVolumeSchema,
    ServiceTmpfsVolumeSchema,
    PortMappingSchema,
    ServiceNetworkConfigSchema
)
from models.database import App, Blueprint, GlobalSettings, get_session
from utils.logger import get_logger
from utils.path_resolver import PathResolver

logger = get_logger("mastarr.compose_generator")


class ComposeGenerator:
    """
    Generates Docker Compose files from blueprints and App data.
    Uses schema routing to properly separate service, compose, and metadata.

    This generator does NOT inject hardcoded values - everything comes from
    the blueprint schema definitions and user inputs.
    """

    def __init__(self):
        self.db = get_session()
        self.path_resolver = PathResolver()

    def generate(self, app: App, blueprint: Blueprint) -> ComposeSchema:
        """
        Generate a ComposeSchema object from app's separated schema data.
        No hardcoded injections - everything comes from blueprint definitions.

        Args:
            app: App instance with service_data, compose_data, metadata_data
            blueprint: Blueprint definition with field schemas

        Returns:
            ComposeSchema object ready to be written to YAML
        """
        logger.info(f"Generating compose for {app.name} ({blueprint.name})")

        # Build service config (only dynamic transforms)
        service_config = self._build_service_config(app)

        # Validate with Pydantic (this also transforms volumes/ports to proper format)
        service = ServiceSchema(**service_config)

        # Build compose config from stored data
        compose_config = app.compose_data.copy() if app.compose_data else {}
        compose_config['services'] = {app.db_name: service}
        compose_config['version'] = "3.9"

        # Validate complete compose structure
        compose = ComposeSchema(**compose_config)

        logger.info(f"✓ Compose generated for {app.name}")
        return compose

    def _build_service_config(self, app: App) -> Dict[str, Any]:
        """
        Build service configuration from service_data.
        Only applies truly dynamic transforms that cannot be defined in blueprints.
        """
        service_config = app.service_data.copy() if app.service_data else {}

        # ONLY dynamic transform: Append :${TAG:-latest} to image if no tag/variable present
        if 'image' in service_config:
            image = service_config['image']
            # Don't add tag if already has : or $ (version or variable)
            if ':' not in image and '$' not in image:
                service_config['image'] = f"{image}:${{TAG:-latest}}"

        # Transform network_config to proper networks format if present
        # This handles the special case where we store network config separately
        network_config = service_config.pop('network_config', None)
        if network_config:
            # network_config format: {"mastarr_net": {"ipv4_address": "10.21.12.3"}}
            if 'networks' not in service_config:
                service_config['networks'] = {}

            if isinstance(service_config['networks'], list):
                # Convert list to dict with config
                networks_dict = {}
                for net in service_config['networks']:
                    networks_dict[net] = network_config.get(net, {})
                service_config['networks'] = networks_dict
            elif isinstance(service_config['networks'], dict):
                # Merge network config
                for net_name, net_conf in network_config.items():
                    if net_name in service_config['networks']:
                        service_config['networks'][net_name].update(net_conf)
                    else:
                        service_config['networks'][net_name] = net_conf

        return service_config


    def generate_env_file(self, app_name: str, user_inputs: Dict[str, Any], blueprint: Blueprint) -> str:
        """
        Generate .env file content with variables extracted from blueprint schema.
        Always includes HOST_PATH.

        Args:
            app_name: Application database name
            user_inputs: Dictionary of user-provided input values
            blueprint: Blueprint definition to extract env.* schema fields

        Returns:
            String content for .env file
        """
        host_path = self.path_resolver.get_host_stack_path(app_name)

        env_vars = {}
        env_vars['HOST_PATH'] = host_path

        # Extract fields with schema: "env.*" from blueprint
        for field_name, field_config in blueprint.schema_json.items():
            schema_path = field_config.get('schema', '')
            if schema_path.startswith('env.'):
                env_var_name = schema_path.split('.', 1)[1]
                value = user_inputs.get(field_name)
                if value is not None:
                    env_vars[env_var_name] = value

        # Build .env file content
        lines = [
            "# Auto-generated by Mastarr",
            f"# Application: {app_name}",
            f"# Generated: {datetime.now().isoformat()}",
            "",
        ]

        # Always add HOST_PATH first
        lines.append("# Host path for this stack - used for volume mounts")
        lines.append(f"HOST_PATH={host_path}")
        lines.append("")

        # Add other env vars
        for key, value in env_vars.items():
            if key != 'HOST_PATH':
                lines.append(f"{key}={value}")

        return '\n'.join(lines)

    def write_env_file(self, app_name: str, user_inputs: Dict[str, Any], blueprint: Blueprint, output_path: str):
        """
        Write .env file to disk.

        Args:
            app_name: Application database name
            user_inputs: Dictionary of user-provided input values
            blueprint: Blueprint definition
            output_path: Path to write the .env file
        """
        env_content = self.generate_env_file(app_name, user_inputs, blueprint)

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
