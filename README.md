# Mastarr - Media Server Application Manager

Mastarr is a Python-based application manager for Docker containers, specifically designed for managing media server applications like Jellyfin, Radarr, Sonarr, Prowlarr, and more.

## Features

- **Database-Driven**: Uses Supabase PostgreSQL for storing app configurations and blueprints
- **Dynamic Compose Generation**: Generates Docker Compose files on-the-fly from validated Pydantic models
- **Dependency Management**: Automatically resolves installation order based on app dependencies
- **System Hooks**: First-run and lifecycle hooks for network setup and system initialization
- **Python-First**: All orchestration logic in Python (no bash scripts)
- **Type-Safe**: Full Pydantic validation for all inputs
- **Web UI**: Alpine.js frontend for easy app management

## Architecture

```
mastarr/
├── models/           # SQLAlchemy + Pydantic models
├── services/         # Business logic (installer, compose generator, hooks)
├── routes/           # FastAPI routes
├── utils/            # Utilities (logging, path resolver, first run)
├── blueprints/       # App blueprint JSON files
├── templates/        # Jinja2 HTML templates
├── static/           # Static assets
└── main.py           # FastAPI application
```

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Supabase project with database access

### Setup

1. **Update Environment Variables**

Edit `.env` file with your Supabase credentials:

```env
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_SUPABASE_ANON_KEY=your-anon-key
```

2. **Build and Start**

```bash
docker-compose up -d --build
```

3. **Load Blueprints**

```bash
docker exec -it mastarr python load_blueprints.py
```

4. **Access the UI**

Open your browser to: `http://localhost:8000`

## How It Works

### 1. Blueprints

Blueprints define app configurations in JSON format.

### 2. Installation Flow

1. User selects an app and fills configuration form
2. FastAPI validates inputs using Pydantic
3. Compose generator creates docker-compose.yml
4. Installer writes compose file to `/stacks/{app_name}/`
5. Docker Compose brings up containers
6. Post-install hooks run (if defined)

### 3. Dependency Resolution

Apps can declare prerequisites and the installer uses topological sort to determine correct installation order.

### 4. System Hooks

Mastarr uses lifecycle hooks for system operations:
- **first_run_only**: Create Docker network (10.21.12.0/26)
- **every_run**: Connect mastarr container to network
- **teardown**: Disconnect from network on shutdown

## API Endpoints

### Apps
- `GET /api/apps/` - List all apps
- `POST /api/apps/` - Create new app instance
- `POST /api/apps/{id}/install` - Install an app
- `DELETE /api/apps/{id}` - Remove an app

### Blueprints
- `GET /api/blueprints/` - List all blueprints
- `GET /api/blueprints/{name}` - Get specific blueprint

### System
- `GET /api/system/health` - Health check
- `GET /api/system/info` - System information

## License

MIT