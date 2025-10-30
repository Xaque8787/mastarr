# Compound Fields Implementation Summary

## What Changed

The UI and backend now support **compound fields** (nested objects) and **dynamic arrays**, eliminating the need for separate field transforms and enabling users to add custom configurations.

## Blueprint Schema Changes

### Before (Separate Fields with Transforms):
```json
{
  "host_port": {
    "type": "integer",
    "label": "Host Port",
    "schema": "service.ports",
    "compose_transform": "port_mapping"
  },
  "container_port": {
    "type": "integer",
    "label": "Container Port",
    "schema": "service.ports",
    "compose_transform": "port_mapping"
  }
}
```

### After (Compound Field):
```json
{
  "web_port": {
    "type": "object",
    "label": "Web Port",
    "description": "HTTP port for accessing Jellyfin",
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
  }
}
```

## New Array Fields for Advanced Settings

### Custom Environment Variables:
```json
{
  "custom_environment": {
    "type": "array",
    "ui_component": "key_value_pairs",
    "label": "Custom Environment Variables",
    "description": "Add custom environment variables",
    "default": [],
    "advanced": true,
    "schema": "service.environment.*"
  }
}
```

**Frontend sends:**
```javascript
{
  custom_environment: [
    { key: "MY_VAR", value: "some_value" },
    { key: "ANOTHER_VAR", value: "another_value" }
  ]
}
```

**Backend converts to:**
```yaml
environment:
  MY_VAR: some_value
  ANOTHER_VAR: another_value
```

### Additional Volumes:
```json
{
  "custom_volumes": {
    "type": "array",
    "label": "Additional Volumes",
    "default": [],
    "advanced": true,
    "item_schema": {
      "source": {
        "type": "string",
        "label": "Host Path"
      },
      "target": {
        "type": "string",
        "label": "Container Path"
      }
    },
    "schema": "service.volumes",
    "compose_transform": "volume_array"
  }
}
```

### Additional Ports:
```json
{
  "custom_ports": {
    "type": "array",
    "label": "Additional Ports",
    "default": [],
    "advanced": true,
    "item_schema": {
      "host": {
        "type": "integer",
        "label": "Host Port"
      },
      "container": {
        "type": "integer",
        "label": "Container Port"
      }
    },
    "schema": "service.ports",
    "compose_transform": "port_array"
  }
}
```

## UI Rendering

### Compound Fields (Object Type)
Renders multiple sub-fields in a grouped container:

```
┌─ Web Port ────────────────────────────────┐
│ HTTP port for accessing Jellyfin          │
│                                            │
│  Host Port        Container Port           │
│  [8096]          [8096]                    │
└────────────────────────────────────────────┘
```

### Array Fields (Dynamic Lists)
Renders with add/remove buttons:

```
┌─ Custom Environment Variables ────────────┐
│ Add custom environment variables           │
│                                            │
│  Key                Value                  │
│  [MY_VAR        ]  [some_value      ] [×]  │
│  [ANOTHER_VAR   ]  [another_val     ] [×]  │
│                                            │
│  [+ Add Custom Environment Variable]       │
└────────────────────────────────────────────┘
```

## Data Flow

### 1. Frontend Form Initialization
When modal opens, `selectBlueprint()` initializes nested structures:

```javascript
// For compound fields (object type)
if (field.type === 'object' && field.fields) {
  this.formData[fieldName] = {};
  Object.keys(field.fields).forEach(subFieldName => {
    this.formData[fieldName][subFieldName] = subField.default;
  });
}

// For array fields
if (field.type === 'array') {
  this.formData[fieldName] = field.default || [];
}
```

### 2. Frontend Sends Nested Data
```javascript
POST /api/apps/
{
  "name": "jellyfin",
  "blueprint_name": "jellyfin",
  "inputs": {
    "web_port": {
      "host": 8096,
      "container": 8096,
      "protocol": "tcp"
    },
    "custom_environment": [
      { "key": "MY_VAR", "value": "test" }
    ],
    "custom_volumes": [
      { "source": "/media", "target": "/media" }
    ]
  }
}
```

### 3. Backend Stores as JSON
```python
app.raw_inputs = {
  "web_port": {"host": 8096, "container": 8096, "protocol": "tcp"},
  "custom_environment": [{"key": "MY_VAR", "value": "test"}],
  "custom_volumes": [{"source": "/media", "target": "/media"}]
}
```

### 4. Backend Transforms During Compose Generation
```python
# _apply_transforms() in compose_generator.py

# Transform compound port field
if isinstance(user_value, dict) and 'host' in user_value:
    port_dict = {
        "published": user_value['host'],
        "target": user_value['container'],
        "protocol": user_value.get('protocol', 'tcp')
    }
    result['ports'].append(port_dict)

# Transform custom environment array
if schema_path == 'service.environment.*':
    for item in user_value:
        result['environment'][item['key']] = item['value']
```

### 5. Generated Docker Compose
```yaml
services:
  jellyfin:
    image: jellyfin/jellyfin:${TAG:-latest}
    ports:
      - published: 8096
        target: 8096
        protocol: tcp
    environment:
      PUID: 1000
      PGID: 1000
      MY_VAR: test
    volumes:
      - type: bind
        source: ./config
        target: /config
      - type: bind
        source: /media
        target: /media
```

## Benefits

### 1. No More Transforms Needed for Simple Cases
Compound fields group related inputs together without backend magic.

### 2. Users Can Customize Everything
Advanced users can add:
- Custom environment variables
- Additional volume mounts
- Extra port mappings
- Network configurations

### 3. Cleaner Blueprint Schema
Related fields are grouped logically instead of split across multiple entries.

### 4. Backend Already Supported This
The routing system and database were always capable of handling nested JSON. We just didn't have UI support.

### 5. Consistent Pattern
- `type: "object"` + `fields: {...}` = Compound field
- `type: "array"` + `item_schema: {...}` = Dynamic array
- `type: "array"` + `ui_component: "key_value_pairs"` = Key-value input

## Advanced Settings

All dynamic inputs are marked as `"advanced": true` so they appear when users click "Show Advanced Options":

- Custom Environment Variables
- Additional Volumes
- Additional Ports
- Standard env vars (PUID, PGID, TZ)
- Network configuration
- Restart policy

## Backwards Compatibility

The system maintains backwards compatibility:
- Old blueprints with separate `host_port`/`container_port` fields still work
- Transform logic checks for compound fields first, falls back to legacy mode
- No existing apps or blueprints need to be updated

## Testing

Run the test suite:
```bash
python3 test_compound_fields.py
```

All tests verify:
- ✓ Blueprint schema structure
- ✓ UI rendering code
- ✓ Backend transform logic
- ✓ Nested object initialization
- ✓ Array manipulation functions
