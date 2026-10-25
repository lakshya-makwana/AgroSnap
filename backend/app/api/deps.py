from fastapi import Header, Request

from app.core.errors import ApiError
from app.services.class_mapping import SUPPORTED_LANGUAGES
from app.services.model_registry import ModelBundle


def get_bundle(request: Request) -> ModelBundle:
    bundle = getattr(request.app.state, "bundle", None)
    if bundle is None:
        raise ApiError(503, "MODEL_UNAVAILABLE", "Disease detection is unavailable right now. Please try again later.")
    return bundle


def get_lang(accept_language: str | None = Header(default=None)) -> str:
    """First supported language in Accept-Language, else English."""
    for part in (accept_language or "").split(","):
        code = part.split(";")[0].strip().lower()[:2]
        if code in SUPPORTED_LANGUAGES:
            return code
    return "en"
