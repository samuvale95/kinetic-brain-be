from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timedelta
import os
import httpx
from app.database import get_db
from app.api.auth import get_current_user
from app.models.user import User, UserProfile
from loguru import logger

router = APIRouter(prefix="/api/weather", tags=["weather"])

# Cache for weather data (in-memory, 30 minutes)
_weather_cache = {}
_cache_duration = timedelta(minutes=30)

WEATHER_CONDITION_EMOJI = {
    "Clear": "☀️",
    "Clouds": "☁️",
    "Rain": "🌧️",
    "Drizzle": "🌦️",
    "Thunderstorm": "⛈️",
    "Snow": "❄️",
    "Mist": "🌫️",
    "Fog": "🌫️",
    "Haze": "🌫️",
}

OPEN_METEO_CODE_MAP = {
    0: ("Clear", "☀️"),
    1: ("Clear", "☀️"),
    2: ("Clouds", "☁️"),
    3: ("Clouds", "☁️"),
    45: ("Fog", "🌫️"),
    48: ("Fog", "🌫️"),
    51: ("Drizzle", "🌦️"),
    53: ("Drizzle", "🌦️"),
    55: ("Drizzle", "🌦️"),
    61: ("Rain", "🌧️"),
    63: ("Rain", "🌧️"),
    65: ("Rain", "🌧️"),
    71: ("Snow", "❄️"),
    73: ("Snow", "❄️"),
    75: ("Snow", "❄️"),
    80: ("Rain", "🌧️"),
    81: ("Rain", "🌧️"),
    82: ("Rain", "🌧️"),
    85: ("Snow", "❄️"),
    86: ("Snow", "❄️"),
    95: ("Thunderstorm", "⛈️"),
    96: ("Thunderstorm", "⛈️"),
    99: ("Thunderstorm", "⛈️"),
}


def _safe_round(value, ndigits: int = 0):
    try:
        if value is None:
            return None
        return round(value, ndigits)
    except (TypeError, ValueError):
        return None


@router.options("/")
async def options_weather():
    """Handle OPTIONS request for CORS preflight"""
    return Response(status_code=200)


