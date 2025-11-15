# Blueprint JSON Template Documentation

This document provides a comprehensive guide to creating blueprint JSON files for Mastarr applications.

---

## Table of Contents

1. [Blueprint Structure Overview](#blueprint-structure-overview)
2. [Top-Level Properties](#top-level-properties)
3. [Schema Field Types](#schema-field-types)
4. [UI Components](#ui-components)
5. [Schema Routing](#schema-routing)
6. [Compose Transforms](#compose-transforms)
7. [Template Variables](#template-variables)
8. [Lifecycle Hooks](#lifecycle-hooks)
9. [Complete Examples](#complete-examples)

---

## Blueprint Structure Overview

A blueprint JSON file defines how an application should be configured and deployed. Here's the basic structure:

```json
{
  "name": "app_name",
  "display_name": "App Display Name",
  "description": "Brief description of the app",
  "category": "CATEGORY_NAME",
  "icon_url": "/static/images/app.png",
  "install_order": 10.0,
  "visible": true,
  "prerequisites": [],
  "schema": {
    "field_name": {
      "type": "string",
      "ui_component": "text",
      "label": "Field Label",
      "schema": "service.property"
    }
  }
}
```

---

## Top-Level Properties

### Required Properties

#### `name` (string, required)
- **Description**: Internal identifier for the blueprint (lowercase, no spaces)
- **Example**: `"jellyfin"`, `"sonarr"`, `"prowlarr"`
- **Usage**: Used for database lookups and file naming

#### `display_name` (string, required)
- **Description**: User-friendly name shown in the UI
- **Example**: `"Jellyfin"`, `"Sonarr"`, `"Prowlarr"`

#### `description` (string, required)
- **Description**: Brief description of what the application does
- **Example**: `"Install Jellyfin Media Server"`

#### `category` (string, required)
- **Description**: Application category for organization
- **Options**:
  - `"SYSTEM"`
  - `"MEDIA SERVERS"`
  - `"STARR APPS"`
  - `"DOWNLOAD CLIENTS"`
  - `"NETWORKING"`
  - `"MANAGEMENT"`
  - `"M3U UTILITY"`

#### `schema` (object, required)
- **Description**: Field definitions for user input
- **Format**: Object with field names as keys and field schemas as values

### Optional Properties

#### `icon_url` (string, optional)
- **Description**: Path to the app's icon image
- **Example**: `"/static/images/jellyfin.png"`
- **Default**: Placeholder image if not provided

#### `install_order` (float, optional)
- **Description**: Controls display order in the UI (lower = shown first)
- **Example**: `1.0`, `10.0`, `20.0`
- **Default**: `10.0`

#### `visible` (boolean, optional)
- **Description**: Whether to show this blueprint in the UI
- **Example**: `true`, `false`
- **Default**: `true`

#### `prerequisites` (array, optional)
- **Description**: List of app names that must be installed first
- **Example**: `["prowlarr"]`
- **Default**: `[]`

---

## Schema Field Types

Each field in the `schema` object represents a user input. Fields have the following structure:

```json
"field_name": {
  "type": "string",
  "ui_component": "text",
  "label": "Field Label",
  "description": "Optional description",
  "default": "default_value",
  "required": false,
  "visible": true,
  "advanced": false,
  "schema": "service.property_path"
}
```

### Field Type: `string`

Used for text inputs.

```json
"container_name": {
  "type": "string",
  "ui_component": "text",
  "label": "Container Name",
  "default": "jellyfin",
  "placeholder": "Enter container name",
  "required": true,
  "visible": true,
  "advanced": false,
  "schema": "service.container_name"
}
```

**Properties:**
- `type`: `"string"`
- `ui_component`: `"text"`, `"password"`, `"textarea"`
- `placeholder`: Text shown when field is empty
- `pattern`: Regex pattern for validation (optional)

### Field Type: `integer`

Used for numeric inputs.

```json
"host_port": {
  "type": "integer",
  "ui_component": "number",
  "label": "Host Port",
  "default": 8096,
  "placeholder": "8096",
  "min_value": 1,
  "max_value": 65535,
  "required": false,
  "visible": true,
  "advanced": false,
  "schema": "service.ports"
}
```

**Properties:**
- `type`: `"integer"`
- `ui_component`: `"number"`
- `min_value`: Minimum allowed value (optional)
- `max_value`: Maximum allowed value (optional)

### Field Type: `boolean`

Used for checkboxes.

```json
"enable_transcoding": {
  "type": "boolean",
  "ui_component": "checkbox",
  "label": "Enable Hardware Transcoding",
  "default": false,
  "required": false,
  "visible": true,
  "advanced": false,
  "schema": "metadata.enable_transcoding"
}
```

**Properties:**
- `type`: `"boolean"`
- `ui_component`: `"checkbox"`
- `default`: `true` or `false`

### Field Type: `object` (Compound Fields)

Used for grouping related inputs together.

```json
"web_port": {
  "type": "object",
  "label": "Web Port",
  "description": "HTTP port for accessing the application",
  "required": false,
  "visible": true,
  "advanced": false,
  "fields": {
    "host": {
      "type": "integer",
      "label": "Host Port",
      "default": 8096,
      "placeholder": "8096"
    },
    "container": {
      "type": "integer",
      "label": "Container Port",
      "default": 8096,
      "placeholder": "8096"
    },
    "protocol": {
      "type": "string",
      "label": "Protocol",
      "default": "tcp",
      "hidden": true
    }
  },
  "schema": "service.ports",
  "compose_transform": "port_mapping"
}
```

**Properties:**
- `type`: `"object"`
- `fields`: Object containing sub-field definitions
- `compose_transform`: Transform function to apply

**Sub-field Properties:**
- `hidden`: Set to `true` to hide from UI but include in data

**Result sent to backend:**
```json
{
  "web_port": {
    "host": 8096,
    "container": 8096,
    "protocol": "tcp"
  }
}
```

### Field Type: `array` (Dynamic Lists)

Used for allowing users to add multiple items.

#### Array with Key-Value Pairs

```json
"custom_environment": {
  "type": "array",
  "ui_component": "key_value_pairs",
  "label": "Custom Environment Variables",
  "description": "Add custom environment variables",
  "default": [],
  "required": false,
  "visible": true,
  "advanced": true,
  "schema": "service.environment.*"
}
```

**Result sent to backend:**
```json
{
  "custom_environment": [
    {"key": "MY_VAR", "value": "some_value"},
    {"key": "ANOTHER_VAR", "value": "another_value"}
  ]
}
```

**Backend converts to:**
```yaml
environment:
  MY_VAR: some_value
  ANOTHER_VAR: another_value
```

#### Array with Item Schema

```json
"custom_volumes": {
  "type": "array",
  "ui_component": "volume_mapping",
  "label": "Additional Volumes",
  "description": "Add additional volume mappings",
  "default": [],
  "required": false,
  "visible": true,
  "advanced": true,
  "item_schema": {
    "type": {
      "type": "select",
      "label": "Type",
      "default": "bind",
      "options": [
        {"label": "Bind Mount", "value": "bind"},
        {"label": "Named Volume", "value": "volume"}
      ]
    },
    "source": {
      "type": "string",
      "label": "Source",
      "placeholder": "./data or volume_name"
    },
    "target": {
      "type": "string",
      "label": "Container Path",
      "placeholder": "/path/in/container"
    },
    "read_only": {
      "type": "boolean",
      "label": "Read Only",
      "default": false,
      "hidden": true
    }
  },
  "schema": "service.volumes",
  "compose_transform": "volume_array"
}
```

**Properties:**
- `type`: `"array"`
- `ui_component`: `"key_value_pairs"` or custom name
- `item_schema`: Defines structure of each array item
- `min_items`: Minimum number of items (optional)
- `max_items`: Maximum number of items (optional)

**Result sent to backend:**
```json
{
  "custom_volumes": [
    {"type": "bind", "source": "./media", "target": "/media", "read_only": false},
    {"type": "volume", "source": "app_data", "target": "/data", "read_only": false}
  ]
}
```

---

## UI Components

The `ui_component` property determines how the field is rendered in the UI.

### Text Components

#### `text`
- Standard text input
- Use for: container names, image names, paths

#### `password`
- Password input (masked)
- Use for: passwords, API keys, secrets

#### `textarea`
- Multi-line text input
- Use for: long descriptions, JSON configs

### Numeric Components

#### `number`
- Numeric input with increment/decrement buttons
- Use for: ports, user IDs, timeouts

### Boolean Components

#### `checkbox`
- Single checkbox
- Use for: enable/disable options

### Selection Components

#### `dropdown`
- Dropdown select menu
- Requires `options` array

```json
"restart_policy": {
  "type": "string",
  "ui_component": "dropdown",
  "label": "Restart Policy",
  "default": "unless-stopped",
  "options": [
    {"label": "No", "value": "no"},
    {"label": "Always", "value": "always"},
    {"label": "On Failure", "value": "on-failure"},
    {"label": "Unless Stopped", "value": "unless-stopped"}
  ],
  "schema": "service.restart"
}
```

#### `radio_group`
- Radio button group
- Requires `options` array

### Specialized Components

#### `port_mapping`
- Port configuration UI (used with compound fields)
- Renders host/container port inputs side-by-side

#### `volume_mapping`
- Volume configuration UI (used with compound fields)
- Renders source/target path inputs

#### `network_config`
- Network configuration UI (used with compound fields)
- Renders network name and IP address inputs

#### `key_value_pairs`
- Dynamic key-value input with add/remove
- Use for custom environment variables

---

## Schema Routing

The `schema` property determines where the input value is stored and used. It uses dot notation to specify the destination.

### Service Properties

Route to Docker Compose service-level properties.

#### Format: `service.<property>`

**Examples:**

```json
// Basic property
"schema": "service.image"
// Result: services.app_name.image

// Nested property
"schema": "service.container_name"
// Result: services.app_name.container_name

// Environment variable
"schema": "service.environment.PUID"
// Result: services.app_name.environment.PUID

// Array property (requires compose_transform)
"schema": "service.ports"
// Result: services.app_name.ports[...]

"schema": "service.volumes"
// Result: services.app_name.volumes[...]

"schema": "service.networks"
// Result: services.app_name.networks
```

#### Special Service Routes

**Environment Variables (Wildcard):**
```json
"schema": "service.environment.*"
```
- Used with `type: "array"` and `ui_component: "key_value_pairs"`
- Spreads array items as environment variables
- Backend converts: `[{key: "VAR", value: "val"}]` → `environment: {VAR: val}`

**Network Configuration:**
```json
"schema": "service.network_config.${GLOBAL.NETWORK_NAME}.ipv4_address"
```
- Routes to network-specific config
- Supports template variables

### Compose-Level Properties

Route to top-level Docker Compose properties (outside services).

#### Format: `compose.<property>`

**Examples:**

```json
// Network definition
"schema": "compose.networks.${GLOBAL.NETWORK_NAME}"
// Result: networks.mastarr_net

// Volume definition
"schema": "compose.volumes.app_data"
// Result: volumes.app_data
```

### Environment File Properties

Route to `.env` file variables.

#### Format: `env.<VARIABLE_NAME>`

**Examples:**

```json
"tag": {
  "type": "string",
  "ui_component": "text",
  "label": "Image Tag",
  "default": "latest",
  "schema": "env.TAG"
}
```

**Result in `.env` file:**
```
TAG=latest
```

**Used in compose file:**
```yaml
services:
  app:
    image: app_image:${TAG:-latest}
```

### Metadata Properties

Route to application metadata (stored in database, not in compose file).

#### Format: `metadata.<property>`

**Examples:**

```json
"admin_user": {
  "type": "string",
  "ui_component": "text",
  "label": "Admin Username",
  "required": true,
  "schema": "metadata.admin_user"
}
```

**Usage:**
- Stored in `app.metadata_data` in database
- Used by post-install hooks
- Not included in Docker Compose file

---

## Compose Transforms

The `compose_transform` property specifies a function to convert user input into Docker Compose format.

### Available Transforms

#### `port_mapping`

Converts compound field to port mapping.

**Input (compound field):**
```json
{
  "web_port": {
    "host": 8096,
    "container": 8096,
    "protocol": "tcp"
  }
}
```

**Output (Docker Compose):**
```yaml
ports:
  - published: 8096
    target: 8096
    protocol: tcp
```

**Legacy Support:** Also works with separate `host_port` and `container_port` fields.

#### `port_array`

Converts array of port objects to port mappings.

**Input:**
```json
{
  "custom_ports": [
    {"host": 8080, "container": 80, "protocol": "tcp"},
    {"host": 8443, "container": 443, "protocol": "tcp"}
  ]
}
```

**Output:**
```yaml
ports:
  - published: 8080
    target: 80
    protocol: tcp
  - published: 8443
    target: 443
    protocol: tcp
```

#### `volume_mapping`

Converts compound field to volume mapping.

**Input (compound field):**
```json
{
  "config_volume": {
    "source": "./config",
    "target": "/config",
    "bind_propagation": "rprivate",
    "bind_create_host_path": true
  }
}
```

**Output (Docker Compose):**
```yaml
volumes:
  - type: bind
    source: ${HOST_PATH}/config
    target: /config
    read_only: false
    bind:
      propagation: rprivate
      create_host_path: true
```

**Note:** Automatically prepends `${HOST_PATH}/` to relative paths starting with `./`

**Advanced Bind Mount Options:**
- `bind_propagation`: Mount propagation mode (rprivate, shared, slave, rshared, rslave)
- `bind_create_host_path`: Create directory on host if it doesn't exist (default: true)

**Legacy Support:** Also works with single `source` string and `volume_target` property.

#### `volume_array`

Converts array of volume objects to volume mappings.

**Input:**
```json
{
  "custom_volumes": [
    {
      "type": "bind",
      "source": "./media",
      "target": "/media",
      "bind_propagation": "shared",
      "bind_create_host_path": true
    },
    {
      "type": "volume",
      "source": "app_data",
      "target": "/data"
    }
  ]
}
```

**Output:**
```yaml
volumes:
  - type: bind
    source: ${HOST_PATH}/media
    target: /media
    read_only: false
    bind:
      propagation: shared
      create_host_path: true
  - type: volume
    source: app_data
    target: /data
    read_only: false
```

#### `network_config`

Converts compound field to network configuration.

**Input:**
```json
{
  "service_network": {
    "network_name": "mastarr_net",
    "ipv4_address": "10.21.12.3"
  }
}
```

**Output (Docker Compose):**
```yaml
networks:
  mastarr_net:
    ipv4_address: 10.21.12.3
```

---

## Template Variables

Template variables are automatically expanded when the blueprint schema is loaded.

### Global Variables

These come from the `GlobalSettings` database table:

- `${GLOBAL.PUID}` - User ID for file permissions (default: 1000)
- `${GLOBAL.PGID}` - Group ID for file permissions (default: 1000)
- `${GLOBAL.USER}` - Docker user for container process (default: computed as PUID:PGID if not set)
- `${GLOBAL.TIMEZONE}` - System timezone (default: America/New_York)
- `${GLOBAL.NETWORK_NAME}` - Docker network name (default: mastarr_net)
- `${GLOBAL.NETWORK_SUBNET}` - Network subnet (default: 10.21.12.0/24)
- `${GLOBAL.NETWORK_GATEWAY}` - Network gateway (default: 10.21.12.1)
- `${GLOBAL.STACKS_PATH}` - Base path for app stacks
- `${GLOBAL.DATA_PATH}` - Base path for app data

#### Understanding PUID/PGID vs USER

**PUID and PGID:**
- Used as environment variables for file ownership/permissions
- Many containers use these environment variables internally to set file ownership
- Example: Files created by the app will be owned by PUID:PGID

**USER:**
- Used as the service-level `user:` field in docker-compose.yml
- Determines which user the container process runs as
- Can be different from PUID:PGID to separate process user from file ownership
- Supports formats: `"1000:1000"`, `"root"`, `"username:groupname"`

**When USER is blank:**
- Automatically computed as `PUID:PGID` (e.g., `"1001:1002"`)
- Provides backward compatibility

**When USER is set:**
- Uses the explicit value (e.g., `"root"`, `"1500:1500"`)
- PUID/PGID still available as environment variables
- Allows running container as root while files are owned by PUID:PGID

**Example Scenarios:**

*Scenario 1: Standard Setup (USER blank)*
```
PUID: 1001
PGID: 1002
USER: (blank)

Result in compose.yaml:
  environment:
    - PUID=1001
    - PGID=1002
  user: "1001:1002"  # Auto-computed
```

*Scenario 2: Root Container, Non-Root Files*
```
PUID: 1001
PGID: 1002
USER: root

Result in compose.yaml:
  environment:
    - PUID=1001       # For file ownership
    - PGID=1002       # For file ownership
  user: "root"        # Container runs as root
```

*Scenario 3: Custom User*
```
PUID: 1001
PGID: 1002
USER: 1500:1500

Result in compose.yaml:
  environment:
    - PUID=1001
    - PGID=1002
  user: "1500:1500"   # Process runs as 1500:1500
```

### Usage Examples

```json
"puid": {
  "type": "integer",
  "ui_component": "number",
  "label": "PUID",
  "default": "${GLOBAL.PUID}",
  "schema": "service.environment.PUID"
}
```

When loaded, `${GLOBAL.PUID}` is replaced with actual value: `1000`

### Template Variables in Schema Paths

Templates can be used in schema routing:

```json
"schema": "service.network_config.${GLOBAL.NETWORK_NAME}.ipv4_address"
```

Expands to:
```json
"schema": "service.network_config.mastarr_net.ipv4_address"
```

---

## Field Properties Reference

### Common Properties (All Field Types)

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `type` | string | ✓ | Field data type: `string`, `integer`, `boolean`, `object`, `array` |
| `ui_component` | string | ✓ | UI rendering component (see UI Components section) |
| `label` | string | ✓ | Display label for the field |
| `description` | string | | Additional help text shown below field |
| `tooltip` | string | | Tooltip text on hover |
| `placeholder` | string | | Placeholder text for empty inputs |
| `default` | any | | Default value when field is initialized |
| `required` | boolean | | Whether field must be filled (default: `false`) |
| `visible` | boolean | | Whether field is shown in UI (default: `true`) |
| `advanced` | boolean | | Whether field is in "Advanced Options" section (default: `false`) |
| `is_sensitive` | boolean | | Whether value is sensitive (masked in logs) (default: `false`) |
| `schema` | string | | Routing path for where value is stored |
| `compose_transform` | string | | Transform function to apply to value |

### String-Specific Properties

| Property | Type | Description |
|----------|------|-------------|
| `pattern` | string | Regex pattern for validation |

### Integer-Specific Properties

| Property | Type | Description |
|----------|------|-------------|
| `min_value` | integer | Minimum allowed value |
| `max_value` | integer | Maximum allowed value |

### Dropdown/Radio Properties

| Property | Type | Description |
|----------|------|-------------|
| `options` | array | Array of `{label, value}` objects |

### Object-Specific Properties

| Property | Type | Description |
|----------|------|-------------|
| `fields` | object | Sub-field definitions (nested schema) |

### Array-Specific Properties

| Property | Type | Description |
|----------|------|-------------|
| `item_schema` | object | Schema definition for array items |
| `min_items` | integer | Minimum number of items allowed |
| `max_items` | integer | Maximum number of items allowed |

### Conditional Properties

| Property | Type | Description |
|----------|------|-------------|
| `show_when` | object | Conditions for showing this field |
| `dependent_fields` | object | Fields that depend on this field's value |
| `prerequisites` | array | Apps that must be installed for this field to show |

---

## Lifecycle Hooks

Mastarr provides a comprehensive hook system that allows you to execute custom code at specific points in an application's lifecycle. Hooks are Python files located in the `hooks/<app_name>/` directory.

### Available Hooks

Ten lifecycle hooks are available:

#### Installation Hooks
- **`pre_install.py`** - Runs before app installation begins
  - Use for: Validating prerequisites, creating required directories
- **`post_install.py`** - Runs after app installation completes
  - Use for: Initial configuration, API key generation, user creation

#### Update Hooks
- **`pre_update.py`** - Runs before configuration update
  - Use for: Backing up current config, validating new settings
- **`post_update.py`** - Runs after configuration update and restart
  - Use for: Verifying new configuration, updating related settings

#### Start Hooks
- **`pre_start.py`** - Runs before container starts
  - Use for: Pre-flight checks, environment preparation
- **`post_start.py`** - Runs after container starts
  - Use for: Health checks, initialization verification

#### Stop Hooks
- **`pre_stop.py`** - Runs before container stops
  - Use for: Graceful shutdown tasks, saving state
- **`post_stop.py`** - Runs after container stops
  - Use for: Cleanup tasks, backup creation

#### Remove Hooks
- **`pre_remove.py`** - Runs before app is uninstalled
  - Use for: Final backups, cleanup preparation
- **`post_remove.py`** - Runs after app is uninstalled
  - Use for: Removing orphaned data, final cleanup

### Hook File Structure

Hooks are organized by app name:

```
hooks/
├── jellyfin/
│   ├── __init__.py
│   ├── pre_install.py
│   ├── post_install.py
│   ├── pre_update.py
│   ├── post_update.py
│   ├── pre_start.py
│   ├── post_start.py
│   ├── pre_stop.py
│   ├── post_stop.py
│   ├── pre_remove.py
│   └── post_remove.py
├── radarr/
│   ├── __init__.py
│   └── post_install.py
└── sonarr/
    ├── __init__.py
    └── post_install.py
```

### Creating a Hook

Each hook file should define an async `run()` function that accepts a `HookContext`:

```python
"""
Post-install hook for MyApp.
Runs after MyApp is installed and started.
"""
from hooks.base import HookContext
from utils.logger import get_logger
import httpx

logger = get_logger("mastarr.hooks.myapp.post_install")


async def run(context: HookContext):
    """
    Execute post-install tasks for MyApp.

    Args:
        context: Hook context with app info
    """
    logger.info("=" * 60)
    logger.info("[POST-INSTALL] Setting up MyApp")
    logger.info(f"App: {context.app_name}")
    logger.info(f"Container: {context.container_name}")

    # Access metadata from blueprint
    if context.app and context.app.metadata_data:
        admin_user = context.app.metadata_data.get("admin_user")
        admin_password = context.app.metadata_data.get("admin_password")

        # Wait for app to be ready
        await wait_for_app_ready(context.container_name)

        # Perform initial configuration
        await configure_app(admin_user, admin_password)

    logger.info("✓ MyApp setup complete")
    logger.info("=" * 60)


async def wait_for_app_ready(container_name: str, max_attempts: int = 30):
    """Wait for app to respond to health checks."""
    for attempt in range(max_attempts):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"http://{container_name}:8080/health",
                    timeout=5.0
                )
                if response.status_code == 200:
                    logger.info(f"✓ {container_name} is ready")
                    return
        except Exception:
            pass

        logger.debug(f"Waiting for {container_name}... ({attempt + 1}/{max_attempts})")
        await asyncio.sleep(2)

    logger.warning(f"{container_name} did not become ready in time")


async def configure_app(username: str, password: str):
    """Configure app with initial settings."""
    # Your configuration logic here
    logger.info(f"Creating admin user: {username}")
```

### HookContext API

The `HookContext` object provides access to app information:

```python
class HookContext:
    app_id: int              # Database ID of the app
    app_name: str            # Name of the app (e.g., "jellyfin")
    blueprint_name: str      # Blueprint name (usually same as app_name)
    container_name: str      # Docker container name
    app: Optional[App]       # Full app database object (includes metadata_data)
```

**Accessing Metadata:**
```python
if context.app and context.app.metadata_data:
    api_key = context.app.metadata_data.get("api_key")
    admin_user = context.app.metadata_data.get("admin_user")
```

**Accessing Service Data:**
```python
if context.app and context.app.service_data:
    image = context.app.service_data.get("image")
    ports = context.app.service_data.get("ports", [])
```

### Hook Best Practices

#### 1. Use Async Functions

All hooks should be async:
```python
async def run(context: HookContext):
    # Your code here
```

#### 2. Add Logging

Provide clear feedback about what the hook is doing:
```python
logger.info("Starting configuration...")
logger.info(f"✓ Created user: {username}")
logger.warning("API key not provided, skipping setup")
logger.error("Failed to connect to app", exc_info=True)
```

#### 3. Handle Errors Gracefully

Don't let hooks crash the entire operation:
```python
try:
    await configure_something()
except Exception as e:
    logger.error(f"Configuration failed: {e}")
    # Decide: raise to stop process, or continue
```

#### 4. Wait for Services

After containers start, wait for them to be ready:
```python
async def wait_for_ready(container_name: str):
    for _ in range(30):
        try:
            async with httpx.AsyncClient() as client:
                await client.get(f"http://{container_name}:8080")
                return
        except:
            await asyncio.sleep(2)
```

#### 5. Use Metadata for Configuration

Store user input in metadata and access it in hooks:
```python
# In blueprint:
"admin_user": {
  "type": "string",
  "schema": "metadata.admin_user"
}

# In hook:
admin_user = context.app.metadata_data.get("admin_user")
```

#### 6. Document Your Hooks

Add clear docstrings explaining what the hook does:
```python
"""
Post-install hook for Jellyfin.
Creates initial admin user and configures media libraries.
"""
```

### Hook Execution Flow

Understanding when hooks run:

#### Install Flow
1. `pre_install` hook
2. Generate docker-compose.yml
3. Start containers (`docker compose up`)
4. `pre_start` hook
5. Containers start
6. `post_start` hook
7. `post_install` hook

#### Update Flow
1. `pre_update` hook
2. Stop containers (`docker compose down`)
3. Update configuration
4. Regenerate docker-compose.yml
5. Start containers (`docker compose up`)
6. `pre_start` hook
7. Containers start
8. `post_start` hook
9. `post_update` hook

#### Start Flow
1. `pre_start` hook
2. Start containers (`docker compose up`)
3. Containers start
4. `post_start` hook

#### Stop Flow
1. `pre_stop` hook
2. Stop containers (`docker compose down`)
3. Containers stop
4. `post_stop` hook

#### Remove Flow
1. `pre_remove` hook
2. Stop containers (`docker compose down`)
3. Remove stack directory
4. Delete from database
5. `post_remove` hook

### Common Hook Patterns

#### Pattern: Wait and Configure
```python
async def run(context: HookContext):
    # Wait for app to be ready
    await wait_for_ready(context.container_name)

    # Perform configuration
    await setup_config(context)
```

#### Pattern: API Integration
```python
async def run(context: HookContext):
    api_key = context.app.metadata_data.get("api_key")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"http://{context.container_name}:7878/api/v3/settings",
            headers={"X-Api-Key": api_key},
            json={"setting": "value"}
        )
```

#### Pattern: File Operations
```python
async def run(context: HookContext):
    from utils.path_resolver import PathResolver

    path_resolver = PathResolver()
    stack_path = path_resolver.get_stack_path(context.app.db_name)
    config_path = stack_path / "config" / "config.xml"

    # Modify configuration file
    if config_path.exists():
        content = config_path.read_text()
        # Modify content...
        config_path.write_text(content)
```

---

## Complete Examples

### Example 1: Simple Media Server App

```json
{
  "name": "jellyfin",
  "display_name": "Jellyfin",
  "description": "Free media server for movies, TV shows, and music",
  "category": "MEDIA SERVERS",
  "icon_url": "/static/images/jellyfin.png",
  "install_order": 1.0,
  "visible": true,
  "prerequisites": [],
  "schema": {
    "image": {
      "type": "string",
      "ui_component": "text",
      "label": "Docker Image",
      "default": "jellyfin/jellyfin",
      "required": false,
      "visible": true,
      "advanced": false,
      "schema": "service.image"
    },
    "tag": {
      "type": "string",
      "ui_component": "text",
      "label": "Image Tag",
      "default": "latest",
      "description": "Docker image tag/version",
      "required": false,
      "visible": true,
      "advanced": true,
      "schema": "env.TAG"
    },
    "container_name": {
      "type": "string",
      "ui_component": "text",
      "label": "Container Name",
      "default": "jellyfin",
      "required": false,
      "visible": true,
      "advanced": false,
      "schema": "service.container_name"
    },
    "web_port": {
      "type": "object",
      "label": "Web Port",
      "description": "HTTP port for accessing Jellyfin",
      "required": false,
      "visible": true,
      "advanced": false,
      "fields": {
        "host": {
          "type": "integer",
          "label": "Host Port",
          "default": 8096
        },
        "container": {
          "type": "integer",
          "label": "Container Port",
          "default": 8096
        },
        "protocol": {
          "type": "string",
          "default": "tcp",
          "hidden": true
        }
      },
      "schema": "service.ports",
      "compose_transform": "port_mapping"
    },
    "config_volume": {
      "type": "object",
      "label": "Config Volume",
      "description": "Path for configuration files",
      "required": false,
      "visible": true,
      "advanced": false,
      "fields": {
        "source": {
          "type": "string",
          "label": "Host Path",
          "default": "./config"
        },
        "target": {
          "type": "string",
          "label": "Container Path",
          "default": "/config",
          "hidden": true
        },
        "bind_propagation": {
          "type": "string",
          "ui_component": "dropdown",
          "label": "Bind Propagation",
          "description": "Mount propagation mode",
          "required": false,
          "advanced": true,
          "options": [
            {"label": "Default (rprivate)", "value": ""},
            {"label": "rprivate - Private, no sub-mount sharing", "value": "rprivate"},
            {"label": "shared - Sub-mounts visible both ways", "value": "shared"},
            {"label": "slave - Host sub-mounts visible in container", "value": "slave"},
            {"label": "rshared - Shared with nested sub-mounts", "value": "rshared"},
            {"label": "rslave - Slave with nested sub-mounts", "value": "rslave"}
          ]
        },
        "bind_create_host_path": {
          "type": "boolean",
          "label": "Create Host Path",
          "default": true,
          "description": "Create directory on host if it doesn't exist",
          "advanced": true
        }
      },
      "schema": "service.volumes",
      "compose_transform": "volume_mapping"
    },
    "puid": {
      "type": "integer",
      "ui_component": "number",
      "label": "PUID",
      "default": "${GLOBAL.PUID}",
      "description": "User ID for file permissions",
      "required": false,
      "visible": true,
      "advanced": true,
      "schema": "service.environment.PUID"
    },
    "pgid": {
      "type": "integer",
      "ui_component": "number",
      "label": "PGID",
      "default": "${GLOBAL.PGID}",
      "description": "Group ID for file permissions",
      "required": false,
      "visible": true,
      "advanced": true,
      "schema": "service.environment.PGID"
    },
    "timezone": {
      "type": "string",
      "ui_component": "text",
      "label": "Timezone",
      "default": "${GLOBAL.TIMEZONE}",
      "required": false,
      "visible": true,
      "advanced": true,
      "schema": "service.environment.TZ"
    },
    "user": {
      "type": "string",
      "ui_component": "text",
      "label": "Docker User",
      "default": "${GLOBAL.USER}",
      "description": "User to run container as (e.g., '1000:1000', 'root'). Leave blank to use PUID:PGID",
      "placeholder": "Leave blank for auto (PUID:PGID)",
      "required": false,
      "visible": true,
      "advanced": true,
      "schema": "service.user",
      "use_global": "USER"
    },
    "custom_environment": {
      "type": "array",
      "ui_component": "key_value_pairs",
      "label": "Custom Environment Variables",
      "description": "Add custom environment variables",
      "default": [],
      "required": false,
      "visible": true,
      "advanced": true,
      "schema": "service.environment.*"
    },
    "service_network": {
      "type": "object",
      "label": "Network Configuration",
      "description": "Docker network settings",
      "required": false,
      "visible": true,
      "advanced": true,
      "fields": {
        "network_name": {
          "type": "string",
          "label": "Network Name",
          "default": "${GLOBAL.NETWORK_NAME}"
        },
        "ipv4_address": {
          "type": "string",
          "label": "Static IP Address",
          "default": "10.21.12.3"
        }
      },
      "schema": "service.networks",
      "compose_transform": "network_config"
    },
    "compose_network_def": {
      "type": "string",
      "ui_component": "text",
      "label": "Network Definition (internal)",
      "default": "{\"external\": true}",
      "required": false,
      "visible": false,
      "advanced": false,
      "schema": "compose.networks.${GLOBAL.NETWORK_NAME}"
    }
  }
}
```

### Example 2: Download Client with Prerequisites

```json
{
  "name": "radarr",
  "display_name": "Radarr",
  "description": "Movie collection manager for Usenet and BitTorrent",
  "category": "STARR APPS",
  "icon_url": "/static/images/radarr.png",
  "install_order": 5.0,
  "visible": true,
  "prerequisites": ["prowlarr"],
  "schema": {
    "image": {
      "type": "string",
      "ui_component": "text",
      "label": "Docker Image",
      "default": "linuxserver/radarr",
      "schema": "service.image"
    },
    "container_name": {
      "type": "string",
      "ui_component": "text",
      "label": "Container Name",
      "default": "radarr",
      "schema": "service.container_name"
    },
    "web_port": {
      "type": "object",
      "label": "Web Port",
      "fields": {
        "host": {
          "type": "integer",
          "label": "Host Port",
          "default": 7878
        },
        "container": {
          "type": "integer",
          "label": "Container Port",
          "default": 7878
        },
        "protocol": {
          "type": "string",
          "default": "tcp",
          "hidden": true
        }
      },
      "schema": "service.ports",
      "compose_transform": "port_mapping"
    },
    "restart_policy": {
      "type": "string",
      "ui_component": "dropdown",
      "label": "Restart Policy",
      "default": "unless-stopped",
      "options": [
        {"label": "No", "value": "no"},
        {"label": "Always", "value": "always"},
        {"label": "On Failure", "value": "on-failure"},
        {"label": "Unless Stopped", "value": "unless-stopped"}
      ],
      "advanced": true,
      "schema": "service.restart"
    },
    "api_key": {
      "type": "string",
      "ui_component": "password",
      "label": "API Key",
      "placeholder": "Generate an API key",
      "is_sensitive": true,
      "required": true,
      "schema": "metadata.api_key"
    }
  }
}
```

---

## Best Practices

### 1. Use Compound Fields for Related Inputs

**Bad:**
```json
"host_port": {...},
"container_port": {...}
```

**Good:**
```json
"web_port": {
  "type": "object",
  "fields": {
    "host": {...},
    "container": {...}
  }
}
```

### 2. Provide Sensible Defaults

Always provide `default` values so users can install with minimal configuration.

### 3. Use Template Variables

Reference global settings instead of hardcoding:
```json
"default": "${GLOBAL.PUID}"  // Good
"default": 1000               // Bad (hardcoded)
```

### 4. Mark Sensitive Fields

```json
"api_key": {
  "type": "string",
  "ui_component": "password",
  "is_sensitive": true
}
```

### 5. Organize with Advanced Settings

Put rarely-changed settings in advanced section:
```json
"advanced": true
```

### 6. Add Descriptions

Help users understand what each field does:
```json
"description": "Port on the host to access Jellyfin web interface"
```

### 7. Use Hidden Fields for Computed Values

```json
"protocol": {
  "type": "string",
  "default": "tcp",
  "hidden": true
}
```

### 8. Validate Input with Constraints

```json
"port": {
  "type": "integer",
  "min_value": 1,
  "max_value": 65535
}
```

---

## Troubleshooting

### Value Not Appearing in Compose File

1. Check `schema` routing path is correct
2. Verify field has a `default` value or user provided input
3. If using `compose_transform`, ensure it's implemented in `compose_generator.py`

### Template Variable Not Expanding

1. Ensure variable name is correct (case-sensitive)
2. Check that global setting exists in database
3. Verify variable is in a `default` value, not in a label/description

### Custom Environment Variables Not Working

1. Ensure `schema` is `"service.environment.*"` (with asterisk)
2. Verify `type` is `"array"`
3. Check `ui_component` is `"key_value_pairs"`

### Network Configuration Not Applied

1. Ensure both network field and compose network definition exist
2. Verify network_name template variable is expanded
3. Check `compose_transform: "network_config"` is set

---

## Advanced Topics

### Creating Custom Transforms

To create a new transform:

1. Add transform logic to `services/compose_generator.py` in `_apply_transforms()`
2. Reference the transform name in blueprint: `"compose_transform": "my_transform"`

### Hook System Details

Refer to the [Lifecycle Hooks](#lifecycle-hooks) section for complete documentation on creating and using hooks.

---

## Summary

This template provides everything needed to create blueprint JSON files for Mastarr applications. Key points:

- Use appropriate field types (`string`, `integer`, `boolean`, `object`, `array`)
- Route values correctly with `schema` property
- Apply transforms for complex Docker Compose structures
- Leverage template variables for global settings
- Use compound fields and arrays for flexible configurations
- Mark sensitive data appropriately
- Provide helpful defaults and descriptions

For questions or issues, refer to the example blueprints in the `blueprints/` directory.
