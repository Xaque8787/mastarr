from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from models.database import App, Blueprint, GlobalSettings, get_session
from models.schemas import AppCreate, AppResponse
from services.installer import AppInstaller
from utils.logger import get_logger
from utils.template_expander import TemplateExpander
from utils.path_resolver import PathResolver
from hooks.base import HookContext, get_hook_executor
import subprocess
import shutil
from pathlib import Path

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

    # Load global settings for template expansion
    global_settings = db.query(GlobalSettings).first()
    if not global_settings:
        global_settings = GlobalSettings()
        db.add(global_settings)
        db.commit()

    # Expand template variables in blueprint schema
    expander = TemplateExpander(global_settings, db_name)
    expanded_schema = expander.expand_blueprint_schema(blueprint.schema_json)

    # Apply defaults where user didn't provide values
    complete_inputs = expander.apply_defaults_to_inputs(app_data.inputs, expanded_schema)

    # Route inputs to correct schemas based on field definitions
    service_data, compose_data, metadata_data = _route_inputs_to_schemas(
        complete_inputs,
        blueprint,
        expanded_schema
    )

    app = App(
        name=app_data.name,
        db_name=db_name,
        blueprint_name=app_data.blueprint_name,
        raw_inputs=complete_inputs,
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


@router.put("/{app_id}")
async def update_app(app_id: int, app_data: dict, db: Session = Depends(get_db)):
    """Update an app's configuration and restart if running"""
    app = db.query(App).filter(App.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="App not found")

    was_running = app.status == "running"

    # Update inputs if provided
    if "inputs" in app_data:
        # Load blueprint for schema routing
        blueprint = db.query(Blueprint).filter(
            Blueprint.name == app.blueprint_name
        ).first()

        if blueprint:
            # Load global settings for template expansion
            global_settings = db.query(GlobalSettings).first()
            if not global_settings:
                global_settings = GlobalSettings()
                db.add(global_settings)
                db.commit()

            # Expand template variables in blueprint schema
            expander = TemplateExpander(global_settings, app.db_name)
            expanded_schema = expander.expand_blueprint_schema(blueprint.schema_json)

            # Apply defaults where user didn't provide values
            complete_inputs = expander.apply_defaults_to_inputs(app_data["inputs"], expanded_schema)

            # Re-route inputs to schemas
            service_data, compose_data, metadata_data = _route_inputs_to_schemas(
                complete_inputs,
                blueprint,
                expanded_schema
            )

            app.raw_inputs = complete_inputs
            app.service_data = service_data
            app.compose_data = compose_data
            app.metadata_data = metadata_data

    db.commit()

    # Store app info before potential session changes
    app_id_stored = app.id
    app_name_stored = app.name
    blueprint_name = app.blueprint_name
    container_name = app.service_data.get('container_name', app.name)

    db.refresh(app)

    # If app was running, run update hooks and restart
    if was_running:
        # Run pre-update hook
        hook_context = HookContext(
            app_id=app_id_stored,
            app_name=app_name_stored,
            blueprint_name=blueprint_name,
            container_name=container_name,
            app=app
        )
        hook_executor = get_hook_executor()
        await hook_executor.execute_hook(blueprint_name, "pre_update", hook_context)

        path_resolver = PathResolver()
        stack_path = path_resolver.get_stack_path(app.db_name)
        compose_path = stack_path / "docker-compose.yml"

        # Stop the existing containers
        if compose_path.exists():
            try:
                result = subprocess.run(
                    [
                        "docker", "compose",
                        "--project-directory", str(stack_path),
                        "-f", str(compose_path),
                        "down"
                    ],
                    check=True,
                    capture_output=True,
                    text=True
                )
                logger.info(f"Stopped {app_name_stored} for update")
            except subprocess.CalledProcessError as e:
                logger.warning(f"Failed to stop containers before update: {e.stderr}")

        # Reinstall with new configuration (using is_initial_install=False to avoid install hooks)
        installer = AppInstaller(db)
        try:
            await installer.install_single_app(app_id_stored, is_initial_install=False)
            logger.info(f"Updated and restarted app: {app_name_stored}")
        except Exception as e:
            logger.error(f"Failed to restart app after update: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Configuration updated but restart failed: {str(e)}"
            )
        finally:
            installer.close()

        # Run post-update hook (refresh context in case app was modified)
        hook_context = HookContext(
            app_id=app_id_stored,
            app_name=app_name_stored,
            blueprint_name=blueprint_name,
            container_name=container_name
        )
        await hook_executor.execute_hook(blueprint_name, "post_update", hook_context)
    else:
        logger.info(f"Updated app: {app_name_stored} (not running, no restart needed)")

    # Re-fetch the app from database to get latest state
    app = db.query(App).filter(App.id == app_id_stored).first()

    # Return a simple success response instead of the full AppResponse
    return {
        "status": "success",
        "message": f"{app.name} updated {'and restarted' if was_running else 'successfully'}",
        "app": {
            "id": app.id,
            "name": app.name,
            "status": app.status
        }
    }


@router.post("/{app_id}/stop")
async def stop_app(app_id: int, db: Session = Depends(get_db)):
    """Stop an app's containers"""
    app = db.query(App).filter(App.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="App not found")

    if app.status != "running":
        raise HTTPException(status_code=400, detail="App is not running")

    # Run pre-stop hook
    hook_context = HookContext(
        app_id=app.id,
        app_name=app.name,
        blueprint_name=app.blueprint_name,
        container_name=app.service_data.get('container_name', app.name),
        app=app
    )
    hook_executor = get_hook_executor()
    await hook_executor.execute_hook(app.blueprint_name, "pre_stop", hook_context)

    try:
        # Get stack path and compose file
        path_resolver = PathResolver()
        stack_path = path_resolver.get_stack_path(app.db_name)
        compose_path = stack_path / "docker-compose.yml"

        if not compose_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Compose file not found at {compose_path}"
            )

        # Run docker compose down
        result = subprocess.run(
            [
                "docker", "compose",
                "--project-directory", str(stack_path),
                "-f", str(compose_path),
                "down"
            ],
            check=True,
            capture_output=True,
            text=True
        )

        logger.info(f"Stopped containers for {app.name}")
        if result.stdout:
            logger.debug(f"Docker output: {result.stdout}")

        app.status = "stopped"
        db.commit()

        # Run post-stop hook
        await hook_executor.execute_hook(app.blueprint_name, "post_stop", hook_context)

        return {"status": "success", "message": f"{app.name} stopped"}

    except subprocess.CalledProcessError as e:
        logger.error(f"Docker compose down failed: {e.stderr}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop containers: {e.stderr}"
        )
    except Exception as e:
        logger.error(f"Stop failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{app_id}")
