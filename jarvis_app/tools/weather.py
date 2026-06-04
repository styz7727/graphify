"""Open-Meteo weather — no API key required."""
from __future__ import annotations

import requests

from jarvis_app import config

_GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
_WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

_WMO_CODES = {
    0: "klar", 1: "meist klar", 2: "teilweise bewölkt", 3: "bewölkt",
    45: "Nebel", 48: "Reifnebel",
    51: "leichter Niesel", 53: "Niesel", 55: "starker Niesel",
    61: "leichter Regen", 63: "Regen", 65: "starker Regen",
    71: "leichter Schnee", 73: "Schnee", 75: "starker Schnee",
    80: "Regenschauer", 81: "Regenschauer", 82: "starke Schauer",
    95: "Gewitter", 96: "Gewitter mit Hagel",
}


def get_weather(city: str | None = None) -> str:
    city = city or config.city()
    try:
        # 1. Geocode
        geo = requests.get(_GEO_URL, params={"name": city, "count": 1, "language": "de"}, timeout=5)
        geo.raise_for_status()
        results = geo.json().get("results")
        if not results:
            return f"Stadt '{city}' nicht gefunden."
        loc = results[0]
        lat, lon = loc["latitude"], loc["longitude"]
        name = loc.get("name", city)

        # 2. Weather
        wx = requests.get(
            _WEATHER_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,weathercode,windspeed_10m",
                "daily": "temperature_2m_max,temperature_2m_min",
                "timezone": "auto",
                "forecast_days": 1,
            },
            timeout=5,
        )
        wx.raise_for_status()
        data = wx.json()
        cur = data["current"]
        daily = data["daily"]

        temp    = cur["temperature_2m"]
        code    = cur["weathercode"]
        wind    = cur["windspeed_10m"]
        t_max   = daily["temperature_2m_max"][0]
        t_min   = daily["temperature_2m_min"][0]
        cond    = _WMO_CODES.get(code, "unbekannt")

        return (
            f"In {name}: {temp}°C, {cond}. "
            f"Wind {wind} km/h. "
            f"Heute {t_min}–{t_max}°C."
        )
    except requests.RequestException as e:
        return f"Wetter nicht verfügbar (Netzwerkfehler: {e})."
    except Exception as e:
        return f"Wetter-Fehler: {e}"
