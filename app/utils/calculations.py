from typing import Dict, Any, Optional
from datetime import datetime


def calculate_hr_zones(threshold_hr: float, max_hr: Optional[float] = None, rest_hr: Optional[float] = None) -> Dict[str, Dict[str, float]]:
    """
    Calculate heart rate zones based on threshold HR
    Uses Joe Friel's 5-zone system
    """
    if max_hr is None:
        max_hr = threshold_hr * 1.1  # Estimate max HR if not provided
    
    if rest_hr is None:
        rest_hr = 50  # Default resting HR
    
    hr_reserve = max_hr - rest_hr
    
    zones = {
        "Z1": {
            "min": rest_hr + (hr_reserve * 0.65),
            "max": rest_hr + (hr_reserve * 0.75),
            "description": "Recovery"
        },
        "Z2": {
            "min": rest_hr + (hr_reserve * 0.75),
            "max": rest_hr + (hr_reserve * 0.85),
            "description": "Aerobic Base"
        },
        "Z3": {
            "min": rest_hr + (hr_reserve * 0.85),
            "max": rest_hr + (hr_reserve * 0.95),
            "description": "Aerobic Threshold"
        },
        "Z4": {
            "min": rest_hr + (hr_reserve * 0.95),
            "max": threshold_hr,
            "description": "Lactate Threshold"
        },
        "Z5": {
            "min": threshold_hr,
            "max": max_hr,
            "description": "VO2 Max"
        }
    }
    
    return zones


def calculate_pace_zones(threshold_pace: float, max_pace: Optional[float] = None) -> Dict[str, Dict[str, float]]:
    """
    Calculate pace zones based on threshold pace (min/km)
    """
    if max_pace is None:
        max_pace = threshold_pace * 0.8  # Estimate max pace if not provided
    
    zones = {
        "Z1": {
            "min": threshold_pace * 1.3,
            "max": threshold_pace * 1.2,
            "description": "Recovery"
        },
        "Z2": {
            "min": threshold_pace * 1.2,
            "max": threshold_pace * 1.1,
            "description": "Aerobic Base"
        },
        "Z3": {
            "min": threshold_pace * 1.1,
            "max": threshold_pace * 1.05,
            "description": "Aerobic Threshold"
        },
        "Z4": {
            "min": threshold_pace * 1.05,
            "max": threshold_pace,
            "description": "Lactate Threshold"
        },
        "Z5": {
            "min": threshold_pace,
            "max": max_pace,
            "description": "VO2 Max"
        }
    }
    
    return zones


def calculate_power_zones(ftp: float, max_power: Optional[float] = None) -> Dict[str, Dict[str, float]]:
    """
    Calculate power zones based on FTP (Functional Threshold Power)
    Uses Andy Coggan's 7-zone system adapted to 5 zones
    """
    if max_power is None:
        max_power = ftp * 1.2  # Estimate max power if not provided
    
    zones = {
        "Z1": {
            "min": 0,
            "max": ftp * 0.55,
            "description": "Recovery"
        },
        "Z2": {
            "min": ftp * 0.55,
            "max": ftp * 0.75,
            "description": "Aerobic Base"
        },
        "Z3": {
            "min": ftp * 0.75,
            "max": ftp * 0.90,
            "description": "Aerobic Threshold"
        },
        "Z4": {
            "min": ftp * 0.90,
            "max": ftp * 1.05,
            "description": "Lactate Threshold"
        },
        "Z5": {
            "min": ftp * 1.05,
            "max": max_power,
            "description": "VO2 Max"
        }
    }
    
    return zones


def calculate_wkg(power: float, weight: float) -> float:
    """
    Calculate watts per kilogram
    """
    if weight <= 0:
        return 0.0
    return power / weight


def calculate_training_load(avg_hr: float, max_hr: float, duration_minutes: int) -> float:
    """
    Calculate training load using TRIMP (Training Impulse)
    """
    if max_hr <= 0 or duration_minutes <= 0:
        return 0.0
    
    hr_ratio = avg_hr / max_hr
    trimp = duration_minutes * hr_ratio * 0.64 * (2.718 ** (1.92 * hr_ratio))
    return round(trimp, 2)


def calculate_pace_from_speed(speed_kmh: float) -> float:
    """
    Convert speed (km/h) to pace (min/km)
    """
    if speed_kmh <= 0:
        return 0.0
    return 60.0 / speed_kmh


def calculate_speed_from_pace(pace_min_km: float) -> float:
    """
    Convert pace (min/km) to speed (km/h)
    """
    if pace_min_km <= 0:
        return 0.0
    return 60.0 / pace_min_km
