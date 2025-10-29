# Mastarr Hooks System - Complete Overview

## What Are App Hooks?

**App hooks** let you run custom Python code after an app's container starts. This enables automatic configuration, user creation, and integration between apps.

---

## Directory Structure

```
hooks/
├── __init__.py
├── base.py                       # Hook infrastructure
├── README.md                     # Full documentation
├── jellyfin/
│   ├── __init__.py
│   └── post_install.py          # Jellyfin automation
├── prowlarr/
│   ├── __init__.py
│   └── post_install.py          # Prowlarr automation
├── radarr/
│   ├── __init__.py
│   └── post_install.py          # Radarr + Prowlarr integration
└── sonarr/
    ├── __init__.py
    └── post_install.py          # Sonarr + Prowlarr integration
```

**Each app gets its own directory!**

---

## How It Works

### Installation Flow

```
User Installs Jellyfin
         │
         ▼
AppInstaller generates docker-compose.yml
         │
         ▼
Container starts (docker-compose up)
         │
         ▼
Installer looks for hooks/jellyfin/post_install.py
         │
         ▼
Hook runs with context (IP, inputs, DB access)
         │
         ▼
Hook configures Jellyfin via API
         │
         ▼
Installation complete - Jellyfin fully configured!
```

---

## Example: Jellyfin Hook

**File**: `hooks/jellyfin/post_install.py`

```python
async def run(context: HookContext):
    """Runs AFTER Jellyfin container starts."""

    # Get user inputs from form
    admin_user = context.inputs['admin_user']
    admin_password = context.inputs['admin_password']

    # Build Jellyfin URL
    url = f"http://{context.container_ip}:8096"

    # Wait for Jellyfin API to be ready
    await wait_for_jellyfin(url)

    # Create admin user via API
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{url}/Startup/User",
            json={
                "Name": admin_user,
                "Password": admin_password
            }
        )

    # Complete setup wizard
    await client.post(f"{url}/Startup/Complete")
```

**Result**: User can immediately login to Jellyfin with their credentials!

---

## Example: Radarr + Prowlarr Integration

**File**: `hooks/radarr/post_install.py`

```python
async def run(context: HookContext):
    """Runs AFTER Radarr container starts."""

    # Wait for Radarr ready
    await wait_for_radarr(radarr_url)

    # Check if Prowlarr is installed
    prowlarr = context.db.query(App).filter(
        App.blueprint_name == "prowlarr"
    ).first()

    if prowlarr:
        # Get Prowlarr details
        prowlarr_url = prowlarr.inputs['server_url']
        prowlarr_key = prowlarr.inputs['api_key']

        # Add Radarr to Prowlarr automatically
        await client.post(
            f"{prowlarr_url}/api/v1/applications",
            json={
                "name": "Radarr",
                "baseUrl": radarr_url,
                "apiKey": radarr_api_key
            }
        )
```

**Result**: Radarr and Prowlarr automatically connected - indexers sync automatically!

---

## Hook Context

Every hook gets a `HookContext` object:

```python
context.app_id           # Database ID: 123
context.app_name         # Display name: "My Jellyfin"
context.blueprint_name   # Blueprint: "jellyfin"
context.container_name   # Container: "jellyfin"
context.container_ip     # IP: "10.21.12.3"
context.inputs           # {'admin_user': 'john', 'admin_password': 'secret'}
context.db               # Database session
context.docker_client    # Docker API client
```

---

## Adding a New App Hook

### 1. Create Directory
```bash
mkdir -p hooks/plex
```

### 2. Create Hook File
**File**: `hooks/plex/post_install.py`

