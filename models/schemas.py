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
    inputs: Dict[str, Any]
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


class ComposeService(BaseModel):
    """Docker compose service definition"""
    image: str
    container_name: str
    restart: str = "unless-stopped"
    environment: Optional[List[str]] = None
    volumes: Optional[List[str]] = None
    ports: Optional[List[str]] = None
    networks: Optional[List[str]] = None
    depends_on: Optional[List[str]] = None
    labels: Optional[Dict[str, str]] = None


class ComposeSchema(BaseModel):
    """Docker compose file schema"""
    version: str = "3.9"
    services: Dict[str, ComposeService]
    networks: Optional[Dict[str, Any]] = None
    volumes: Optional[Dict[str, Any]] = None


# Allow recursive model for dependent_fields
FieldSchema.model_rebuild()
