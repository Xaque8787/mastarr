from typing import Dict, Any, Union, Tuple, Optional


def parse_short_form_volume(volume_str: str) -> Tuple[str, str, Optional[str]]:
    """
    Parse short-form volume string into (source, target, options).

    Strategy: Find the first ':/' pattern - everything before is source,
    everything after is destination (and optional options).

    Args:
        volume_str: Short-form volume string (e.g., "./config:/config:ro")

    Returns:
        Tuple of (source, target, options)

    Examples:
        "./config:/config" → ("./config", "/config", None)
        "./config:/config:ro" → ("./config", "/config", "ro")
        "/path/with:colon:/app" → ("/path/with:colon", "/app", None)
        "/path/with:colon:/app:ro,shared" → ("/path/with:colon", "/app", "ro,shared")
    """
    idx = volume_str.find(':/')

    if idx == -1:
        raise ValueError(f"Invalid volume format (no container path): {volume_str}")

    source = volume_str[:idx]
    remainder = volume_str[idx+1:]

    dest_parts = remainder.split(':', 1)
    destination = dest_parts[0]
    options = dest_parts[1] if len(dest_parts) > 1 else None

    return (source, destination, options)


def transform_volume_to_long_form(volume_definition: Union[Dict[str, Any], str]) -> Dict[str, Any]:
    """
    Transform volume to long-form syntax with HOST_PATH for relative paths.

    Args:
        volume_definition: Either a short-form string or already long-form dict

    Returns:
        Dictionary with long-form volume definition

    Examples:
        "./config:/config:ro" →
        {
            "type": "bind",
            "source": "${HOST_PATH}/config",
            "target": "/config",
            "read_only": True
        }
    """
    if isinstance(volume_definition, dict):
        return transform_long_form_volume(volume_definition)

    source, target, options = parse_short_form_volume(volume_definition)

    long_form = {
        "type": "bind",
        "target": target
    }

    if source.startswith('./'):
        long_form["source"] = f"${{HOST_PATH}}/{source[2:]}"
    else:
        long_form["source"] = source

    if options:
        options_lower = options.lower()
        if 'ro' in options_lower:
            long_form["read_only"] = True

        if 'shared' in options_lower or 'slave' in options_lower or 'private' in options_lower:
            if "bind" not in long_form:
                long_form["bind"] = {}

            if 'rshared' in options_lower:
                long_form["bind"]["propagation"] = "rshared"
            elif 'rslave' in options_lower:
                long_form["bind"]["propagation"] = "rslave"
            elif 'rprivate' in options_lower:
                long_form["bind"]["propagation"] = "rprivate"
            elif 'shared' in options_lower:
                long_form["bind"]["propagation"] = "shared"
            elif 'slave' in options_lower:
                long_form["bind"]["propagation"] = "slave"
            elif 'private' in options_lower:
                long_form["bind"]["propagation"] = "private"

    return long_form


def transform_long_form_volume(volume_def: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform already long-form volume definition.
    Updates source path to use HOST_PATH if relative.

    Args:
        volume_def: Long-form volume dictionary

    Returns:
        Transformed volume dictionary
    """
    transformed = volume_def.copy()

    source = transformed.get("source", "")

    if source.startswith('./'):
        transformed["source"] = f"${{HOST_PATH}}/{source[2:]}"

    return transformed


def parse_short_form_port(port_definition: Union[str, int]) -> Dict[str, Any]:
    """
    Parse short-form port string/int into components.

    Args:
        port_definition: Short-form port (e.g., "8096:8096", "127.0.0.1:8080:8080", "7359:7359/udp")

    Returns:
        Dictionary with parsed port components

    Examples:
        "8096" → {"target": 8096, "published": 8096, "protocol": "tcp"}
        "8096:8096" → {"target": 8096, "published": 8096, "protocol": "tcp"}
        "127.0.0.1:8080:8080" → {"target": 8080, "published": 8080, "host_ip": "127.0.0.1", "protocol": "tcp"}
        "7359:7359/udp" → {"target": 7359, "published": 7359, "protocol": "udp"}
    """
    port_str = str(port_definition)

    host_ip = None
    published = None
    target = None
    protocol = "tcp"

    if '/' in port_str:
        port_str, protocol = port_str.split('/', 1)

    parts = port_str.split(':')

    if len(parts) == 1:
        target = int(parts[0])
        published = target
    elif len(parts) == 2:
        published = int(parts[0])
        target = int(parts[1])
    elif len(parts) == 3:
        host_ip = parts[0]
        published = int(parts[1])
        target = int(parts[2])
    else:
        raise ValueError(f"Invalid port format: {port_definition}")

    long_form = {
        "target": target,
        "published": published,
        "protocol": protocol
    }

    if host_ip:
        long_form["host_ip"] = host_ip

    return long_form


def transform_port_to_long_form(port_definition: Union[Dict[str, Any], str, int]) -> Dict[str, Any]:
    """
    Transform port to long-form syntax.

    Args:
        port_definition: Short-form string/int or already long-form dict

    Returns:
        Dictionary with long-form port definition

    Examples:
        "8096:8096" →
        {
            "target": 8096,
            "published": 8096,
            "protocol": "tcp"
        }
    """
    if isinstance(port_definition, dict):
        return port_definition

    return parse_short_form_port(port_definition)


def transform_user_format(user_input: Union[str, int, Dict[str, int]]) -> str:
    """
    Transform user input into Docker user format (PUID:PGID).

    Args:
        user_input: Can be:
            - String: "1000:1000" (already formatted)
            - String: "1000" (just PUID, will duplicate)
            - Int: 1000 (just PUID, will duplicate)
            - Dict: {"puid": 1000, "pgid": 1000}

    Returns:
        Formatted user string: "1000:1000"

    Examples:
        "1000:1000" → "1000:1000"
        "1000" → "1000:1000"
        1000 → "1000:1000"
        {"puid": 1000, "pgid": 1001} → "1000:1001"
    """
    if isinstance(user_input, dict):
        puid = user_input.get("puid", user_input.get("PUID", 1000))
        pgid = user_input.get("pgid", user_input.get("PGID", 1000))
        return f"{puid}:{pgid}"

    user_str = str(user_input)

    if ":" in user_str:
        return user_str

    return f"{user_str}:{user_str}"
