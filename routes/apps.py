from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from models.database import App, get_session
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

    app = App(
        name=app_data.name,
        db_name=db_name,
        blueprint_name=app_data.blueprint_name,
        inputs=app_data.inputs,
        status="configured"
    )

    db.add(app)
    db.commit()
    db.refresh(app)

    logger.info(f"Created app: {app.name}")
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
        app.inputs = app_data["inputs"]

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
