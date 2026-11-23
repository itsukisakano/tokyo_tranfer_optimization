import time
import requests
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


def fetch_tokyo_weather(lat: float = 35.6812, lon: float = 139.7671, retries: int = 3) -> dict:
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,precipitation,rain,weather_code,wind_speed_10m,wind_gusts_10m",
        "timezone": "Asia/Tokyo",
    }

    last_err = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(OPEN_METEO_URL, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json().get("current", {})
            return {
                "fetched_at": datetime.now(JST).isoformat(),
                "temperature_2m": data.get("temperature_2m"),
                "precipitation": data.get("precipitation"),
                "rain": data.get("rain"),
                "weather_code": data.get("weather_code"),
                "wind_speed_10m": data.get("wind_speed_10m"),
                "wind_gusts_10m": data.get("wind_gusts_10m"),
            }
        except requests.RequestException as e:
            last_err = e
            if attempt < retries:
                time.sleep(3 * attempt)

    raise RuntimeError(f"Failed to fetch weather data after {retries} attempts: {last_err}")
