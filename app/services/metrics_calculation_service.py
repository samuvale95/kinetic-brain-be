"""
Metrics Calculation Service
Implements TrainingPeaks-style metrics: TSS, IF, TRIMP, CTL, ATL, TSB
"""

import math
from typing import Dict, Any, Optional, List
from datetime import date, datetime, timedelta
import numpy as np


class MetricsCalculationService:
    """
    Calculates training metrics based on TrainingPeaks methodology
    """
    
    def __init__(self):
        # Constants for TSS calculation
        self.TSS_EXPONENT = 1.921
        self.TSS_INTENSITY_CONSTANT = 1.865
        self.NORMALIZATION_CONSTANT = 100
        
    def calculate_intensity_factor(self, 
                                  normalized_power: Optional[float] = None,
                                  avg_power: Optional[float] = None,
                                  avg_hr: Optional[float] = None,
                                  threshold_power: Optional[float] = None,
                                  threshold_hr: Optional[float] = None) -> Optional[float]:
        """
        Calculate Intensity Factor (IF)
        
        For cycling: IF = Normalized Power / Threshold Power
        For HR-based: IF = Avg HR / Threshold HR
        
        Args:
            normalized_power: Normalized power (cycling)
            avg_power: Average power (cycling)
            avg_hr: Average heart rate
            threshold_power: FTP (cycling threshold power)
            threshold_hr: LTHR (heart rate threshold)
        
        Returns:
            Intensity factor (0.0 - 1.5+)
        """
        if normalized_power and threshold_power:
            # Cycling: IF = NP / FTP
            if threshold_power > 0:
                return min(normalized_power / threshold_power, 1.5)
            return None
        elif avg_power and threshold_power:
            # Fallback to avg power
            if threshold_power > 0:
                return min(avg_power / threshold_power, 1.5)
            return None
        elif avg_hr and threshold_hr:
            # HR-based: IF = Avg HR / Threshold HR
            if threshold_hr > 0:
                return min(avg_hr / threshold_hr, 1.5)
            return None
        
        return None
    
    def calculate_normalized_power(self, power_data: List[float], interval_seconds: int = 30) -> float:
        """
        Calculate Normalized Power (cycling)
        
        Args:
            power_data: List of power values in watts
            interval_seconds: Sampling interval (default 30s)
        
        Returns:
            Normalized power in watts
        """
        if not power_data or len(power_data) == 0:
            return 0.0
        
        # Use numpy for efficient calculation
        power_array = np.array(power_data)
        
        # Step 1: Calculate 30-second rolling average
        window_size = max(1, interval_seconds // interval_seconds)
        if len(power_array) >= window_size:
            rolling_avg = np.convolve(power_array, 
                                     np.ones(window_size) / window_size, 
                                     mode='valid')
        else:
            rolling_avg = power_array
        
        # Step 2: Raise to 4th power
        powered = np.power(rolling_avg, 4)
        
        # Step 3: Take 4th root of mean
        if len(powered) > 0:
            normalized_power = np.power(np.mean(powered), 1.0 / 4.0)
        else:
            normalized_power = np.mean(power_array) if len(power_array) > 0 else 0.0
        
        return float(normalized_power)
    
    def calculate_tss(self, 
                     duration_seconds: int,
                     intensity_factor: Optional[float] = None,
                     normalized_power: Optional[float] = None,
                     avg_power: Optional[float] = None,
                     threshold_power: Optional[float] = None) -> float:
        """
        Calculate Training Stress Score (TSS)
        
        TSS = (Duration in hours) × IF × 100
        
        Args:
            duration_seconds: Workout duration in seconds
            intensity_factor: Pre-calculated IF
            normalized_power: NP for cycling
            avg_power: Average power (used if NP not available)
            threshold_power: FTP or threshold power
        
        Returns:
            Training Stress Score (typically 0-200 per workout)
        """
        # Convert seconds to hours
        duration_hours = duration_seconds / 3600.0
        
        # Calculate IF if not provided
        if intensity_factor is None:
            if normalized_power and threshold_power:
                intensity_factor = self.calculate_intensity_factor(
                    normalized_power=normalized_power,
                    threshold_power=threshold_power
                )
            elif avg_power and threshold_power:
                intensity_factor = self.calculate_intensity_factor(
                    avg_power=avg_power,
                    threshold_power=threshold_power
                )
            
            if intensity_factor is None:
                # Default IF if can't calculate
                intensity_factor = 0.7
        
        # TSS formula
        tss = duration_hours * (intensity_factor ** self.TSS_EXPONENT) * self.NORMALIZATION_CONSTANT
        
        return round(tss, 2)
    
    def calculate_trimp(self, 
                       duration_seconds: int,
                       avg_hr: float,
                       max_hr: float,
                       resting_hr: Optional[float] = None) -> float:
        """
        Calculate Training Impulse (TRIMP)
        
        TRIMP = Duration × Intensity Factor
        Where Intensity Factor = Avg HR Reserve × Exp(1.92 × Avg HR Reserve)
        
        Args:
            duration_seconds: Workout duration in seconds
            avg_hr: Average heart rate
            max_hr: Maximum heart rate
            resting_hr: Resting heart rate (defaults to max_hr * 0.5)
        
        Returns:
            TRIMP score
        """
        if resting_hr is None:
            resting_hr = max_hr * 0.5
        
        # Calculate heart rate reserve
        hr_reserve = max_hr - resting_hr
        
        if hr_reserve <= 0:
            return 0.0
        
        # Calculate AVG HR Reserve as a fraction
        avg_hr_reserve = (avg_hr - resting_hr) / hr_reserve
        
        # Cap at 1.0 (100%)
        avg_hr_reserve = min(avg_hr_reserve, 1.0)
        
        # TRIMP formula
        intensity_factor = avg_hr_reserve * math.exp(1.92 * avg_hr_reserve)
        
        # Convert seconds to minutes for TRIMP
        duration_minutes = duration_seconds / 60.0
        
        trimp = duration_minutes * intensity_factor
        
        return round(trimp, 2)
    
    def calculate_time_in_zones(self,
                               hr_data: Optional[List[float]] = None,
                               zones: Dict[str, Dict[str, float]] = None,
                               duration_seconds: int = 0,
                               avg_hr: Optional[float] = None) -> Dict[str, int]:
        """
        Calculate time spent in each training zone
        
        Args:
            hr_data: List of heart rate values
            zones: Zone definitions with min/max for each zone
            duration_seconds: Total duration
            avg_hr: Average heart rate (used if hr_data not available)
        
        Returns:
            Dictionary with time in each zone (minutes)
        """
        result = {
            'z1': 0,
            'z2': 0,
            'z3': 0,
            'z4': 0,
            'z5': 0
        }
        
        # If no zones provided, return zeros
        if zones is None:
            return result
        
        duration_minutes = duration_seconds / 60.0
        
        # If we have detailed HR data
        if hr_data and len(hr_data) > 0:
            for hr_value in hr_data:
                for zone_idx in range(1, 6):
                    zone_key = f"z{zone_idx}"
                    if zone_key in zones:
                        zone_min = zones[zone_key].get('min', 0)
                        zone_max = zones[zone_key].get('max', 999)
                        
                        if zone_min <= hr_value <= zone_max:
                            # Increment time for this zone
                            # Assuming each data point represents the same time
                            increment = duration_minutes / len(hr_data)
                            result[zone_key] += increment
                            break
        
        # Fallback: estimate based on average HR
        elif avg_hr is not None and zones:
            for zone_idx in range(1, 6):
                zone_key = f"z{zone_idx}"
                if zone_key in zones:
                    zone_min = zones[zone_key].get('min', 0)
                    zone_max = zones[zone_key].get('max', 999)
                    
                    if zone_min <= avg_hr <= zone_max:
                        # Assume all time in this zone
                        result[zone_key] = int(duration_minutes)
                        break
        
        return {k: int(v) for k, v in result.items()}
    
    def calculate_ctl_atl_tsb(self,
                              daily_tss: List[float],
                              ctl_days: int = 42,
                              atl_days: int = 7,
                              include_rest_days: bool = True) -> Dict[str, float]:
        """
        Calculate CTL (Chronic Training Load), ATL (Acute Training Load), and TSB (Training Stress Balance)
        
        Uses exponential moving average with time constants:
        - CTL: 42 days (fitness)
        - ATL: 7 days (fatigue)
        - TSB: CTL - ATL (form)
        
        IMPORTANT: If include_rest_days=True, the algorithm considers ALL days in the period,
        including days with 0 TSS (rest days), which is crucial for accurate decay calculation.
        
        Args:
            daily_tss: List of TSS values, most recent first (should include ALL days)
            ctl_days: Time constant for CTL (default 42)
            atl_days: Time constant for ATL (default 7)
            include_rest_days: If True, treats 0 TSS days as rest days (decay calculation)
        
        Returns:
            Dictionary with 'ctl', 'atl', 'tsb'
        """
        # Calculate exponential smoothing constants
        ctl_tc = ctl_days / 7.0  # time constant in weeks
        atl_tc = atl_days / 7.0   # time constant in weeks
        
        # Exponential smoothing factor
        ctl_lambda = 1.0 - math.exp(-1.0 / ctl_tc)
        atl_lambda = 1.0 - math.exp(-1.0 / atl_tc)
        
        # IMPORTANT: Initialize with OLDEST value (last in list since it's "most recent first")
        # We need to process from OLDEST to NEWEST to get today's state
        ctl = daily_tss[-1] if len(daily_tss) > 0 else 0.0
        atl = daily_tss[-1] if len(daily_tss) > 0 else 0.0
        
        # Apply exponential moving average from OLDEST to NEWEST
        # Reverse the list to process from oldest (42 days ago) to most recent (today)
        for tss in reversed(daily_tss[:-1]):
            # Apply decay even on rest days (TSS=0)
            # This is the correct TrainingPeaks methodology
            ctl = ctl + (tss - ctl) * ctl_lambda
            atl = atl + (tss - atl) * atl_lambda
        
        # TSB = CTL - ATL
        tsb = ctl - atl
        
        return {
            'ctl': round(ctl, 2),
            'atl': round(atl, 2),
            'tsb': round(tsb, 2)
        }
    
    def get_tsb_status(self, tsb: float) -> str:
        """
        Determine TSB status based on value
        
        Args:
            tsb: Training Stress Balance
        
        Returns:
            'fresh', 'optimal', or 'fatigued'
        """
        if tsb > 10:
            return 'fresh'
        elif tsb < -10:
            return 'fatigued'
        else:
            return 'optimal'
    
    def get_tsb_color(self, tsb: float) -> str:
        """
        Get color for TSB indicator
        
        Args:
            tsb: Training Stress Balance
        
        Returns:
            'green', 'yellow', or 'red'
        """
        if tsb > 10:
            return 'green'
        elif tsb < -10:
            return 'red'
        else:
            return 'yellow'
    
    def calculate_weekly_metrics_summary(self,
                                        daily_tss: List[float],
                                        daily_duration: List[float],
                                        ctl: float,
                                        atl: float,
                                        tsb: float) -> Dict[str, Any]:
        """
        Calculate summary metrics for a week
        
        Args:
            daily_tss: TSS for each day of the week
            daily_duration: Duration in hours for each day
            ctl: Chronic Training Load
            atl: Acute Training Load
            tsb: Training Stress Balance
        
        Returns:
            Summary dictionary
        """
        weekly_tss = sum(daily_tss)
        weekly_hours = sum(daily_duration)
        
        # Calculate trends
        avg_daily_tss = weekly_tss / len(daily_tss) if daily_tss else 0
        training_frequency = len([t for t in daily_tss if t > 0])
        
        return {
            'weekly_tss': round(weekly_tss, 2),
            'weekly_hours': round(weekly_hours, 2),
            'avg_daily_tss': round(avg_daily_tss, 2),
            'training_frequency': training_frequency,
            'ctl': ctl,
            'atl': atl,
            'tsb': tsb,
            'tsb_status': self.get_tsb_status(tsb),
            'tsb_color': self.get_tsb_color(tsb)
        }

