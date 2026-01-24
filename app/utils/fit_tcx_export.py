"""
Utility for exporting workouts to FIT and TCX formats
"""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
from loguru import logger


def export_to_tcx(workout_data: Dict[str, Any], user_profile: Optional[Dict[str, Any]] = None) -> bytes:
    """
    Export workout to TCX (Training Center XML) format.
    
    Args:
        workout_data: Workout data with structure_json
        user_profile: Optional user profile for zones
    
    Returns:
        TCX file content as bytes
    """
    # Create TCX root
    root = ET.Element("TrainingCenterDatabase", {
        "xmlns": "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2",
        "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
        "xsi:schemaLocation": "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2 "
                               "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2 "
                               "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2 "
                               "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"
    })
    
    activities = ET.SubElement(root, "Activities")
    activity = ET.SubElement(activities, "Activity", Sport=workout_data.get("sport_type", "Running").capitalize())
    
    # Activity ID (timestamp)
    activity_id = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    ET.SubElement(activity, "Id").text = activity_id
    
    # Create lap
    lap = ET.SubElement(activity, "Lap", StartTime=activity_id)
    
    # Total time (in seconds)
    duration_seconds = workout_data.get("duration_minutes", 60) * 60
    ET.SubElement(lap, "TotalTimeSeconds").text = str(duration_seconds)
    
    # Distance (estimate based on sport and duration)
    distance_meters = _estimate_distance(workout_data.get("sport_type", "run"), duration_seconds)
    ET.SubElement(lap, "DistanceMeters").text = str(distance_meters)
    
    # Maximum speed (estimate)
    max_speed = distance_meters / duration_seconds if duration_seconds > 0 else 0
    ET.SubElement(lap, "MaximumSpeed").text = f"{max_speed:.2f}"
    
    # Calories (estimate)
    calories = _estimate_calories(workout_data.get("sport_type", "run"), duration_seconds)
    ET.SubElement(lap, "Calories").text = str(calories)
    
    # Average heart rate (if available from zones)
    avg_hr = _get_zone_heart_rate(workout_data.get("zone", "Z2"), user_profile)
    if avg_hr:
        avg_hr_elem = ET.SubElement(lap, "AverageHeartRateBpm")
        ET.SubElement(avg_hr_elem, "Value").text = str(avg_hr)
    
    # Intensity
    intensity_map = {"easy": "Active", "moderate": "Active", "hard": "Active"}
    intensity = intensity_map.get(workout_data.get("intensity", "moderate"), "Active")
    ET.SubElement(lap, "Intensity").text = intensity
    
    # Trigger method
    ET.SubElement(lap, "TriggerMethod").text = "Manual"
    
    # Track (for GPS data simulation)
    track = ET.SubElement(lap, "Track")
    
    # Create trackpoints based on workout structure
    structure = workout_data.get("structure_json") or {}
    segments = structure.get("segments", [])
    
    current_time = datetime.now()
    elapsed_seconds = 0
    
    for segment in segments:
        segment_type = segment.get("segment_type", "main")
        steps = segment.get("steps", [])
        
        for step in steps:
            step_duration = _get_step_duration_seconds(step)
            if step_duration > 0:
                # Create trackpoint for step start
                trackpoint = ET.SubElement(track, "Trackpoint")
                ET.SubElement(trackpoint, "Time").text = (current_time + timedelta(seconds=elapsed_seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")
                
                # Position (simulated - in real app would use GPS)
                position = ET.SubElement(trackpoint, "Position")
                ET.SubElement(position, "LatitudeDegrees").text = "0.0"
                ET.SubElement(position, "LongitudeDegrees").text = "0.0"
                
                # Altitude
                ET.SubElement(trackpoint, "AltitudeMeters").text = "0.0"
                
                # Distance
                step_distance = _estimate_distance(workout_data.get("sport_type", "run"), step_duration)
                ET.SubElement(trackpoint, "DistanceMeters").text = str(int(elapsed_seconds * max_speed))
                
                # Heart rate (from zone)
                step_zone = _get_step_zone(step, workout_data.get("zone", "Z2"))
                step_hr = _get_zone_heart_rate(step_zone, user_profile)
                if step_hr:
                    hr_elem = ET.SubElement(trackpoint, "HeartRateBpm")
                    ET.SubElement(hr_elem, "Value").text = str(step_hr)
                
                elapsed_seconds += step_duration
    
    # Add final trackpoint
    if elapsed_seconds > 0:
        trackpoint = ET.SubElement(track, "Trackpoint")
        ET.SubElement(trackpoint, "Time").text = (current_time + timedelta(seconds=elapsed_seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")
        position = ET.SubElement(trackpoint, "Position")
        ET.SubElement(position, "LatitudeDegrees").text = "0.0"
        ET.SubElement(position, "LongitudeDegrees").text = "0.0"
        ET.SubElement(trackpoint, "AltitudeMeters").text = "0.0"
        ET.SubElement(trackpoint, "DistanceMeters").text = str(distance_meters)
    
    # Notes
    notes = ET.SubElement(activity, "Notes")
    notes.text = workout_data.get("title", "Workout")
    
    # Convert to XML string
    xml_str = ET.tostring(root, encoding='utf-8', xml_declaration=True)
    return xml_str


def export_to_fit(workout_data: Dict[str, Any], user_profile: Optional[Dict[str, Any]] = None) -> bytes:
    """
    Export workout to FIT format.
    Note: FIT is a binary format. For a full implementation, use fitfile library.
    This is a simplified version that creates a basic FIT file structure.
    
    Args:
        workout_data: Workout data with structure_json
        user_profile: Optional user profile for zones
    
    Returns:
        FIT file content as bytes (simplified)
    """
    # FIT format is complex binary format. For production, use:
    # from fitfile import FitFile, messages
    # 
    # For now, return a basic structure that can be enhanced
    logger.warning("FIT export is simplified - consider using fitfile library for full support")
    
    # Basic FIT file structure (simplified)
    # In production, use proper FIT SDK or fitfile library
    fit_data = bytearray()
    
    # FIT file header (14 bytes)
    # File header structure:
    # - Header size (1 byte): 14
    # - Protocol version (1 byte): 0x20
    # - Profile version (2 bytes): 0x0100
    # - Data size (4 bytes): size of data records
    # - Data type (4 bytes): ".FIT"
    # - CRC (2 bytes): header CRC
    
    header_size = 14
    protocol_version = 0x20
    profile_version = 0x0100
    data_type = b".FIT"
    
    # For now, return a placeholder
    # In production, implement full FIT file generation using fitfile library
    logger.info("FIT export placeholder - implement with fitfile library")
    
    # Return minimal FIT structure
    return fit_data


def _estimate_distance(sport_type: str, duration_seconds: int) -> float:
    """Estimate distance in meters based on sport and duration"""
    # Average speeds (m/s)
    speeds = {
        "run": 3.0,  # ~10.8 km/h
        "bike": 8.0,  # ~28.8 km/h
        "swim": 1.0,  # ~3.6 km/h
        "triathlon": 3.0,
    }
    
    speed = speeds.get(sport_type.lower(), 3.0)
    return speed * duration_seconds


def _estimate_calories(sport_type: str, duration_seconds: int) -> int:
    """Estimate calories burned"""
    # Calories per minute (rough estimates)
    calories_per_min = {
        "run": 10,
        "bike": 8,
        "swim": 12,
        "triathlon": 10,
    }
    
    rate = calories_per_min.get(sport_type.lower(), 10)
    return int(rate * (duration_seconds / 60))


def _get_zone_heart_rate(zone: str, user_profile: Optional[Dict[str, Any]]) -> Optional[int]:
    """Get heart rate for a zone"""
    if not user_profile:
        # Default heart rates (estimate)
        default_zones = {
            "Z1": 120,
            "Z2": 140,
            "Z3": 160,
            "Z4": 175,
            "Z5": 190,
        }
        return default_zones.get(zone.upper(), 140)
    
    # Try to get from user profile
    hr_zones = user_profile.get("hr_zones", {})
    zone_lower = zone.lower()
    
    if zone_lower in hr_zones:
        zone_str = hr_zones[zone_lower]
        # Parse zone string like "120-135" or "140-150"
        if "-" in zone_str:
            parts = zone_str.split("-")
            if len(parts) == 2:
                try:
                    min_hr = int(parts[0].strip())
                    max_hr = int(parts[1].strip())
                    return (min_hr + max_hr) // 2
                except ValueError:
                    pass
    
    return 140  # Default


def _get_step_duration_seconds(step: Dict[str, Any]) -> int:
    """Get duration of a step in seconds"""
    duration = step.get("duration", {})
    if isinstance(duration, dict):
        if duration.get("type") == "time" and duration.get("seconds"):
            return duration["seconds"]
        elif duration.get("type") == "distance" and duration.get("meters"):
            # Estimate time from distance (simplified)
            return int(duration["meters"] / 3.0)  # Assume 3 m/s average
    return 0


def _get_step_zone(step: Dict[str, Any], default_zone: str) -> str:
    """Get zone from step target"""
    target = step.get("target", {})
    if isinstance(target, dict) and target.get("type") == "zone":
        return target.get("zone", default_zone)
    return default_zone
