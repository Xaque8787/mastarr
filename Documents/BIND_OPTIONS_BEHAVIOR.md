# Bind Options Behavior Documentation

This document explains how bind mount options are handled and how empty values are excluded from the generated Docker Compose files.

---

## Overview

Bind mount options (`propagation` and `create_host_path`) are now supported in volume definitions. The system automatically excludes empty, null, or unset values from the final compose file.

---

## Pydantic Schema Configuration

### BindOptionsSchema
```python
class BindOptionsSchema(BaseModel):
    """Bind mount specific options"""
    propagation: Optional[Literal["shared", "slave", "private", "rshared", "rslave", "rprivate"]] = None
    create_host_path: Optional[bool] = None

    class Config:
        # Exclude None values when serializing
        exclude_none = True
```

### ServiceBindVolumeSchema
```python
class ServiceBindVolumeSchema(BaseModel):
    type: Literal["bind"] = "bind"
    source: str
    target: str
    read_only: Optional[bool] = None
    bind: Optional[BindOptionsSchema] = None

    class Config:
        # Exclude None values when serializing
        exclude_none = True
```

---

## How Empty Values Are Handled

### 1. Pydantic `exclude_none=True`

When calling `model_dump(exclude_none=True)`, Pydantic automatically excludes any fields set to `None`.

**Example:**
```python
volume = ServiceBindVolumeSchema(
    source="${HOST_PATH}/config",
    target="/config",
    read_only=None,  # Will be excluded
    bind=None        # Will be excluded
)

result = volume.model_dump(exclude_none=True)
# Result: {"type": "bind", "source": "${HOST_PATH}/config", "target": "/config"}
```

### 2. Empty Dictionary Cleanup

The `_clean_empty_values()` method in `ComposeGenerator` and `AppInstaller` recursively removes:
- Empty strings: `""`
- Empty dictionaries: `{}`
- Empty lists: `[]`

**But keeps valid falsy values:**
- `False` (boolean)
- `0` (integer)

**Example:**
```python
data = {
    "volumes": [
        {
            "type": "bind",
            "source": "${HOST_PATH}/config",
            "target": "/config",
            "bind": {}  # Empty dict - will be removed
        }
    ]
}

cleaned = self._clean_empty_values(data)
# Result: {"volumes": [{"type": "bind", "source": "${HOST_PATH}/config", "target": "/config"}]}
```

---

## Scenarios and Results

### Scenario 1: User Sets All Options

**User Input:**
```json
{
  "config_volume": {
    "source": "./config",
    "target": "/config",
    "bind_propagation": "shared",
    "bind_create_host_path": true
  }
}
```

**Transform Applied:**
```python
volume_dict = {
    "type": "bind",
    "source": "${HOST_PATH}/config",
    "target": "/config",
    "bind": {
        "propagation": "shared",
        "create_host_path": true
    }
}
```

**Docker Compose Output:**
```yaml
volumes:
  - type: bind
    source: ${HOST_PATH}/config
    target: /config
    bind:
      propagation: shared
      create_host_path: true
```

---

### Scenario 2: User Leaves Options Empty

**User Input:**
```json
{
  "config_volume": {
    "source": "./config",
    "target": "/config",
    "bind_propagation": "",
    "bind_create_host_path": true
  }
}
```

**Transform Applied:**
```python
bind_options = {}

# bind_propagation is empty string - skipped
if user_value.get('bind_propagation'):  # Empty string is falsy
    # Not executed

# bind_create_host_path has value
if 'bind_create_host_path' in user_value and user_value['bind_create_host_path'] is not None:
    bind_options['create_host_path'] = True

volume_dict = {
    "type": "bind",
    "source": "${HOST_PATH}/config",
    "target": "/config",
    "bind": {"create_host_path": true}
}
```

**Docker Compose Output:**
```yaml
volumes:
  - type: bind
    source: ${HOST_PATH}/config
    target: /config
    bind:
      create_host_path: true
```

---

### Scenario 3: User Doesn't Set Any Bind Options

**User Input:**
```json
{
  "config_volume": {
    "source": "./config",
    "target": "/config"
  }
}
```

**Transform Applied:**
```python
bind_options = {}

# No bind_propagation provided
if user_value.get('bind_propagation'):  # Returns None/empty
    # Not executed

# No bind_create_host_path provided
if 'bind_create_host_path' in user_value:  # Key doesn't exist
    # Not executed

if bind_options:  # Empty dict is falsy
    volume_dict['bind'] = bind_options
# bind key not added
```

**After `_clean_empty_values()`:**
- Even if `bind: {}` was somehow added, it would be removed

**Docker Compose Output:**
```yaml
volumes:
  - type: bind
    source: ${HOST_PATH}/config
    target: /config
```

---

