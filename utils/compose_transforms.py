"""
Compose transform functions for converting user inputs to Docker Compose format.

Each transform is a pure function that takes user input and returns compose-formatted output.
Transforms are registered in TRANSFORM_REGISTRY and called by compose_generator.py.
"""

from typing import Dict, Any, Optional
import subprocess
from utils.logger import get_logger

logger = get_logger("mastarr.compose_transforms")


def transform_port_mapping(
    user_value: Any,
    field_schema: Dict[str, Any],
    app: Any,
    result: Dict[str, Any],
    transform_cache: Dict[str, Any]
) -> None:
    """
    Transform port mapping input to Docker Compose port format.

    Handles compound field: {host: 8096, container: 8096, protocol: "tcp"}
    Converts to: {"published": 8096, "target": 8096, "protocol": "tcp"}

    Args:
        user_value: User input (dict with host/container/protocol keys)
        field_schema: Blueprint field schema
        app: App instance with raw_inputs
        result: Service data dict to modify
        transform_cache: Cache to prevent duplicate processing
    """
    # Handle compound field (object with host/container/protocol)
    if isinstance(user_value, dict) and 'host' in user_value and 'container' in user_value:
        if 'ports' not in result:
            result['ports'] = []

        port_dict = {
            "published": user_value['host'],
            "target": user_value['container'],
            "protocol": user_value.get('protocol', 'tcp')
        }
        result['ports'].append(port_dict)

    # Legacy handling: separate host_port and container_port fields
    elif 'port_mapping' not in transform_cache:
        host_port = app.raw_inputs.get('host_port')
        container_port = app.raw_inputs.get('container_port')

        if host_port and container_port:
            if 'ports' not in result:
                result['ports'] = []

            port_dict = {
                "published": host_port,
                "target": container_port,
                "protocol": "tcp"
            }
            result['ports'].append(port_dict)
            transform_cache['port_mapping'] = True


def transform_port_array(
    user_value: Any,
    field_schema: Dict[str, Any],
    app: Any,
    result: Dict[str, Any],
    transform_cache: Dict[str, Any]
) -> None:
    """
    Transform array of port objects to Docker Compose port format.

    Input: [{"host": 8096, "container": 8096, "protocol": "tcp"}, ...]
    Output: [{"published": 8096, "target": 8096, "protocol": "tcp"}, ...]

    Skips empty port mappings where host or container is empty.
    """
    if not isinstance(user_value, list):
        return

    if 'ports' not in result:
        result['ports'] = []

    for port_item in user_value:
        if isinstance(port_item, dict) and 'host' in port_item and 'container' in port_item:
            # Skip empty port mappings
            host = port_item['host']
            container = port_item['container']

            # Skip if either value is empty string or None
            if not host or not container or host == '' or container == '':
                continue

            port_dict = {
                "published": port_item['host'],
                "target": port_item['container'],
                "protocol": port_item.get('protocol', 'tcp')
            }
            result['ports'].append(port_dict)


def transform_volume_mapping(
    user_value: Any,
    field_schema: Dict[str, Any],
    app: Any,
    result: Dict[str, Any],
    transform_cache: Dict[str, Any]
) -> None:
    """
    Transform volume mapping input to Docker Compose volume format.

    Handles compound field: {source: "./config", target: "/config", type: "bind"}
    Supports bind options like propagation and create_host_path.

    Legacy mode: If user_value is a string, uses volume_target from field_schema.
    """
    # Handle compound field (object with source/target)
    if isinstance(user_value, dict) and 'source' in user_value and 'target' in user_value:
        if 'volumes' not in result:
            result['volumes'] = []

        volume_dict = {
            "type": user_value.get('type', 'bind'),
            "source": user_value['source'],
            "target": user_value['target']
        }

        # Only add read_only if explicitly set to True
        if user_value.get('read_only'):
            volume_dict['read_only'] = True

        # Handle bind-specific options
        if volume_dict['type'] == 'bind':
            bind_options = {}
            if user_value.get('bind_propagation'):
                bind_options['propagation'] = user_value['bind_propagation']
            if 'bind_create_host_path' in user_value and user_value['bind_create_host_path'] is not None:
                bind_options['create_host_path'] = user_value['bind_create_host_path']

            if bind_options:
                volume_dict['bind'] = bind_options

        result['volumes'].append(volume_dict)

    # Legacy handling: volume_target from field_schema
    elif isinstance(user_value, str):
        volume_target = field_schema.get('volume_target', '/data')

        if 'volumes' not in result:
            result['volumes'] = []

        volume_dict = {
            "type": "bind",
            "source": user_value,
            "target": volume_target,
            "read_only": False
        }
        result['volumes'].append(volume_dict)


