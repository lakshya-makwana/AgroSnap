from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", protected_namespaces=())

    app_env: str = "local"
    api_prefix: str = "/api/v1"
    app_version: str = "0.1.0"

    # Database. SQLite is fine for local development; use PostgreSQL in staging/production.
    database_url: str = f"sqlite:///{BACKEND_DIR / 'agrosnap_local.db'}"

    # Model bundle (exported by ml/training/AgroSnap_Training_v3.ipynb §14)
    model_path: Path = BACKEND_DIR.parent / "ml" / "artifacts" / "model.keras"
    model_meta_path: Path = BACKEND_DIR.parent / "ml" / "artifacts" / "model_meta.json"
    class_mapping_path: Path = BACKEND_DIR.parent / "ml" / "artifacts" / "class_mapping.json"
    translations_dir: Path = BACKEND_DIR.parent / "ml" / "artifacts" / "translations"
    model_sha256: str = ""  # if set, the model file must match it or startup fails

    # Demo mode: a fake model so the app can be built before training finishes.
    # Refused when app_env == "production".
    demo_model: bool = False

    # Uncertainty overrides. Empty = use the values from model_meta.json.
    uncertainty_t_conf: float | None = None
    uncertainty_m_min: float | None = None

    max_upload_mb: float = 8.0
    min_image_side_px: int = 224
    dark_image_mean_luma: float = 25.0
    inference_max_concurrency: int = 2
    idempotency_ttl_sec: int = 600

    feedback_dir: Path = BACKEND_DIR / "feedback_store"

    weather_base_url: str = "https://api.open-meteo.com/v1/forecast"
    weather_cache_ttl_min: int = 20


@lru_cache
def get_settings() -> Settings:
    return Settings()
