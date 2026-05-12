from __future__ import annotations

from datetime import date

import httpx

from src.config import get_settings

ENDPOINT = "https://api.open-meteo.com/v1/forecast"

# WMO weather codes → short PT-BR label.
_CODE = {
    0: "céu limpo", 1: "quase limpo", 2: "parcialmente nublado", 3: "encoberto",
    45: "nevoeiro", 48: "nevoeiro gelado",
    51: "chuvisco leve", 53: "chuvisco", 55: "chuvisco forte",
    61: "chuva leve", 63: "chuva", 65: "chuva forte",
    66: "chuva congelante", 67: "chuva congelante forte",
    71: "neve leve", 73: "neve", 75: "neve forte", 77: "neve granular",
    80: "pancadas de chuva", 81: "pancadas fortes", 82: "pancadas violentas",
    85: "pancadas de neve", 86: "pancadas fortes de neve",
    95: "tempestade", 96: "tempestade com granizo", 99: "tempestade severa",
}

_PT_DOW = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]


def _icon(code: int) -> str:
    if code in (0, 1):
        return "sun"
    if code in (2, 3):
        return "cloud"
    if code in (45, 48):
        return "cloud-fog"
    if 51 <= code <= 67 or 80 <= code <= 82:
        return "cloud-rain"
    if 71 <= code <= 86:
        return "cloud-snow"
    if 95 <= code <= 99:
        return "cloud-lightning"
    return "cloud"


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
                "forecast_days": 7,
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

    times = daily.get("time") or []
    codes = daily.get("weathercode") or []
    maxs = daily.get("temperature_2m_max") or []
    mins = daily.get("temperature_2m_min") or []
    pops = daily.get("precipitation_probability_max") or []
    winds = daily.get("wind_speed_10m_max") or []

    code = codes[0] if codes else 0
    t_max = maxs[0] if maxs else None
    t_min = mins[0] if mins else None
    pop = pops[0] if pops else 0
    wind = winds[0] if winds else 0

    forecast = []
    for i in range(min(7, len(times))):
        d = date.fromisoformat(times[i])
        forecast.append({
            "weekday": _PT_DOW[d.weekday()],
            "date": d.isoformat(),
            "code": codes[i] if i < len(codes) else 0,
            "icon": _icon(codes[i] if i < len(codes) else 0),
            "min_c": mins[i] if i < len(mins) else None,
            "max_c": maxs[i] if i < len(maxs) else None,
        })

    return {
        "summary": _CODE.get(code, f"código {code}"),
        "icon": _icon(code),
        "temp_min_c": t_min,
        "temp_max_c": t_max,
        "precip_prob": pop,
        "wind_kmh": wind,
        "current_c": current.get("temperature_2m"),
        "wear_jacket": (t_min is not None and t_min < 15) or pop >= 40,
        "forecast": forecast,
    }
