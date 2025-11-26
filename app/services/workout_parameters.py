"""
Configurazione centralizzata per parametri di allenamento (stretching e forza)
per ogni sport e fase di allenamento.
"""
from typing import Dict, List
from dataclasses import dataclass


@dataclass
class WorkoutFrequencyConfig:
    """Configurazione frequenza allenamenti per settimana"""
    min_sessions: int  # Numero minimo sessioni/settimana
    max_sessions: int  # Numero massimo sessioni/settimana
    preferred_sessions: int  # Numero preferito (usato se giorni disponibili >= preferred)


@dataclass
class WorkoutDurationConfig:
    """Configurazione durata allenamento"""
    min_minutes: int
    max_minutes: int
    default_minutes: int


@dataclass
class ExerciseCountConfig:
    """Configurazione numero esercizi per allenamento"""
    min_exercises: int
    max_exercises: int
    default_exercises: int
    exercises_per_minute: float  # Esercizi per minuto di durata (per calcolo dinamico)


@dataclass
class WorkoutTypeConfig:
    """Configurazione completa per un tipo di allenamento (stretching/strength)"""
    frequency: WorkoutFrequencyConfig
    duration: WorkoutDurationConfig
    exercise_count: ExerciseCountConfig
    intensity: str  # "easy", "moderate", "hard"
    rpe_range: tuple  # (min_rpe, max_rpe)
    focus_type: str  # "sport_specific", "balanced", "sport_plus_balance"


@dataclass
class PhaseConfig:
    """Configurazione per una fase di allenamento (BASE/BUILD/PEAK/TAPER)"""
    stretching: WorkoutTypeConfig
    strength: WorkoutTypeConfig


@dataclass
class SportWorkoutConfig:
    """Configurazione completa per uno sport"""
    sport_type: str
    phases: Dict[str, PhaseConfig]  # "BASE", "BUILD", "PEAK", "TAPER"
    target_muscle_groups: Dict[str, List[str]]  # Per fase: lista gruppi muscolari target


