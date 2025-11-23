# Presets System

Presets allow you to quickly configure multiple apps at once by bundling common application stacks together. Instead of configuring apps one by one, presets intelligently handle defaults and only ask for required fields without default values.

## Table of Contents
- [What are Presets?](#what-are-presets)
- [How Presets Work](#how-presets-work)
- [Using Presets](#using-presets)
- [Creating Presets](#creating-presets)
- [Preset File Format](#preset-file-format)
- [Advanced Topics](#advanced-topics)
- [Troubleshooting](#troubleshooting)

---

## What are Presets?

Presets are pre-configured collections of apps designed to work together. For example:

- **Media Stack**: Jellyfin + Prowlarr + Sonarr + Radarr (complete media server setup)
- **Download Stack**: Prowlarr only (indexer management for downloads)
- ***arr Suite**: Prowlarr + Sonarr + Radarr (automation suite without media player)

Instead of individually configuring each app, presets:
1. Use blueprint default values automatically
2. Only ask for required fields that have no defaults
3. Create apps in "configured" state ready for installation
4. Allow post-preset customization before installation

---

## How Presets Work

### The Philosophy

Presets follow the **two-stage refinement** approach:

1. **Quick Start**: Apply a preset using defaults, minimal input required
2. **Customize**: Edit any pending app to adjust configuration before installation

### Intelligent Input Detection

When you apply a preset, the system:

1. **Checks Prerequisites**: Identifies which apps are available to install
2. **Detects Conflicts**: Shows which apps are already installed or pending
3. **Analyzes Requirements**: Scans each app's blueprint to find required fields without defaults
4. **Groups by App**: Organizes required inputs by application for clarity
5. **Fills Defaults**: Automatically uses default values for all non-required fields

### Example Flow

```
User applies "Media Stack" preset
  ↓
System finds: Jellyfin needs username + password (no defaults)
              Prowlarr, Sonarr, Radarr have all defaults
  ↓
User fills in Jellyfin credentials only
  ↓
All 4 apps created with status="configured"
  ↓
User can edit any app, add volumes, change ports, etc.
  ↓
User clicks "Install Apps" when ready
```

---

## Using Presets

### Step-by-Step Guide

1. **Open Presets Modal**
   - Click the **"Presets"** button in the header (next to Settings)

2. **Select a Preset**
   - Click on any preset card to view details
   - Review apps included in the preset
   - Check for warnings (missing blueprints, already installed apps)

3. **Review Analysis**
   - **Green section**: Apps that will be added to pending
   - **Yellow section**: Apps already installed or pending (will be skipped)
   - **Red section**: Apps with missing blueprints (won't be added)
   - **Blue section**: Shows if any required inputs are needed

4. **Apply Preset**
   - Click **"Apply Preset"**
   - If no inputs required: Apps created immediately
   - If inputs required: Form appears organized by app

5. **Fill Required Fields (if needed)**
   - Only fields without defaults are shown
   - Grouped by application name
   - Other fields use blueprint defaults

6. **Review Pending Apps**
   - Apps appear in "Configured & Installed Apps" section
   - Status: "pending install"
   - Actions available:
     - **Edit**: Modify any configuration before installation
     - **Install**: Install this single app
     - **Remove**: Delete pending app

7. **Customize (Optional)**
   - Click **"Edit"** on any pending app
   - Modify ports, volumes, environment variables, etc.
   - Click **"Show Advanced Options"** for more fields
   - Save changes

8. **Install Apps**
   - Option 1: Click **"Install"** on individual apps
   - Option 2: Click **"Install All Pending Apps"** (batch install)

---

## Creating Presets

Presets are simple JSON files in the `presets/` directory.

### Basic Structure

```json
{
  "id": "preset_identifier",
  "name": "Display Name",
  "description": "Brief description of what this preset includes",
  "icon": "optional_icon_name",
  "apps": [
    "app1_blueprint_name",
    "app2_blueprint_name",
    "app3_blueprint_name"
  ]
}
```

### Field Descriptions

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Unique identifier (used in filename and API calls) |
| `name` | Yes | User-friendly display name |
| `description` | Yes | Brief explanation shown in UI |
| `icon` | No | Icon identifier for future use |
| `apps` | Yes | Array of blueprint names to include |

### Example: Download Stack

```json
{
  "id": "download_stack",
  "name": "Download Manager Stack",
  "description": "Prowlarr for indexer management - perfect starting point for download automation",
  "icon": "download",
  "apps": [
    "prowlarr"
  ]
}
```

### Example: Media Stack

```json
{
  "id": "media_stack",
  "name": "Complete Media Stack",
  "description": "Full *arr suite with Jellyfin for comprehensive media management and streaming",
  "icon": "film",
  "apps": [
    "jellyfin",
    "prowlarr",
    "sonarr",
    "radarr"
  ]
}
```

---

## Preset File Format

### Naming Convention

- **Filename**: `{preset_id}.json` (must match the `id` field)
- **Location**: `presets/` directory at project root
- **Format**: Valid JSON with UTF-8 encoding

### App Order

Apps in the `apps` array don't need to be in any specific order. The system:
- Uses each app's `install_order` from its blueprint for actual installation
- Checks prerequisites automatically
- Skips already-installed apps
- Shows all conflicts to the user before applying

### Validation

The system validates:
- ✅ JSON syntax is correct
- ✅ Required fields are present
- ✅ Blueprint names exist in database
- ❌ Does NOT validate app compatibility (user decides)

---

## Advanced Topics

### Handling Required Fields

When creating presets, understand how required fields work:

```json
// In a blueprint
{
  "admin_user": {
    "type": "string",
    "label": "Admin Username",
    "required": true,
    "default": null  // ← No default, so user MUST provide
  },
  "web_port": {
    "type": "object",
    "label": "Web Port",
    "required": false,
    "fields": {
      "host": {
        "default": 8096  // ← Has default, preset auto-fills
      }
    }
  }
}
```

**Result**: Preset only asks for `admin_user`, auto-fills `web_port` with 8096.

### Global Settings Integration

Presets respect global settings via the `use_global` field:

```json
{
  "puid_env": {
    "type": "integer",
    "label": "PUID",
    "default": null,
    "use_global": "PUID"  // ← Uses global PUID setting
  }
}
```

When a preset creates apps, fields with `use_global` automatically pull values from Settings.

### Preset Best Practices

1. **Keep Presets Focused**
   - Group apps that naturally work together
   - Don't create "everything" presets
   - Consider user skill level

2. **Test Prerequisites**
   - Ensure blueprint names are correct
   - Verify blueprints exist in your instance
   - Test with fresh database

3. **Write Clear Descriptions**
   - Explain what the preset includes
   - Mention use cases
   - Highlight any assumptions

4. **Consider Dependencies**
   - If apps depend on each other, mention in description
   - Example: "Sonarr and Radarr work best with Prowlarr configured first"
   - Presets don't enforce order, they just group apps

---

## Adding Presets

### Method 1: Manual Creation

1. Create a JSON file in `presets/` directory:
   ```bash
   nano presets/my_stack.json
   ```

2. Add your preset configuration:
   ```json
   {
     "id": "my_stack",
     "name": "My Custom Stack",
     "description": "My personalized app stack",
     "apps": ["app1", "app2", "app3"]
   }
   ```

3. Save the file

4. Restart Mastarr (or just reload the Presets modal)

5. Your preset appears in the list!

### Method 2: Copy and Modify

1. Copy an existing preset:
   ```bash
   cp presets/media_stack.json presets/my_stack.json
   ```

2. Edit the new file:
   ```bash
   nano presets/my_stack.json
   ```

3. Change `id`, `name`, `description`, and `apps` array

4. Save and reload

---

## Removing Presets

### Simple Removal

1. Delete the preset file:
   ```bash
   rm presets/unwanted_preset.json
   ```

2. Reload the Presets modal

**Note**: Removing a preset does NOT affect apps already created from it.

### Disabling Temporarily

Rename the file with a different extension:
```bash
mv presets/preset_name.json presets/preset_name.json.disabled
```

To re-enable:
```bash
mv presets/preset_name.json.disabled presets/preset_name.json
```

---

## Troubleshooting

### Preset Not Appearing

**Problem**: Created a preset but it doesn't show in UI.

**Solutions**:
1. Check filename matches `id` field: `my_stack.json` needs `"id": "my_stack"`
2. Verify JSON syntax: Use `python3 -m json.tool presets/my_stack.json`
3. Check file permissions: `chmod 644 presets/my_stack.json`
4. Reload the page or restart Mastarr

### "Blueprint Not Found" Warning

**Problem**: Preset shows missing blueprint warning.

**Solutions**:
1. Check spelling in `apps` array matches exact blueprint name
2. Verify blueprint exists: Check `blueprints/` directory
3. Ensure blueprint was loaded into database
4. Check Mastarr logs for blueprint loading errors

### Some Apps Skipped

**Problem**: Preset skips some apps during application.

**Reasons** (not errors, by design):
- App already installed: Use Edit to modify instead
- App already pending: Apply creates one app per blueprint
- Blueprint missing: Fix blueprint or remove from preset

**To Apply Anyway**: Remove existing app first, then re-apply preset.

### Required Fields Not Showing

**Problem**: Expected to fill in fields but preset applies instantly.

**Explanation**: This is correct behavior! It means all fields have defaults. The preset uses blueprint defaults automatically.

**To Customize**: Click "Edit" on the pending app after preset is applied.

### Apps Created but Wrong Configuration

**Problem**: Apps have incorrect ports, paths, etc.

**Solution**: Presets use blueprint defaults. You have two options:
1. **Before applying**: Modify blueprint defaults (affects all future installs)
2. **After applying**: Click "Edit" on pending app to customize per-app

---

## Examples

### Example 1: Minimal Preset

```json
{
  "id": "simple_test",
  "name": "Simple Test",
  "description": "Single app for testing",
  "apps": ["prowlarr"]
}
```

### Example 2: Complex Stack

```json
{
  "id": "complete_automation",
  "name": "Complete Automation Stack",
  "description": "Everything you need for automated media management: indexer, downloaders, organizers, and player",
  "icon": "layers",
  "apps": [
    "prowlarr",
    "sonarr",
    "radarr",
    "jellyfin"
  ]
}
```

### Example 3: Specialized Use Case

```json
{
  "id": "tv_only_stack",
  "name": "TV Shows Only",
  "description": "Focused on TV series automation with Prowlarr and Sonarr",
  "icon": "tv",
  "apps": [
    "prowlarr",
    "sonarr"
  ]
}
```

---

## API Reference

For developers integrating with the presets system:

### Endpoints

- `GET /api/presets` - List all presets
- `GET /api/presets/{preset_id}` - Get preset details
- `GET /api/presets/{preset_id}/required-inputs` - Analyze preset requirements
- `POST /api/presets/{preset_id}/apply` - Apply preset with inputs

### Response: Required Inputs Analysis

```json
{
  "available_apps": ["jellyfin", "prowlarr"],
  "missing_blueprints": ["nonexistent_app"],
  "already_exists": ["sonarr"],
  "required_inputs": {
    "jellyfin": [
      {
        "field": "admin_user",
        "label": "Admin Username",
        "type": "string",
        "ui_component": "text",
        "required": true
      }
    ]
  }
}
```

### Apply Preset Request

```json
{
  "inputs": {
    "jellyfin": {
      "admin_user": "admin",
      "admin_password": "secret123"
    }
  }
}
```

### Apply Preset Response

```json
{
  "created_apps": [1, 2, 3],
  "skipped": ["sonarr"],
  "errors": {"app_name": "error message"},
  "message": "Applied preset successfully. 3 app(s) created, 1 app(s) skipped"
}
```

---

## FAQ

**Q: Can I apply the same preset multiple times?**
A: No. Apps already installed or pending are skipped automatically. To re-apply, remove the existing apps first.

**Q: Do presets handle app dependencies?**
A: No. Presets simply group apps together. You're responsible for configuring them to work together after installation.

**Q: Can I modify a preset after applying it?**
A: Yes! Click "Edit" on any pending app to customize before installation.

**Q: What happens if I delete a preset file?**
A: The preset disappears from the UI, but existing apps created from it are unaffected.

**Q: Can presets configure app settings (like Prowlarr indexers)?**
A: No. Presets only handle initial Docker container configuration. In-app configuration must be done through each app's web interface.

**Q: Do I need to restart Mastarr after adding a preset?**
A: No. Just reload the Presets modal. The system loads presets on-demand.

**Q: Can I include the same app in multiple presets?**
A: Yes! Users choose which preset to apply. Only one instance of each app can be installed.

---

## Conclusion

Presets are a powerful way to streamline app deployment in Mastarr. By understanding how they work and following best practices, you can create efficient workflows for common application stacks.

**Key Takeaways**:
- Presets use blueprint defaults automatically
- Only required fields without defaults need user input
- Apps are created in "configured" state for further customization
- Presets are simple JSON files anyone can create
- The system handles conflicts and missing blueprints gracefully

For more information, see:
- [Blueprint Documentation](APP_TEMPLATE.md)
- [Global Settings System](GLOBAL_SETTINGS_SYSTEM.md)
- [Hook System](../hooks/README.md)
