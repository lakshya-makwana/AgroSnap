import hashlib
import time
import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, Header, Query, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

from app.api.deps import get_bundle, get_lang
from app.core.errors import ApiError
from app.db import Feedback
from app.services.image_validation import decode_upload
from app.services.inference import decide, score_band
from app.services.model_registry import ModelBundle
from app.services.preprocessing import preprocess

router = APIRouter()

SCORE_EXPLANATION = {
    "en": "This score shows how closely the photo matches what AgroSnap learned. "
          "It is not a guarantee that the result is correct.",
    "hi": "यह स्कोर बताता है कि फ़ोटो AgroSnap की सीखी हुई जानकारी से कितनी मिलती है। "
          "यह इस बात की गारंटी नहीं है कि परिणाम सही है।",
}


@router.get("/health")
def health(request: Request) -> dict:
    bundle: ModelBundle | None = getattr(request.app.state, "bundle", None)
    return {"status": "ok", "model_loaded": bundle is not None, "demo_model": bool(bundle and bundle.is_demo),
            "version": request.app.state.settings.app_version}


@router.get("/model-info")
def model_info(bundle: Annotated[ModelBundle, Depends(get_bundle)]) -> dict:
    return {
        "model_name": bundle.architecture, "model_version": bundle.version, "is_demo": bundle.is_demo,
        "num_classes": bundle.mapping.num_classes, "mapping_version": bundle.mapping.version,
        "input_size": [224, 224], "tta_hflip": bundle.tta_hflip, "temperature": bundle.temperature,
        "metrics": {"test_macro_f1": bundle.metrics.get("test_macro_f1"),
                    "test_accuracy": bundle.metrics.get("test_acc")},
        "crop_thresholds_calibrated": bundle.thresholds.t_conf_crop is not None,
        "compression": bundle.compression,
        "supported_crops": sorted(bundle.mapping.crops),
    }


@router.get("/crops")
def crops(bundle: Annotated[ModelBundle, Depends(get_bundle)], lang: Annotated[str, Depends(get_lang)]) -> dict:
    m = bundle.mapping
    items = []
    for crop in sorted(m.crops):
        classes = [m.classes[i] for i in m.crops[crop]]
        items.append({
            "crop": crop, "name": m.crop_display(crop, lang),
            "classes": [{"class_id": c.index, "disease": c.display(lang)[1], "is_healthy": c.is_healthy}
                        for c in classes],
        })
    return {"language": lang, "items": items}


def _candidate_json(bundle: ModelBundle, index: int, score: float, lang: str) -> dict:
    c = bundle.mapping.classes[index]
    crop, disease = c.display(lang)
    return {"class_id": c.index, "class_key": c.class_key, "crop": crop, "disease": disease,
            "is_healthy": c.is_healthy, "score": round(score, 4), "band": score_band(score)}


