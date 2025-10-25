import yaml
from typing import Dict, Any
from models.schemas import ComposeSchema, ComposeService
from models.database import Blueprint, GlobalSettings, get_session
from utils.logger import get_logger

logger = get_logger("mastarr.compose_generator")


class ComposeGenerator:
    """
    Generates Docker Compose files from blueprints and user inputs.
    Replaces MESS's static compose files with dynamic generation.
    """

    def __init__(self):
        self.db = get_session()

    def generate(
        self,
        blueprint: Blueprint,
        validated_inputs: Dict[str, Any]
    ) -> ComposeSchema:
        """
        Generate a ComposeSchema object from blueprint and user inputs.

        Args:
            blueprint: Blueprint definition
            validated_inputs: User's validated configuration inputs

        Returns:
            ComposeSchema object ready to be written to YAML
        """
        logger.info(f"Generating compose for {blueprint.name}")

        # Get global settings
        global_settings = self.db.query(GlobalSettings).first()
        if not global_settings:
            global_settings = GlobalSettings()
            self.db.add(global_settings)
            self.db.commit()

        # Build environment variables
        environment = self._build_environment(
            blueprint,
            validated_inputs,
            global_settings
        )

        # Build volumes
        volumes = self._build_volumes(blueprint, validated_inputs)

        # Build ports
        ports = self._build_ports(blueprint, validated_inputs)

        # Get static IP if defined
        static_ip = None
        if blueprint.static_ips:
            service_name = blueprint.name
            static_ip = blueprint.static_ips.get(service_name)

        # Create service definition
        container_name = validated_inputs.get(
            'container_name',
            blueprint.name
        )

        service = ComposeService(
            image=validated_inputs.get('image', f"{blueprint.name}:latest"),
            container_name=container_name,
            restart="unless-stopped",
            environment=environment,
            volumes=volumes,
            ports=ports,
            networks=[global_settings.network_name]
        )

        # Create compose object
        compose = ComposeSchema(
            version="3.9",
            services={container_name: service},
            networks={
                global_settings.network_name: {
                    "external": True
                }
            }
        )

        logger.info(f"✓ Compose generated for {blueprint.name}")
        return compose

    def _build_environment(
        self,
        blueprint: Blueprint,
        inputs: Dict[str, Any],
        global_settings: GlobalSettings
    ) -> list:
        """Build environment variables list"""
        env = []

        # Add global settings
        env.append(f"PUID={global_settings.puid}")
        env.append(f"PGID={global_settings.pgid}")
        env.append(f"TZ={global_settings.timezone}")

        # Add user inputs
        for key, value in inputs.items():
            if isinstance(value, bool):
                env.append(f"{key.upper()}={str(value).lower()}")
            elif value is not None and value != "":
                env.append(f"{key.upper()}={value}")

        return env

    def _build_volumes(
        self,
        blueprint: Blueprint,
        inputs: Dict[str, Any]
    ) -> list:
        """Build volumes list"""
        volumes = []

        # Default config volume
        volumes.append(f"./config:/config")

        # Check for user-defined volumes in inputs
        if 'volumes' in inputs and isinstance(inputs['volumes'], list):
            for vol in inputs['volumes']:
                if isinstance(vol, dict):
                    host = vol.get('host_path')
                    container = vol.get('container_path')
                    mode = vol.get('mode', 'rw')
                    if host and container:
                        volumes.append(f"{host}:{container}:{mode}")

        return volumes

    def _build_ports(
        self,
        blueprint: Blueprint,
        inputs: Dict[str, Any]
    ) -> list:
        """Build ports list"""
        ports = []

        # Look for port mappings in inputs
        if 'host_port' in inputs and 'container_port' in inputs:
            host_port = inputs['host_port']
            container_port = inputs['container_port']
            ports.append(f"{host_port}:{container_port}")
        elif 'port' in inputs:
            port = inputs['port']
            ports.append(f"{port}:{port}")

        return ports

    def write_compose_file(
        self,
        compose: ComposeSchema,
        output_path: str
    ):
        """
        Write ComposeSchema to YAML file.

        Args:
            compose: ComposeSchema object
            output_path: Path to write the compose file
        """
        compose_dict = compose.model_dump(exclude_none=True)

        with open(output_path, 'w') as f:
            yaml.dump(compose_dict, f, default_flow_style=False, sort_keys=False)

        logger.info(f"✓ Compose file written to {output_path}")

    def close(self):
        """Close database session"""
        self.db.close()


def generate_compose(
    blueprint: Blueprint,
    validated_inputs: Dict[str, Any]
) -> ComposeSchema:
    """
    Convenience function to generate compose.

    Args:
        blueprint: Blueprint definition
        validated_inputs: User's validated inputs

    Returns:
        ComposeSchema object
    """
    generator = ComposeGenerator()
    compose = generator.generate(blueprint, validated_inputs)
    generator.close()
    return compose
