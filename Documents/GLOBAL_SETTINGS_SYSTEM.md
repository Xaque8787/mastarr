# Global Settings System

This document describes the implementation of the Global Settings system that allows apps to dynamically use global PUID, PGID, TZ, and USER values.

## Overview

The system allows blueprints to define fields that can optionally use global settings. If a user leaves these fields blank during app configuration, the system will automatically inject the global values when generating the Docker Compose file.

## Key Features

1. **Dynamic Detection**: No explicit flags stored - the system checks if a value exists in `service_data` to determine if it should use the global value
2. **Blueprint Hints**: Blueprints use `use_global` metadata to indicate which fields support global values
3. **Compose-time Injection**: Global values are injected during compose generation, not at configuration time
4. **Settings UI**: Users can update global settings and restart affected apps with new values

## Implementation Details

### 1. Schema Addition

**File**: `models/schemas.py`

Added `use_global` field to `FieldSchema`:

```python
use_global: Optional[str] = None  # "PUID", "PGID", "TZ", "USER"
```

### 2. Transform Function

**File**: `utils/compose_transforms.py`

Added `transform_user_format()` to format user values as `PUID:PGID`.

### 3. Compose Generator Enhancement

**File**: `services/compose_generator.py`

Added `_inject_global_values()` method that:
- Scans blueprint schema for fields with `use_global` set
- Checks if values are missing from `service_data`
- Injects appropriate global values from `GlobalSettings`

Supports both service-level fields (`service.user`) and environment variables (`service.environment.PUID`).

### 4. API Endpoints

**File**: `routes/system.py`

Added three new endpoints:

- `GET /api/system/settings/affected-apps`: Returns list of apps using global settings
- `POST /api/system/settings/regenerate-affected`: Regenerates compose files and restarts affected apps
- `PUT /api/system/settings`: Updated to accept JSON body (already existed)

### 5. Blueprint Updates

**File**: `blueprints/jellyfin.json`

Updated PUID, PGID, and TZ fields:

```json
{
  "puid_env": {
    "type": "integer",
    "label": "PUID",
    "default": null,
    "placeholder": "Leave blank to use global setting",
    "schema": "service.environment.PUID",
    "use_global": "PUID"
  }
}
```

### 6. Frontend UI

**File**: `templates/index.html`

Added:
- Settings button in System Information section
- Global Settings modal with:
  - PUID, PGID, Timezone input fields
  - List of affected apps
  - "Apply Settings" button
  - "Restart Apps with New Settings" button (enabled after applying)

## User Flow

### Configuring an App

1. User opens Jellyfin configuration
2. Sees PUID field with placeholder: "Leave blank to use global setting"
3. Leaves field blank (or enters custom value)
4. Saves configuration

**Result**: If blank, value is NOT stored in `service_data`. If custom value entered, it IS stored.

### When Global Settings Change

1. User clicks "Settings" button
2. Sees current global settings and list of affected apps
3. Modifies PUID/PGID/TZ values
4. Clicks "Apply Settings" (saves to database)
5. Clicks "Restart Apps with New Settings"
6. System regenerates compose files with new global values
7. Containers are restarted

## Technical Details

### Global Value Injection Logic

```python
# In compose_generator.py
def _inject_global_values(service_config, blueprint, global_settings):
    for field_name, field_schema in blueprint.schema_json.items():
        use_global = field_schema.get('use_global')
        if not use_global:
            continue
        
        schema_path = field_schema.get('schema')
        # Parse: "service.environment.PUID"
        
        # Check if value exists in service_config
        if value_not_in_service_config:
            # Inject global value
            service_config[...] = global_settings.puid
```

### Detection Algorithm

```python
def uses_global_puid(app, blueprint):
    """Check if app uses global PUID"""
    env = app.service_data.get("environment", {})
    
    # Check if blueprint has a field with use_global="PUID"
    has_puid_field = any(
        f.get("use_global") == "PUID" 
        for f in blueprint.schema_json.values()
    )
    
    # If field exists in blueprint but NOT in service_data, uses global
    return has_puid_field and "PUID" not in env
```

### Supported Global Fields

| Global Key | Maps To | Description |
|------------|---------|-------------|
| `PUID` | `global_settings.puid` | User ID for file permissions |
| `PGID` | `global_settings.pgid` | Group ID for file permissions |
| `TZ` | `global_settings.timezone` | Container timezone |
| `USER` | `f"{puid}:{pgid}"` | Docker user field format |

## Example Scenarios

### Scenario 1: App Uses All Globals

**Blueprint**: Has PUID, PGID, TZ with `use_global` hints
**User Input**: Leaves all blank
**service_data**: `{"environment": {}}`
**Compose Result**: PUID=1001, PGID=1001, TZ=America/New_York (from globals)

### Scenario 2: App Overrides PGID

**Blueprint**: Has PUID, PGID, TZ with `use_global` hints
**User Input**: PUID blank, PGID=1002, TZ blank
**service_data**: `{"environment": {"PGID": 1002}}`
**Compose Result**: PUID=1001 (global), PGID=1002 (override), TZ=America/New_York (global)

### Scenario 3: Blueprint Without Global Support

**Blueprint**: Has PUID field without `use_global` hint
**User Input**: PUID=1000
**service_data**: `{"environment": {"PUID": 1000}}`
**Compose Result**: PUID=1000 (never uses global because no hint)

## Benefits

1. **No Database Changes**: Uses existing `service_data` column
2. **Backward Compatible**: Apps without `use_global` hints work as before
3. **User Control**: Users can override globals per-app if needed
4. **Centralized Management**: Change globals once, apply to all apps
5. **Self-Documenting**: Blueprint clearly shows which fields support globals

## Future Enhancements

1. Add `use_global` support to more blueprints (Sonarr, Radarr, etc.)
2. Add more global settings (UMASK, default network, etc.)
3. Show global value preview in form field placeholder
4. Batch update: apply new globals to selected apps only
