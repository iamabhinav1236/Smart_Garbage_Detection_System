import logging
import os
from pathlib import Path

LOGS_DIR = Path("data/logs")
LOGS_DIR.mkdir(parents=True, exist_ok=True)
log_file = LOGS_DIR / "system.log"

logger = logging.getLogger("SmartGarbageSystem")
logger.setLevel(logging.INFO)

if not logger.handlers:
    # Console handler
    c_handler = logging.StreamHandler()
    c_handler.setLevel(logging.INFO)
    c_format = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    c_handler.setFormatter(c_format)
    logger.addHandler(c_handler)

    # File handler
    f_handler = logging.FileHandler(str(log_file), encoding="utf-8")
    f_handler.setLevel(logging.INFO)
    f_format = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    f_handler.setFormatter(f_format)
    logger.addHandler(f_handler)
