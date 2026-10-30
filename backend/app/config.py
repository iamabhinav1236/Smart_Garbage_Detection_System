import os
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = "Smart Garbage Detection System"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api"
    
    # Security
    SECRET_KEY: str = "smart-garbage-detection-secret-key-2026-super-secure"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    
    # Default Admin
    DEFAULT_ADMIN_USER: str = "admin"
    DEFAULT_ADMIN_PASS: str = "admin123"
    
    # Database
    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/smart_garbage.db"
    
    # AI & YOLO
    YOLO_MODEL_PATH: str = str(BASE_DIR / "models" / "yolov8n.onnx")
    YOLO_FALLBACK_PT: str = str(BASE_DIR / "models" / "yolov8n.pt")
    DETECTION_FPS: int = 5
    CONFIDENCE_THRESHOLD: float = 0.25
    
    # Email / SMTP defaults (can also be overridden in DB)
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", 587))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    CARETAKER_EMAIL: str = os.getenv("CARETAKER_EMAIL", "")
    CARETAKER_NAME: str = os.getenv("CARETAKER_NAME", "Campus Sanitation Caretaker")
    ALERT_THRESHOLD: float = 85.0
    COOLDOWN_MINUTES: int = 15
    
    # Paths
    SNAPSHOTS_DIR: str = str(BASE_DIR / "data" / "snapshots")
    LOGS_DIR: str = str(BASE_DIR / "data" / "logs")
    REFERENCES_DIR: str = str(BASE_DIR / "data" / "references")

    # Browser origins allowed to call the API (comma-separated in .env)
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    class Config:
        env_file = str(BASE_DIR / ".env")
        extra = "allow"

    @property
    def cors_origins_list(self) -> list:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


def _from_base(path: str) -> str:
    """Relative paths in .env are resolved against the project root, not the current folder."""
    p = Path(path)
    return str(p if p.is_absolute() else (BASE_DIR / p).resolve())


settings = Settings()

# Make the app independent of the folder it is started from
if settings.DATABASE_URL.startswith("sqlite:///") and not settings.DATABASE_URL.startswith("sqlite:////"):
    db_path = settings.DATABASE_URL[len("sqlite:///"):]
    if not Path(db_path).is_absolute():
        settings.DATABASE_URL = f"sqlite:///{_from_base(db_path)}"
for _field in ("YOLO_MODEL_PATH", "YOLO_FALLBACK_PT", "SNAPSHOTS_DIR", "LOGS_DIR", "REFERENCES_DIR"):
    setattr(settings, _field, _from_base(getattr(settings, _field)))
