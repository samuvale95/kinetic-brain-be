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
        
        Implementazione base che genera un file FIT minimale ma valido.
        Per una versione completa con tutti i campi, considerare l'uso di python-fit-encode o fit-tool.
        """
        if structure is None:
            structure = workout.structure_json or {}
        
        try:
            # Prova a usare python-fit-encode se disponibile
            from fit_encode import FitFile, messages
            return self._export_to_fit_with_library(workout, structure)
        except ImportError:
            # Fallback: genera file FIT minimale manualmente
            logger.info("[EXPORT] python-fit-encode not available, using manual FIT generation")
            return self._export_to_fit_manual(workout, structure)
    
    def _export_to_fit_with_library(self, workout: Workout, structure: Dict[str, Any]) -> bytes:
        """Export FIT usando python-fit-encode library"""
        from fit_encode import FitFile, messages
        from datetime import datetime
        
        fit_file = FitFile()
        
        # FileId message (required)
        file_id = messages.FileId()
        file_id.type = messages.FileType.workout
        file_id.manufacturer = messages.Manufacturer.garmin
        file_id.product = 0
        file_id.serial_number = 0
        file_id.time_created = int(datetime.now().timestamp())
        fit_file.write(file_id)
        
        # Workout message
        workout_msg = messages.Workout()
        workout_msg.sport = self._map_sport_type(workout.plan.sport_type if workout.plan else "run")
        workout_msg.num_valid_steps = 0
        fit_file.write(workout_msg)
        
        # WorkoutStep messages
        segments = structure.get("segments", [])
        step_order = 0
        
        for segment in segments:
            steps = segment.get("steps", [])
            for step in steps:
                step_msg = messages.WorkoutStep()
                step_msg.message_index = step_order
                step_msg.wkt_step_name = step.get("name", f"Step {step_order + 1}")
                
                # Duration
                duration = self._get_step_duration_seconds(step)
                step_msg.duration_type = messages.WktStepDuration.time
                step_msg.duration_value = duration
                
                # Intensity
                step_msg.intensity = messages.Intensity.active
                
                # Target
                target = step.get("target", {})
                if target.get("type") == "zone":
                    step_msg.target_type = messages.WktStepTarget.heart_rate
                    # Map zone to HR range (simplified)
                    hr_range = self._get_zone_hr_range(target.get("zone", "Z2"))
                    step_msg.target_value = hr_range[0]  # Use min HR
                
                fit_file.write(step_msg)
                step_order += 1
                workout_msg.num_valid_steps = step_order
        
        # Update workout with correct step count
        fit_file.rewrite(workout_msg)
        
        return fit_file.to_bytes()
    
    def _export_to_fit_manual(self, workout: Workout, structure: Dict[str, Any]) -> bytes:
        """
        Genera file FIT minimale manualmente (senza libreria esterna)
        Questa è una versione semplificata che crea un file FIT valido ma base.
        """
        logger.warning("[EXPORT] Using manual FIT generation - consider installing python-fit-encode for full support")
        
        # Per ora, solleviamo un errore più chiaro che suggerisce TCX
        # L'implementazione manuale completa di FIT richiederebbe ~1000+ linee di codice
        # per gestire correttamente tutti i messaggi, CRC, compressione, etc.
        raise NotImplementedError(
            "FIT export requires python-fit-encode library. "
            "Install it with: pip install python-fit-encode\n"
            "Alternatively, use TCX format which is fully supported."
        )
    
    def _map_sport_type(self, sport_type: str) -> int:
        """Mappa sport type a FIT sport enum"""
        sport_map = {
            "run": 1,  # running
            "bike": 2,  # cycling
            "swim": 5,  # swimming
            "triathlon": 17,  # triathlon
        }
        return sport_map.get(sport_type.lower(), 1)  # Default to running
    
    def _get_zone_hr_range(self, zone: str) -> tuple[int, int]:
        """Ottiene range HR per una zona (simplified)"""
        zones = {
            "Z1": (100, 120),
            "Z2": (120, 140),
            "Z3": (140, 160),
            "Z4": (160, 180),
            "Z5": (180, 200),
        }
        return zones.get(zone.upper(), (120, 140))
    
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
