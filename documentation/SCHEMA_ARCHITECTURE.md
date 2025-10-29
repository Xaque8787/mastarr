# Schema Architecture - Implementation Guide

## Overview

The application now uses a **three-schema architecture** to properly separate Docker configuration from application metadata. This allows clean compose files and enables hooks to access setup data.

---

## Three Schema Types

### 1. **ServiceSchema** - Docker Service Configuration
- **Purpose**: Define Docker service properties (image, ports, volumes, environment)
- **Used by**: Compose generator to create service definitions
- **Stored in**: `app.service_data` column

**Example Data**:
```json
{
  "image": "jellyfin/jellyfin:latest",
  "container_name": "jellyfin",
  "ports": ["8096:8096"],
  "volumes": ["./config:/config", "./cache:/cache"]
}
```

---

### 2. **ComposeSchema** - Top-Level Compose Configuration
- **Purpose**: Define top-level compose elements (networks, volumes, secrets)
- **Used by**: Compose generator to create complete compose file
- **Stored in**: `app.compose_data` column

**Example Data**:
```json
{
  "networks": {
    "mastarr_net": {
      "external": true
    }
  }
}
```

---

### 3. **MetadataSchema** - Application Metadata
- **Purpose**: Store app-specific configuration NOT in compose file
- **Used by**: Post-install hooks for application setup
- **Stored in**: `app.metadata_data` column

**Example Data**:
```json
{
  "admin_user": "myadmin",
  "admin_password": "securepass123",
  "enable_transcoding": true
}
```

---

## Blueprint Field Configuration

### Dot Notation Schema Routing

Each field in a blueprint specifies where its data goes using **dot notation**:

```json
{
  "field_name": {
    "type": "string",
    "ui_component": "text",
    "label": "Field Label",
    "schema": "service.image"
  }
}
```

### Schema Path Format

- **`service.<field>`** - Goes to ServiceSchema
  - Examples: `service.image`, `service.container_name`, `service.restart`

- **`service.<nested>.<field>`** - Nested service fields
  - Examples: `service.environment.VAR_NAME`, `service.labels.traefik.enable`

- **`compose.<field>`** - Goes to ComposeSchema (top-level)
  - Examples: `compose.networks`, `compose.volumes`

- **`metadata.<field>`** - Goes to MetadataSchema
  - Examples: `metadata.admin_user`, `metadata.admin_password`

---

## Transform System

Some fields need transformation before being written to compose file.

### Port Mapping Transform

**Blueprint Configuration**:
```json
{
  "host_port": {
    "type": "integer",
    "schema": "service.ports",
    "compose_transform": "port_mapping"
  },
  "container_port": {
    "type": "integer",
    "schema": "service.ports",
    "compose_transform": "port_mapping"
  }
}
```

**Transform Logic**: Combines `host_port` + `container_port` → `"8096:8096"`

---

### Volume Mapping Transform

**Blueprint Configuration**:
```json
{
  "config_path": {
    "type": "string",
    "schema": "service.volumes",
    "compose_transform": "volume_mapping",
    "volume_target": "/config"
  }
}
```

**Transform Logic**: Combines `config_path` + `volume_target` → `"./config:/config"`

---

## Data Flow

### 1. User Submits Form
```javascript
POST /api/apps/
{
  "name": "My Jellyfin",
  "blueprint_name": "jellyfin",
  "inputs": {
    "image": "jellyfin/jellyfin:latest",
    "container_name": "jellyfin",
    "host_port": 8096,
    "container_port": 8096,
    "config_path": "./config",
    "admin_user": "admin",
    "admin_password": "secret123"
  }
}
```

---

### 2. Backend Routes Data to Schemas

**Function**: `_route_inputs_to_schemas()` in `routes/apps.py`

```python
# Reads blueprint field schemas
# Routes each input to correct schema based on "schema" field
# Returns: (service_data, compose_data, metadata_data)
```

**Result in Database**:
```python
app.raw_inputs = {
  "image": "jellyfin/jellyfin:latest",
  "host_port": 8096,
  "admin_user": "admin",
  # ... all form fields
}

app.service_data = {
  "image": "jellyfin/jellyfin:latest",
  "container_name": "jellyfin"
  # ports will be added by transform
}

app.compose_data = {}

app.metadata_data = {
  "admin_user": "admin",
  "admin_password": "secret123"
}
```

---

### 3. Compose Generator Applies Transforms

**Function**: `generate_compose()` in `services/compose_generator.py`

```python
# 1. Loads app.service_data
# 2. Applies transforms (port_mapping, volume_mapping)
# 3. Adds global environment (PUID, PGID, TZ)
# 4. Validates with ServiceSchema
# 5. Combines with app.compose_data
# 6. Validates with ComposeSchema
```

**Result - Clean Compose File**:
```yaml
version: '3.9'

services:
  jellyfin_abc123:
    image: jellyfin/jellyfin:latest
    container_name: jellyfin
    restart: unless-stopped
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=UTC
    ports:
      - "8096:8096"
    volumes:
      - "./config:/config"
    networks:
      - mastarr_net

networks:
  mastarr_net:
    external: true
```

