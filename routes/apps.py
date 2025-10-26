from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from models.database import App, Blueprint, get_session
from models.schemas import AppCreate, AppResponse
from services.installer import AppInstaller
from utils.logger import get_logger

logger = get_logger("mastarr.routes.apps")
router = APIRouter(prefix="/api/apps", tags=["apps"])


def get_db():
    """Dependency for database session"""
    db = get_session()
    try:
        yield db
    finally:
        db.close()


@router.get("/", response_model=List[AppResponse])
async def list_apps(db: Session = Depends(get_db)):
    """List all apps"""
    apps = db.query(App).all()
    return apps


@router.get("/{app_id}", response_model=AppResponse)
async def get_app(app_id: int, db: Session = Depends(get_db)):
    """Get a specific app"""
    app = db.query(App).filter(App.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    return app


@router.post("/", response_model=AppResponse)
async def create_app(app_data: AppCreate, db: Session = Depends(get_db)):
    """Create a new app instance (without installing)"""
    db_name = app_data.name.lower().replace(" ", "_")

    existing = db.query(App).filter(App.db_name == db_name).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"App with name '{app_data.name}' already exists"
        )

    # Load blueprint to get field schemas
    blueprint = db.query(Blueprint).filter(
        Blueprint.name == app_data.blueprint_name
    ).first()
    if not blueprint:
        raise HTTPException(
            status_code=404,
            detail=f"Blueprint '{app_data.blueprint_name}' not found"
        )

    # Route inputs to correct schemas based on field definitions
    service_data, compose_data, metadata_data = _route_inputs_to_schemas(
        app_data.inputs,
        blueprint
    )

    app = App(
        name=app_data.name,
        db_name=db_name,
        blueprint_name=app_data.blueprint_name,
        raw_inputs=app_data.inputs,
        service_data=service_data,
        compose_data=compose_data,
        metadata_data=metadata_data,
        status="configured"
    )

    db.add(app)
    db.commit()
    db.refresh(app)

    logger.info(
        f"Created app: {app.name} "
        f"(service: {len(service_data)} fields, "
        f"compose: {len(compose_data)} fields, "
        f"metadata: {len(metadata_data)} fields)"
    )
    return app


@router.post("/{app_id}/install")
async def install_app(app_id: int, db: Session = Depends(get_db)):
    """Install a single app"""
    app = db.query(App).filter(App.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="App not found")

    if app.status == "running":
        raise HTTPException(status_code=400, detail="App is already running")

    installer = AppInstaller(db)

    try:
        await installer.install_single_app(app_id)
        return {"status": "success", "message": f"{app.name} installed successfully"}
    except Exception as e:
        logger.error(f"Installation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        installer.close()


@router.post("/batch-install")
async def batch_install_apps(
    app_ids: List[int],
    db: Session = Depends(get_db)
):
    """Install multiple apps in dependency order"""
    installer = AppInstaller(db)

    try:
        await installer.install_apps_batch(app_ids)
        return {"status": "success", "message": "All apps installed"}

    except ValueError as e:
        if "Missing required apps" in str(e):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "missing_prerequisites",
                    "message": str(e)
                }
            )
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"Batch install failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        installer.close()


@router.put("/{app_id}", response_model=AppResponse)
async def update_app(app_id: int, app_data: dict, db: Session = Depends(get_db)):
    """Update an app's configuration"""
    app = db.query(App).filter(App.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="App not found")

    # Update inputs if provided
    if "inputs" in app_data:
        # Load blueprint for schema routing
        blueprint = db.query(Blueprint).filter(
            Blueprint.name == app.blueprint_name
        ).first()

        if blueprint:
            # Re-route inputs to schemas
            service_data, compose_data, metadata_data = _route_inputs_to_schemas(
                app_data["inputs"],
                blueprint
            )

            app.raw_inputs = app_data["inputs"]
            app.service_data = service_data
            app.compose_data = compose_data
            app.metadata_data = metadata_data

    # Update status to configured if it was running (requires reinstall)
    if app.status == "running":
        app.status = "configured"

    db.commit()
    db.refresh(app)

    logger.info(f"Updated app: {app.name}")
    return app


@router.post("/{app_id}/stop")
async def stop_app(app_id: int, db: Session = Depends(get_db)):
    """Stop an app's containers"""
    app = db.query(App).filter(App.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="App not found")

    if app.status != "running":
        raise HTTPException(status_code=400, detail="App is not running")

    # TODO: Stop docker containers
    # For now, just update status
    app.status = "stopped"
    db.commit()

    logger.info(f"Stopped app: {app.name}")
    return {"status": "success", "message": f"{app.name} stopped"}


@router.delete("/{app_id}")
async def delete_app(app_id: int, db: Session = Depends(get_db)):
    """Delete an app (and stop its containers)"""
    app = db.query(App).filter(App.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="App not found")

    # TODO: Stop and remove docker containers

    db.delete(app)
    db.commit()

    logger.info(f"Deleted app: {app.name}")
    return {"status": "success", "message": f"{app.name} deleted"}


def _route_inputs_to_schemas(
    inputs: Dict[str, Any],
    blueprint: Blueprint
) -> tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """
    Route user inputs to correct schemas based on blueprint field definitions.

    Args:
        inputs: User's form inputs
        blueprint: Blueprint with field schemas

    Returns:
        Tuple of (service_data, compose_data, metadata_data)
    """
    service_data = {}
    compose_data = {}
    metadata_data = {}

    for field_name, field_value in inputs.items():
        field_schema = blueprint.schema_json.get(field_name)
        if not field_schema:
            # Field not in blueprint, skip
            continue

        # Skip fields with compose_transform - they'll be handled by transform phase
        if field_schema.get('compose_transform'):
            continue

        # Get schema routing from field (dot notation)
        schema_path = field_schema.get('schema')
        if not schema_path:
            # No schema defined, default to service
            schema_path = 'service'

        # Parse schema path: "service.image", "compose.networks", "metadata.admin_user"
        parts = schema_path.split('.', 1)
        schema_type = parts[0]

        if schema_type == 'service':
            if len(parts) > 1:
                # Nested path like "service.environment.VAR_NAME"
                _set_nested_value(service_data, parts[1], field_value)
            else:
                # Direct service field (shouldn't happen, but handle it)
                service_data[field_name] = field_value

        elif schema_type == 'compose':
            if len(parts) > 1:
                _set_nested_value(compose_data, parts[1], field_value)
            else:
                compose_data[field_name] = field_value

        elif schema_type == 'metadata':
            if len(parts) > 1:
                _set_nested_value(metadata_data, parts[1], field_value)
            else:
                metadata_data[field_name] = field_value

    return service_data, compose_data, metadata_data


def _set_nested_value(data: Dict[str, Any], path: str, value: Any):
    """
    Set a value at a nested path like 'environment.VAR_NAME' or just 'image'.

    Args:
        data: Dictionary to modify
        path: Dot-separated path (e.g., "environment.VAR_NAME" or "image")
        value: Value to set
    """
    if '.' in path:
        # Nested path
        keys = path.split('.')
        current = data

        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        current[keys[-1]] = value
    else:
        # Simple path
        data[path] = value
