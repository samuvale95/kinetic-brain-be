"""
Servizio per generare allenamenti di stretching usando la tabella exercises
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.services.exercise_service import ExerciseService
from app.services.workout_config_service import WorkoutConfigService
from loguru import logger
import random


class StretchingWorkoutService:
    """Servizio per generare allenamenti di stretching"""
    
    def __init__(self, db: Session):
        self.db = db
        self.exercise_service = ExerciseService(db)
        self.config_service = WorkoutConfigService()
    
    def generate_stretching_workout(
        self,
        sport_type: str,
        level: str,
        available_equipment: List[str],
        week_phase: str,
        target_muscles: Optional[List[str]] = None,
        duration_minutes: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Genera un allenamento di stretching
        
        Args:
            sport_type: Tipo di sport
            level: Livello utente (beginner, intermediate, advanced)
            available_equipment: Lista attrezzi disponibili
            week_phase: Fase allenamento (BASE, BUILD, PEAK, TAPER)
            target_muscles: Gruppi muscolari target (opzionale, default da config)
            duration_minutes: Durata allenamento (opzionale, default da config)
        
        Returns:
            Dict con struttura workout compatibile con create_workouts_from_progressive_week
        """
        try:
            # Carica configurazione
            config = self.config_service.get_workout_config(
                sport_type=sport_type,
                phase=week_phase,
                workout_type="stretching"
            )
            
            if not config:
                logger.error(f"No stretching config found for sport={sport_type}, phase={week_phase}")
                return self._create_fallback_workout(sport_type, level)
            
            # Determina durata
            if duration_minutes is None:
                duration_minutes = config.duration.default_minutes
            
            # Determina numero esercizi
            num_exercises = self.config_service.calculate_exercise_count(
                config.exercise_count,
                duration_minutes
            )
            
            # Determina target muscles
            if target_muscles is None:
                target_muscles = self.config_service.get_target_muscle_groups(
                    sport_type,
                    week_phase
                )
            
            # Seleziona esercizi
            exercises = self.exercise_service.select_exercises_for_workout(
                category="stretching",
                level=level,
                available_equipment=available_equipment,
                target_muscles=target_muscles,
                num_exercises=num_exercises,
                focus_type=config.focus_type
            )
            
            if not exercises:
                logger.warning(f"No exercises found for stretching workout, using fallback")
                return self._create_fallback_workout(sport_type, level)
            
            # Costruisci struttura workout
            workout_structure = self._build_workout_structure(
                exercises=exercises,
                duration_minutes=duration_minutes,
                config=config,
                sport_type=sport_type
            )
            
            return {
                "type": "stretching",
                "sport": sport_type.lower(),
                "duration_minutes": duration_minutes,
                "intensity": config.intensity,
                "zone": "Z1",
                "rpe_target": random.randint(*config.rpe_range),
                "description": f"Stretching session focusing on {', '.join(target_muscles[:3])}",
                "structure": workout_structure
            }
        
        except Exception as e:
            logger.error(f"Error generating stretching workout: {e}")
            return self._create_fallback_workout(sport_type, level)
    
    def _build_workout_structure(
        self,
        exercises: List,
        duration_minutes: int,
        config,
        sport_type: str
    ) -> Dict[str, Any]:
        """Costruisce la struttura JSON del workout"""
        
        # Calcola durata per esercizio (approssimativa)
        # Warmup: 2-3 min, Cooldown: 1-2 min, resto per esercizi
        warmup_minutes = min(3, max(2, duration_minutes // 6))
        cooldown_minutes = min(2, max(1, duration_minutes // 8))
        main_minutes = duration_minutes - warmup_minutes - cooldown_minutes
        
        # Durata per esercizio (secondi)
        time_per_exercise = (main_minutes * 60) // len(exercises) if exercises else 60
        # Per stretching: 30-60 secondi per esercizio, 2-3 serie
        exercise_duration = min(60, max(30, time_per_exercise))
        sets = 2 if duration_minutes < 15 else 3
        
        # Costruisci lista esercizi
        exercise_list = []
        for exercise in exercises:
            exercise_data = {
                "exercise_id": str(exercise.id),
                "name": exercise.name,
                "sets": sets,
                "reps": f"{exercise_duration} seconds",
                "rest_seconds": 10,  # Breve pausa tra serie
                "instructions": exercise.instructions or [],
                "equipment": str(exercise.equipment) if exercise.equipment else "body only",
                "primary_muscles": [str(m) for m in (exercise.primary_muscles or [])],
                "secondary_muscles": [str(m) for m in (exercise.secondary_muscles or [])]
            }
            if exercise.description:
                exercise_data["description"] = exercise.description
            exercise_list.append(exercise_data)
        
        return {
            "sport": "stretching",
            "segments": [
                {
                    "segment_type": "warmup",
                    "name": "Warm-up",
                    "steps": [
                        {
                            "step_type": "steady",
                            "duration": {"type": "time", "seconds": warmup_minutes * 60},
                            "target": {"type": "zone", "zone": "Z1"},
                            "notes": "Gentle warm-up movements"
                        }
                    ]
                },
                {
                    "segment_type": "main",
                    "name": "Stretching Exercises",
                    "exercises": exercise_list
                },
                {
                    "segment_type": "cooldown",
                    "name": "Cool-down",
                    "steps": [
                        {
                            "step_type": "steady",
                            "duration": {"type": "time", "seconds": cooldown_minutes * 60},
                            "target": {"type": "zone", "zone": "Z1"},
                            "notes": "Relaxation and breathing"
                        }
                    ]
                }
            ],
            "metadata": {
                "focus": f"Flexibility and mobility for {sport_type}",
                "rpe_target": random.randint(*config.rpe_range),
                "description": f"Stretching session with {len(exercises)} exercises"
            }
        }
    
    def _create_fallback_workout(self, sport_type: str, level: str) -> Dict[str, Any]:
        """Crea workout fallback se non ci sono esercizi disponibili"""
        return {
            "type": "stretching",
            "sport": sport_type.lower(),
            "duration_minutes": 15,
            "intensity": "easy",
            "zone": "Z1",
            "rpe_target": 2,
            "description": "General stretching session",
            "structure": {
                "sport": "stretching",
                "segments": [
                    {
                        "segment_type": "main",
                        "name": "Stretching",
                        "exercises": []
                    }
                ],
                "metadata": {
                    "focus": "General flexibility",
                    "description": "Stretching session"
                }
            }
        }


