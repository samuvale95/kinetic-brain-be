"""
Validazione custom per strutture workout specifiche (es. Hyrox)
"""
from typing import Dict, Any, Optional, List
from loguru import logger


def find_main_segment(workout: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Trova il segmento 'main' nella struttura workout"""
    structure = workout.get("structure_json")
    if not structure:
        return None
    
    segments = structure.get("segments", [])
    for segment in segments:
        if segment.get("segment_type") == "main":
            return segment
    return None


def count_repeat_steps(segment: Dict[str, Any]) -> int:
    """Conta il numero di round in un segmento con step_type 'repeat'"""
    if not segment:
        return 0
    
    steps = segment.get("steps", [])
    for step in steps:
        if step.get("step_type") == "repeat":
            return step.get("repeat", 0)
    return 0


def validate_hyrox_structure(workout: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Verifica che workout Hyrox abbia struttura corretta: 8 round obbligatori
    
    Returns:
        (is_valid, error_message)
    """
    sport_type = workout.get("sport_type", "").lower()
    if sport_type != "hyrox":
        return True, None  # Non è un workout Hyrox, skip validazione
    
    structure = workout.get("structure_json")
    if not structure:
        return False, "Workout Hyrox deve avere structure_json definita"
    
    main_segment = find_main_segment(workout)
    if not main_segment:
        return False, "Workout Hyrox deve avere un segmento 'main'"
    
    repeat_count = count_repeat_steps(main_segment)
    if repeat_count != 8:
        return False, f"Workout Hyrox deve avere esattamente 8 round, trovati {repeat_count}"
    
    # Verifica che ogni round contenga 1km run + 1 station
    steps = main_segment.get("steps", [])
    for step in steps:
        if step.get("step_type") == "repeat":
            nested_steps = step.get("steps", [])
            if len(nested_steps) < 2:
                return False, "Ogni round Hyrox deve contenere almeno 1km run + 1 station"
            
            # Verifica presenza run e station
            has_run = False
            has_station = False
            for nested in nested_steps:
                name = nested.get("name", "").lower()
                if "run" in name or "1 km" in name or "1km" in name:
                    has_run = True
                if any(station in name for station in [
                    "skierg", "sled push", "sled pull", "burpee", "rowing",
                    "farmer", "sandbag", "wall ball"
                ]):
                    has_station = True
            
            if not has_run:
                return False, "Ogni round Hyrox deve contenere 1km run"
            if not has_station:
                return False, "Ogni round Hyrox deve contenere una station"
    
    return True, None


def validate_workout_structure(workout: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validazione generale struttura workout con validazioni specifiche per sport
    
    Returns:
        (is_valid, error_message)
    """
    sport_type = workout.get("sport_type", "").lower()
    
    # Validazione specifica per Hyrox
    if sport_type == "hyrox":
        return validate_hyrox_structure(workout)
    
    # Altre validazioni specifiche per sport possono essere aggiunte qui
    # Es: validazione triathlon, validazione gym, etc.
    
    return True, None
