import logging
import sys
from pathlib import Path
from rich.logging import RichHandler
from rich.console import Console

console = Console()


def setup_logging(log_level: str = "INFO"):
    """
    Configure application logging with rich formatting.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    # Create logs directory
    log_dir = Path("/app/logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(
                console=console,
                rich_tracebacks=True,
                tracebacks_show_locals=True
            ),
            logging.FileHandler(log_dir / "mastarr.log")
        ]
    )

    # Create logger
    logger = logging.getLogger("mastarr")
    logger.setLevel(log_level)

    return logger


def get_logger(name: str = "mastarr"):
    """Get a logger instance"""
    return logging.getLogger(name)
