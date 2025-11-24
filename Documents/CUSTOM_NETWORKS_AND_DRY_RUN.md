# Custom Networks and Dry-Run Mode

This document describes the custom networks feature and dry-run mode implementation.

## Overview

### Custom Networks Feature
Allows apps to attach to additional Docker networks beyond the primary network configured in the `network_config` field. Useful for:
- VPN networks
- Monitoring networks
- Service mesh networks
- Isolated communication networks

### Dry-Run Mode
Allows testing compose file generation without running `docker compose up`. Compose files are still written to disk but containers aren't started. Perfect for:
- Development and debugging
- Validating blueprint changes
- Inspecting generated compose files without side effects

## Transform Registry Architecture

All compose transforms have been refactored into a modular registry pattern:

**File: `utils/compose_transforms.py`**
- Contains all transform functions (port_mapping, volume_mapping, network_config, etc.)
- Each transform is a pure function with clear inputs/outputs
- `TRANSFORM_REGISTRY` maps transform names to functions
- `apply_transform()` provides unified interface

**Benefits:**
- Easy to add new transforms (just add function + registry entry)
- Each transform is testable in isolation
- Cleaner compose_generator.py (20 lines instead of 180)
- Clear separation of concerns

### Available Transforms

| Transform Name | Purpose | Input | Output |
|----------------|---------|-------|--------|
| `port_mapping` | Single port mapping | `{host: 8096, container: 8096, protocol: "tcp"}` | Service-level ports array |
| `port_array` | Multiple port mappings | Array of port objects | Service-level ports array |
| `volume_mapping` | Single volume mapping | `{source: "./config", target: "/config"}` | Service-level volumes array |
| `volume_array` | Multiple volume mappings | Array of volume objects | Service-level volumes array |
| `network_config` | Primary network config | `{network_name: "net", ipv4_address: "10.0.0.1"}` | Service-level networks dict |
| `custom_networks_array` | Additional networks | Array of network objects | Service + compose networks |

## Custom Networks Implementation

### Blueprint Configuration

Add to any blueprint's schema:

```json
{
  "custom_networks": {
    "type": "array",
    "ui_component": "compound_array",
    "label": "Custom Networks",
    "description": "Attach to additional Docker networks",
    "required": false,
    "visible": true,
    "advanced": true,
    "properties": {
      "network_name": {
        "type": "string",
        "label": "Network Name",
        "placeholder": "vpn_network"
      },
      "mode": {
        "type": "select",
        "label": "Mode",
        "default": "existing",
        "options": [
          {"value": "existing", "label": "Use Existing Network"},
          {"value": "create", "label": "Create If Missing"}
        ]
      }
    },
    "compose_transform": "custom_networks_array"
  }
}
```

### User Input Format

```json
{
  "custom_networks": [
    {"network_name": "vpn_net", "mode": "create"},
    {"network_name": "monitoring", "mode": "existing"}
  ]
}
```

### Transform Behavior

**The `custom_networks_array` transform:**

1. **Validates Input**: Skips empty network names
2. **Creates Networks** (if mode="create"):
   - Checks if network exists via `docker network inspect`
   - Creates network via `docker network create` if missing
   - Logs success/failure
3. **Adds to Service Networks**: Attaches service to each network (no IP config)
4. **Stores in Cache**: Saves network info for compose-level processing
5. **Compose-Level Networks**: Generator adds networks to compose file with `external: true`

### Generated Compose File

**Input:**
```json
{
  "custom_networks": [
    {"network_name": "vpn_net", "mode": "create"},
    {"network_name": "monitoring", "mode": "existing"}
  ]
}
```

**Output:**
```yaml
services:
  jellyfin:
    image: jellyfin/jellyfin
    networks:
      vpn_net: {}
      monitoring: {}
      mastarr_net:
        ipv4_address: 10.21.12.3

networks:
  mastarr_net:
    external: true
  vpn_net:
    external: true
  monitoring:
    external: true
```

### How It Doesn't Break Existing Functionality

**Existing `network_config` field:**
- Still works exactly as before
- Uses `network_config` transform
- Adds primary network with optional static IP
- Stored in `compose.networks` via schema routing

**New `custom_networks` field:**
- Uses `custom_networks_array` transform
- Adds additional networks via transform cache
- Does NOT use schema routing (handled by transform)
- Service-level: Merged into existing `networks` dict
- Compose-level: Added via transform cache after service processing

**They coexist peacefully:**
```python
# Service-level networks dict merges both sources:
result['networks'] = {
    'mastarr_net': {'ipv4_address': '10.21.12.3'},  # from network_config
    'vpn_net': {},                                   # from custom_networks
    'monitoring': {}                                 # from custom_networks
}

# Compose-level networks from both sources:
compose_config['networks'] = {
    'mastarr_net': {'external': True},    # from schema routing
    'vpn_net': {'external': True},        # from transform cache
    'monitoring': {'external': True}      # from transform cache
}
```

## Dry-Run Mode

### Usage

**Set environment variable in `.env` file:**
```bash
DRY_RUN=true
```

