from typing import Dict, Any, Optional
from app.utils.calculations import (
    calculate_hr_zones, 
    calculate_pace_zones, 
    calculate_power_zones,
    calculate_wkg,
    calculate_training_load,
    convert_zones_to_string_format,
    parse_pace_string
)
from datetime import datetime


class CalculationService:
    """Service for calculating training zones and metrics"""
    
    
    @staticmethod
    def calculate_zones_string_format(metric_type: str, 
                                     threshold_value: Optional[float] = None,
                                     threshold_hr: Optional[float] = None,
                                     hr_max: Optional[float] = None,
                                     hr_rest: Optional[float] = None,
                                     threshold_pace: Optional[str] = None,
                                     ftp: Optional[float] = None) -> Dict[str, Any]:
        """Calculate training zones and return in string format (z1-z5/z7 with ranges)"""
        
        if metric_type == "hr":
            if threshold_hr is None:
                threshold_hr = threshold_value
            if threshold_hr is None:
                raise ValueError("threshold_hr or threshold_value required for HR zones")
            
            zones = calculate_hr_zones(threshold_hr, hr_max, hr_rest)
            zones_string = convert_zones_to_string_format(zones, "hr")
            
            return {
                "hr_zones": zones_string,
                "hr_zones_source": "auto",
                "hr_threshold_used": threshold_hr
            }
        
        elif metric_type == "pace":
            if threshold_pace:
                threshold_pace_float = parse_pace_string(threshold_pace)
            elif threshold_value:
                threshold_pace_float = threshold_value
            else:
                raise ValueError("threshold_pace or threshold_value required for pace zones")
            
            # Estimate max pace if needed
            max_pace = threshold_pace_float * 0.8
            zones = calculate_pace_zones(threshold_pace_float, max_pace)
            zones_string = convert_zones_to_string_format(zones, "pace")
            
            return {
                "pace_zones": zones_string,
                "pace_zones_source": "auto",
                "threshold_pace_used": threshold_pace if threshold_pace else f"{int(threshold_pace_float)}:{int((threshold_pace_float - int(threshold_pace_float)) * 60):02d}"
            }
        
        elif metric_type == "power":
            if ftp is None:
                ftp = threshold_value
            if ftp is None:
                raise ValueError("ftp or threshold_value required for power zones")
            
            # Calculate 7-zone Coggan/Allen system
            zones = {
                "Z1": {"min": 0, "max": ftp * 0.55},
                "Z2": {"min": ftp * 0.55, "max": ftp * 0.75},
                "Z3": {"min": ftp * 0.75, "max": ftp * 0.90},
                "Z4": {"min": ftp * 0.90, "max": ftp * 1.05},
                "Z5": {"min": ftp * 1.05, "max": ftp * 1.20},
                "Z6": {"min": ftp * 1.20, "max": ftp * 1.50},
                "Z7": {"min": ftp * 1.50, "max": ftp * 2.00}
            }
            zones_string = convert_zones_to_string_format(zones, "power")
            
            return {
                "power_zones": zones_string,
                "power_zones_source": "auto",
                "ftp_used": ftp
            }
        
        else:
            raise ValueError(f"Unsupported metric type: {metric_type}")
    
    @staticmethod
    def calculate_workout_metrics(workout_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate additional metrics for a workout"""
        metrics = {}
        
        # Calculate watts per kg if power and weight are available
        if "avg_power" in workout_data and "weight" in workout_data:
            metrics["wkg"] = calculate_wkg(
                workout_data["avg_power"], 
                workout_data["weight"]
            )
        
        # Calculate training load if HR data is available
        if all(key in workout_data for key in ["avg_hr", "max_hr", "duration_minutes"]):
            metrics["training_load"] = calculate_training_load(
                workout_data["avg_hr"],
                workout_data["max_hr"], 
                workout_data["duration_minutes"]
            )
        
        # Calculate pace from speed if needed
        if "avg_speed_kmh" in workout_data and "avg_pace" not in workout_data:
            from app.utils.calculations import calculate_pace_from_speed
            metrics["avg_pace"] = calculate_pace_from_speed(workout_data["avg_speed_kmh"])
        
        return metrics
    
    @staticmethod
    def validate_zone_data(zone_data: Dict[str, Any]) -> bool:
        """Validate that zone data is properly structured"""
        required_zones = ["Z1", "Z2", "Z3", "Z4", "Z5"]
        
        if not all(zone in zone_data for zone in required_zones):
            return False
        
        for zone in required_zones:
            zone_info = zone_data[zone]
            if not all(key in zone_info for key in ["min", "max"]):
                return False
            
            if zone_info["min"] >= zone_info["max"]:
                return False
        
        return True
    
    @staticmethod
    def get_zone_for_value(value: float, zones: Dict[str, Any]) -> Optional[str]:
        """Determine which zone a value falls into"""
        for zone_name, zone_data in zones.items():
            if zone_data["min"] <= value <= zone_data["max"]:
                return zone_name
        return None
