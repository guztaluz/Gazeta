from __future__ import annotations

import httpx

from src.config import get_settings

ENDPOINT = "https://api.open-meteo.com/v1/forecast"

# WMO weather codes → short English label.
_CODE = {
    0: "clear", 1: "mostly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "freezing fog",
    51: "light drizzle", 53: "drizzle", 55: "heavy drizzle",
    61: "light rain", 63: "rain", 65: "heavy rain",
    66: "freezing rain", 67: "heavy freezing rain",
    71: "light snow", 73: "snow", 75: "heavy snow", 77: "snow grains",
    80: "rain showers", 81: "heavy rain showers", 82: "violent rain showers",
    85: "snow showers", 86: "heavy snow showers",
    95: "thunderstorm", 96: "thunderstorm with hail", 99: "severe thunderstorm",
}


async def fetch(client: httpx.AsyncClient | None = None) -> dict:
    s = get_settings()
    own = client is None
    c = client or httpx.AsyncClient(timeout=5)
    try:
        r = await c.get(
            ENDPOINT,
            params={
                "latitude": s.weather_lat,
                "longitude": s.weather_lon,
                "daily": "weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_max,wind_speed_10m_max",
                "current": "temperature_2m,weathercode,wind_speed_10m",
                "timezone": s.weather_tz,
                "forecast_days": 1,
            },
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        return {"error": str(e)}
    finally:
        if own:
            await c.aclose()

    daily = data.get("daily", {})
    current = data.get("current", {})
    code = (daily.get("weathercode") or [0])[0]
    t_max = (daily.get("temperature_2m_max") or [None])[0]
    t_min = (daily.get("temperature_2m_min") or [None])[0]
    pop = (daily.get("precipitation_probability_max") or [0])[0]
    wind = (daily.get("wind_speed_10m_max") or [0])[0]

    return {
        "summary": _CODE.get(code, f"code {code}"),
        "temp_min_c": t_min,
        "temp_max_c": t_max,
        "precip_prob": pop,
        "wind_kmh": wind,
        "current_c": current.get("temperature_2m"),
        "wear_jacket": (t_min is not None and t_min < 15) or pop >= 40,
    }