def transform_volume_array(
    user_value: Any,
    field_schema: Dict[str, Any],
    app: Any,
    result: Dict[str, Any],
    transform_cache: Dict[str, Any]
) -> None:
    """
    Transform array of volume objects to Docker Compose volume format.

    Handles relative paths by prepending ${HOST_PATH}/ for bind mounts.
    Skips empty volume mappings where source or target is empty.
    """
    if not isinstance(user_value, list):
        return

    if 'volumes' not in result:
        result['volumes'] = []

    for volume_item in user_value:
        if isinstance(volume_item, dict) and 'source' in volume_item and 'target' in volume_item:
            # Skip empty volume mappings
            source = volume_item['source']
            target = volume_item['target']

            # Skip if either value is empty string or None
            if not source or not target or source == '' or target == '':
                continue

            volume_type = volume_item.get('type', 'bind')

            # Apply HOST_PATH prepending for bind mounts with relative paths
            if volume_type == 'bind' and source.startswith('./'):
                source = f"${{HOST_PATH}}/{source[2:]}"

            volume_dict = {
                "type": volume_type,
                "source": source,
                "target": target
            }

            # Only add read_only if explicitly set to True
            if volume_item.get('read_only'):
                volume_dict['read_only'] = True

            # Handle bind-specific options
            if volume_type == 'bind':
                bind_options = {}
                if volume_item.get('bind_propagation'):
                    bind_options['propagation'] = volume_item['bind_propagation']
                if 'bind_create_host_path' in volume_item and volume_item['bind_create_host_path'] is not None:
                    bind_options['create_host_path'] = volume_item['bind_create_host_path']

                if bind_options:
                    volume_dict['bind'] = bind_options

            result['volumes'].append(volume_dict)


def transform_network_config(
    user_value: Any,
    field_schema: Dict[str, Any],
    app: Any,
    result: Dict[str, Any],
    transform_cache: Dict[str, Any]
) -> None:
    """
    Transform network configuration to Docker Compose network format.

    Input: {network_name: "mastarr_net", ipv4_address: "10.21.12.3"}
    Output: {"mastarr_net": {"ipv4_address": "10.21.12.3"}}

    This is for the existing single network field (service-level).
    """
    if not isinstance(user_value, dict):
        return

    network_name = user_value.get('network_name')
    ipv4_address = user_value.get('ipv4_address')

    if network_name:
        if 'networks' not in result:
            result['networks'] = {}

        # Add network with optional IP configuration
        if ipv4_address:
            result['networks'][network_name] = {
                'ipv4_address': ipv4_address
            }
        else:
            # Network without specific config (use dict to allow merge)
            result['networks'][network_name] = {}


