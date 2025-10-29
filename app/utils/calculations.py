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


def format_hr_zone_string(min_hr: float, max_hr: float) -> str:
    """Format HR zone as string 'min-max'"""
    return f"{int(min_hr)}-{int(max_hr)}"


def format_pace_zone_string(min_pace: float, max_pace: float) -> str:
    """Format pace zone as string 'mm:ss-mm:ss'"""
    def pace_to_string(pace_min: float) -> str:
        minutes = int(pace_min)
        seconds = int((pace_min - minutes) * 60)
        return f"{minutes}:{seconds:02d}"
    
    return f"{pace_to_string(min_pace)}-{pace_to_string(max_pace)}"


def format_power_zone_string(min_power: float, max_power: float) -> str:
    """Format power zone as string 'min-max'"""
    return f"{int(min_power)}-{int(max_power)}"


def convert_zones_to_string_format(zones: Dict[str, Dict[str, float]], metric_type: str) -> Dict[str, str]:
    """
    Convert zones from old format (Z1-Z5 with min/max) to new format (z1-z5 with string ranges)
    """
    result = {}
    
    if metric_type == "hr":
        for zone_name, zone_data in zones.items():
            zone_key = zone_name.lower()  # Z1 -> z1
            result[zone_key] = format_hr_zone_string(zone_data["min"], zone_data["max"])
    elif metric_type == "pace":
        for zone_name, zone_data in zones.items():
            zone_key = zone_name.lower()
            result[zone_key] = format_pace_zone_string(zone_data["min"], zone_data["max"])
    elif metric_type == "power":
        for zone_name, zone_data in zones.items():
            zone_key = zone_name.lower()
            result[zone_key] = format_power_zone_string(zone_data["min"], zone_data["max"])
    
    return result


def _parse_range_to_min_max(range_str: str) -> Dict[str, float]:
    """
    Parse a generic numeric range string like "139-153" into a dict with min/max floats.
    Gracefully handles extra spaces.
    """
    parts = [p.strip() for p in range_str.split("-")]
    if len(parts) != 2:
        return {"min": 0.0, "max": 0.0}
    try:
        return {"min": float(parts[0]), "max": float(parts[1])}
    except ValueError:
        return {"min": 0.0, "max": 0.0}


def _parse_pace_range_to_min_max(range_str: str) -> Dict[str, float]:
    """
    Parse a pace range like "5:00-4:45" into numeric minutes per km min/max.
    """
    parts = [p.strip() for p in range_str.split("-")]
    if len(parts) != 2:
        return {"min": 0.0, "max": 0.0}
    try:
        return {"min": parse_pace_string(parts[0]), "max": parse_pace_string(parts[1])}
    except Exception:
        return {"min": 0.0, "max": 0.0}


def convert_zones_string_to_structured(zones: Dict[str, str], metric_type: str) -> Dict[str, Dict[str, float | str]]:
    """
    Convert zones from string range format (e.g., {"z1": "139-153"}) to structured dict
    with numeric min/max and a description field.
    Keys are preserved (e.g., "z1".."z5").
    """
    descriptions_hr = {
        "z1": "Recovery",
        "z2": "Aerobic Base",
        "z3": "Aerobic Threshold",
        "z4": "Lactate Threshold",
        "z5": "VO2 Max",
    }
    descriptions_pace = descriptions_hr
    descriptions_power = descriptions_hr

    result: Dict[str, Dict[str, float | str]] = {}
    for key, value in zones.items():
        key_lower = key.lower()
        if metric_type == "pace":
            mm = _parse_pace_range_to_min_max(value)
            desc = descriptions_pace.get(key_lower)
        else:
            mm = _parse_range_to_min_max(value)
            desc = descriptions_power.get(key_lower) if metric_type == "power" else descriptions_hr.get(key_lower)
        zone_struct = {"min": mm["min"], "max": mm["max"]}
        if desc:
            zone_struct["description"] = desc
        result[key_lower] = zone_struct
    return result


def parse_pace_string(pace_str: str) -> float:
    """
    Parse pace string format "mm:ss" or "mm.ss" to minutes (float)
    Returns pace in minutes per km
    """
    pace_str = pace_str.strip()
    
    # Support both ":" and "." separators
    if ":" in pace_str:
        parts = pace_str.split(":")
    elif "." in pace_str:
        parts = pace_str.split(".")
    else:
        raise ValueError(f"Invalid pace format: {pace_str}")
    
    if len(parts) != 2:
        raise ValueError(f"Invalid pace format: {pace_str}")
    
    try:
        minutes = int(parts[0])
        seconds = int(parts[1])
        
        if seconds < 0 or seconds >= 60:
            raise ValueError(f"Seconds must be 0-59: {pace_str}")
        
        return minutes + (seconds / 60.0)
    except ValueError as e:
        raise ValueError(f"Invalid pace format: {pace_str}") from e
