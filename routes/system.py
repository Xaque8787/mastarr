from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from models.database import GlobalSettings, App, Blueprint, get_session
from models.schemas import GlobalSettingsResponse
from utils.first_run import FirstRunInitializer
from utils.logger import get_logger
from services.compose_generator import ComposeGenerator
import docker

logger = get_logger("mastarr.routes.system")
router = APIRouter(prefix="/api/system", tags=["system"])


def get_db():
    """Dependency for database session"""
    db = get_session()
    try:
        yield db
    finally:
        db.close()


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@router.get("/info")
async def system_info():
    """Get system information"""
    initializer = FirstRunInitializer()
    info = initializer.get_system_info()
    return info


@router.get("/settings", response_model=GlobalSettingsResponse)
async def get_settings(db: Session = Depends(get_db)):
    """Get global settings"""
    settings = db.query(GlobalSettings).first()
    if not settings:
        settings = GlobalSettings()
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


@router.put("/settings")
async def update_settings(
    settings_update: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Update global settings"""
    settings = db.query(GlobalSettings).first()
    if not settings:
        settings = GlobalSettings()
        db.add(settings)

    # Update fields if provided
    if 'puid' in settings_update and settings_update['puid'] is not None:
        settings.puid = settings_update['puid']
    if 'pgid' in settings_update and settings_update['pgid'] is not None:
        settings.pgid = settings_update['pgid']
    if 'user' in settings_update:
        # Allow setting user to None (to clear it)
        settings.user = settings_update['user'] if settings_update['user'] else None
    if 'timezone' in settings_update and settings_update['timezone'] is not None:
        settings.timezone = settings_update['timezone']

    db.commit()
    db.refresh(settings)

    logger.info(f"Global settings updated: PUID={settings.puid}, PGID={settings.pgid}, USER={settings.user}, TZ={settings.timezone}")
    return settings


@router.get("/settings/affected-apps")
async def get_affected_apps(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Get list of apps that use global settings (PUID, PGID, TZ, USER).
    These apps will be affected if global settings are changed.
    """
    apps = db.query(App).filter(App.status == "running").all()
    affected = []

    for app in apps:
        blueprint = db.query(Blueprint).filter(Blueprint.name == app.blueprint_name).first()
        if not blueprint:
            continue

        uses_globals = []
        service_data = app.service_data or {}
        env = service_data.get("environment", {})

        for field_name, field_schema in blueprint.schema_json.items():
            use_global = field_schema.get("use_global")
            if not use_global:
                continue

            schema_path = field_schema.get("schema", "")
            parts = schema_path.split(".")

            if len(parts) == 2 and parts[0] == "service":
                field_key = parts[1]
                # Check if field is missing OR is None
                if field_key not in service_data or service_data[field_key] is None:
                    uses_globals.append(use_global)

            elif len(parts) == 3 and parts[0] == "service" and parts[1] == "environment":
                env_key = parts[2]
                # Check if env var is missing OR is None
                if env_key not in env or env[env_key] is None:
                    uses_globals.append(use_global)

        if uses_globals:
            affected.append({
                "id": app.id,
                "name": app.name,
                "blueprint_name": app.blueprint_name,
                "uses_globals": list(set(uses_globals))
            })

    return {
        "count": len(affected),
        "apps": affected
    }


@router.post("/settings/regenerate-affected")
async def regenerate_affected_apps(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Regenerate compose files and restart apps that use global settings.
    This applies the new global settings to affected apps.
    """
    affected_response = await get_affected_apps(db)
    affected_apps = affected_response["apps"]

    if not affected_apps:
        return {
            "success": True,
            "message": "No apps are affected by global settings",
            "regenerated": []
        }

    docker_client = docker.from_env()
    generator = ComposeGenerator()
    regenerated = []
    errors = []

    for app_info in affected_apps:
        try:
            app = db.query(App).filter(App.id == app_info["id"]).first()
            if not app:
                continue

            blueprint = db.query(Blueprint).filter(Blueprint.name == app.blueprint_name).first()
            if not blueprint:
                continue

            logger.info(f"Regenerating compose for {app.name} with new global settings")

            compose = generator.generate(app, blueprint)
            compose_path = app.compose_file_path

            if compose_path:
                generator.write_compose_file(compose, compose_path)

                try:
                    container_name = app.service_data.get("container_name", app.db_name)
                    container = docker_client.containers.get(container_name)
                    container.restart()
                    logger.info(f"Restarted container: {container_name}")

                    regenerated.append({
                        "name": app.name,
                        "status": "restarted"
                    })
                except docker.errors.NotFound:
                    logger.warning(f"Container {container_name} not found, skipping restart")
                    regenerated.append({
                        "name": app.name,
                        "status": "compose_updated_no_restart"
                    })
                except Exception as e:
                    logger.error(f"Failed to restart {app.name}: {str(e)}")
                    errors.append({
                        "name": app.name,
                        "error": str(e)
                    })

        except Exception as e:
            logger.error(f"Failed to regenerate {app_info['name']}: {str(e)}")
            errors.append({
                "name": app_info["name"],
                "error": str(e)
            })

    generator.close()

    return {
        "success": len(errors) == 0,
        "regenerated": regenerated,
        "errors": errors if errors else None
    }