@router.get("/")
async def get_weather(
    lat: Optional[float] = Query(None, description="Latitude"),
    lon: Optional[float] = Query(None, description="Longitude"),
    city: Optional[str] = Query(None, description="City name (e.g., 'Milano', 'Rome')"),
    days: int = Query(7, ge=1, le=7, description="Number of forecast days to include"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current weather and multi-day forecast for user's location"""
    user_id = current_user["user_id"]
    api_key = os.getenv("WEATHER_API_KEY")
    use_openweather = api_key is not None

    # Priority: 1) Query param city, 2) User profile city, 3) Default
    profile_city = None
    profile_lat = None
    profile_lon = None

    user_profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if user_profile:
        if user_profile.city:
            profile_city = user_profile.city
        if user_profile.latitude is not None and user_profile.longitude is not None:
            profile_lat = user_profile.latitude
            profile_lon = user_profile.longitude

    # Use query param city if provided, otherwise fall back to profile city
    use_city = city if city is not None else profile_city
    use_lat = lat if lat is not None else profile_lat
    use_lon = lon if lon is not None else profile_lon

    location_query = None
    if use_lat is not None and use_lon is not None:
        location_query = f"lat={use_lat}&lon={use_lon}"
    elif use_city:
        location_query = f"q={use_city}"
    else:
        use_city = "Rome"
        location_query = "q=Rome"

    cache_key = f"{location_query}_{days}_{datetime.now().replace(minute=0, second=0, microsecond=0).isoformat()}"
    cached = _weather_cache.get(cache_key)
    if cached and datetime.now() - cached.get("timestamp", datetime.min) < _cache_duration:
        return cached["data"]

    logger.info(
        f"[WEATHER] Request: location_query={location_query}, lat={use_lat}, lon={use_lon}, city={use_city}, days={days}, user_id={user_id}"
    )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            if use_openweather:
                logger.info("[WEATHER] Using OpenWeather (onecall) provider")
                location_name, current_payload, forecast_payload = await _fetch_openweather(
                    client,
                    location_query,
                    use_lat,
                    use_lon,
                    use_city,
                    api_key,
                    days,
                )
            else:
                logger.info("[WEATHER] Using Open-Meteo provider")
                location_name, current_payload, forecast_payload = await _fetch_openmeteo(
                    client,
                    use_lat,
                    use_lon,
                    use_city,
                    days,
                )
    except httpx.TimeoutException:
        logger.error("[WEATHER] Weather service timeout after 10s")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Weather service timeout"
        )
    except Exception as e:
        logger.exception(f"[WEATHER] Weather service error: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Weather service error: {str(e)}"
        )

    weather_response = {
        "city": location_name,
        "temp": current_payload.get("temp"),
        "condition": current_payload.get("condition"),
        "description": current_payload.get("description"),
        "wind": current_payload.get("wind"),
        "humidity": current_payload.get("humidity"),
        "icon": current_payload.get("icon"),
        "forecast": forecast_payload,
    }

    _weather_cache[cache_key] = {
        "data": weather_response,
        "timestamp": datetime.now(),
    }

    return weather_response


async def _fetch_openweather(
    client: httpx.AsyncClient,
    location_query: str,
    use_lat: Optional[float],
    use_lon: Optional[float],
    fallback_city: Optional[str],
    api_key: str,
    days: int,
):
    current_url = (
        f"http://api.openweathermap.org/data/2.5/weather?{location_query}&appid={api_key}&units=metric&lang=it"
    )
    current_resp = await client.get(current_url)
    logger.debug(
        f"[WEATHER][OpenWeather] Current weather response status={current_resp.status_code}"
    )
    if current_resp.status_code != 200:
        logger.error(
            f"[WEATHER][OpenWeather] Current weather request failed: status={current_resp.status_code}, body={current_resp.text}"
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Weather service unavailable",
        )

    current_data = current_resp.json()
    resolved_lat = use_lat or current_data.get("coord", {}).get("lat")
    resolved_lon = use_lon or current_data.get("coord", {}).get("lon")
    if resolved_lat is None or resolved_lon is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to determine coordinates for weather lookup",
        )

    condition_main = current_data.get("weather", [{}])[0].get("main", "Clear")
    description = (
        current_data.get("weather", [{}])[0].get("description", condition_main).title()
    )
    icon = WEATHER_CONDITION_EMOJI.get(condition_main, "☀️")
    location_name = (
        current_data.get("name")
        or fallback_city
        or f"{resolved_lat:.1f}, {resolved_lon:.1f}"
    )

    current_payload = {
        "temp": _safe_round(current_data.get("main", {}).get("temp")),
        "condition": condition_main,
        "description": description,
        "wind": _safe_round(
            (current_data.get("wind", {}).get("speed")) * 3.6
            if current_data.get("wind", {}).get("speed") is not None
            else None
        ),
        "humidity": current_data.get("main", {}).get("humidity"),
        "icon": icon,
    }

    forecast_url = (
        f"https://api.openweathermap.org/data/2.5/onecall?lat={resolved_lat}&lon={resolved_lon}"
        f"&units=metric&lang=it&exclude=minutely,hourly,alerts&appid={api_key}"
    )
    forecast_resp = await client.get(forecast_url)
    logger.debug(
        f"[WEATHER][OpenWeather] Forecast response status={forecast_resp.status_code}"
    )
    forecast_payload: List[dict] = []

    if forecast_resp.status_code == 200:
        forecast_data = forecast_resp.json()
        daily_entries = forecast_data.get("daily", [])[:days]
        for entry in daily_entries:
            dt = datetime.fromtimestamp(entry.get("dt", 0))
            day_condition = entry.get("weather", [{}])[0].get("main", "Clear")
            day_description = (
                entry.get("weather", [{}])[0]
                .get("description", day_condition)
                .title()
            )
            day_icon = WEATHER_CONDITION_EMOJI.get(day_condition, "☀️")
            forecast_payload.append(
                {
                    "date": dt.strftime("%Y-%m-%d"),
                    "day": dt.strftime("%A"),
                    "condition": day_condition,
                    "description": day_description,
                    "icon": day_icon,
                    "temp_min": _safe_round(entry.get("temp", {}).get("min")),
                    "temp_max": _safe_round(entry.get("temp", {}).get("max")),
                    "wind": _safe_round(
                        entry.get("wind_speed") * 3.6
                        if entry.get("wind_speed") is not None
                        else None
                    ),
                    "humidity": entry.get("humidity"),
                    "precipitation_probability": _safe_round(
                        entry.get("pop") * 100 if entry.get("pop") is not None else None
                    ),
                }
            )
    else:
        logger.warning(
            f"[WEATHER] Failed to fetch OpenWeather forecast: status={forecast_resp.status_code}, body={forecast_resp.text}"
        )

    return location_name, current_payload, forecast_payload


