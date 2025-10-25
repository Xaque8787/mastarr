from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi import Request
from contextlib import asynccontextmanager
import os

from models.database import init_db
from services.system_hooks import SystemHooks, get_hooks, initialize_system_hooks, mark_hook_executed
from utils.logger import setup_logging
from utils.first_run import FirstRunInitializer
from routes import apps_router, blueprints_router, system_router

logger = setup_logging(os.getenv("LOG_LEVEL", "INFO"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown"""
    logger.info("=" * 60)
    logger.info("Mastarr Starting...")
    logger.info("=" * 60)

    initializer = FirstRunInitializer()
    initializer.initialize()

    logger.info("Initializing database...")
    init_db()

    logger.info("Initializing system hooks...")
    initialize_system_hooks()

    hooks = SystemHooks()

    first_run_hooks = get_hooks(hook_type="first_run_only", executed=False)
    for hook in first_run_hooks:
        logger.info(f"Executing first-run hook: {hook.name}")
        hook_func = getattr(hooks, hook.function_name)
        await hook_func()
        mark_hook_executed(hook.name)

    every_run_hooks = get_hooks(hook_type="every_run")
    for hook in every_run_hooks:
        logger.info(f"Executing startup hook: {hook.name}")
        hook_func = getattr(hooks, hook.function_name)
        await hook_func()

    logger.info("=" * 60)
    logger.info("✓ Mastarr Ready!")
    logger.info("=" * 60)

    yield

    logger.info("Shutting down...")

    teardown_hooks = get_hooks(hook_type="teardown")
    for hook in teardown_hooks:
        logger.info(f"Executing teardown hook: {hook.name}")
        hook_func = getattr(hooks, hook.function_name)
        await hook_func()

    logger.info("Mastarr Shutdown Complete")


app = FastAPI(
    title="Mastarr",
    description="Media Server Application Manager",
    version="0.1.0",
    lifespan=lifespan
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.include_router(apps_router)
app.include_router(blueprints_router)
app.include_router(system_router)


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve the main application page"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