# Configurazione globale per tutti gli sport
WORKOUT_PARAMETERS: Dict[str, SportWorkoutConfig] = {
    "running": SportWorkoutConfig(
        sport_type="running",
        phases={
            "BASE": PhaseConfig(
                stretching=WorkoutTypeConfig(
                    frequency=WorkoutFrequencyConfig(4, 5, 5),
                    duration=WorkoutDurationConfig(15, 20, 18),
                    exercise_count=ExerciseCountConfig(6, 10, 8, 0.4),
                    intensity="easy",
                    rpe_range=(2, 3),
                    focus_type="sport_plus_balance"
                ),
                strength=WorkoutTypeConfig(
                    frequency=WorkoutFrequencyConfig(2, 3, 3),
                    duration=WorkoutDurationConfig(20, 30, 25),
                    exercise_count=ExerciseCountConfig(4, 6, 5, 0.2),
                    intensity="moderate",
                    rpe_range=(4, 6),
                    focus_type="sport_plus_balance"
                )
            ),
            "BUILD": PhaseConfig(
                stretching=WorkoutTypeConfig(
                    frequency=WorkoutFrequencyConfig(4, 4, 4),
                    duration=WorkoutDurationConfig(10, 12, 11),
                    exercise_count=ExerciseCountConfig(5, 8, 6, 0.5),
                    intensity="easy",
                    rpe_range=(2, 3),
                    focus_type="sport_plus_balance"
                ),
                strength=WorkoutTypeConfig(
                    frequency=WorkoutFrequencyConfig(2, 3, 2),
                    duration=WorkoutDurationConfig(45, 60, 50),
                    exercise_count=ExerciseCountConfig(5, 7, 6, 0.12),
                    intensity="hard",
                    rpe_range=(6, 8),
                    focus_type="sport_plus_balance"
                )
            ),
            "PEAK": PhaseConfig(
                stretching=WorkoutTypeConfig(
                    frequency=WorkoutFrequencyConfig(4, 4, 4),
                    duration=WorkoutDurationConfig(8, 10, 9),
                    exercise_count=ExerciseCountConfig(4, 7, 5, 0.5),
                    intensity="easy",
                    rpe_range=(2, 3),
                    focus_type="sport_plus_balance"
                ),
                strength=WorkoutTypeConfig(
                    frequency=WorkoutFrequencyConfig(1, 2, 1),
                    duration=WorkoutDurationConfig(45, 50, 47),
                    exercise_count=ExerciseCountConfig(4, 6, 5, 0.1),
                    intensity="hard",
                    rpe_range=(7, 8),
                    focus_type="sport_plus_balance"
                )
            ),
            "TAPER": PhaseConfig(
                stretching=WorkoutTypeConfig(
                    frequency=WorkoutFrequencyConfig(2, 3, 3),
                    duration=WorkoutDurationConfig(5, 8, 6),
                    exercise_count=ExerciseCountConfig(3, 5, 4, 0.6),
                    intensity="easy",
                    rpe_range=(1, 2),
                    focus_type="sport_plus_balance"
                ),
                strength=WorkoutTypeConfig(
                    frequency=WorkoutFrequencyConfig(1, 1, 1),
                    duration=WorkoutDurationConfig(20, 40, 30),
                    exercise_count=ExerciseCountConfig(3, 5, 4, 0.13),
                    intensity="moderate",
                    rpe_range=(4, 6),
                    focus_type="sport_plus_balance"
                )
            )
        },
        target_muscle_groups={
            "BASE": ["hamstrings", "calves", "hip flexors", "glutes", "quadriceps"],
            "BUILD": ["hamstrings", "calves", "glutes", "core", "quadriceps"],
            "PEAK": ["hamstrings", "calves", "glutes"],
            "TAPER": ["hamstrings", "calves", "hip flexors"]
        }
    ),
    "cycling": SportWorkoutConfig(
        sport_type="cycling",
        phases={
            "BASE": PhaseConfig(
                stretching=WorkoutTypeConfig(
                    frequency=WorkoutFrequencyConfig(4, 5, 5),
                    duration=WorkoutDurationConfig(15, 20, 18),
                    exercise_count=ExerciseCountConfig(6, 10, 8, 0.4),
                    intensity="easy",
                    rpe_range=(2, 3),
                    focus_type="sport_plus_balance"
                ),
                strength=WorkoutTypeConfig(
                    frequency=WorkoutFrequencyConfig(2, 3, 3),
                    duration=WorkoutDurationConfig(20, 30, 25),
                    exercise_count=ExerciseCountConfig(4, 6, 5, 0.2),
                    intensity="moderate",
                    rpe_range=(4, 6),
                    focus_type="sport_plus_balance"
                )
            ),
            "BUILD": PhaseConfig(
                stretching=WorkoutTypeConfig(
                    frequency=WorkoutFrequencyConfig(4, 4, 4),
                    duration=WorkoutDurationConfig(10, 12, 11),
                    exercise_count=ExerciseCountConfig(5, 8, 6, 0.5),
                    intensity="easy",
                    rpe_range=(2, 3),
                    focus_type="sport_plus_balance"
                ),
                strength=WorkoutTypeConfig(
                    frequency=WorkoutFrequencyConfig(2, 3, 2),
                    duration=WorkoutDurationConfig(45, 60, 50),
                    exercise_count=ExerciseCountConfig(5, 7, 6, 0.12),
                    intensity="hard",
                    rpe_range=(6, 8),
                    focus_type="sport_plus_balance"
                )
            ),
            "PEAK": PhaseConfig(
                stretching=WorkoutTypeConfig(
                    frequency=WorkoutFrequencyConfig(4, 4, 4),
                    duration=WorkoutDurationConfig(8, 10, 9),
                    exercise_count=ExerciseCountConfig(4, 7, 5, 0.5),
                    intensity="easy",
                    rpe_range=(2, 3),
                    focus_type="sport_plus_balance"
                ),
                strength=WorkoutTypeConfig(
                    frequency=WorkoutFrequencyConfig(1, 2, 1),
                    duration=WorkoutDurationConfig(45, 50, 47),
                    exercise_count=ExerciseCountConfig(4, 6, 5, 0.1),
                    intensity="hard",
                    rpe_range=(7, 8),
                    focus_type="sport_plus_balance"
                )
            ),
            "TAPER": PhaseConfig(
                stretching=WorkoutTypeConfig(
                    frequency=WorkoutFrequencyConfig(2, 3, 3),
                    duration=WorkoutDurationConfig(5, 8, 6),
                    exercise_count=ExerciseCountConfig(3, 5, 4, 0.6),
                    intensity="easy",
                    rpe_range=(1, 2),
                    focus_type="sport_plus_balance"
                ),
                strength=WorkoutTypeConfig(
                    frequency=WorkoutFrequencyConfig(1, 1, 1),
                    duration=WorkoutDurationConfig(20, 40, 30),
                    exercise_count=ExerciseCountConfig(3, 5, 4, 0.13),
                    intensity="moderate",
                    rpe_range=(4, 6),
                    focus_type="sport_plus_balance"
                )
            )
        },
        target_muscle_groups={
            "BASE": ["quadriceps", "hip flexors", "glutes", "calves"],
            "BUILD": ["quadriceps", "glutes", "core", "calves"],
            "PEAK": ["quadriceps", "glutes"],
            "TAPER": ["quadriceps", "hip flexors"]
        }
    ),
    "swimming": SportWorkoutConfig(
        sport_type="swimming",
        phases={
            "BASE": PhaseConfig(
                stretching=WorkoutTypeConfig(
                    frequency=WorkoutFrequencyConfig(4, 5, 5),
                    duration=WorkoutDurationConfig(15, 20, 18),
                    exercise_count=ExerciseCountConfig(6, 10, 8, 0.4),
                    intensity="easy",
                    rpe_range=(2, 3),
                    focus_type="sport_plus_balance"
                ),
                strength=WorkoutTypeConfig(
                    frequency=WorkoutFrequencyConfig(2, 3, 3),
                    duration=WorkoutDurationConfig(20, 30, 25),
                    exercise_count=ExerciseCountConfig(4, 6, 5, 0.2),
                    intensity="moderate",
                    rpe_range=(4, 6),
                    focus_type="sport_plus_balance"
                )
            ),
            "BUILD": PhaseConfig(
                stretching=WorkoutTypeConfig(
                    frequency=WorkoutFrequencyConfig(4, 4, 4),
                    duration=WorkoutDurationConfig(10, 12, 11),
                    exercise_count=ExerciseCountConfig(5, 8, 6, 0.5),
                    intensity="easy",
                    rpe_range=(2, 3),
                    focus_type="sport_plus_balance"
                ),
                strength=WorkoutTypeConfig(
                    frequency=WorkoutFrequencyConfig(2, 3, 2),
                    duration=WorkoutDurationConfig(45, 60, 50),
                    exercise_count=ExerciseCountConfig(5, 7, 6, 0.12),
                    intensity="hard",
                    rpe_range=(6, 8),
                    focus_type="sport_plus_balance"
                )
            ),
            "PEAK": PhaseConfig(
                stretching=WorkoutTypeConfig(
                    frequency=WorkoutFrequencyConfig(4, 4, 4),
                    duration=WorkoutDurationConfig(8, 10, 9),
                    exercise_count=ExerciseCountConfig(4, 7, 5, 0.5),
                    intensity="easy",
                    rpe_range=(2, 3),
                    focus_type="sport_plus_balance"
                ),
                strength=WorkoutTypeConfig(
                    frequency=WorkoutFrequencyConfig(1, 2, 1),
                    duration=WorkoutDurationConfig(45, 50, 47),
                    exercise_count=ExerciseCountConfig(4, 6, 5, 0.1),
                    intensity="hard",
                    rpe_range=(7, 8),
                    focus_type="sport_plus_balance"
                )
            ),
            "TAPER": PhaseConfig(
                stretching=WorkoutTypeConfig(
                    frequency=WorkoutFrequencyConfig(2, 3, 3),
                    duration=WorkoutDurationConfig(5, 8, 6),
                    exercise_count=ExerciseCountConfig(3, 5, 4, 0.6),
                    intensity="easy",
                    rpe_range=(1, 2),
                    focus_type="sport_plus_balance"
                ),
                strength=WorkoutTypeConfig(
                    frequency=WorkoutFrequencyConfig(1, 1, 1),
                    duration=WorkoutDurationConfig(20, 40, 30),
                    exercise_count=ExerciseCountConfig(3, 5, 4, 0.13),
                    intensity="moderate",
                    rpe_range=(4, 6),
                    focus_type="sport_plus_balance"
                )
            )
        },
        target_muscle_groups={
            "BASE": ["shoulders", "chest", "lats", "triceps", "core"],
            "BUILD": ["shoulders", "lats", "triceps", "core"],
            "PEAK": ["shoulders", "lats"],
            "TAPER": ["shoulders", "chest"]
        }
    ),
    "triathlon": SportWorkoutConfig(
        sport_type="triathlon",
        phases={
            "BASE": PhaseConfig(
                stretching=WorkoutTypeConfig(
                    frequency=WorkoutFrequencyConfig(4, 5, 5),
                    duration=WorkoutDurationConfig(15, 20, 18),
                    exercise_count=ExerciseCountConfig(6, 10, 8, 0.4),
                    intensity="easy",
                    rpe_range=(2, 3),
                    focus_type="sport_plus_balance"
                ),
                strength=WorkoutTypeConfig(
                    frequency=WorkoutFrequencyConfig(2, 3, 3),
                    duration=WorkoutDurationConfig(20, 30, 25),
                    exercise_count=ExerciseCountConfig(4, 6, 5, 0.2),
                    intensity="moderate",
                    rpe_range=(4, 6),
                    focus_type="sport_plus_balance"
                )
            ),
            "BUILD": PhaseConfig(
                stretching=WorkoutTypeConfig(
                    frequency=WorkoutFrequencyConfig(4, 4, 4),
                    duration=WorkoutDurationConfig(10, 12, 11),
                    exercise_count=ExerciseCountConfig(5, 8, 6, 0.5),
                    intensity="easy",
                    rpe_range=(2, 3),
                    focus_type="sport_plus_balance"
                ),
                strength=WorkoutTypeConfig(
                    frequency=WorkoutFrequencyConfig(1, 2, 2),
                    duration=WorkoutDurationConfig(45, 60, 50),
                    exercise_count=ExerciseCountConfig(5, 7, 6, 0.12),
                    intensity="hard",
                    rpe_range=(6, 8),
                    focus_type="sport_plus_balance"
                )
            ),
            "PEAK": PhaseConfig(
                stretching=WorkoutTypeConfig(
                    frequency=WorkoutFrequencyConfig(4, 4, 4),
                    duration=WorkoutDurationConfig(8, 10, 9),
                    exercise_count=ExerciseCountConfig(4, 7, 5, 0.5),
                    intensity="easy",
                    rpe_range=(2, 3),
                    focus_type="sport_plus_balance"
                ),
                strength=WorkoutTypeConfig(
                    frequency=WorkoutFrequencyConfig(1, 1, 1),
                    duration=WorkoutDurationConfig(45, 50, 47),
                    exercise_count=ExerciseCountConfig(4, 6, 5, 0.1),
                    intensity="hard",
                    rpe_range=(7, 8),
                    focus_type="sport_plus_balance"
                )
            ),
            "TAPER": PhaseConfig(
                stretching=WorkoutTypeConfig(
                    frequency=WorkoutFrequencyConfig(2, 3, 3),
                    duration=WorkoutDurationConfig(5, 8, 6),
                    exercise_count=ExerciseCountConfig(3, 5, 4, 0.6),
                    intensity="easy",
                    rpe_range=(1, 2),
                    focus_type="sport_plus_balance"
                ),
                strength=WorkoutTypeConfig(
                    frequency=WorkoutFrequencyConfig(1, 1, 1),
                    duration=WorkoutDurationConfig(20, 40, 30),
                    exercise_count=ExerciseCountConfig(3, 5, 4, 0.13),
                    intensity="moderate",
                    rpe_range=(4, 6),
                    focus_type="sport_plus_balance"
                )
            )
        },
        target_muscle_groups={
            "BASE": ["quadriceps", "hamstrings", "glutes", "shoulders", "core"],
            "BUILD": ["quadriceps", "glutes", "shoulders", "core"],
            "PEAK": ["quadriceps", "glutes", "shoulders"],
            "TAPER": ["quadriceps", "hamstrings", "shoulders"]
        }
    )
}


def get_default_sport_config() -> SportWorkoutConfig:
    """Restituisce configurazione di default (running) se sport non trovato"""
    return WORKOUT_PARAMETERS["running"]


def normalize_sport_type(sport_type: str) -> str:
    """Normalizza il tipo di sport per la ricerca nella configurazione"""
    sport_lower = sport_type.lower()
    if sport_lower in ["run", "running"]:
        return "running"
    elif sport_lower in ["bike", "cycling", "cycle"]:
        return "cycling"
    elif sport_lower in ["swim", "swimming"]:
        return "swimming"
    elif sport_lower in ["triathlon", "tri"]:
        return "triathlon"
    return "running"  # Default


