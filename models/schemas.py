from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime


class UIOption(BaseModel):
    """Dropdown/Radio option"""
    label: str
    value: str


class FieldPrerequisite(BaseModel):
    """Prerequisite for showing a field"""
    app_name: str
    status: Literal["installed", "running"] = "installed"
    input_name: Optional[str] = None
    input_value: Optional[Any] = None


class FieldSchema(BaseModel):
    """Schema for a single input field"""
    type: Literal["string", "integer", "boolean", "object", "array"]
    ui_component: Literal[
        "text", "password", "checkbox", "dropdown",
        "radio_group", "conditional", "number", "textarea"
    ]
    label: str
    description: Optional[str] = None
    tooltip: Optional[str] = None
    placeholder: Optional[str] = None
    default: Optional[Any] = None
    required: bool = False
    visible: bool = True
    is_sensitive: bool = False
    advanced: bool = False

    # For dropdowns/radios
    options: Optional[List[UIOption]] = None

    # For conditional fields
    show_when: Optional[Dict[str, Any]] = None
    dependent_fields: Optional[Dict[str, "FieldSchema"]] = None

    # Prerequisites
    prerequisites: Optional[List[FieldPrerequisite]] = None

    # Validation rules
    min_value: Optional[int] = None
    max_value: Optional[int] = None
    pattern: Optional[str] = None

    # Schema routing - dot notation: "service.image", "compose.networks", "metadata.admin_user"
    schema: Optional[str] = None
    compose_transform: Optional[str] = None  # Transform function name: "port_mapping", "volume_mapping"


class BlueprintSchema(BaseModel):
    """Complete blueprint definition"""
    name: str
    display_name: str
    description: str
    category: Literal[
        "SYSTEM", "MEDIA SERVERS", "STARR APPS",
        "DOWNLOAD CLIENTS", "NETWORKING", "MANAGEMENT", "M3U UTILITY"
    ]
    icon_url: Optional[str] = None
    install_order: float = 10.0
    visible: bool = True

    # App prerequisites
    prerequisites: List[str] = Field(default_factory=list)

    # Static IP assignments
    static_ips: Optional[Dict[str, str]] = None

    # Field definitions
    schema: Dict[str, FieldSchema]

    # Hooks
    post_install_hook: Optional[str] = None
    pre_uninstall_hook: Optional[str] = None
    health_check_hook: Optional[str] = None


class AppCreate(BaseModel):
    """Request to create a new app instance"""
    name: str
    blueprint_name: str
    inputs: Dict[str, Any]


class AppResponse(BaseModel):
    """App response model"""
    id: int
    name: str
    db_name: str
    blueprint_name: str
    status: str
    error_message: Optional[str] = None
    raw_inputs: Dict[str, Any]
    service_data: Dict[str, Any] = {}
    compose_data: Dict[str, Any] = {}
    metadata_data: Dict[str, Any] = {}
    created_at: datetime
    installed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BlueprintResponse(BaseModel):
    """Blueprint response model"""
    id: int
    name: str
    display_name: str
    description: str
    category: str
    icon_url: Optional[str] = None
    install_order: float
    visible: bool
    prerequisites: List[str]
    schema_json: Dict[str, Any]

    class Config:
        from_attributes = True


class GlobalSettingsResponse(BaseModel):
    """Global settings response"""
    puid: int
    pgid: int
    timezone: str
    network_name: str
    network_subnet: str
    network_gateway: str
    stacks_path: str
    data_path: str

    class Config:
        from_attributes = True


class ServiceSchema(BaseModel):
    """Docker compose service definition - allows extra fields for flexibility"""
    image: str
    container_name: Optional[str] = None
    restart: str = "unless-stopped"
    environment: Optional[Dict[str, Any]] = None
    volumes: Optional[List[Any]] = None
    ports: Optional[List[Any]] = None
    networks: Optional[List[str]] = None
    depends_on: Optional[List[str]] = None
    labels: Optional[Dict[str, str]] = None

    class Config:
        extra = "allow"  # Allow additional fields not defined in schema


class ComposeSchema(BaseModel):
    """Docker compose file schema - top-level compose structure"""
    version: str = "3.9"
    services: Dict[str, ServiceSchema]
    networks: Optional[Dict[str, Any]] = None
    volumes: Optional[Dict[str, Any]] = None
    secrets: Optional[Dict[str, Any]] = None
    configs: Optional[Dict[str, Any]] = None

    class Config:
        extra = "allow"  # Allow additional top-level fields


class MetadataSchema(BaseModel):
    """
    Application metadata - NOT in compose file, used by hooks and setup.

    Common fields defined here, app-specific fields handled via extra='allow'.
    Blueprint JSON is the source of truth for all app-specific metadata fields.
    """
    # Common auth/credentials (used by many apps)
    admin_user: Optional[str] = None
    admin_password: Optional[str] = None
    api_key: Optional[str] = None

    # General metadata (documentation/organization)
    author: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None

    class Config:
        extra = "allow"  # All app-specific fields go through extra (e.g., enable_transcoding, library_paths, etc.)


# Allow recursive model for dependent_fields
FieldSchema.model_rebuild()
