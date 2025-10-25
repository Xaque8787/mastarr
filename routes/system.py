from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from models.database import GlobalSettings, get_session
from models.schemas import GlobalSettingsResponse
from utils.first_run import FirstRunInitializer
from utils.logger import get_logger

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
    puid: int = None,
    pgid: int = None,
    timezone: str = None,
    db: Session = Depends(get_db)
):
    """Update global settings"""
    settings = db.query(GlobalSettings).first()
    if not settings:
        settings = GlobalSettings()
        db.add(settings)

    if puid is not None:
        settings.puid = puid
    if pgid is not None:
        settings.pgid = pgid
    if timezone is not None:
        settings.timezone = timezone

    db.commit()
    db.refresh(settings)

    logger.info("Global settings updated")
    return settings
