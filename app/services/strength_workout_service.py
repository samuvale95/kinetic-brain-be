"""
Servizio per generare allenamenti di forza usando la tabella exercises
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.services.exercise_service import ExerciseService
from app.services.workout_config_service import WorkoutConfigService
from loguru import logger
import random
import time


class StrengthWorkoutService:
    """Servizio per generare allenamenti di forza"""
    
    def __init__(self, db: Session):
        self.db = db
        self.exercise_service = ExerciseService(db)
        self.config_service = WorkoutConfigService()
    
    def generate_strength_workout(
        self,
        sport_type: str,
        level: str,
        available_equipment: List[str],
        week_phase: str,
        weeks_remaining: Optional[int] = None,
        target_muscles: Optional[List[str]] = None,
        duration_minutes: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Genera un allenamento di forza
        
        Args:
            sport_type: Tipo di sport
            level: Livello utente (beginner, intermediate, advanced)
            available_equipment: Lista attrezzi disponibili
            week_phase: Fase allenamento (BASE, BUILD, PEAK, TAPER)
            weeks_remaining: Settimane rimanenti (opzionale, per determinare fase)
            target_muscles: Gruppi muscolari target (opzionale, default da config)
            duration_minutes: Durata allenamento (opzionale, default da config)
        
        Returns:
            Dict con struttura workout compatibile con create_workouts_from_progressive_week
        """
        gen_start = time.time()
        logger.info(f"[STRENGTH][START] Generating strength workout - sport: {sport_type}, level: {level}, phase: {week_phase}, equipment: {len(available_equipment) if available_equipment else 0}, timestamp: {datetime.utcnow().isoformat()}")
        try:
            # Determina fase se non specificata
            if not week_phase and weeks_remaining is not None:
                week_phase = self.config_service.determine_phase(weeks_remaining)
            elif not week_phase:
                week_phase = "BASE"
            
            # Carica configurazione
            config_start = time.time()
            logger.debug(f"[STRENGTH] Loading config for sport={sport_type}, phase={week_phase}")
            config = self.config_service.get_workout_config(
                sport_type=sport_type,
                phase=week_phase,
                workout_type="strength"
            )
            config_duration = time.time() - config_start
            logger.debug(f"[STRENGTH] Config loaded - duration: {config_duration:.2f}s")
            
            if not config:
                logger.error(f"[STRENGTH] No strength config found for sport={sport_type}, phase={week_phase}")
                return self._create_fallback_workout(sport_type, level)
            
            # Determina durata
            if duration_minutes is None:
                duration_minutes = config.duration.default_minutes
            
            # Determina numero esercizi
            num_exercises = self.config_service.calculate_exercise_count(
                config.exercise_count,
                duration_minutes
            )
            logger.debug(f"[STRENGTH] Calculated: duration={duration_minutes}min, num_exercises={num_exercises}")
            
            # Determina target muscles
            if target_muscles is None:
                target_muscles = self.config_service.get_target_muscle_groups(
                    sport_type,
                    week_phase
                )
            logger.debug(f"[STRENGTH] Target muscles: {target_muscles}")
            
            # Determina mechanic in base alla fase
            mechanic = None
            if week_phase in ["BUILD", "PEAK"]:
                # Preferisci compound movements per forza massima
                mechanic = "compound"
            elif week_phase == "TAPER":
                # Mix per mantenimento
                mechanic = None  # Qualsiasi
            logger.debug(f"[STRENGTH] Mechanic: {mechanic}")
            
            # Seleziona esercizi
            exercise_start = time.time()
            logger.info(f"[STRENGTH] Selecting exercises - category: strength, level: {level}, num_exercises: {num_exercises}, mechanic: {mechanic}, equipment: {available_equipment}, timestamp: {datetime.utcnow().isoformat()}")
            exercises = self.exercise_service.select_exercises_for_workout(
                category="strength",
                level=level,
                available_equipment=available_equipment,
                target_muscles=target_muscles,
                num_exercises=num_exercises,
                focus_type=config.focus_type,
                mechanic=mechanic
            )
            exercise_duration = time.time() - exercise_start
            logger.info(f"[STRENGTH] Exercises selected - count: {len(exercises) if exercises else 0}, duration: {exercise_duration:.2f}s")
            
            if not exercises:
                logger.warning(f"[STRENGTH] No exercises found for strength workout, using fallback")
                return self._create_fallback_workout(sport_type, level)
            
            # Costruisci struttura workout
            structure_start = time.time()
            logger.debug(f"[STRENGTH] Building workout structure - timestamp: {datetime.utcnow().isoformat()}")
            workout_structure = self._build_workout_structure(
                exercises=exercises,
                duration_minutes=duration_minutes,
                config=config,
                sport_type=sport_type,
                week_phase=week_phase,
                level=level
            )
            structure_duration = time.time() - structure_start
            logger.debug(f"[STRENGTH] Workout structure built - duration: {structure_duration:.2f}s")
            
            gen_duration = time.time() - gen_start
            result = {
                "type": "strength",
                "sport": sport_type.lower(),
                "duration_minutes": duration_minutes,
                "intensity": config.intensity,
                "zone": "Z1",  # Strength è sempre Z1 per HR
                "rpe_target": random.randint(*config.rpe_range),
                "description": f"Strength training focusing on {', '.join(target_muscles[:3])}",
                "structure": workout_structure
            }
            logger.info(f"[STRENGTH][END] Strength workout generated - duration: {gen_duration:.2f}s, exercises: {len(exercises)}, timestamp: {datetime.utcnow().isoformat()}")
            return result
        
        except Exception as e:
            gen_duration = time.time() - gen_start
            logger.error(f"[STRENGTH][ERROR] Error generating strength workout after {gen_duration:.2f}s: {e}", exc_info=True)
            return self._create_fallback_workout(sport_type, level)
    
    def _build_workout_structure(
        self,
        exercises: List,
        duration_minutes: int,
        config,
        sport_type: str,
        week_phase: str,
        level: str
    ) -> Dict[str, Any]:
        """Costruisce la struttura JSON del workout"""
        
        # Determina serie e ripetizioni in base alla fase
        if week_phase == "BASE":
            sets = 3
            reps_range = (10, 12)  # Endurance strength
            rest_seconds = 60
        elif week_phase == "BUILD":
            sets = 4
            reps_range = (6, 8)  # Strength
            rest_seconds = 90
        elif week_phase == "PEAK":
            sets = 3
            reps_range = (4, 6)  # Power
            rest_seconds = 120
        else:  # TAPER
            sets = 2
            reps_range = (8, 10)  # Maintenance
            rest_seconds = 60
        
        # Costruisci lista esercizi
        exercise_list = []
        for exercise in exercises:
            # Calcola numero medio di ripetizioni (non range stringa)
            avg_reps = (reps_range[0] + reps_range[1]) // 2
            
            # Gestisci correttamente gli array di muscoli (potrebbero essere array PostgreSQL)
            def normalize_muscle_array(muscle_array):
                """Normalizza un array di muscoli in una lista di stringhe"""
                if not muscle_array:
                    return []
                # Se è già una lista, converti ogni elemento in stringa
                if isinstance(muscle_array, list):
                    return [str(m) for m in muscle_array if m]
                # Se è una stringa (array PostgreSQL serializzato come {valore1,valore2})
                if isinstance(muscle_array, str):
                    # Rimuovi parentesi graffe e split per virgola
                    cleaned = muscle_array.strip('{}')
                    if cleaned:
                        # Split per virgola e rimuovi spazi e virgolette
                        return [m.strip().strip('"').strip("'") for m in cleaned.split(',') if m.strip()]
                return []
            
            exercise_data = {
                "exercise_id": str(exercise.id),
                "name": exercise.name,
                "sets": sets,
                "reps": avg_reps,  # Numero di ripetizioni (non stringa)
                "rest_seconds": rest_seconds,
                "instructions": exercise.instructions or [],
                "equipment": str(exercise.equipment) if exercise.equipment else "body only",
                "primary_muscles": normalize_muscle_array(exercise.primary_muscles),
                "secondary_muscles": normalize_muscle_array(exercise.secondary_muscles)
            }
            if exercise.description:
                exercise_data["description"] = exercise.description
            if exercise.mechanic:
                exercise_data["mechanic"] = str(exercise.mechanic)
            exercise_list.append(exercise_data)
        
        return {
            "sport": "strength",
            "segments": [
                {
                    "segment_type": "main",
                    "name": "Strength Exercises",
                    "exercises": exercise_list
                }
            ],
            "metadata": {
                "focus": f"Strength training for {sport_type} - {week_phase} phase",
                "rpe_target": random.randint(*config.rpe_range),
                "description": f"Strength session with {len(exercises)} exercises, {sets} sets each"
            }
        }
    
    def _create_fallback_workout(self, sport_type: str, level: str) -> Dict[str, Any]:
        """Crea workout fallback se non ci sono esercizi disponibili"""
        return {
            "type": "strength",
            "sport": sport_type.lower(),
            "duration_minutes": 30,
            "intensity": "moderate",
            "zone": "Z1",
            "rpe_target": 5,
            "description": "General strength training session",
            "structure": {
                "sport": "strength",
                "segments": [
                    {
                        "segment_type": "main",
                        "name": "Strength Training",
                        "exercises": []
                    }
                ],
                "metadata": {
                    "focus": "General strength",
                    "description": "Strength training session"
                }
            }
        }

