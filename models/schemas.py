from pydantic import BaseModel, Field, validator, field_validator
from typing import Optional, List, Dict, Any, Literal, Union
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
        "radio_group", "conditional", "number", "textarea",
        "port_mapping", "volume_mapping", "network_config",
        "device_mapping", "healthcheck_config"
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

    # For compound fields (type: "object")
    fields: Optional[Dict[str, "FieldSchema"]] = None

    # For array fields
    item_schema: Optional["FieldSchema"] = None
    min_items: Optional[int] = None
    max_items: Optional[int] = None

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

    # Lifecycle Hooks
    pre_install_hook: Optional[str] = None
    post_install_hook: Optional[str] = None
    pre_update_hook: Optional[str] = None
    post_update_hook: Optional[str] = None
    pre_start_hook: Optional[str] = None
    post_start_hook: Optional[str] = None
    pre_stop_hook: Optional[str] = None
    post_stop_hook: Optional[str] = None
    pre_remove_hook: Optional[str] = None
    post_remove_hook: Optional[str] = None
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


class BindOptionsSchema(BaseModel):
    """Bind mount specific options"""
    propagation: Optional[Literal["shared", "slave", "private", "rshared", "rslave", "rprivate"]] = None
    create_host_path: Optional[bool] = None

    class Config:
        # Exclude None values when serializing
        exclude_none = True


class ServiceBindVolumeSchema(BaseModel):
    """
    Long syntax for bind mount volumes.
    Automatically prepends ${HOST_PATH}/ to relative paths starting with ./
    """
    type: Literal["bind"] = "bind"
    source: str
    target: str
    read_only: Optional[bool] = None
    bind: Optional[BindOptionsSchema] = None

    @field_validator('source')
    @classmethod
    def transform_relative_path(cls, v: str) -> str:
        """Prepend ${HOST_PATH}/ to relative paths"""
        if v.startswith('./'):
            return f"${{HOST_PATH}}/{v[2:]}"
        return v

    class Config:
        # Exclude None values when serializing
        exclude_none = True


class ServiceNamedVolumeSchema(BaseModel):
    """Long syntax for named Docker volumes"""
    type: Literal["volume"] = "volume"
    source: str
    target: str
    read_only: Optional[bool] = None
    volume: Optional[Dict[str, Any]] = None

    class Config:
        exclude_none = True


class ServiceTmpfsVolumeSchema(BaseModel):
    """Long syntax for tmpfs volumes"""
    type: Literal["tmpfs"] = "tmpfs"
    target: str
    tmpfs: Optional[Dict[str, Any]] = None

    class Config:
        exclude_none = True


class PortMappingSchema(BaseModel):
    """Long syntax for port mappings"""
    target: int
    published: int
    protocol: Literal["tcp", "udp"] = "tcp"
    mode: Optional[Literal["host", "ingress"]] = None

    class Config:
        exclude_none = True


class ServiceNetworkConfigSchema(BaseModel):
    """Network configuration for a service"""
    ipv4_address: Optional[str] = None
    ipv6_address: Optional[str] = None
    aliases: Optional[List[str]] = None
    priority: Optional[int] = None

    class Config:
        exclude_none = True


class ComposeNetworkSchema(BaseModel):
    """Top-level network definition in compose file"""
    external: Optional[bool] = None
    driver: Optional[str] = None
    driver_opts: Optional[Dict[str, str]] = None
    ipam: Optional[Dict[str, Any]] = None
    internal: Optional[bool] = None
    attachable: Optional[bool] = None
    labels: Optional[Dict[str, str]] = None

    class Config:
        exclude_none = True


class ComposeVolumeSchema(BaseModel):
    """Top-level volume definition in compose file"""
    driver: Optional[str] = "local"
    driver_opts: Optional[Dict[str, str]] = None
    external: Optional[bool] = None
    name: Optional[str] = None
    labels: Optional[Dict[str, str]] = None

    class Config:
        exclude_none = True


class HealthcheckSchema(BaseModel):
    """Healthcheck configuration"""
    test: Union[str, List[str]]
    interval: Optional[str] = None
    timeout: Optional[str] = None
    retries: Optional[int] = None
    start_period: Optional[str] = None

    class Config:
        exclude_none = True


class DeviceSchema(BaseModel):
    """Device mapping for hardware access"""
    host_path: str
    container_path: str
    permissions: Optional[str] = None

    class Config:
        exclude_none = True


class ServiceSchema(BaseModel):
    """
    Docker compose service definition with comprehensive Docker Compose support.
    Allows extra fields for flexibility with uncommon Docker Compose options.
    """
    # Required
    image: str

    # Common options
    container_name: Optional[str] = None
    restart: Optional[str] = "unless-stopped"

    # Environment & Config
    environment: Optional[Dict[str, Any]] = None
    env_file: Optional[Union[str, List[str]]] = None

    # Volumes & Storage
    volumes: Optional[List[Union[ServiceBindVolumeSchema, ServiceNamedVolumeSchema, ServiceTmpfsVolumeSchema, str]]] = None

    # Networking
    ports: Optional[List[Union[PortMappingSchema, str]]] = None
    networks: Optional[Union[List[str], Dict[str, ServiceNetworkConfigSchema]]] = None
    hostname: Optional[str] = None
    domainname: Optional[str] = None

    # Runtime
    command: Optional[Union[str, List[str]]] = None
    entrypoint: Optional[Union[str, List[str]]] = None
    working_dir: Optional[str] = None
    user: Optional[str] = None

    # Resources & Limits
    mem_limit: Optional[str] = None
    mem_reservation: Optional[str] = None
    memswap_limit: Optional[str] = None
    cpus: Optional[float] = None
    cpu_shares: Optional[int] = None
    cpu_quota: Optional[int] = None
    cpu_period: Optional[int] = None
    cpuset: Optional[str] = None

    # Security
    privileged: Optional[bool] = None
    cap_add: Optional[List[str]] = None
    cap_drop: Optional[List[str]] = None
    security_opt: Optional[List[str]] = None

    # Devices & Hardware
    devices: Optional[List[Union[DeviceSchema, str]]] = None

    # Health & Monitoring
    healthcheck: Optional[HealthcheckSchema] = None

    # Dependencies
    depends_on: Optional[Union[List[str], Dict[str, Any]]] = None

    # Metadata
    labels: Optional[Dict[str, str]] = None

    # System options
    sysctls: Optional[Dict[str, Any]] = None
    ulimits: Optional[Dict[str, Any]] = None
    shm_size: Optional[str] = None

    # Logging
    logging: Optional[Dict[str, Any]] = None

    # Other common options
    stdin_open: Optional[bool] = None
    tty: Optional[bool] = None
    stop_grace_period: Optional[str] = None
    stop_signal: Optional[str] = None

    class Config:
        extra = "allow"  # Allow additional fields not defined in schema
        exclude_none = True


class ComposeSchema(BaseModel):
    """Docker compose file schema - top-level compose structure"""
    services: Dict[str, ServiceSchema]
    networks: Optional[Dict[str, Union[ComposeNetworkSchema, Any]]] = None
    volumes: Optional[Dict[str, Union[ComposeVolumeSchema, Any]]] = None
    secrets: Optional[Dict[str, Any]] = None
    configs: Optional[Dict[str, Any]] = None

    class Config:
        extra = "allow"  # Allow additional top-level fields
        exclude_none = True


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
        exclude_none = True


# Allow recursive model for dependent_fields
FieldSchema.model_rebuild()