def transform_custom_networks_array(
    user_value: Any,
    field_schema: Dict[str, Any],
    app: Any,
    result: Dict[str, Any],
    transform_cache: Dict[str, Any]
) -> None:
    """
    Transform custom networks array to Docker Compose network format.

    Handles network creation via Docker API and compose configuration.

    Input: [
        {"network_name": "vpn_net", "mode": "create"},
        {"network_name": "monitoring", "mode": "existing"}
    ]

    Side effects:
        - Creates networks via Docker API if mode == "create"
        - Stores network info in transform_cache for compose-level networks
        - Adds to service-level networks

    Args:
        user_value: Array of network objects
        field_schema: Blueprint field schema
        app: App instance
        result: Service data dict to modify
        transform_cache: Cache to store networks for compose-level processing
    """
    logger.info(f"🔍 transform_custom_networks_array called")
    logger.info(f"  user_value type: {type(user_value)}")
    logger.info(f"  user_value: {user_value}")

    if not isinstance(user_value, list):
        logger.warning(f"  user_value is not a list, skipping")
        return

    if 'networks' not in result:
        result['networks'] = {}

    # Store custom networks in cache for compose-level processing
    if 'custom_networks' not in transform_cache:
        transform_cache['custom_networks'] = []

    for network_item in user_value:
        if not isinstance(network_item, dict) or 'network_name' not in network_item:
            continue

        network_name = network_item.get('network_name')
        mode = network_item.get('mode', 'existing')

        logger.info(f"  Processing network item: {network_item}")
        logger.info(f"    network_name: '{network_name}', mode: '{mode}'")

        # Skip empty network names
        if not network_name or network_name == '':
            logger.warning(f"    Skipping empty network name")
            continue

        # Create network via Docker API if mode is "create"
        if mode == 'create':
            try:
                # Check if network already exists
                inspect = subprocess.run(
                    ["docker", "network", "inspect", network_name],
                    capture_output=True,
                    text=True
                )

                if inspect.returncode != 0:
                    # Network doesn't exist, create it
                    create_result = subprocess.run(
                        ["docker", "network", "create", network_name],
                        capture_output=True,
                        text=True
                    )

                    if create_result.returncode == 0:
                        logger.info(f"Created custom network: {network_name}")
                    else:
                        logger.error(f"Failed to create network {network_name}: {create_result.stderr}")
                        continue
                else:
                    logger.info(f"Network {network_name} already exists, reusing")

            except Exception as e:
                logger.error(f"Error creating network {network_name}: {e}")
                continue

        # Add to service-level networks (simple attach, no IP config)
        result['networks'][network_name] = {}

        # Store in cache for compose-level networks section
        transform_cache['custom_networks'].append({
            'name': network_name,
            'mode': mode
        })

        logger.info(f"✓ Added custom network '{network_name}' to service (mode: {mode})")
        logger.info(f"  Service networks now: {list(result.get('networks', {}).keys())}")


# Transform registry - maps transform names to functions
TRANSFORM_REGISTRY = {
    'port_mapping': transform_port_mapping,
    'port_array': transform_port_array,
    'volume_mapping': transform_volume_mapping,
    'volume_array': transform_volume_array,
    'network_config': transform_network_config,
    'custom_networks_array': transform_custom_networks_array,
}


def apply_transform(
    transform_type: str,
    user_value: Any,
    field_schema: Dict[str, Any],
    app: Any,
    result: Dict[str, Any],
    transform_cache: Dict[str, Any]
) -> None:
    """
    Apply a transform function to convert user input to compose format.

    Args:
        transform_type: Name of transform (e.g., "port_mapping")
        user_value: User input value from raw_inputs
        field_schema: Blueprint field schema
        app: App instance
        result: Service data dict to modify (mutated in place)
        transform_cache: Cache to prevent duplicate processing and store shared data

    Raises:
        ValueError: If transform_type not found in registry
    """
    transform_func = TRANSFORM_REGISTRY.get(transform_type)

    if not transform_func:
        logger.warning(f"Unknown transform type: {transform_type}")
        return

    transform_func(user_value, field_schema, app, result, transform_cache)


def get_available_transforms():
    """Return list of available transform names."""
    return list(TRANSFORM_REGISTRY.keys())
