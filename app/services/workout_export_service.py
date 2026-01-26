"""
Service per export workout in formati FIT e TCX
"""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from lxml import etree
from loguru import logger
from app.models.workout import Workout


class WorkoutExportService:
    """Service per convertire workout in formati FIT e TCX"""
    
    def __init__(self):
        pass
    
    def export_to_fit(self, workout: Workout, structure: Optional[Dict[str, Any]] = None) -> bytes:
        """
        Converte workout in formato FIT
        
        Note: fitparse è principalmente un parser, non un writer.
        Per generare file FIT, potremmo dover usare una libreria diversa come 'python-fit'
        o costruire manualmente i messaggi FIT.
        
        Per ora, restituiamo un errore indicando che la generazione FIT richiede una libreria aggiuntiva.
        """
        logger.warning("[EXPORT] FIT export not fully implemented - requires python-fit or manual FIT message construction")
        raise NotImplementedError(
            "FIT export requires python-fit library or manual FIT message construction. "
            "fitparse is primarily a parser, not a writer. "
            "Consider using TCX format instead or installing python-fit."
        )
    
    def export_to_tcx(self, workout: Workout, structure: Optional[Dict[str, Any]] = None) -> bytes:
        """
        Converte workout in formato TCX (Training Center XML)
        
        TCX è un formato XML standardizzato da Garmin per workout e attività.
        """
        if structure is None:
            structure = workout.structure_json or {}
        
        # Crea root element TrainingCenterDatabase
        root = etree.Element(
            "TrainingCenterDatabase",
            xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"
        )
        
        # Folders (opzionale, per organizzazione)
        folders = etree.SubElement(root, "Folders")
        workouts_folder = etree.SubElement(folders, "Workouts")
        
        # Workout
        workout_elem = etree.SubElement(workouts_folder, "Workout")
        
        # Name
        name_elem = etree.SubElement(workout_elem, "Name")
        name_elem.text = workout.title or "Workout"
        
        # WorkoutSamples (steps del workout)
        workout_samples = etree.SubElement(workout_elem, "WorkoutSamples")
        
        # Converti structure_json in WorkoutSamples
        segments = structure.get("segments", [])
        total_duration_seconds = 0
        
        for segment in segments:
            segment_type = segment.get("segment_type", "")
            steps = segment.get("steps", [])
            
            # Skip warmup/cooldown per semplicità (o includili come step)
            if segment_type == "main":
                for step in steps:
                    step_elem = self._convert_step_to_tcx(step, workout_samples)
                    if step_elem is not None:
                        # Calcola durata step
                        duration = self._get_step_duration_seconds(step)
                        total_duration_seconds += duration
        
        # Se non ci sono step, crea un workout semplice basato su duration_minutes
        if total_duration_seconds == 0:
            step_elem = etree.SubElement(workout_samples, "WorkoutStep")
            step_elem.set("Order", "1")
            
            name = etree.SubElement(step_elem, "Name")
            name.text = workout.title or "Workout"
            
            duration = etree.SubElement(step_elem, "Duration")
            total_time = etree.SubElement(duration, "TotalTimeSeconds")
            total_time.text = str(workout.duration_minutes * 60)
            
            intensity = etree.SubElement(step_elem, "Intensity")
            intensity.text = workout.intensity or "Active"
        
        # Crea XML string
        xml_string = etree.tostring(
            root,
            encoding="UTF-8",
            xml_declaration=True,
            pretty_print=True
        )
        
        return xml_string
    
    def _convert_step_to_tcx(self, step: Dict[str, Any], parent: etree.Element, order: int = 1) -> Optional[etree.Element]:
        """Converte uno step della struttura workout in elemento TCX WorkoutStep"""
        step_type = step.get("step_type", "")
        
        if step_type == "repeat":
            # Per step repeat, crea un WorkoutStep con Repeat
            repeat_count = step.get("repeat", 1)
            nested_steps = step.get("steps", [])
            
            step_elem = etree.SubElement(parent, "WorkoutStep")
            step_elem.set("Order", str(order))
            
            name = etree.SubElement(step_elem, "Name")
            name.text = step.get("name", f"Repeat {repeat_count}x")
            
            # Duration: TotalTimeSeconds basato su nested steps
            duration = etree.SubElement(step_elem, "Duration")
            total_time = etree.SubElement(duration, "TotalTimeSeconds")
            nested_duration = sum(self._get_step_duration_seconds(s) for s in nested_steps) * repeat_count
            total_time.text = str(nested_duration)
            
            intensity = etree.SubElement(step_elem, "Intensity")
            intensity.text = "Active"
            
            # Repeat
            repeat_elem = etree.SubElement(step_elem, "Repeat")
            repeat_elem.text = str(repeat_count)
            
            # Steps (nested)
            steps_elem = etree.SubElement(repeat_elem, "Steps")
            nested_order = 1
            for nested_step in nested_steps:
                self._convert_step_to_tcx(nested_step, steps_elem, nested_order)
                nested_order += 1
            
            return step_elem
        
        elif step_type in ["steady", "interval", "recovery", "rest"]:
            # Step normale
            step_elem = etree.SubElement(parent, "WorkoutStep")
            step_elem.set("Order", str(order))
            
            name = etree.SubElement(step_elem, "Name")
            name.text = step.get("name", step_type.capitalize())
            
            # Duration
            duration = etree.SubElement(step_elem, "Duration")
            step_duration = self._get_step_duration_seconds(step)
            total_time = etree.SubElement(duration, "TotalTimeSeconds")
            total_time.text = str(step_duration)
            
            # Intensity
            intensity = etree.SubElement(step_elem, "Intensity")
            target = step.get("target", {})
            if target.get("type") == "zone":
                zone = target.get("zone", "Z2")
                # Mappa zone a intensity
                zone_intensity_map = {
                    "Z1": "Resting",
                    "Z2": "Active",
                    "Z3": "Active",
                    "Z4": "Active",
                    "Z5": "Active",
                    "Z6": "Active",
                    "Z7": "Active"
                }
                intensity.text = zone_intensity_map.get(zone, "Active")
            else:
                intensity.text = "Active"
            
            # Target (opzionale)
            if target:
                target_elem = etree.SubElement(step_elem, "Target")
                if target.get("type") == "zone":
                    zone_elem = etree.SubElement(target_elem, "Zone")
                    zone_elem.text = target.get("zone", "Z2")
                elif target.get("type") in ["heart_rate", "pace", "power"]:
                    # Per HR/Pace/Power, usa SpeedZone o HeartRateZone
                    if target.get("type") == "heart_rate":
                        hr_zone = etree.SubElement(target_elem, "HeartRateZone")
                        if target.get("min_value") or target.get("max_value"):
                            if target.get("min_value"):
                                min_hr = etree.SubElement(hr_zone, "Low")
                                min_hr.text = str(int(target["min_value"]))
                            if target.get("max_value"):
                                max_hr = etree.SubElement(hr_zone, "High")
                                max_hr.text = str(int(target["max_value"]))
            
            return step_elem
        
        return None
    
    def _get_step_duration_seconds(self, step: Dict[str, Any]) -> int:
        """Calcola durata step in secondi"""
        duration = step.get("duration", {})
        if not duration:
            return 60  # Default 1 minuto
        
        duration_type = duration.get("type", "time")
        
        if duration_type == "time":
            return duration.get("seconds", 60)
        elif duration_type == "distance":
            # Stima tempo basato su distanza (assumendo velocità media)
            meters = duration.get("meters", 0)
            # Assumiamo 4 min/km = 240 secondi/km = 0.24 secondi/metro
            return int(meters * 0.24)
        elif duration_type == "repetitions":
            # Stima tempo per ripetizioni (assumendo 1 ripetizione = 5 secondi)
            reps = duration.get("repetitions", 1)
            return reps * 5
        
        return 60  # Default
