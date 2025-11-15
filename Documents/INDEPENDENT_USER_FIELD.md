# Independent User Field Implementation

## Overview

The User field is now completely independent from PUID and PGID. This allows you to:
- Set different PUID/PGID values for file permissions
- Set a different USER value for the Docker container process
- Use named users like "root", "nobody", or custom usernames
- Leave User blank to auto-compute as PUID:PGID (backward compatible)

## Database Changes

### New Column: `global_settings.user`
- **Type**: VARCHAR
- **Default**: NULL
- **Nullable**: Yes
- **Purpose**: Store optional user override independent of PUID/PGID

### Migration Required

If you have an existing database, you need to add this column:

```sql
ALTER TABLE global_settings ADD COLUMN user VARCHAR;
```

Or recreate the database (will lose existing data).

## Modified Files

### 1. `models/database.py`
Added user column to GlobalSettings model:
```python
user = Column(String, default=None, nullable=True)
```

### 2. `models/schemas.py`
Added user field to GlobalSettingsResponse:
```python
user: Optional[str] = None
```

### 3. `routes/system.py`
Updated PUT /api/system/settings endpoint to accept user field:
```python
if 'user' in settings_update:
    settings.user = settings_update['user'] if settings_update['user'] else None
```

### 4. `services/compose_generator.py`
Updated global value injection logic:
```python
# Use explicit user field if set, otherwise fallback to PUID:PGID
user_value = global_settings.user if global_settings.user else f"{global_settings.puid}:{global_settings.pgid}"
```

### 5. `templates/index.html`
Replaced computed display with editable input field showing:
- Dynamic placeholder: "{PUID}:{PGID} (default fallback)"
- Visual indicator showing current behavior
- Real-time updates as PUID/PGID change

## Usage Examples

### Example 1: Default Behavior (Auto-Compute)
```yaml
Global Settings:
  PUID: 1001
  PGID: 1002
  USER: (blank)

Result in compose.yaml:
  user: "1001:1002"  # Auto-computed
```

### Example 2: Override with Different User
```yaml
Global Settings:
  PUID: 1001        # For file permissions
  PGID: 1002        # For file permissions
  USER: 1500:1500   # For container process

Result in compose.yaml:
  environment:
    - PUID=1001     # Environment variable
    - PGID=1002     # Environment variable
  user: "1500:1500" # Service-level user
```

### Example 3: Root User
```yaml
Global Settings:
  PUID: 1001
  PGID: 1002
  USER: root

Result in compose.yaml:
  environment:
    - PUID=1001
    - PGID=1002
  user: "root"
```

### Example 4: Named User
```yaml
Global Settings:
  PUID: 1001
  PGID: 1002
  USER: appuser:appgroup

Result in compose.yaml:
  user: "appuser:appgroup"
```

## UI Behavior

### When User Field is Blank
```
┌─────────────────────────────────────┐
│ Docker User                         │
│ [                             ]     │
│ Placeholder: 1001:1002 (default...) │
│                                     │
│ ℹ️ Will use computed value:         │
│    1001:1002                        │
└─────────────────────────────────────┘
```

### When User Field Has Value
```
┌─────────────────────────────────────┐
│ Docker User                         │
│ [root                         ]     │
│                                     │
│ ℹ️ Using explicit value:            │
│    root                             │
└─────────────────────────────────────┘
```

## Key Design Decisions

### 1. Independence from PUID/PGID
The User field is stored separately and doesn't automatically update when PUID/PGID change. This is intentional to allow different values for different purposes.

### 2. Fallback Behavior
When User is blank (NULL), the system automatically computes PUID:PGID. This ensures backward compatibility and provides sensible defaults.

### 3. String Type
User is stored as a string (not numeric) to support:
- Numeric UIDs: "1000:1000"
- Named users: "root"
- Named users with groups: "appuser:appgroup"
- Any other Docker-compatible user format

### 4. Visual Feedback
The UI provides clear visual feedback about what value will be used, helping users understand the system's behavior.

## Affected Apps Detection

Apps are considered "affected" by global settings if they use any of:
- PUID (environment variable or service-level)
- PGID (environment variable or service-level)
- TZ (timezone)
- USER (service-level user field)

When you change global settings and restart affected apps, all these values are regenerated from the current global settings.

## Benefits

✅ **Flexibility**: Use different values for file permissions vs process user
✅ **Named Users**: Support root, nobody, or custom usernames
✅ **Backward Compatible**: Leave blank to use PUID:PGID automatically
✅ **Clear Intent**: Explicit field makes the purpose obvious
✅ **Independence**: PUID/PGID and User can be managed separately

## Testing

See TESTING_GUIDE.md for comprehensive test cases covering all scenarios.
