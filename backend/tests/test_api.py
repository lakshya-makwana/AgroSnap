import uuid

from tests.conftest import jpeg_bytes


def post_image(client, data, key=None, **form):
    return client.post("/api/v1/predictions", files={"image": ("leaf.jpg", data, "image/jpeg")},
                       data=form, headers={"Idempotency-Key": key or str(uuid.uuid4())})


def test_health_reports_demo(client):
    r = client.get("/api/v1/health").json()
    assert r["model_loaded"] and r["demo_model"]


def test_crops_in_hindi(client):
    r = client.get("/api/v1/crops", headers={"Accept-Language": "hi-IN,hi;q=0.9"}).json()
    assert r["language"] == "hi"
    tomato = next(i for i in r["items"] if i["crop"] == "Tomato")
    assert tomato["name"] == "टमाटर" and len(tomato["classes"]) == 4


def test_prediction_shape(client):
    r = post_image(client, jpeg_bytes(), source="camera")
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["status"] in {"confident", "uncertain", "unsupported"}
    assert b["is_demo"] is True and b["model_version"].startswith("demo")
    assert len(b["alternatives"]) == 2
    assert b["top_prediction"]["score"] >= b["alternatives"][0]["score"]


def test_crop_filter(client):
    b = post_image(client, jpeg_bytes(), crop="tomato").json()
    assert b["crop_filter"]["applied"] and b["crop_filter"]["crop"] == "Tomato"
    assert all(c["crop"] == "Tomato" for c in [b["top_prediction"], *b["alternatives"]])


def test_unknown_crop_is_422(client):
    r = post_image(client, jpeg_bytes(), crop="Banana")
    assert r.status_code == 422 and r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_idempotency(client):
    key = str(uuid.uuid4())
    a = post_image(client, jpeg_bytes(), key=key).json()
    b = post_image(client, jpeg_bytes(), key=key).json()
    assert a == b
    r = post_image(client, jpeg_bytes(color=(10, 200, 10)), key=key)
    assert r.status_code == 409 and r.json()["error"]["code"] == "IDEMPOTENCY_MISMATCH"


def test_missing_idempotency_key_is_422(client):
    r = client.post("/api/v1/predictions", files={"image": ("a.jpg", jpeg_bytes(), "image/jpeg")})
    assert r.status_code == 422


def test_bad_inputs_are_4xx(client, settings):
    assert post_image(client, b"").status_code == 422
    assert post_image(client, b"not an image at all").status_code == 415
    assert post_image(client, jpeg_bytes(fmt="GIF")).status_code == 415
    big = b"\xff\xd8" + b"0" * int(settings.max_upload_mb * 1024 * 1024 + 10)
    assert post_image(client, big).status_code == 413
    truncated = jpeg_bytes()[:300]
    assert post_image(client, truncated).status_code in (415, 422)


def test_small_and_dark_photos_are_unsupported(client):
    b = post_image(client, jpeg_bytes(size=(120, 100))).json()
    assert b["status"] == "unsupported" and b["reason"] == "too_small"
    b = post_image(client, jpeg_bytes(color=(5, 5, 5), noise=False)).json()
    assert b["status"] == "unsupported" and b["reason"] == "too_dark"


def test_png_with_exif_rotation_and_png(client):
    assert post_image(client, jpeg_bytes(fmt="PNG")).status_code == 200


def test_feedback_without_photo(client, settings):
    r = client.post("/api/v1/feedback", data={"verdict": "correct", "predicted_class_id": 8,
                                              "model_version": "demo", "crop": "Tomato"})
    assert r.status_code == 201 and r.json()["photo_stored"] is False
    assert not settings.feedback_dir.exists()


def test_feedback_with_photo_is_filed_under_correct_class(client, settings):
    r = client.post("/api/v1/feedback",
                    data={"verdict": "wrong", "predicted_class_id": 8, "correct_class_id": 9,
                          "model_version": "demo", "share_photo": "true"},
                    files={"image": ("leaf.jpg", jpeg_bytes(), "image/jpeg")})
    assert r.status_code == 201 and r.json()["photo_stored"] is True
    assert len(list((settings.feedback_dir / "Tomato_Late_blight").glob("*.jpg"))) == 1


def test_feedback_validation(client):
    base = {"model_version": "demo"}
    r = client.post("/api/v1/feedback", data={**base, "verdict": "wrong", "predicted_class_id": 99})
    assert r.status_code == 422
    r = client.post("/api/v1/feedback", data={**base, "verdict": "correct", "predicted_class_id": 1,
                                              "correct_class_id": 2})
    assert r.status_code == 422
    r = client.post("/api/v1/feedback", data={**base, "verdict": "correct", "predicted_class_id": 1,
                                              "share_photo": "true"})
    assert r.status_code == 422


def test_weather_is_shaped_and_cached(client, monkeypatch):
    calls = []

    def fake_fetch(lat, lon):
        calls.append((lat, lon))
        return {"timezone": "Asia/Kolkata",
                "current": {"temperature_2m": 30.1, "relative_humidity_2m": 74, "precipitation": 0.0,
                            "wind_speed_10m": 12, "weather_code": 2, "time": "2026-10-24T11:00"},
                "hourly": {"time": ["2026-10-24T12:00"], "temperature_2m": [31], "precipitation_probability": [10],
                           "weather_code": [2]},
                "daily": {"time": ["2026-10-24"], "weather_code": [2], "temperature_2m_max": [33],
                          "temperature_2m_min": [24], "precipitation_sum": [0], "precipitation_probability_max": [20]}}

    monkeypatch.setattr(client.app.state.weather, "fetch_raw", fake_fetch)
    a = client.get("/api/v1/weather", params={"lat": 19.07612, "lon": 72.87765}).json()
    client.get("/api/v1/weather", params={"lat": 19.0812, "lon": 72.8801})
    assert a["location"]["lat"] == 19.08 and a["current"]["temp_c"] == 30.1 and a["fetched_at"]
    assert len(calls) == 1  # second call (same rounded location) served from cache