@router.post("/predictions")
async def create_prediction(
    request: Request,
    bundle: Annotated[ModelBundle, Depends(get_bundle)],
    lang: Annotated[str, Depends(get_lang)],
    image: Annotated[UploadFile, File()],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=64)],
    source: Annotated[Literal["camera", "gallery"] | None, Form()] = None,
    crop: Annotated[str | None, Form(max_length=80)] = None,
) -> JSONResponse:
    s = request.app.state.settings
    data = await image.read()
    image_hash = hashlib.sha256(data).hexdigest()
    cache_key = f"{idempotency_key}:{lang}:{crop or ''}"
    cached = request.app.state.idempotency.get(cache_key)
    if cached:
        if cached[0] != image_hash:
            raise ApiError(409, "IDEMPOTENCY_MISMATCH", "This request was already used for a different photo.")
        return JSONResponse(cached[1])

    crop_key = None
    if crop:
        crop_key = bundle.mapping.find_crop(crop)
        if crop_key is None:
            raise ApiError(422, "VALIDATION_ERROR", "This crop is not supported.", {"crop": crop})

    decoded = await run_in_threadpool(decode_upload, data, s.max_upload_mb, s.min_image_side_px,
                                      s.dark_image_mean_luma)
    started = time.perf_counter()
    async with request.app.state.inference_sem:
        x = await run_in_threadpool(preprocess, decoded.image)
        probs = (await run_in_threadpool(bundle.probabilities, x))[0]
    inference_ms = int((time.perf_counter() - started) * 1000)
    d = decide(bundle, probs, crop_key, decoded.quality_issue)

    top, *alts = d.candidates
    body = {
        "id": None,
        "status": d.status,
        "reason": d.reason,
        "top_prediction": _candidate_json(bundle, top.index, top.score, lang),
        "alternatives": [_candidate_json(bundle, c.index, c.score, lang) for c in alts],
        "crop_filter": {"crop": crop_key, "applied": crop_key is not None, "mismatch": d.crop_mismatch,
                        "detected_crop": bundle.mapping.crop_display(d.detected_crop, lang) if d.detected_crop
                        else None},
        "score_explanation": SCORE_EXPLANATION[lang],
        "advisory_available": False,  # Phase 5: reviewed advisories
        "model_version": bundle.version,
        "is_demo": bundle.is_demo,
        "language": lang,
        "source": source,
        "inference_ms": inference_ms,
        "saved": False,
    }
    request.app.state.idempotency.put(cache_key, image_hash, body)
    return JSONResponse(body)


@router.post("/feedback", status_code=201)
async def create_feedback(
    request: Request,
    bundle: Annotated[ModelBundle, Depends(get_bundle)],
    verdict: Annotated[Literal["correct", "wrong", "unsure"], Form()],
    predicted_class_id: Annotated[int, Form()],
    model_version: Annotated[str, Form(max_length=80)],
    correct_class_id: Annotated[int | None, Form()] = None,
    crop: Annotated[str | None, Form(max_length=80)] = None,
    share_photo: Annotated[bool, Form()] = False,
    image: Annotated[UploadFile | None, File()] = None,
) -> dict:
    s = request.app.state.settings
    n = bundle.mapping.num_classes
    for name, value in (("predicted_class_id", predicted_class_id), ("correct_class_id", correct_class_id)):
        if value is not None and not 0 <= value < n:
            raise ApiError(422, "VALIDATION_ERROR", "Unknown disease class.", {name: value})
    if correct_class_id is not None and verdict != "wrong":
        raise ApiError(422, "VALIDATION_ERROR", "correct_class_id is only allowed with verdict 'wrong'.")
    crop_key = bundle.mapping.find_crop(crop) if crop else None

    fb_id = str(uuid.uuid4())
    image_key = None
    if share_photo:
        if image is None:
            raise ApiError(422, "VALIDATION_ERROR", "A photo is required when share_photo is true.")
        decoded = await run_in_threadpool(decode_upload, await image.read(), s.max_upload_mb, 1, 0.0)
        label = correct_class_id if verdict == "wrong" else predicted_class_id if verdict == "correct" else None
        folder = s.feedback_dir / (bundle.mapping.classes[label].class_key if label is not None else "_unsure")
        folder.mkdir(parents=True, exist_ok=True)
        # Store the full photo (EXIF already applied; metadata such as GPS is dropped by re-encoding).
        await run_in_threadpool(decoded.image.save, folder / f"{fb_id}.jpg", "JPEG", quality=92)
        image_key = f"{folder.name}/{fb_id}.jpg"

    def _save() -> None:
        with request.app.state.sessionmaker() as db:
            db.add(Feedback(id=fb_id, model_version=model_version, mapping_version=bundle.mapping.version,
                            verdict=verdict, predicted_class_id=predicted_class_id,
                            correct_class_id=correct_class_id, crop=crop_key, photo_consent=share_photo,
                            image_key=image_key))
            db.commit()

    await run_in_threadpool(_save)
    return {"id": fb_id, "photo_stored": image_key is not None}


@router.get("/weather")
async def weather(
    request: Request,
    lat: Annotated[float, Query(ge=-90, le=90)],
    lon: Annotated[float, Query(ge=-180, le=180)],
) -> dict:
    return await run_in_threadpool(request.app.state.weather.forecast, lat, lon)
