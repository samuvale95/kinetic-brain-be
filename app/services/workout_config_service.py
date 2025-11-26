"""
Servizio helper per gestire la configurazione dei workout
"""
from typing import Optional, List
from app.services.workout_parameters import (
    WORKOUT_PARAMETERS,
    SportWorkoutConfig,
    PhaseConfig,
    WorkoutTypeConfig,
    normalize_sport_type,
    get_default_sport_config
)
from loguru import logger


class WorkoutConfigService:
    """Servizio per gestire la configurazione dei workout"""
    
    @staticmethod
    def determine_phase(weeks_remaining: Optional[int], week_phase: Optional[str] = None) -> str:
        """
        Determina la fase di allenamento (BASE/BUILD/PEAK/TAPER)
        
        Args:
            weeks_remaining: Settimane rimanenti alla gara
            week_phase: Fase esplicita (opzionale, prevale su weeks_remaining)
        
        Returns:
            Fase: "BASE", "BUILD", "PEAK", o "TAPER"
        """
        if week_phase:
            phase_upper = week_phase.upper()
            if phase_upper in ["BASE", "BUILD", "PEAK", "TAPER"]:
                return phase_upper
        
        if weeks_remaining is None:
            return "BASE"
        
        if weeks_remaining > 12:
            return "BASE"
        elif weeks_remaining > 8:
            return "BUILD"
        elif weeks_remaining > 4:
            return "PEAK"
        else:
            return "TAPER"
    
    @staticmethod
    def get_workout_config(
        sport_type: str,
        phase: str,
        workout_type: str  # "stretching" o "strength"
    ) -> Optional[WorkoutTypeConfig]:
        """
        Restituisce configurazione per sport/fase/tipo
        
        Args:
            sport_type: Tipo di sport (running, cycling, etc.)
            phase: Fase (BASE, BUILD, PEAK, TAPER)
            workout_type: Tipo workout ("stretching" o "strength")
        
        Returns:
            WorkoutTypeConfig o None se non trovato
        """
        normalized_sport = normalize_sport_type(sport_type)
        sport_config = WORKOUT_PARAMETERS.get(normalized_sport, get_default_sport_config())
        
        phase_config = sport_config.phases.get(phase.upper())
        if not phase_config:
            logger.warning(f"Phase {phase} not found for sport {normalized_sport}, using BASE")
            phase_config = sport_config.phases.get("BASE")
            if not phase_config:
                return None
        
        if workout_type.lower() == "stretching":
            return phase_config.stretching
        elif workout_type.lower() == "strength":
            return phase_config.strength
        else:
            logger.error(f"Invalid workout_type: {workout_type}")
            return None
    
    @staticmethod
    def calculate_sessions_per_week(
        frequency_config,
        available_days: Optional[List[str]] = None
    ) -> int:
        """
        Calcola numero di sessioni per settimana in base a giorni disponibili e config
        
        Args:
            frequency_config: WorkoutFrequencyConfig
            available_days: Lista giorni disponibili (opzionale, default tutti i giorni)
        
        Returns:
            Numero di sessioni per settimana
        """
        if available_days is None:
            # Tutti i giorni disponibili
            return frequency_config.preferred_sessions
        
        num_available_days = len(available_days)
        
        if num_available_days >= frequency_config.preferred_sessions:
            return frequency_config.preferred_sessions
        elif num_available_days >= frequency_config.min_sessions:
            return num_available_days
        else:
            return min(num_available_days, frequency_config.min_sessions)
    
    @staticmethod
    def calculate_exercise_count(
        exercise_count_config,
        duration_minutes: int
    ) -> int:
        """
        Calcola numero di esercizi in base a durata e configurazione
        
        Args:
            exercise_count_config: ExerciseCountConfig
            duration_minutes: Durata allenamento in minuti
        
        Returns:
            Numero di esercizi
        """
        # Calcolo dinamico basato su exercises_per_minute
        dynamic_count = int(duration_minutes * exercise_count_config.exercises_per_minute)
        
        # Applica min/max
        exercise_count = max(
            exercise_count_config.min_exercises,
            min(dynamic_count, exercise_count_config.max_exercises)
        )
        
        # Se il calcolo dinamico è fuori range, usa default
        if exercise_count < exercise_count_config.min_exercises:
            exercise_count = exercise_count_config.default_exercises
        elif exercise_count > exercise_count_config.max_exercises:
            exercise_count = exercise_count_config.default_exercises
        
        return exercise_count
    
    @staticmethod
    def get_target_muscle_groups(sport_type: str, phase: str) -> List[str]:
        """
        Restituisce lista gruppi muscolari target per sport e fase
        
        Args:
            sport_type: Tipo di sport
            phase: Fase (BASE, BUILD, PEAK, TAPER)
        
        Returns:
            Lista di gruppi muscolari
        """
        normalized_sport = normalize_sport_type(sport_type)
        sport_config = WORKOUT_PARAMETERS.get(normalized_sport, get_default_sport_config())
        
        return sport_config.target_muscle_groups.get(phase.upper(), [])