**Notice**: NO `admin_user`, NO `admin_password` in compose file!

---

### 4. Hooks Access Metadata

**Function**: `run()` in `hooks/jellyfin/post_install.py`

```python
async def run(context: HookContext):
    # Access metadata (NOT in compose file)
    admin_user = context.app.metadata_data.get('admin_user')
    admin_password = context.app.metadata_data.get('admin_password')

    # Get container info from service_data
    container_name = context.app.service_data.get('container_name')

    # Configure Jellyfin via API
    await create_admin_user(jellyfin_url, admin_user, admin_password)
```

---

## Example Blueprint - Jellyfin

**File**: `blueprints/jellyfin.json`

```json
{
  "name": "jellyfin",
  "display_name": "Jellyfin",
  "schema": {
    "image": {
      "type": "string",
      "ui_component": "text",
      "label": "Docker Image",
      "default": "jellyfin/jellyfin:latest",
      "schema": "service.image"
    },
    "container_name": {
      "type": "string",
      "ui_component": "text",
      "label": "Container Name",
      "default": "jellyfin",
      "schema": "service.container_name"
    },
    "host_port": {
      "type": "integer",
      "ui_component": "number",
      "label": "Host Port",
      "default": 8096,
      "schema": "service.ports",
      "compose_transform": "port_mapping"
    },
    "container_port": {
      "type": "integer",
      "ui_component": "number",
      "label": "Container Port",
      "default": 8096,
      "visible": false,
      "schema": "service.ports",
      "compose_transform": "port_mapping"
    },
    "config_path": {
      "type": "string",
      "ui_component": "text",
      "label": "Config Directory",
      "default": "./config",
      "schema": "service.volumes",
      "compose_transform": "volume_mapping",
      "volume_target": "/config"
    },
    "admin_user": {
      "type": "string",
      "ui_component": "text",
      "label": "Admin Username",
      "required": true,
      "schema": "metadata.admin_user"
    },
    "admin_password": {
      "type": "string",
      "ui_component": "password",
      "label": "Admin Password",
      "required": true,
      "is_sensitive": true,
      "schema": "metadata.admin_password"
    },
    "enable_transcoding": {
      "type": "boolean",
      "ui_component": "checkbox",
      "label": "Enable Hardware Transcoding",
      "default": false,
      "schema": "metadata.enable_transcoding"
    }
  },
  "post_install_hook": "jellyfin.post_install"
}
```

---

## Database Schema

### App Model

```python
class App(Base):
    __tablename__ = "apps"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    db_name = Column(String, unique=True, nullable=False)
    blueprint_name = Column(String, nullable=False)
    status = Column(String, default="configured")

    # Raw user inputs (kept for reference)
    raw_inputs = Column(JSON, default=dict)

    # Separated schema data
    service_data = Column(JSON, default=dict)    # ServiceSchema
    compose_data = Column(JSON, default=dict)    # ComposeSchema
    metadata_data = Column(JSON, default=dict)   # MetadataSchema

    compose_file_path = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    installed_at = Column(DateTime)
```

---

## Benefits

### ✅ Clean Compose Files
- Only Docker-relevant fields in compose
- No passwords or API keys exposed
- Easier to debug and maintain

### ✅ Flexible Hook System
- Hooks know exactly where to find data
- Metadata separate from Docker config
- Can store any app-specific settings

### ✅ Blueprint-Driven Architecture
- Each field explicitly declares its purpose
- No hardcoded logic in code
- Easy to add new apps without code changes

### ✅ Type Safety
- Pydantic validates all schemas
- Catch errors before writing files
- ServiceSchema and ComposeSchema ensure valid compose

### ✅ Transform System
- Clean separation between user input and compose format
- Reusable transforms (port_mapping, volume_mapping)
- Easy to add new transform types

---

## Adding New Fields to Blueprint

### Service Field (goes in compose)
```json
{
  "restart_policy": {
    "type": "string",
    "ui_component": "dropdown",
    "label": "Restart Policy",
    "default": "unless-stopped",
    "schema": "service.restart"
  }
}
```

### Metadata Field (NOT in compose)
```json
{
  "api_key": {
    "type": "string",
    "ui_component": "text",
    "label": "API Key",
    "is_sensitive": true,
    "schema": "metadata.api_key"
  }
}
```

### Field with Transform
```json
{
  "media_path": {
    "type": "string",
    "ui_component": "text",
    "label": "Media Directory",
    "schema": "service.volumes",
    "compose_transform": "volume_mapping",
    "volume_target": "/media"
  }
}
```

---

## Summary

This architecture provides:
1. **Clear separation** between Docker config and app metadata
2. **Blueprint-driven routing** via dot notation (`service.field`, `metadata.field`)
3. **Transform system** for complex compose syntax (ports, volumes)
4. **Type-safe validation** with Pydantic schemas
5. **Hook-friendly** metadata storage for post-install configuration

The result: Clean compose files, flexible app configuration, and maintainable code!
