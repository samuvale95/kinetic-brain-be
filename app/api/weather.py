from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
import os
import httpx
from app.database import get_db
from app.api.auth import get_current_user
from app.models.user import User, UserProfile

router = APIRouter(prefix="/api/weather", tags=["weather"])

# Cache for weather data (in-memory, 30 minutes)
_weather_cache = {}
_cache_duration = timedelta(minutes=30)


@router.options("/")
async def options_weather():
    """Handle OPTIONS request for CORS preflight"""
    return Response(status_code=200)


@router.get("/")
async def get_weather(
    lat: Optional[float] = Query(None, description="Latitude"),
    lon: Optional[float] = Query(None, description="Longitude"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get weather information for user's location"""
    user_id = current_user["user_id"]
    
    # Get API key from environment (optional for Open-Meteo, required for OpenWeatherMap)
    api_key = os.getenv("WEATHER_API_KEY")
    use_openweather = api_key is not None
    
    # Try to get user's location from profile (coordinates take priority)
    city = None
    profile_lat = None
    profile_lon = None
    
    from app.models.user import UserProfile
    user_profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if user_profile:
        if user_profile.city:
            city = user_profile.city
        if user_profile.latitude is not None and user_profile.longitude is not None:
            profile_lat = user_profile.latitude
            profile_lon = user_profile.longitude
    
    # Check cache first
    cache_key = f"{city}_{lat}_{lon}_{datetime.now().replace(minute=0, second=0, microsecond=0).isoformat()}"
    if cache_key in _weather_cache:
        cached_data = _weather_cache[cache_key]
        if datetime.now() - cached_data.get("timestamp", datetime.min) < _cache_duration:
            return cached_data["data"]
    
    # Determine location to use (priority: query params > profile coords > city > default)
    location_query = None
    use_lat = lat
    use_lon = lon
    
    # If no coordinates in request, try from profile
    if not use_lat or not use_lon:
        if profile_lat is not None and profile_lon is not None:
            use_lat = profile_lat
            use_lon = profile_lon
    
    if use_lat and use_lon:
        location_query = f"lat={use_lat}&lon={use_lon}"
    elif city:
        location_query = f"q={city}"
    else:
        # Default to Rome if no location provided
        location_query = "q=Rome"
    
    # Call weather API
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            if use_openweather:
                # OpenWeatherMap API
                url = f"http://api.openweathermap.org/data/2.5/weather?{location_query}&appid={api_key}&units=metric&lang=it"
            else:
                # Open-Meteo API (free, no registration needed)
                if use_lat and use_lon:
                    url = f"https://api.open-meteo.com/v1/forecast?latitude={use_lat}&longitude={use_lon}&current_weather=true&hourly=relativehumidity_2m&timezone=auto"
                else:
                    # Default to Rome if no coordinates
                    url = "https://api.open-meteo.com/v1/forecast?latitude=41.9028&longitude=12.4964&current_weather=true&hourly=relativehumidity_2m&timezone=auto"
            
            response = await client.get(url)
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Weather service unavailable"
                )
            
            data = response.json()
            
            # Map weather conditions to emojis
            condition_emoji = {
                "Clear": "☀️",
                "Clouds": "☁️",
                "Rain": "🌧️",
                "Drizzle": "🌦️",
                "Thunderstorm": "⛈️",
                "Snow": "❄️",
                "Mist": "🌫️",
                "Fog": "🌫️",
                "Haze": "🌫️"
            }
            
            if use_openweather:
                # OpenWeatherMap response format
                weather_main = data["weather"][0]["main"]
                icon = condition_emoji.get(weather_main, "☀️")
                
                # Format response
                weather_response = {
                    "city": data["name"],
                    "temp": round(data["main"]["temp"]),
                    "condition": weather_main,
                    "description": data["weather"][0]["description"].title(),
                    "wind": round(data.get("wind", {}).get("speed", 0) * 3.6),  # Convert m/s to km/h
                    "humidity": data["main"]["humidity"],
                    "icon": icon
                }
            else:
                # Open-Meteo response format
                current = data.get("current_weather", {})
                weather_code = current.get("weathercode", 0)
                
                # Map weather codes to conditions
                code_to_condition = {
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
                    99: ("Thunderstorm", "⛈️")
                }
                
                condition, icon = code_to_condition.get(weather_code, ("Clear", "☀️"))
                
                # Use city from profile or coordinates
                location_name = city or f"{use_lat:.1f}, {use_lon:.1f}"
                
                # Get humidity from hourly data (current hour)
                humidity = None
                if "hourly" in data and "relativehumidity_2m" in data["hourly"]:
                    humidity_values = data["hourly"]["relativehumidity_2m"]
                    # Get first value (current hour) or average
                    if humidity_values and len(humidity_values) > 0:
                        humidity = round(humidity_values[0])
                
                weather_response = {
                    "city": location_name,
                    "temp": round(current.get("temperature", 0)),
                    "condition": condition,
                    "description": condition,
                    "wind": round(current.get("windspeed", 0) * 3.6),  # Convert km/h
                    "humidity": humidity,
                    "icon": icon
                }
            
            # Cache the result
            _weather_cache[cache_key] = {
                "data": weather_response,
                "timestamp": datetime.now()
            }
            
            return weather_response
            
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Weather service timeout"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Weather service error: {str(e)}"
        )