### Scenario 4: read_only = False

**User Input:**
```json
{
  "config_volume": {
    "source": "./config",
    "target": "/config",
    "read_only": false
  }
}
```

**Transform Applied:**
```python
# Only add read_only if explicitly True
if user_value.get('read_only'):  # False is falsy
    volume_dict['read_only'] = True
# read_only not added
```

**Docker Compose Output:**
```yaml
volumes:
  - type: bind
    source: ${HOST_PATH}/config
    target: /config
```

**Note:** Docker's default for `read_only` is `false`, so we only include it when it's `true`.

---

### Scenario 5: read_only = True

**User Input:**
```json
{
  "config_volume": {
    "source": "./config",
    "target": "/config",
    "read_only": true
  }
}
```

**Transform Applied:**
```python
if user_value.get('read_only'):  # True is truthy
    volume_dict['read_only'] = True
```

**Docker Compose Output:**
```yaml
volumes:
  - type: bind
    source: ${HOST_PATH}/config
    target: /config
    read_only: true
```

---

## Propagation Modes

Valid values for `bind.propagation`:

| Mode | Description |
|------|-------------|
| `shared` | Sub-mounts of the original mount are exposed to replica mounts, and sub-mounts of replica mounts are also propagated to the original mount |
| `slave` | Similar to shared mount, but only in one direction |
| `private` | The mount is private (default) |
| `rshared` | Recursive shared |
| `rslave` | Recursive slave |
| `rprivate` | Recursive private |

Reference: [Docker Compose Volumes Documentation](https://docs.docker.com/compose/compose-file/05-services/#volumes)

---

## Create Host Path

The `bind.create_host_path` option:

- **`true`** - Docker creates the directory on the host if it doesn't exist
- **`false`** - Docker does not create the directory; mount will fail if path doesn't exist
- **Default** - Docker's default behavior (typically creates the directory)

---

## Complete Flow

```
User Input (JSON)
    ↓
Blueprint Schema (defines fields)
    ↓
Transform Function (compose_generator.py)
    ↓
Build volume_dict with only non-empty values
    ↓
Pass to Pydantic Schema
    ↓
model_dump(exclude_none=True)
    ↓
_clean_empty_values() - removes empty dicts/lists/strings
    ↓
YAML Generation
    ↓
Docker Compose File
```

---

## Code References

### Transform Functions

**Location:** `services/compose_generator.py`

**volume_mapping transform:**
```python
# Handle bind-specific options
if volume_dict['type'] == 'bind':
    bind_options = {}
    if user_value.get('bind_propagation'):
        bind_options['propagation'] = user_value['bind_propagation']
    if 'bind_create_host_path' in user_value and user_value['bind_create_host_path'] is not None:
        bind_options['create_host_path'] = user_value['bind_create_host_path']

    if bind_options:
        volume_dict['bind'] = bind_options
```

**volume_array transform:**
- Same logic as above, applied to each item in the array

### Cleanup Function

**Location:** `services/compose_generator.py` and `services/installer.py`

```python
def _clean_empty_values(self, data):
    if isinstance(data, dict):
        cleaned = {}
        for key, value in data.items():
            cleaned_value = self._clean_empty_values(value)

            # Skip empty strings, empty dicts, empty lists
            if cleaned_value == '' or \
               (isinstance(cleaned_value, dict) and len(cleaned_value) == 0) or \
               (isinstance(cleaned_value, list) and len(cleaned_value) == 0):
                continue

            cleaned[key] = cleaned_value
        return cleaned
    elif isinstance(data, list):
        return [self._clean_empty_values(item) for item in data if item not in ('', None)]
    else:
        return data
```

---

## Testing

To verify the behavior:

1. **Create an app with bind options set:**
   - Verify `bind.propagation` and `bind.create_host_path` appear in compose file

2. **Create an app with bind options empty:**
   - Verify `bind` section is omitted from compose file

3. **Create an app with mixed options:**
   - Set only `bind_propagation` → only `bind.propagation` in compose
   - Set only `bind_create_host_path` → only `bind.create_host_path` in compose

4. **Check that valid falsy values are kept:**
   - `read_only: false` → omitted (Docker default)
   - `bind.create_host_path: false` → included (explicitly false)

---

## Summary

The system uses a multi-layered approach to exclude empty values:

1. **Pydantic Config** - `exclude_none=True` removes None values
2. **Transform Logic** - Only adds properties when they have meaningful values
3. **Cleanup Function** - Recursively removes empty strings, dicts, and lists
4. **Result** - Clean, minimal Docker Compose files with only necessary configuration

This ensures:
- ✅ No clutter in compose files
- ✅ Docker defaults are respected
- ✅ Valid falsy values (0, False) are preserved when meaningful
- ✅ Empty configurations don't break compose validation