```python
import httpx
import asyncio
from hooks.base import HookContext
from utils.logger import get_logger

logger = get_logger("mastarr.hooks.plex")

async def run(context: HookContext):
    """Configure Plex after installation."""
    logger.info("Configuring Plex...")

    # Your automation code here
    admin_user = context.inputs.get('admin_user')
    port = context.inputs.get('port', 32400)
    url = f"http://{context.container_ip}:{port}"

    # Wait for Plex ready
    await wait_for_plex(url)

    # Configure via API
    async with httpx.AsyncClient() as client:
        await client.post(f"{url}/api/setup", json={
            "username": admin_user
        })

    logger.info("✓ Plex configured")

async def wait_for_plex(url: str):
    async with httpx.AsyncClient(timeout=10) as client:
        for i in range(30):
            try:
                r = await client.get(f"{url}/status")
                if r.status_code == 200:
                    return
            except:
                pass
            await asyncio.sleep(2)
```

### 3. Done!
The hook automatically runs when Plex is installed. No registration needed!

---

## Multiple Files Per App

For complex apps, organize into multiple files:

```
hooks/plex/
├── __init__.py
├── post_install.py        # Main hook
├── api_client.py          # Plex API functions
├── library_manager.py     # Library setup
└── user_manager.py        # User management
```

Then import:

```python
# hooks/plex/post_install.py
from hooks.plex.api_client import get_auth_token
from hooks.plex.library_manager import create_library

async def run(context):
    token = await get_auth_token(context)
    await create_library(token, context)
```

---

## Two Hook Systems

Mastarr has **two separate hook systems**:

### 1. System Hooks (Infrastructure)
**File**: `services/system_hooks.py`

```python
create_mastarr_network()          # Create Docker network
connect_mastarr_to_network()      # Connect Mastarr container
```

**Purpose**: Set up Mastarr's infrastructure (networks, etc.)

### 2. App Hooks (Per-App) ← YOU'RE HERE
**Location**: `hooks/{app_name}/`

```python
hooks/jellyfin/post_install.py    # Configure Jellyfin
hooks/radarr/post_install.py      # Configure Radarr
```

**Purpose**: Configure individual apps after installation

---

## Benefits

### Before (Manual Setup)
1. Install Jellyfin
2. Open browser
3. Go through setup wizard
4. Create admin user
5. Configure settings

### After (With Hooks)
1. Install Jellyfin
2. **Done!** Hook already configured everything

---

## Best Practices

✅ **Always wait for app to be ready**
```python
await wait_for_ready(url, max_attempts=30)
```

✅ **Use timeouts**
```python
async with httpx.AsyncClient(timeout=30) as client:
```

✅ **Log everything**
```python
logger.info("Starting configuration...")
logger.info("✓ User created")
```

✅ **Handle errors gracefully**
```python
try:
    await configure()
except Exception as e:
    logger.error(f"Failed: {e}")
    # Don't raise - app still works
```

✅ **Store important data**
```python
app.inputs['api_key'] = api_key
context.db.commit()
```

---

## Real-World Use Cases

### 1. Jellyfin
- Create admin user automatically
- Skip setup wizard
- User logs in immediately

### 2. Prowlarr
- Extract API key from config
- Store for other apps to use

### 3. Radarr + Prowlarr
- Check if Prowlarr installed
- Add Radarr to Prowlarr
- Enable indexer syncing
- **Zero manual configuration!**

### 4. Sonarr + Prowlarr
- Same as Radarr but for TV shows
- Different category IDs
- Anime support

---

## Debugging

### View Logs
```bash
docker logs mastarr -f | grep hooks
```

### Check Hook Exists
```bash
ls hooks/jellyfin/post_install.py
```

### Common Issues

**Hook not running?**
- File missing or wrong name
- No `run()` function
- Import error (check logs)

**Container IP is None?**
- Container not on mastarr_net
- Use `localhost` + host port

**API not responding?**
- App still starting
- Increase wait time (max_attempts)

---

## Summary

**App hooks = Automatic configuration after installation**

- Each app gets its own directory
- Hooks auto-discovered (no registration)
- Full context (IP, inputs, database)
- Can integrate apps together
- Organized and maintainable

**Check `hooks/README.md` for full documentation!**
