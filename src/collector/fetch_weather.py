import time
import requests
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
JMA_TOKYO_URL = "https://www.jma.go.jp/bosai/forecast/data/forecast/130000.json"


def fetch_tokyo_weather(lat: float = 35.6812, lon: float = 139.7671, retries: int = 2) -> dict:
    fetched_at = datetime.now(JST).isoformat()
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,precipitation,rain,weather_code,wind_speed_10m,wind_gusts_10m",
        "timezone": "Asia/Tokyo",
    }

    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(OPEN_METEO_URL, params=params, timeout=(10, 20))
            resp.raise_for_status()
            data = resp.json().get("current", {})
            return {
                "fetched_at": fetched_at,
                "weather_source": "open-meteo",
                "temperature_2m": data.get("temperature_2m"),
                "precipitation": data.get("precipitation"),
                "rain": data.get("rain"),
                "weather_code": data.get("weather_code"),
                "wind_speed_10m": data.get("wind_speed_10m"),
                "wind_gusts_10m": data.get("wind_gusts_10m"),
            }
        except requests.RequestException as e:
            print(f"[Warn] Open-Meteo attempt {attempt} failed: {e}")
            if attempt < retries:
                time.sleep(2 * attempt)

    try:
        jma_resp = requests.get(JMA_TOKYO_URL, timeout=(10, 20))
        jma_resp.raise_for_status()
        jma_data = jma_resp.json()
        weather_code_str = jma_data[0]["timeSeries"][0]["areas"][0]["weatherCodes"][0]
        return {
            "fetched_at": fetched_at,
            "weather_source": "jma_fallback",
            "temperature_2m": None,
            "precipitation": None,
            "rain": None,
            "weather_code": int(weather_code_str),
            "wind_speed_10m": None,
            "wind_gusts_10m": None,
        }
    except Exception as jma_err:
        print(f"[Warn] JMA fallback also failed: {jma_err}. Proceeding with null weather.")

    return {
        "fetched_at": fetched_at,
        "weather_source": "unavailable",
        "temperature_2m": None,
        "precipitation": None,
        "rain": None,
        "weather_code": None,
        "wind_speed_10m": None,
        "wind_gusts_10m": None,
    }