async def delete_app(app_id: int, db: Session = Depends(get_db)):
    """Delete an app (stop containers, remove files, and delete from database)"""
    app = db.query(App).filter(App.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="App not found")

    # Run pre-remove hook
    hook_context = HookContext(
        app_id=app.id,
        app_name=app.name,
        blueprint_name=app.blueprint_name,
        container_name=app.service_data.get('container_name', app.name),
        app=app
    )
    hook_executor = get_hook_executor()
    await hook_executor.execute_hook(app.blueprint_name, "pre_remove", hook_context)

    path_resolver = PathResolver()
    stack_path = path_resolver.get_stack_path(app.db_name)
    compose_path = stack_path / "docker-compose.yml"

    # Stop containers if running
    if app.status == "running" and compose_path.exists():
        try:
            result = subprocess.run(
                [
                    "docker", "compose",
                    "--project-directory", str(stack_path),
                    "-f", str(compose_path),
                    "down"
                ],
                check=True,
                capture_output=True,
                text=True
            )
            logger.info(f"Stopped containers for {app.name} before removal")
            if result.stdout:
                logger.debug(f"Docker output: {result.stdout}")
        except subprocess.CalledProcessError as e:
            logger.warning(f"Failed to stop containers (continuing with removal): {e.stderr}")
        except Exception as e:
            logger.warning(f"Error stopping containers (continuing with removal): {e}")

    # Remove stack directory
    if stack_path.exists():
        try:
            shutil.rmtree(stack_path)
            logger.info(f"Removed stack directory: {stack_path}")
        except Exception as e:
            logger.error(f"Failed to remove stack directory: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to remove stack directory: {str(e)}"
            )

    # Delete from database
    db.delete(app)
    db.commit()

    # Run post-remove hook
    await hook_executor.execute_hook(app.blueprint_name, "post_remove", hook_context)

    logger.info(f"Deleted app: {app.name}")
    return {"status": "success", "message": f"{app.name} deleted"}


