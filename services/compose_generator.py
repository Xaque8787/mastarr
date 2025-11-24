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
from utils.compose_transforms import apply_transform

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

        # Get global settings for fallback values
        global_settings = self.db.query(GlobalSettings).first()

        # Build service config with transforms and globals applied
        service_config, transform_cache = self._build_service_config(app, blueprint, global_settings)

        # Validate with Pydantic (this also transforms volumes/ports to proper format)
        service = ServiceSchema(**service_config)

        # Build compose config from stored data
        compose_config = app.compose_data.copy() if app.compose_data else {}
        compose_config['services'] = {app.db_name: service}

        # Add custom networks to compose-level networks section
        if 'custom_networks' in transform_cache:
            if 'networks' not in compose_config:
                compose_config['networks'] = {}

            for network_info in transform_cache['custom_networks']:
                network_name = network_info['name']
                # Mark all custom networks as external (they exist outside compose)
                compose_config['networks'][network_name] = {'external': True}
                logger.debug(f"Added compose-level network: {network_name} (external: true)")

        # Validate complete compose structure
        compose = ComposeSchema(**compose_config)

        logger.info(f"✓ Compose generated for {app.name}")
        return compose

    def _build_service_config(self, app: App, blueprint: Blueprint, global_settings: GlobalSettings):
        """
        Build service configuration from service_data and apply compose_transforms.
        Injects global values for fields that support use_global and are not present in service_data.

        Returns:
            Tuple of (service_config, transform_cache)
        """
        service_config = app.service_data.copy() if app.service_data else {}

        # Inject global values for missing fields that support use_global
        service_config = self._inject_global_values(service_config, blueprint, global_settings)

        # Apply compose_transform functions and get transform cache
        service_config, transform_cache = self._apply_transforms(service_config, blueprint, app)

        # Append :${TAG:-latest} to image if no tag/variable present
        if 'image' in service_config:
            image = service_config['image']
            # Don't add tag if already has : or $ (version or variable)
            if ':' not in image and '$' not in image:
                service_config['image'] = f"{image}:${{TAG:-latest}}"

        # Transform network_config to proper networks format if present
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

        return service_config, transform_cache

    def _inject_global_values(
        self,
        service_config: Dict[str, Any],
        blueprint: Blueprint,
        global_settings: GlobalSettings
    ) -> Dict[str, Any]:
        """
        Inject global values for fields that have use_global set and are missing from service_config.

        Args:
            service_config: Service configuration dict
            blueprint: Blueprint definition with field schemas
            global_settings: Global settings to use for injection

        Returns:
            Updated service_config with global values injected
        """
        result = service_config.copy()

        # Build mapping of global keys to values
        # USER: Use explicit user field if set, otherwise fallback to PUID:PGID
        user_value = global_settings.user if global_settings.user else f"{global_settings.puid}:{global_settings.pgid}"

        global_mapping = {
            "PUID": global_settings.puid,
            "PGID": global_settings.pgid,
            "UMASK": global_settings.umask,
            "TZ": global_settings.timezone,
            "USER": user_value
        }

        # Scan blueprint schema for fields with use_global
        for field_name, field_schema in blueprint.schema_json.items():
            use_global = field_schema.get('use_global')
            if not use_global:
                continue

            schema_path = field_schema.get('schema', '')
            if not schema_path:
                continue

            # Parse schema path: "service.environment.PUID" or "service.user"
            parts = schema_path.split('.')
            if len(parts) < 2 or parts[0] != 'service':
                continue

            # Check if value exists in service_config
            if len(parts) == 2:
                # Service-level field like "service.user"
                field_key = parts[1]
                # Inject if field is missing OR if it's None
                if field_key not in result or result[field_key] is None:
                    # Field missing or None, inject global value
                    if use_global in global_mapping:
                        result[field_key] = global_mapping[use_global]
                        logger.debug(f"Injected global {use_global} into service.{field_key}")

            elif len(parts) == 3 and parts[1] == 'environment':
                # Environment variable like "service.environment.PUID"
                env_key = parts[2]
                if 'environment' not in result:
                    result['environment'] = {}

                # Inject if env var is missing OR if it's None
                if env_key not in result['environment'] or result['environment'][env_key] is None:
                    # Environment var missing or None, inject global value
                    if use_global in global_mapping:
                        result['environment'][env_key] = global_mapping[use_global]
                        logger.debug(f"Injected global {use_global} into service.environment.{env_key}")

        return result

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

            # Delegate to transform registry
            apply_transform(
                transform_type=transform_type,
                user_value=user_value,
                field_schema=field_schema,
                app=app,
                result=result,
                transform_cache=transform_cache
            )

        # Handle custom environment variables (schema: "service.environment.*")
        for field_name, field_schema in blueprint.schema_json.items():
            schema_path = field_schema.get('schema', '')
            if schema_path == 'service.environment.*':
                user_value = app.raw_inputs.get(field_name)
                if isinstance(user_value, list):
                    if 'environment' not in result:
                        result['environment'] = {}

                    for item in user_value:
                        if isinstance(item, dict) and 'key' in item and 'value' in item:
                            # Skip empty key-value pairs
                            key = item['key']
                            value = item['value']

                            if not key or key == '':
                                continue

                            result['environment'][key] = value

        return result, transform_cache


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
        In dry-run mode, prints to console instead of writing to file.

        Args:
            compose: ComposeSchema object
            output_path: Path to write the compose file
        """
        compose_dict = compose.model_dump(exclude_none=True)

        # Remove empty strings, empty dicts, and empty lists recursively
        compose_dict = self._clean_empty_values(compose_dict)

        if 'services' in compose_dict:
            for service_name, service_config in compose_dict['services'].items():
                if 'environment' in service_config and isinstance(service_config['environment'], dict):
                    service_config['environment'] = [
                        f"{k}={v}" for k, v in service_config['environment'].items()
                    ]

        with open(output_path, 'w') as f:
            yaml.dump(compose_dict, f, default_flow_style=False, sort_keys=False)

        logger.info(f"✓ Compose file written to {output_path}")

    def _clean_empty_values(self, data):
        """
        Recursively remove empty strings, empty dicts, and empty lists from data.
        Keeps False and 0 as they are valid values.

        Args:
            data: Dictionary, list, or other value to clean

        Returns:
            Cleaned data structure
        """
        if isinstance(data, dict):
            cleaned = {}
            for key, value in data.items():
                # Recursively clean nested structures
                cleaned_value = self._clean_empty_values(value)

                # Skip empty strings, empty dicts, empty lists
                # But keep False and 0 as they are valid values
                if cleaned_value == '' or \
                   (isinstance(cleaned_value, dict) and len(cleaned_value) == 0) or \
                   (isinstance(cleaned_value, list) and len(cleaned_value) == 0):
                    continue

                cleaned[key] = cleaned_value
            return cleaned
        elif isinstance(data, list):
            # Clean each item in the list
            return [self._clean_empty_values(item) for item in data if item not in ('', None)]
        else:
            return data

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
