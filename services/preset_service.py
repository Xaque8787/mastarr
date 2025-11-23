import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session

from models.database import Blueprint, App
from models.schemas import FieldSchema
from utils.logger import get_logger

logger = get_logger(__name__)


class PresetService:
    def __init__(self, presets_dir: str = "presets"):
        self.presets_dir = Path(presets_dir)

    def get_all_presets(self) -> List[Dict[str, Any]]:
        """Load all preset definitions from the presets directory"""
        presets = []

        if not self.presets_dir.exists():
            logger.warning(f"Presets directory not found: {self.presets_dir}")
            return presets

        for preset_file in self.presets_dir.glob("*.json"):
            try:
                with open(preset_file, 'r') as f:
                    preset_data = json.load(f)
                    presets.append(preset_data)
            except Exception as e:
                logger.error(f"Failed to load preset {preset_file}: {e}")
                continue

        return sorted(presets, key=lambda x: x.get('name', ''))

    def get_preset(self, preset_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific preset by ID"""
        preset_file = self.presets_dir / f"{preset_id}.json"

        if not preset_file.exists():
            return None

        try:
            with open(preset_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load preset {preset_id}: {e}")
            return None

    def analyze_required_inputs(
        self,
        preset_id: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        Analyze blueprints in a preset and return required inputs that have no defaults.

        Returns:
        {
            "available_apps": ["jellyfin", "prowlarr"],
            "missing_blueprints": ["nonexistent_app"],
            "already_exists": ["sonarr"],
            "required_inputs": {
                "jellyfin": [
                    {
                        "field": "username",
                        "label": "Username",
                        "type": "string",
                        "ui_component": "text",
                        "description": "...",
                        "required": true
                    }
                ]
            }
        }
        """
        preset = self.get_preset(preset_id)
        if not preset:
            raise ValueError(f"Preset not found: {preset_id}")

        app_names = preset.get('apps', [])

        available_apps = []
        missing_blueprints = []
        already_exists = []
        required_inputs = {}

        for app_name in app_names:
            blueprint = db.query(Blueprint).filter(Blueprint.name == app_name).first()

            if not blueprint:
                missing_blueprints.append(app_name)
                continue

            existing_app = db.query(App).filter(
                App.blueprint_name == app_name
            ).first()

            if existing_app:
                already_exists.append(app_name)
                continue

            available_apps.append(app_name)

            schema_dict = blueprint.schema_json
            required_fields = self._extract_required_inputs(schema_dict)

            if required_fields:
                required_inputs[app_name] = required_fields

        return {
            "available_apps": available_apps,
            "missing_blueprints": missing_blueprints,
            "already_exists": already_exists,
            "required_inputs": required_inputs
        }

    def _extract_required_inputs(self, schema_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract fields that are required but have no default value"""
        required_fields = []

        for field_name, field_data in schema_dict.items():
            if not isinstance(field_data, dict):
                continue

            is_required = field_data.get('required', False)
            has_default = 'default' in field_data and field_data['default'] is not None

            if is_required and not has_default:
                required_fields.append({
                    'field': field_name,
                    'label': field_data.get('label', field_name),
                    'type': field_data.get('type', 'string'),
                    'ui_component': field_data.get('ui_component', 'text'),
                    'description': field_data.get('description'),
                    'placeholder': field_data.get('placeholder'),
                    'is_sensitive': field_data.get('is_sensitive', False),
                    'required': True
                })

        return required_fields

    def apply_preset(
        self,
        preset_id: str,
        user_inputs: Dict[str, Dict[str, Any]],
        db: Session
    ) -> Dict[str, Any]:
        """
        Apply a preset by creating pending apps.

        Args:
            preset_id: ID of the preset to apply
            user_inputs: Dictionary of app_name -> {field: value} for required inputs
            db: Database session

        Returns:
            {
                "created_apps": [app_id1, app_id2, ...],
                "skipped": ["app1", "app2"],
                "errors": {"app3": "error message"}
            }
        """
        preset = self.get_preset(preset_id)
        if not preset:
            raise ValueError(f"Preset not found: {preset_id}")

        app_names = preset.get('apps', [])
        created_apps = []
        skipped = []
        errors = {}

        for app_name in app_names:
            try:
                blueprint = db.query(Blueprint).filter(Blueprint.name == app_name).first()

                if not blueprint:
                    skipped.append(app_name)
                    errors[app_name] = "Blueprint not found"
                    continue

                existing_app = db.query(App).filter(
                    App.blueprint_name == app_name
                ).first()

                if existing_app:
                    skipped.append(app_name)
                    errors[app_name] = "App already exists"
                    continue

                inputs = user_inputs.get(app_name, {})

                inputs = self._fill_default_values(blueprint.schema_json, inputs)

                app = App(
                    name=app_name,
                    db_name=app_name,
                    blueprint_name=app_name,
                    status="configured",
                    raw_inputs=inputs
                )

                db.add(app)
                db.flush()

                created_apps.append(app.id)
                logger.info(f"Created pending app from preset: {app_name} (ID: {app.id})")

            except Exception as e:
                logger.error(f"Failed to create app {app_name}: {e}")
                errors[app_name] = str(e)
                skipped.append(app_name)

        db.commit()

        return {
            "created_apps": created_apps,
            "skipped": skipped,
            "errors": errors
        }

    def _fill_default_values(
        self,
        schema_dict: Dict[str, Any],
        user_inputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Fill in default values for fields not provided by user.
        Only fills in values for fields that have defaults in the schema.
        """
        filled_inputs = user_inputs.copy()

        for field_name, field_data in schema_dict.items():
            if not isinstance(field_data, dict):
                continue

            if field_name not in filled_inputs:
                if 'default' in field_data and field_data['default'] is not None:
                    filled_inputs[field_name] = field_data['default']

        return filled_inputs
