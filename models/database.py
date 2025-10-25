from sqlalchemy import Column, Integer, String, Float, Boolean, JSON, ARRAY, Text, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from typing import Optional
import os

Base = declarative_base()


class Blueprint(Base):
    """App blueprint definitions stored in database"""
    __tablename__ = "blueprints"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    display_name = Column(String, nullable=False)
    description = Column(Text)
    category = Column(String, nullable=False)
    icon_url = Column(String)
    install_order = Column(Float, default=10.0)
    visible = Column(Boolean, default=True)

    # Prerequisites: list of blueprint names
    prerequisites = Column(ARRAY(String), default=list)

    # Static IP assignments for containers
    static_ips = Column(JSON)

    # Field schema (JSON)
    schema_json = Column(JSON, nullable=False)

    # Hooks
    post_install_hook = Column(String)
    pre_uninstall_hook = Column(String)
    health_check_hook = Column(String)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)


class App(Base):
    """User's installed app instances"""
    __tablename__ = "apps"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    db_name = Column(String, unique=True, nullable=False)
    blueprint_name = Column(String, nullable=False)

    # Status: pending, installing, running, error, stopped
    status = Column(String, default="pending")
    error_message = Column(Text)

    # User's configuration inputs (validated)
    inputs = Column(JSON, default=dict)

    # Generated compose data
    compose_data = Column(JSON)
    compose_file_path = Column(String)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    installed_at = Column(DateTime)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)


class SystemHook(Base):
    """System lifecycle hooks"""
    __tablename__ = "system_hooks"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)

    # Hook type: first_run_only, every_run, teardown
    hook_type = Column(String, nullable=False)

    # Function name to execute (must exist in services/system_hooks.py)
    function_name = Column(String, nullable=False)

    execution_order = Column(Integer, default=0)
    enabled = Column(Boolean, default=True)

    # Track if first_run hooks have been executed
    executed = Column(Boolean, default=False)
    last_executed = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)


class GlobalSettings(Base):
    """Global configuration settings"""
    __tablename__ = "global_settings"

    id = Column(Integer, primary_key=True)

    # Docker user/group IDs
    puid = Column(Integer, default=1000)
    pgid = Column(Integer, default=1000)

    # Timezone
    timezone = Column(String, default="UTC")

    # Network settings
    network_name = Column(String, default="mastarr_net")
    network_subnet = Column(String, default="10.21.12.0/26")
    network_gateway = Column(String, default="10.21.12.1")

    # Paths
    stacks_path = Column(String, default="/stacks")
    data_path = Column(String, default="/app/data")

    updated_at = Column(DateTime, onupdate=datetime.utcnow)


# Database connection
def get_database_url():
    """Get database URL from environment"""
    supabase_url = os.getenv("SUPABASE_URL", "")

    if not supabase_url:
        raise ValueError("SUPABASE_URL not set in environment")

    # Extract project reference from Supabase URL
    # Format: https://<project-ref>.supabase.co
    project_ref = supabase_url.replace("https://", "").replace(".supabase.co", "")

    # Construct PostgreSQL connection string
    # Supabase provides direct PostgreSQL access
    db_url = f"postgresql://postgres:postgres@db.{project_ref}.supabase.co:5432/postgres"

    return db_url


def get_engine():
    """Create SQLAlchemy engine"""
    database_url = get_database_url()
    return create_engine(database_url, echo=False)


def get_session():
    """Create database session"""
    engine = get_engine()
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def init_db():
    """Initialize database tables"""
    engine = get_engine()
    Base.metadata.create_all(engine)
