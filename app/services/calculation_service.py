from typing import Dict, Any, Optional
from app.utils.calculations import (
    calculate_hr_zones, 
    calculate_pace_zones, 
    calculate_power_zones,
    calculate_wkg,
    calculate_training_load
)
from datetime import datetime


class CalculationService:
    """Service for calculating training zones and metrics"""
    
    @staticmethod
    def calculate_zones(metric_type: str, threshold_value: float, 
                       max_value: Optional[float] = None, 
                       rest_value: Optional[float] = None) -> Dict[str, Any]:
        """Calculate training zones based on metric type"""
        
        if metric_type == "hr":
            zones = calculate_hr_zones(threshold_value, max_value, rest_value)
        elif metric_type == "pace":
            zones = calculate_pace_zones(threshold_value, max_value)
        elif metric_type == "power":
            zones = calculate_power_zones(threshold_value, max_value)
        else:
            raise ValueError(f"Unsupported metric type: {metric_type}")
        
        return {
            "zones": zones,
            "calculated_at": datetime.utcnow().isoformat(),
            "metric_type": metric_type,
            "threshold_value": threshold_value
        }
    
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