def _route_inputs_to_schemas(
    inputs: Dict[str, Any],
    blueprint: Blueprint,
    expanded_schema: Dict[str, Any]
) -> tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """
    Route user inputs to correct schemas based on blueprint field definitions.
    Handles compound fields (type: "object") and routes them to the correct location.

    Args:
        inputs: User's form inputs (with defaults applied)
        blueprint: Blueprint with field schemas
        expanded_schema: Expanded blueprint schema (with template variables resolved)

    Returns:
        Tuple of (service_data, compose_data, metadata_data)
    """
    service_data = {}
    compose_data = {}
    metadata_data = {}

    for field_name, field_value in inputs.items():
        field_schema = expanded_schema.get(field_name)
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

        # Skip wildcard schemas (e.g., "service.environment.*") - handled by compose_generator
        if schema_path.endswith('.*'):
            continue

        # Parse schema path: "service.image", "compose.networks", "metadata.admin_user", "env.TAG"
        parts = schema_path.split('.', 1)
        schema_type = parts[0]

        # Skip env.* fields - they go to .env file only, not compose or metadata
        if schema_type == 'env':
            continue

        # Handle compound fields (type: "object")
        # These are already structured objects, so we append them to arrays
        field_type = field_schema.get('type')
        if field_type == 'object' and isinstance(field_value, dict):
            # Compound field like port_mapping or volume_mapping
            # Route to the target as an array element
            if schema_type == 'service':
                if len(parts) > 1:
                    target_path = parts[1]
                    # Append to array (e.g., service.ports, service.volumes)
                    _append_to_array(service_data, target_path, field_value)
                else:
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

        else:
            # Regular field routing
            if schema_type == 'service':
                if len(parts) > 1:
                    target_path = parts[1]

                    # Special handling for networks - must be a list
                    if target_path == 'networks' and isinstance(field_value, str):
                        # Convert string network name to list
                        field_value = [field_value]

                    # Nested path like "service.environment.VAR_NAME"
                    _set_nested_value(service_data, target_path, field_value)
                else:
                    # Direct service field (shouldn't happen, but handle it)
                    service_data[field_name] = field_value

            elif schema_type == 'compose':
                if len(parts) > 1:
                    # Special handling for JSON strings that need parsing
                    if isinstance(field_value, str) and field_value.startswith('{'):
                        try:
                            import json
                            field_value = json.loads(field_value)
                        except:
                            pass  # Keep as string if parsing fails

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


def _append_to_array(data: Dict[str, Any], path: str, value: Any):
    """
    Append a value to an array at a nested path.
    Creates the array if it doesn't exist.

    Args:
        data: Dictionary to modify
        path: Dot-separated path (e.g., "ports" or "nested.array")
        value: Value to append to the array
    """
    if '.' in path:
        # Nested path
        keys = path.split('.')
        current = data

        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        # Ensure the target is an array
        final_key = keys[-1]
        if final_key not in current:
            current[final_key] = []
        elif not isinstance(current[final_key], list):
            current[final_key] = [current[final_key]]

        current[final_key].append(value)
    else:
        # Simple path
        if path not in data:
            data[path] = []
        elif not isinstance(data[path], list):
            data[path] = [data[path]]

        data[path].append(value)