async def _fetch_openmeteo(
    client: httpx.AsyncClient,
    use_lat: Optional[float],
    use_lon: Optional[float],
    fallback_city: Optional[str],
    days: int,
):
    latitude = use_lat if use_lat is not None else 41.9028
    longitude = use_lon if use_lon is not None else 12.4964
    location_name = fallback_city or f"{latitude:.1f}, {longitude:.1f}"

    url = (
        "https://api.open-meteo.com/v1/forecast?"
        f"latitude={latitude}&longitude={longitude}"
        "&current_weather=true"
        "&daily=weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_max," \
        "windspeed_10m_max"
        "&timezone=auto"
    )
    response = await client.get(url)
    logger.debug(
        f"[WEATHER][OpenMeteo] Response status={response.status_code}"
    )
    if response.status_code != 200:
        logger.error(
            f"[WEATHER][OpenMeteo] Request failed: status={response.status_code}, body={response.text}"
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Weather service unavailable",
        )

    data = response.json()
    current = data.get("current_weather", {})
    weather_code = current.get("weathercode", 0)
    condition, icon = OPEN_METEO_CODE_MAP.get(weather_code, ("Clear", "☀️"))

    current_payload = {
        "temp": _safe_round(current.get("temperature")),
        "condition": condition,
        "description": condition,
        "wind": _safe_round(current.get("windspeed")),
        "humidity": None,
        "icon": icon,
    }

    forecast_payload: List[dict] = []
    daily = data.get("daily", {})
    dates = daily.get("time", [])
    temps_max = daily.get("temperature_2m_max", [])
    temps_min = daily.get("temperature_2m_min", [])
    pops = daily.get("precipitation_probability_max", [])
    winds = daily.get("windspeed_10m_max", [])
    codes = daily.get("weathercode", [])

    for idx in range(min(days, len(dates))):
        date_str = dates[idx]
        try:
            dt = datetime.fromisoformat(date_str)
        except ValueError:
            dt = datetime.strptime(date_str, "%Y-%m-%d")

        day_code = codes[idx] if idx < len(codes) else 0
        day_condition, day_icon = OPEN_METEO_CODE_MAP.get(day_code, ("Clear", "☀️"))

        forecast_payload.append(
            {
                "date": dt.strftime("%Y-%m-%d"),
                "day": dt.strftime("%A"),
                "condition": day_condition,
                "description": day_condition,
                "icon": day_icon,
                "temp_min": _safe_round(temps_min[idx]) if idx < len(temps_min) else None,
                "temp_max": _safe_round(temps_max[idx]) if idx < len(temps_max) else None,
                "wind": _safe_round(winds[idx]) if idx < len(winds) else None,
                "humidity": None,
                "precipitation_probability": (
                    _safe_round(pops[idx]) if idx < len(pops) else None
                ),
            }
        )

    return location_name, current_payload, forecast_payload

