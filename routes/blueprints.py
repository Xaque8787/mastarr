from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from models.database import Blueprint, App, get_session
from models.schemas import BlueprintResponse
from utils.logger import get_logger

logger = get_logger("mastarr.routes.blueprints")
router = APIRouter(prefix="/api/blueprints", tags=["blueprints"])


def get_db():
    """Dependency for database session"""
    db = get_session()
    try:
        yield db
    finally:
        db.close()


@router.get("/", response_model=List[BlueprintResponse])
async def list_blueprints(
    category: str = None,
    visible_only: bool = True,
    db: Session = Depends(get_db)
):
    """List all available blueprints"""
    query = db.query(Blueprint)

    if visible_only:
        query = query.filter(Blueprint.visible == True)

    if category:
        query = query.filter(Blueprint.category == category)

    blueprints = query.order_by(Blueprint.install_order).all()
    return blueprints


@router.get("/{blueprint_name}", response_model=BlueprintResponse)
async def get_blueprint(blueprint_name: str, db: Session = Depends(get_db)):
    """Get a specific blueprint"""
    blueprint = db.query(Blueprint).filter(Blueprint.name == blueprint_name).first()
    if not blueprint:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    return blueprint


@router.get("/{blueprint_name}/schema")
async def get_blueprint_schema(blueprint_name: str, db: Session = Depends(get_db)):
    """
    Get blueprint schema with prerequisites evaluated.
    Returns only fields that should be visible based on installed apps.
    """
    blueprint = db.query(Blueprint).filter(Blueprint.name == blueprint_name).first()
    if not blueprint:
        raise HTTPException(status_code=404, detail="Blueprint not found")

    installed_apps = db.query(App).filter(App.status == "running").all()

    visible_schema = {}

    for field_name, field in blueprint.schema_json.items():
        if 'prerequisites' in field and field['prerequisites']:
            if not all(
                check_prerequisite(prereq, installed_apps)
                for prereq in field['prerequisites']
            ):
                continue

        visible_schema[field_name] = field

    return {
        "name": blueprint.name,
        "display_name": blueprint.display_name,
        "schema": visible_schema
    }


def check_prerequisite(prereq: dict, installed_apps: List[App]) -> bool:
    """Check if a prerequisite is satisfied"""
    app = next(
        (a for a in installed_apps if a.blueprint_name == prereq['app_name']),
        None
    )

    if not app:
        return False

    if app.status != prereq.get('status', 'running'):
        return False

    if 'input_name' in prereq and 'input_value' in prereq:
        if app.inputs.get(prereq['input_name']) != prereq['input_value']:
            return False

    return True


@router.get("/categories/list")
async def list_categories(db: Session = Depends(get_db)):
    """Get list of all blueprint categories"""
    categories = db.query(Blueprint.category).distinct().all()
    return [cat[0] for cat in categories]