Or set it at runtime:
```bash
export DRY_RUN=true
docker-compose up
```

### Behavior

**When DRY_RUN=true:**
- Compose files are generated and written to disk normally
- All blueprints and validations run as usual
- Container startup is SKIPPED (no `docker compose up`)
- Logs show: `🔍 DRY RUN MODE: Skipping container startup for {app_name}`

**When DRY_RUN=false (default):**
- Full installation: compose files written AND containers started
- Normal production behavior

### Benefits

1. **Inspect Generated Files**: Check compose YAML before containers start
2. **Validate Blueprints**: Test blueprint changes without side effects
3. **Development Testing**: Verify transform logic without Docker overhead
4. **Safe Experimentation**: Test custom networks without affecting running services

### Environment Variable

The `DRY_RUN` variable is passed to the application container via docker-compose.yml:

```yaml
services:
  mastarr:
    environment:
      - DRY_RUN=${DRY_RUN:-false}
```

### Testing Locally

**Set dry-run in .env:**
```bash
# .env file
DRY_RUN=true
```

**Start application:**
```bash
docker-compose up
```

**Try installing an app via UI:**
- Compose file will be created at `/var/lib/mastarr/stacks/{app_name}/docker-compose.yml`
- Check logs for: `🔍 DRY RUN MODE: Skipping container startup`
- Inspect generated compose file to verify custom networks

## Adding New Transforms

### Step 1: Write Transform Function

**File: `utils/compose_transforms.py`**

```python
def transform_my_custom_transform(
    user_value: Any,
    field_schema: Dict[str, Any],
    app: Any,
    result: Dict[str, Any],
    transform_cache: Dict[str, Any]
) -> None:
    """
    Transform description.

    Input: ...
    Output: ...
    """
    # Your transform logic here
    # Modify result dict in place
    # Use transform_cache for shared data
    pass
```

### Step 2: Register Transform

**Add to TRANSFORM_REGISTRY:**
```python
TRANSFORM_REGISTRY = {
    'port_mapping': transform_port_mapping,
    'volume_mapping': transform_volume_mapping,
    'my_custom_transform': transform_my_custom_transform,  # Add here
}
```

### Step 3: Use in Blueprint

```json
{
  "my_field": {
    "type": "object",
    "compose_transform": "my_custom_transform"
  }
}
```

**That's it!** No need to modify `compose_generator.py`.

## Best Practices

### Custom Networks

1. **Use descriptive names**: `vpn_network`, `monitoring_net`, not `net1`, `net2`
2. **Prefer existing mode**: Only use `create` mode if you control the network lifecycle
3. **Document purpose**: Use blueprint description field to explain why network is needed
4. **Test with dry-run**: Verify compose output before installing apps

### Transform Functions

1. **Keep transforms pure**: No side effects except Docker API calls
2. **Validate input**: Check types and skip empty values
3. **Use transform_cache**: Share data between transforms (e.g., custom networks)
4. **Log actions**: Use logger for debugging
5. **Handle errors gracefully**: Don't crash on invalid input

### Dry-Run Mode

1. **Always test locally**: Set DRY_RUN=true before deploying changes
2. **Check compose output**: Inspect generated files in `/var/lib/mastarr/stacks/`
3. **Validate networks**: Ensure external networks are marked correctly in compose files
4. **Test empty cases**: Verify behavior when optional fields are omitted

## Troubleshooting

### Custom Network Not Appearing

**Check:**
1. Is `compose_transform: "custom_networks_array"` set in blueprint?
2. Is field visible and not empty in raw_inputs?
3. Check logs for Docker API errors
4. Verify network name is not empty string

### Network Creation Fails

**Possible causes:**
1. Docker daemon not running
2. Permission issues
3. Network name already exists with different settings
4. Invalid network name (Docker naming rules)

**Solution:**
- Check Docker logs
- Use `docker network inspect <name>` to check status
- Use `mode: "existing"` if network exists

### Dry-Run Not Working

**Check:**
1. Is `DRY_RUN=true` set in `.env` file or environment?
2. Check logs for `🔍 DRY RUN MODE: Skipping container startup` message
3. Verify docker-compose.yml passes DRY_RUN variable to container
4. Check logger level (should see INFO messages)

### Transform Not Running

**Check:**
1. Is transform registered in TRANSFORM_REGISTRY?
2. Is `compose_transform` field set correctly in blueprint?
3. Is user_value None or empty?
4. Check logs for "Unknown transform type" warning

## Migration Notes

### Upgrading from Previous Versions

**No breaking changes!** All existing functionality preserved:

- ✅ Existing blueprints work without changes
- ✅ Existing apps continue working
- ✅ network_config field still works
- ✅ All transforms behave identically

**Optional upgrades:**
1. Add custom_networks field to blueprints where needed
2. Use dry-run mode for testing
3. Create custom transforms for special cases

### Rollback

If issues occur:
1. Remove `custom_networks` field from blueprints
2. Apps without custom_networks work normally
3. No database migration needed
