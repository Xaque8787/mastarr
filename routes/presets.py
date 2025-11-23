from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List

from models.database import get_session
from services.preset_service import PresetService
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api", tags=["presets"])


def get_db():
    """Dependency for database session"""
    db = get_session()
    try:
        yield db
    finally:
        db.close()


@router.get("/presets")
async def list_presets():
    """
    List all available presets
    """
    try:
        preset_service = PresetService()
        presets = preset_service.get_all_presets()
        return {"presets": presets}
    except Exception as e:
        logger.error(f"Failed to list presets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/presets/{preset_id}")
async def get_preset(preset_id: str):
    """
    Get details of a specific preset
    """
    try:
        preset_service = PresetService()
        preset = preset_service.get_preset(preset_id)

        if not preset:
            raise HTTPException(status_code=404, detail=f"Preset not found: {preset_id}")

        return preset
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get preset {preset_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/presets/{preset_id}/required-inputs")
async def get_required_inputs(preset_id: str, db: Session = Depends(get_db)):
    """
    Analyze a preset and return required inputs that need user input.
    Also returns information about missing blueprints and already-existing apps.
    """
    try:
        preset_service = PresetService()
        result = preset_service.analyze_required_inputs(preset_id, db)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to analyze preset {preset_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/presets/{preset_id}/apply")
async def apply_preset(
    preset_id: str,
    payload: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    Apply a preset by creating pending apps.

    Request body:
    {
        "inputs": {
            "jellyfin": {
                "username": "admin",
                "password": "secret123"
            },
            "prowlarr": {
                "api_key": "abc123"
            }
        }
    }

    Response:
    {
        "created_apps": [1, 2, 3],
        "skipped": ["app_name"],
        "errors": {"app_name": "error message"},
        "message": "Success message"
    }
    """
    try:
        user_inputs = payload.get('inputs', {})

        preset_service = PresetService()
        result = preset_service.apply_preset(preset_id, user_inputs, db)

        created_count = len(result['created_apps'])
        skipped_count = len(result['skipped'])

        message = f"Applied preset successfully. {created_count} app(s) created"
        if skipped_count > 0:
            message += f", {skipped_count} app(s) skipped"

        return {
            **result,
            "message": message
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to apply preset {preset_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
