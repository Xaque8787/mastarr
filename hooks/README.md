# App Hooks System

## Overview

The **app hooks system** allows you to run custom automation scripts after an app's container starts. Each app gets its own directory with hook files, keeping everything organized and maintainable.

## Quick Start

### Creating a Hook

1. **Create directory**: `mkdir -p hooks/myapp`
2. **Create hook file**: `hooks/myapp/post_install.py`
3. **Write hook**:

```python
import httpx
import asyncio
from hooks.base import HookContext
from utils.logger import get_logger

logger = get_logger("mastarr.hooks.myapp")

async def run(context: HookContext):
    """Configure MyApp after installation."""
    logger.info("Configuring MyApp...")

    # Get user inputs
    admin_user = context.inputs.get('admin_user')
    port = context.inputs.get('port', 8080)

    # Build URL
    url = f"http://{context.container_ip}:{port}"

    # Wait for app ready
    await wait_for_ready(url)

    # Configure via API
    async with httpx.AsyncClient() as client:
        await client.post(f"{url}/api/setup", json={
            "username": admin_user
        })

    logger.info("✓ MyApp configured")

async def wait_for_ready(url: str):
    async with httpx.AsyncClient(timeout=10) as client:
        for i in range(30):
            try:
                r = await client.get(f"{url}/health")
                if r.status_code == 200:
                    return
            except:
                pass
            await asyncio.sleep(2)
```

That's it! The hook automatically runs when the app installs.

---

## Hook Context

Every hook receives a `HookContext` with:

```python
context.app_id           # Database ID
context.app_name         # Display name
context.blueprint_name   # Blueprint name
context.container_name   # Docker container name
context.container_ip     # IP on mastarr_net (e.g., "10.21.12.3")
context.inputs           # User's form inputs (dict)
context.db               # Database session
context.docker_client    # Docker API client
```

### Accessing User Inputs

```python
admin_user = context.inputs.get('admin_user')
admin_password = context.inputs.get('admin_password')
port = context.inputs.get('port', 8080)
```

### Accessing Other Apps

```python
from models.database import App

prowlarr = context.db.query(App).filter(
    App.blueprint_name == "prowlarr",
    App.status == "running"
).first()

if prowlarr:
    prowlarr_url = prowlarr.inputs['server_url']
    # Configure integration
```

---

## Hook Types

| Hook | When | Purpose |
|------|------|---------|
| `post_install.py` | After container starts | Configure app, create users |
| `pre_uninstall.py` | Before container stops | Backup data, cleanup |
| `health_check.py` | On-demand | Custom health checks |
| `configure.py` | Manual | Advanced configuration |

---

## Examples

### Example 1: Jellyfin - Create Admin User

See `hooks/jellyfin/post_install.py`:
- Wait for Jellyfin HTTP server
- Create admin user via API
- Complete setup wizard

### Example 2: Radarr - Auto-configure Prowlarr

See `hooks/radarr/post_install.py`:
- Wait for Radarr ready
- Check if Prowlarr installed
- Add Radarr to Prowlarr automatically
- Enable indexer syncing

---

## Best Practices

### 1. Always Wait for App Ready

```python
async def wait_for_app(url: str, max_attempts: int = 30):
    for attempt in range(max_attempts):
        try:
            response = await client.get(f"{url}/health")
            if response.status_code == 200:
                return True
        except:
            pass
        await asyncio.sleep(2)
    return False
```

### 2. Use Timeouts

```python
async with httpx.AsyncClient(timeout=30.0) as client:
    response = await client.post(url, json=data)
```

### 3. Handle Errors Gracefully

```python
try:
    await configure_app()
    logger.info("✓ Configuration successful")
except Exception as e:
    logger.error(f"Configuration failed: {e}")
    # Don't raise - app is still running
```

### 4. Log Everything

```python
logger.info("Starting configuration...")
logger.info(f"App URL: {app_url}")
logger.info("✓ Step 1 complete")
```

### 5. Store Important Data

```python
app = context.db.query(App).filter(App.id == context.app_id).first()
app.inputs['api_key'] = api_key
context.db.commit()
```

---

## Multiple Files Per App

```
hooks/myapp/
├── __init__.py
├── post_install.py       # Main hook
├── api_client.py         # Helper functions
├── health_check.py       # Health monitoring
└── utils.py              # Utilities
```

Then import helpers:

```python
from hooks.myapp.api_client import create_user

async def run(context):
    await create_user(context)
```

---

## Troubleshooting

**Hook not running?**
- Check file exists: `hooks/{blueprint_name}/post_install.py`
- Check has `run()` function
- Check logs for errors

**Container IP is None?**
- Use `localhost` with host port instead

**API not responding?**
- Increase wait time
- Check container logs: `docker logs {container_name}`
