from datetime import datetime, timezone, timedelta
import requests

JST = timezone(timedelta(hours=9))
TOKYO_LAT = 35.6812
TOKYO_LON = 139.7671


def fetch_tokyo_weather() -> dict:
    """Fetch current weather conditions in central Tokyo via Open-Meteo API."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": TOKYO_LAT,
        "longitude": TOKYO_LON,
        "current": [
            "temperature_2m",
            "precipitation",
            "rain",
            "snowfall",
            "weather_code",
            "wind_speed_10m",
            "wind_direction_10m",
            "wind_gusts_10m",
        ],
        "wind_speed_unit": "ms",  # m/s (Japanese rail regulation standard)
        "timezone": "Asia/Tokyo",
    }

    response = requests.get(url, params=params, timeout=15)
    response.raise_for_status()
    data = response.json()
    current = data.get("current", {})

    return {
        "fetched_at_jst": datetime.now(JST).isoformat(),
        "weather_time": current.get("time"),
        "temperature_c": current.get("temperature_2m"),
        "precipitation_mm": current.get("precipitation"),
        "rain_mm": current.get("rain"),
        "snowfall_cm": current.get("snowfall"),
        "weather_code": current.get("weather_code"),
        "wind_speed_ms": current.get("wind_speed_10m"),
        "wind_direction_deg": current.get("wind_direction_10m"),
        "wind_gusts_ms": current.get("wind_gusts_10m"),
    }


if __name__ == "__main__":
    weather = fetch_tokyo_weather()
    print("=== Current Tokyo Weather ===")
    for k, v in weather.items():
        print(f"{k}: {v}")
