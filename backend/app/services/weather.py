"""Weather proxy (Open-Meteo, no API key) with a per-location server cache. D5 may replace the provider."""

import threading
import time
from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.errors import ApiError

PROVIDER = "open-meteo"


class WeatherService:
    def __init__(self, base_url: str, ttl_min: int):
        self.base_url, self.ttl = base_url, ttl_min * 60
        self._cache: dict[tuple[float, float], tuple[float, dict[str, Any]]] = {}
        self._lock = threading.Lock()

    def fetch_raw(self, lat: float, lon: float) -> dict[str, Any]:
        params = {
            "latitude": lat, "longitude": lon, "timezone": "auto", "forecast_days": 7, "forecast_hours": 24,
            "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,weather_code",
            "hourly": "temperature_2m,precipitation_probability,weather_code",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,"
                     "precipitation_probability_max",
        }
        r = httpx.get(self.base_url, params=params, timeout=10.0)
        r.raise_for_status()
        return r.json()

    def forecast(self, lat: float, lon: float) -> dict[str, Any]:
        key = (round(lat, 2), round(lon, 2))  # ~1 km; avoids sending exact farm locations
        with self._lock:
            hit = self._cache.get(key)
            if hit and time.time() - hit[0] < self.ttl:
                return hit[1]
        try:
            raw = self.fetch_raw(*key)
        except Exception as e:
            if hit:  # serve stale data; fetched_at tells the app how old it is
                return hit[1]
            raise ApiError(503, "WEATHER_UNAVAILABLE",
                           "Weather is unavailable right now. Please try again later.") from e
        data = self._shape(key, raw)
        with self._lock:
            self._cache[key] = (time.time(), data)
        return data

    @staticmethod
    def _shape(key: tuple[float, float], raw: dict[str, Any]) -> dict[str, Any]:
        cur, hourly, daily = raw.get("current", {}), raw.get("hourly", {}), raw.get("daily", {})
        return {
            "location": {"lat": key[0], "lon": key[1], "timezone": raw.get("timezone")},
            "fetched_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "provider": PROVIDER,
            "current": {
                "temp_c": cur.get("temperature_2m"), "humidity_pct": cur.get("relative_humidity_2m"),
                "rain_mm": cur.get("precipitation"), "wind_kph": cur.get("wind_speed_10m"),
                "weather_code": cur.get("weather_code"), "observed_at": cur.get("time"),
            },
            "hourly": [
                {"time": t, "temp_c": tc, "rain_chance_pct": pp, "weather_code": wc}
                for t, tc, pp, wc in zip(hourly.get("time", []), hourly.get("temperature_2m", []),
                                         hourly.get("precipitation_probability", []), hourly.get("weather_code", []),
                                         strict=False)
            ],
            "daily": [
                {"date": d, "max_c": mx, "min_c": mn, "rain_mm": rs, "rain_chance_pct": pp, "weather_code": wc}
                for d, wc, mx, mn, rs, pp in zip(daily.get("time", []), daily.get("weather_code", []),
                                                 daily.get("temperature_2m_max", []),
                                                 daily.get("temperature_2m_min", []),
                                                 daily.get("precipitation_sum", []),
                                                 daily.get("precipitation_probability_max", []), strict=False)
            ],
            "alerts": [],  # Open-Meteo has no alerts; see DECISIONS D5
        }
