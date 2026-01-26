from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_, desc, func as sql_func
from typing import List, Optional, Dict, Any
from copy import deepcopy
import re
from datetime import date, datetime, timedelta
from app.models.workout import WorkoutPlan, Workout, WorkoutSession, WorkoutStatus
from app.models.calendar import CalendarEvent
from app.models.strava import StravaActivity
from app.models.daily_metrics import DailyReadinessMetrics, DailyPerformanceMetrics
from app.schemas.workout import (
    WorkoutPlanCreate,
    WorkoutPlanUpdate,
    WorkoutCreate,
    WorkoutUpdate,
    WorkoutSessionCreate,
    # WorkoutStructure, WorkoutSegment, WorkoutSegmentStep temporarily removed to prevent recursion
    WorkoutDuration,
    WorkoutTarget,
)
from app.services.workout_validator import validate_workout_structure
from loguru import logger


class WorkoutService:
    def __init__(self, db: Session):
        self.db = db
    
    @staticmethod
    def _clean_text(value: Optional[str], default: str, max_length: Optional[int] = None) -> str:
        text = value if isinstance(value, str) else default
        text = text.strip()
        if not text:
            text = default
        if max_length is not None:
            text = text[:max_length]
        return text

    @staticmethod
    def _extract_zone(workout_data: Dict[str, Any], fallback: str = "Z2") -> str:
        zone_value = workout_data.get("zone")
        if isinstance(zone_value, str) and zone_value.strip():
            return zone_value.strip().upper()[:10]

        intensity = workout_data.get("intensity")
        if isinstance(intensity, str):
            match = re.search(r"Z\d+", intensity.upper())
            if match:
                return match.group(0)[:10]

        target_hr = workout_data.get("target_hr")
        if isinstance(target_hr, str):
            match = re.search(r"Z\d+", target_hr.upper())
            if match:
                return match.group(0)[:10]

        return fallback.upper()[:10]

    @staticmethod
    def _normalize_sport(sport: Optional[str]) -> str:
        if not sport:
            return "run"
        sport_lower = sport.lower()
        mapping = {
            "running": "run",
            "trail": "run",
            "trail running": "run",
            "road": "run",
            "cycling": "bike",
            "bicycling": "bike",
            "bike": "bike",
            "mtb": "bike",
            "road cycling": "bike",
            "swimming": "swim",
            "triathlon": "triathlon",
        }
        return mapping.get(sport_lower, sport_lower)

    @staticmethod
    def _default_zone_for_sport(sport: str) -> str:
        if sport in {"bike", "cycling"}:
            return "Z2"
        return "Z2"

    def _build_structure_payload(
        self,
        *,
        plan_sport: Optional[str],
        workout_data: Dict[str, Any],
        week_focus: Optional[str],
    ) -> Dict[str, Any]:
        structure = workout_data.get("structure")
        normalized_sport = self._normalize_sport(
            workout_data.get("sport")
            or workout_data.get("sport_type")
            or plan_sport
        )

        if isinstance(structure, dict):
            payload = deepcopy(structure)
            payload["sport"] = self._normalize_sport(payload.get("sport") or normalized_sport)
            self._normalize_structure_targets(payload)

            segments = payload.get("segments") or []
            if not segments:
                raise ValueError("Structure contains no segments")

            metadata = payload.get("metadata") or {}
            if week_focus and not metadata.get("focus"):
                metadata["focus"] = week_focus
            if workout_data.get("rpe_target") is not None and metadata.get("rpe_target") is None:
                metadata["rpe_target"] = workout_data.get("rpe_target")
            if workout_data.get("description") and not metadata.get("description"):
                metadata["description"] = workout_data.get("description")
            if metadata.get("rpe_target") is not None and metadata["rpe_target"] < 1:
                metadata["rpe_target"] = None
            payload["metadata"] = metadata or None
            # TEMPORARY FIX: WorkoutStructure validation disabled to prevent recursion
            # Just return the payload as-is (it's already a dict)
            try:
                enriched = self._ensure_structure_segments(
                    payload,  # Pass dict instead of WorkoutStructure
                    normalized_sport=normalized_sport,
                    duration_minutes=workout_data.get("duration_minutes", 60),
                )
                return enriched
            except Exception as exc:
                logger.warning(
                    f"[WORKOUT_SERVICE] Invalid structured payload from AI, regenerating fallback. Error: {exc}"
                )

        # Fallback to build a basic structure when AI data is missing the structured payload
        zone = self._extract_zone(workout_data, fallback=self._default_zone_for_sport(normalized_sport)).upper()
        allowed_zones = {"Z1", "Z2", "Z3", "Z4", "Z5"}
        if normalized_sport in {"bike", "cycling"}:
            allowed_zones = {"Z1", "Z2", "Z3", "Z4", "Z5", "Z6", "Z7"}
        if zone not in allowed_zones:
            zone = self._default_zone_for_sport(normalized_sport).upper()
        duration_minutes_raw = workout_data.get("duration_minutes", 60)
        try:
            duration_minutes = float(duration_minutes_raw)
        except (TypeError, ValueError):
            duration_minutes = 60
        duration_minutes = max(duration_minutes, 1)
        duration_seconds = max(int(duration_minutes * 60), 60)
        warmup_seconds = min(600, max(duration_seconds // 6, 180))
        cooldown_seconds = min(600, max(duration_seconds // 6, 180))
        main_seconds = duration_seconds - warmup_seconds - cooldown_seconds
        if main_seconds < 120:
            deficit = 120 - main_seconds
            reduction = min(deficit // 2, warmup_seconds - 60)
            if reduction > 0:
                warmup_seconds -= reduction
            deficit = 120 - (duration_seconds - warmup_seconds - cooldown_seconds)
            reduction = min(deficit, cooldown_seconds - 60)
            if reduction > 0:
                cooldown_seconds -= reduction
            main_seconds = max(duration_seconds - warmup_seconds - cooldown_seconds, 60)

        metadata = {
            "focus": week_focus,
            "rpe_target": workout_data.get("rpe_target"),
            "description": workout_data.get("description"),
            "notes": workout_data.get("modifications"),
        }
        if metadata["rpe_target"] is not None and metadata["rpe_target"] < 1:
            metadata["rpe_target"] = None

        warmup_step = {
            "step_type": "steady",
            "name": "Warm-up",
            "duration": {
                "type": "time",
                "seconds": warmup_seconds,
            },
            "target": {
                "type": "zone",
                "zone": "Z1" if normalized_sport not in {"bike", "cycling"} else "Z1",
            },
            "notes": "Gradual build-in",
        }

        main_step = {
            "step_type": "steady",
            "name": workout_data.get("type", "Main Session"),
            "duration": {
                "type": "time",
                "seconds": main_seconds,
            },
            "target": {
                "type": "zone",
                "zone": zone,
            },
            "notes": workout_data.get("description"),
        }

        cooldown_step = {
            "step_type": "steady",
            "name": "Cool-down",
            "duration": {
                "type": "time",
                "seconds": cooldown_seconds,
            },
            "target": {
                "type": "zone",
                "zone": "Z1",
            },
            "notes": "Gradual cool-down",
        }

        # Per strength e stretching, non aggiungere warmup e cooldown
        workout_type = workout_data.get("type", "").lower()
        is_strength_or_stretching = workout_type in ["strength", "stretching"]
        
        if is_strength_or_stretching:
            # Solo segmento main per strength e stretching
            # Se c'è già una struttura con esercizi, preservala
            existing_structure = workout_data.get("structure", {})
            existing_segments = existing_structure.get("segments", [])
            main_segment = None
            if existing_segments:
                # Cerca il segmento main nella struttura esistente
                for seg in existing_segments:
                    if seg.get("segment_type") == "main":
                        main_segment = seg
                        break
            
            if main_segment:
                # Usa il segmento main esistente (con esercizi)
                structure_payload = {
                    "sport": normalized_sport,
                    "segments": [main_segment],
                    "metadata": {k: v for k, v in metadata.items() if v is not None},
                }
            else:
                # Crea un segmento main vuoto (fallback)
                structure_payload = {
                    "sport": normalized_sport,
                    "segments": [
                        {
                            "segment_type": "main",
                            "name": workout_data.get("title") or workout_data.get("type") or "Session",
                            "exercises": [],
                            "notes": workout_data.get("modifications"),
                        },
                    ],
                    "metadata": {k: v for k, v in metadata.items() if v is not None},
                }
        else:
            # Per altri sport, includi warmup e cooldown
            structure_payload = {
                "sport": normalized_sport,
                "segments": [
                    {
                        "segment_type": "warmup",
                        "name": "Warm-up",
                        "steps": [warmup_step],
                    },
                    {
                        "segment_type": "main",
                        "name": workout_data.get("title") or workout_data.get("type") or "Session",
                        "steps": [main_step],
                        "notes": workout_data.get("modifications"),
                    },
                    {
                        "segment_type": "cooldown",
                        "name": "Cool-down",
                        "steps": [cooldown_step],
                    },
                ],
                "metadata": {k: v for k, v in metadata.items() if v is not None},
            }

        self._normalize_structure_targets(structure_payload)

        # TEMPORARY FIX: WorkoutStructure validation disabled to prevent recursion
        # Just return the structure_payload as-is (it's already a dict)
        try:
            enriched = self._ensure_structure_segments(
                structure_payload,  # Pass dict instead of WorkoutStructure
                normalized_sport=normalized_sport,
                duration_minutes=duration_minutes,
            )
            return enriched
        except Exception as exc:
            logger.error(f"[WORKOUT_SERVICE] Failed to build fallback structure payload: {exc}")
            raise

    def _ensure_structure_segments(
        self,
        structure: Dict[str, Any],  # Changed from WorkoutStructure to Dict[str, Any]
        *,
        normalized_sport: str,
        duration_minutes: int,
    ) -> Dict[str, Any]:
        # TEMPORARY FIX: Work with dict instead of WorkoutStructure model
        segments = list(structure.get("segments", []))
        has_warmup = any(seg.get("segment_type") == "warmup" for seg in segments)
        has_cooldown = any(seg.get("segment_type") == "cooldown" for seg in segments)

        if has_warmup and has_cooldown:
            return structure

        total_seconds = max(int(duration_minutes * 60), 300)
        warmup_seconds = min(600, max(total_seconds // 10, 180))
        cooldown_seconds = min(600, max(total_seconds // 10, 180))
        zone_easy = "Z1" if normalized_sport not in {"bike", "cycling"} else "Z1"

        def make_step(seconds: int, note: str) -> Dict[str, Any]:
            return {
                "step_type": "steady",
                "duration": {"type": "time", "seconds": seconds},
                "target": {"type": "zone", "zone": zone_easy},
                "notes": note,
                "name": None,
            }

        if not has_warmup:
            warmup_segment = {
                "segment_type": "warmup",
                "name": "Warm-up",
                "steps": [make_step(warmup_seconds, "Gradual warm-up")],
            }
            segments.insert(0, warmup_segment)

        if not has_cooldown:
            cooldown_segment = {
                "segment_type": "cooldown",
                "name": "Cool-down",
                "steps": [make_step(cooldown_seconds, "Gradual cool-down")],
            }
            segments.append(cooldown_segment)

        updated_structure = {
            "sport": structure.get("sport"),
            "segments": segments,
            "metadata": structure.get("metadata"),
            "equipment": structure.get("equipment"),
        }
        return updated_structure

    @staticmethod
    def _normalize_structure_targets(structure: Dict[str, Any]) -> None:
        def normalize_step(step: Dict[str, Any]) -> None:
            target = step.get("target")
            if isinstance(target, dict):
                target_type = target.get("type")
                zone = target.get("zone")
                has_numeric = any(
                    target.get(field) is not None
                    for field in ("min_value", "max_value")
                )

                if target_type in {"heart_rate", "power", "pace"} and zone and not has_numeric:
                    target["type"] = "zone"
                    if isinstance(zone, str):
                        target["zone"] = zone.upper()
                    else:
                        target["zone"] = str(zone).upper()
                    target["min_value"] = None
                    target["max_value"] = None
                    target["units"] = target.get("units")
            nested_steps = step.get("steps")
            if isinstance(nested_steps, list):
                for nested in nested_steps:
                    if isinstance(nested, dict):
                        normalize_step(nested)

        for segment in structure.get("segments", []):
            steps = segment.get("steps")
            if isinstance(steps, list):
                for step in steps:
                    if isinstance(step, dict):
                        normalize_step(step)
    
    # Workout Plans
    def create_workout_plan(self, user_id: int, plan_data: WorkoutPlanCreate) -> WorkoutPlan:
        """Create a new workout plan. Only one active plan per user - existing active plans are paused."""
        logger.info(f"[WORKOUT_SERVICE] Creating workout plan - user_id: {user_id}, title: {plan_data.title}")
        logger.debug(f"[WORKOUT_SERVICE] Plan data: title={plan_data.title}, sport_type={plan_data.sport_type}, level={plan_data.level}, start_date={plan_data.start_date}, end_date={plan_data.end_date}")
        
        # Suspend all existing active plans for this user (only one active plan at a time)
        existing_active_plans = self.db.execute(
            select(WorkoutPlan)
            .where(and_(WorkoutPlan.user_id == user_id, WorkoutPlan.status == "active"))
        ).scalars().all()
        
        if existing_active_plans:
            logger.info(f"[WORKOUT_SERVICE] Pausing {len(existing_active_plans)} existing active plans for user {user_id}")
            for plan in existing_active_plans:
                plan.status = "paused"
            self.db.commit()
        else:
            logger.debug(f"[WORKOUT_SERVICE] No existing active plans to pause")
        
        # Create new plan
        db_plan = WorkoutPlan(
            user_id=user_id,
            **plan_data.dict()
        )
        
        # Calculate total weeks
        delta = plan_data.end_date - plan_data.start_date
        db_plan.total_weeks = delta.days // 7
        logger.debug(f"[WORKOUT_SERVICE] Calculated total_weeks: {db_plan.total_weeks}")
        
        self.db.add(db_plan)
        self.db.commit()
        self.db.refresh(db_plan)
        
        logger.info(f"[WORKOUT_SERVICE] Workout plan created successfully - plan_id: {db_plan.id}, total_weeks: {db_plan.total_weeks}")
        return db_plan
    
    def _archive_workouts_from_plan(self, plan_id: int):
        """Archive workouts from a plan before deleting it"""
        # Get all workouts for this plan
        workouts = self.db.execute(
            select(Workout)
            .where(Workout.plan_id == plan_id)
        ).scalars().all()
        
        # Update workouts to historical status (remove from plan but keep in history)
        for workout in workouts:
            workout.plan_id = None  # Remove from plan
            workout.status = WorkoutStatus.COMPLETED  # Mark as completed for history
            # Keep the workout in the database for historical purposes
    
    def create_workouts_from_ai_plan(self, user_id: int, plan_id: int, ai_plan_data: Dict[str, Any]) -> List[Workout]:
        """Create individual workouts from AI plan data"""
        logger.info(f"[WORKOUT_SERVICE] Creating workouts from AI plan - user_id: {user_id}, plan_id: {plan_id}")
        logger.debug(f"[WORKOUT_SERVICE] AI plan data keys: {list(ai_plan_data.keys())}")
        
        workouts = []
        
        if "weeks" not in ai_plan_data:
            logger.warning(f"[WORKOUT_SERVICE] AI plan data missing 'weeks' key, returning empty workouts list")
            return workouts
        
        # Get the plan to get start date
        plan = self.get_workout_plan(plan_id, user_id)
        if not plan:
            logger.error(f"[WORKOUT_SERVICE] Plan {plan_id} not found for user {user_id}")
            return workouts
        
        logger.debug(f"[WORKOUT_SERVICE] Plan found - start_date: {plan.start_date}, total_weeks: {plan.total_weeks}")
        current_date = plan.start_date
        
        total_weeks = len(ai_plan_data["weeks"])
        logger.info(f"[WORKOUT_SERVICE] Processing {total_weeks} weeks from AI plan")
        
        for week_data in ai_plan_data["weeks"]:
            week_number = week_data.get("week", 1)
            week_workouts = week_data.get("workouts", [])
            logger.debug(f"[WORKOUT_SERVICE] Processing week {week_number} with {len(week_workouts)} workouts")
            
            for workout_data in week_workouts:
                # Calculate scheduled date
                day_mapping = {
                    "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3,
                    "Friday": 4, "Saturday": 5, "Sunday": 6
                }
                day_offset = day_mapping.get(workout_data.get("day", "Monday"), 0)
                scheduled_date = current_date + timedelta(days=day_offset)
                
                # Create workout
                title = self._clean_text(workout_data.get("type", "Workout"), "Workout", max_length=200)
                workout_type = self._clean_text(workout_data.get("type", "endurance"), "endurance", max_length=50)
                intensity = self._clean_text(workout_data.get("intensity", "moderate"), "moderate", max_length=20)
                zone_value = self._extract_zone(workout_data, fallback=intensity if intensity.upper().startswith("Z") else "Z2")
                zone = self._clean_text(zone_value, "Z2", max_length=10)

                structure_payload = self._build_structure_payload(
                    plan_sport=plan.sport_type,
                    workout_data=workout_data,
                    week_focus=week_data.get("focus"),
                )

                workout = Workout(
                    plan_id=plan_id,
                    user_id=user_id,
                    title=title,
                    type=workout_type,
                    day_number=len(workouts) + 1,
                    scheduled_date=scheduled_date,
                    duration_minutes=workout_data.get("duration_minutes", 60),
                    intensity=intensity,
                    zone=zone,
                    structure_json=structure_payload,
                    status=WorkoutStatus.SCHEDULED
                )
                
                self.db.add(workout)
                workouts.append(workout)
            
            # Move to next week
            current_date += timedelta(days=7)
        
        self.db.commit()
        logger.info(f"[WORKOUT_SERVICE] Created {len(workouts)} workouts from AI plan successfully")
        return workouts
    
    def create_workouts_from_progressive_week(self, user_id: int, plan_id: int, week_data: Dict[str, Any]) -> List[Workout]:
        """Create individual workouts from progressive plan week data"""
        logger.info(f"[WORKOUT_SERVICE] Creating workouts from progressive week - user_id: {user_id}, plan_id: {plan_id}")
        logger.debug(f"[WORKOUT_SERVICE] Week data keys: {list(week_data.keys())}")
        
        workouts = []
        
        if "workouts" not in week_data:
            logger.warning(f"[WORKOUT_SERVICE] Week data missing 'workouts' key, returning empty workouts list")
            return workouts
        
        # Get the plan to get start date
        plan = self.get_workout_plan(plan_id, user_id)
        if not plan:
            logger.error(f"[WORKOUT_SERVICE] Plan {plan_id} not found for user {user_id}")
            return workouts
        
        # Always use plan start_date to calculate week start date
        # This ensures workouts are aligned with the plan dates
        week_number = week_data.get("week", 1)
        
        # Per la prima settimana, usa la data di inizio del piano direttamente
        # Per settimane successive, calcola dal lunedì successivo alla domenica della settimana 1
        if week_number == 1:
            week_start = plan.start_date
            # Per la prima settimana, il mapping dei giorni deve essere relativo alla data di inizio
            start_weekday = plan.start_date.weekday()  # 0=lunedì, 6=domenica
        else:
            # Settimane successive: calcola il lunedì della settimana
            # La settimana 1 finisce domenica, quindi la settimana 2 inizia lunedì successivo
            week1_end = plan.start_date + timedelta(days=(6 - plan.start_date.weekday()))
            week_start = week1_end + timedelta(days=1)  # Lunedì successivo
            if week_number > 2:
                week_start = week_start + timedelta(weeks=week_number - 2)
            start_weekday = 0  # Sempre lunedì per settimane successive
        
        logger.debug(f"[WORKOUT_SERVICE] Week {week_number} start date: {week_start}, start_weekday: {start_weekday}")
        
        week_workouts = week_data.get("workouts", [])
        week_focus = week_data.get("focus", "Base Building")
        logger.info(f"[WORKOUT_SERVICE] Processing {len(week_workouts)} workouts for week {week_number} (focus: {week_focus})")
        
        # Mapping giorni della settimana
        day_mapping = {
            "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3,
            "Friday": 4, "Saturday": 5, "Sunday": 6
        }
        
        for workout_data in week_workouts:
            # Calculate scheduled date
            workout_day = workout_data.get("day", "Monday")
            day_offset_in_week = day_mapping.get(workout_day, 0)
            
            if week_number == 1:
                # Prima settimana: calcola offset relativo alla data di inizio
                # Se la settimana inizia mercoledì (weekday=2) e l'allenamento è per mercoledì (offset=2),
                # l'offset relativo è 0
                relative_offset = day_offset_in_week - start_weekday
                # Se l'offset è negativo, significa che il giorno richiesto è prima della data di inizio
                # (non dovrebbe succedere se l'AI ha seguito le istruzioni, ma gestiamo il caso)
                if relative_offset < 0:
                    logger.warning(f"[WORKOUT_SERVICE] Workout day {workout_day} is before start date {plan.start_date}, skipping")
                    continue
                scheduled_date = week_start + timedelta(days=relative_offset)
            else:
                # Settimane successive: sempre da lunedì, quindi offset normale
                scheduled_date = week_start + timedelta(days=day_offset_in_week)
            
            # Create workout
            title = self._clean_text(workout_data.get("type", "Workout"), "Workout", max_length=200)
            workout_type = self._clean_text(workout_data.get("type", "endurance"), "endurance", max_length=50)
            intensity = self._clean_text(workout_data.get("intensity", "moderate"), "moderate", max_length=20)
            zone_value = self._extract_zone(workout_data, fallback=intensity if intensity.upper().startswith("Z") else "Z2")
            zone = self._clean_text(zone_value, "Z2", max_length=10)

            structure_payload = self._build_structure_payload(
                plan_sport=plan.sport_type,
                workout_data=workout_data,
                week_focus=week_focus,
            )

            # Validazione struttura workout (es. Hyrox deve avere 8 round)
            workout_dict = {
                "sport_type": plan.sport_type,
                "structure_json": structure_payload
            }
            is_valid, error_msg = validate_workout_structure(workout_dict)
            if not is_valid:
                logger.warning(f"[WORKOUT_SERVICE] Invalid workout structure for {title}: {error_msg}")
                # Per ora loggiamo solo, non blocchiamo la creazione (l'AI dovrebbe generare strutture corrette)
                # In futuro possiamo sollevare un'eccezione se necessario

            workout = Workout(
                plan_id=plan_id,
                user_id=user_id,
                title=title,
                type=workout_type,
                day_number=len(workouts) + 1,
                scheduled_date=scheduled_date,
                duration_minutes=workout_data.get("duration_minutes", 60),
                intensity=intensity,
                zone=zone,
                structure_json=structure_payload,
                status=WorkoutStatus.SCHEDULED
            )
            
            self.db.add(workout)
            workouts.append(workout)
        
        self.db.commit()
        logger.info(f"[WORKOUT_SERVICE] Created {len(workouts)} workouts from progressive week successfully")
        return workouts
    
    def create_calendar_events_from_workouts(self, user_id: int, workouts: List[Workout]) -> List[CalendarEvent]:
        """Create calendar events from workouts"""
        events = []
        
        for workout in workouts:
            if not workout.scheduled_date:
                continue
                
            # Create calendar event for workout
            event = CalendarEvent(
                user_id=user_id,
                workout_id=workout.id,
                title=workout.title,
                event_type="workout",
                scheduled_date=workout.scheduled_date,
                duration_minutes=workout.duration_minutes,
                is_recurring=False
            )
            
            self.db.add(event)
            events.append(event)
        
        self.db.commit()
        return events
    
    def _is_progressive_plan(self, plan: WorkoutPlan) -> bool:
        """Determine if a plan is progressive based on description"""
        if not plan.description:
            return False
        # Check if description contains "progressivo" or "progressive"
        description_lower = plan.description.lower()
        return "progressivo" in description_lower or "progressive" in description_lower
    
    def get_workout_plans(self, user_id: int, skip: int = 0, limit: int = 100) -> List[WorkoutPlan]:
        """Get user's workout plans"""
        return self.db.execute(
            select(WorkoutPlan)
            .where(WorkoutPlan.user_id == user_id)
            .offset(skip)
            .limit(limit)
        ).scalars().all()
    
    def get_workout_plan(self, plan_id: int, user_id: int) -> Optional[WorkoutPlan]:
        """Get specific workout plan"""
        return self.db.execute(
            select(WorkoutPlan)
            .where(and_(WorkoutPlan.id == plan_id, WorkoutPlan.user_id == user_id))
        ).scalar_one_or_none()
    
    def update_workout_plan(self, plan_id: int, user_id: int, plan_data: WorkoutPlanUpdate) -> Optional[WorkoutPlan]:
        """Update workout plan"""
        plan = self.get_workout_plan(plan_id, user_id)
        if not plan:
            return None
        
        update_data = plan_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(plan, field, value)
        
        self.db.commit()
        self.db.refresh(plan)
        return plan
    
    def delete_workout_plan(self, plan_id: int, user_id: int) -> bool:
        """Delete workout plan"""
        plan = self.get_workout_plan(plan_id, user_id)
        if not plan:
            return False
        
        self.db.delete(plan)
        self.db.commit()
        return True
    
    # Workouts
    def create_workout(self, user_id: int, workout_data: WorkoutCreate) -> Workout:
        """Create a new workout"""
        db_workout = Workout(
            user_id=user_id,
            **workout_data.dict()
        )
        
        self.db.add(db_workout)
        self.db.commit()
        self.db.refresh(db_workout)
        
        # If workout is standalone (no plan_id) and has a scheduled_date, create a calendar event
        if db_workout.plan_id is None and db_workout.scheduled_date:
            self.create_calendar_event(
                user_id=user_id,
                workout_id=db_workout.id,
                title=db_workout.title,
                event_type="workout",
                scheduled_date=db_workout.scheduled_date,
                duration_minutes=db_workout.duration_minutes,
                is_recurring=False
            )
        
        return db_workout
    
    def get_workouts(self, user_id: int, skip: int = 0, limit: int = 100, 
                    plan_id: Optional[int] = None) -> List[Workout]:
        """Get user's workouts"""
        query = select(Workout).where(Workout.user_id == user_id)
        
        if plan_id:
            query = query.where(Workout.plan_id == plan_id)
        
        return self.db.execute(
            query.offset(skip).limit(limit)
        ).scalars().all()
    
    def get_workout(self, workout_id: int, user_id: int) -> Optional[Workout]:
        """Get specific workout"""
        return self.db.execute(
            select(Workout)
            .where(and_(Workout.id == workout_id, Workout.user_id == user_id))
        ).scalar_one_or_none()
    
    def update_workout(self, workout_id: int, user_id: int, workout_data: WorkoutUpdate) -> Optional[Workout]:
        """Update workout"""
        workout = self.get_workout(workout_id, user_id)
        if not workout:
            return None
        
        update_data = workout_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(workout, field, value)
        
        self.db.commit()
        self.db.refresh(workout)
        return workout
    
    def delete_workout(self, workout_id: int, user_id: int) -> bool:
        """Delete workout"""
        workout = self.get_workout(workout_id, user_id)
        if not workout:
            return False
        
        self.db.delete(workout)
        self.db.commit()
        return True
    
    # Workout Sessions
    def create_workout_session(self, user_id: int, session_data: WorkoutSessionCreate) -> WorkoutSession:
        """Create a new workout session"""
        db_session = WorkoutSession(
            user_id=user_id,
            **session_data.dict()
        )
        
        self.db.add(db_session)
        self.db.commit()
        self.db.refresh(db_session)
        
        return db_session
    
    def get_workout_sessions(self, user_id: int, workout_id: Optional[int] = None,
                           skip: int = 0, limit: int = 100) -> List[WorkoutSession]:
        """Get workout sessions"""
        query = select(WorkoutSession).where(WorkoutSession.user_id == user_id)
        
        if workout_id:
            query = query.where(WorkoutSession.workout_id == workout_id)
        
        return self.db.execute(
            query.offset(skip).limit(limit)
        ).scalars().all()
    
    def get_workout_session(self, session_id: int, user_id: int) -> Optional[WorkoutSession]:
        """Get specific workout session"""
        return self.db.execute(
            select(WorkoutSession)
            .where(and_(WorkoutSession.id == session_id, WorkoutSession.user_id == user_id))
        ).scalar_one_or_none()
    
    # Calendar Integration
    def create_calendar_event(self, user_id: int, workout_id: Optional[int], 
                            title: str, event_type: str, scheduled_date: date,
                            duration_minutes: int, is_recurring: bool = False) -> CalendarEvent:
        """Create calendar event for workout"""
        db_event = CalendarEvent(
            user_id=user_id,
            workout_id=workout_id,
            title=title,
            event_type=event_type,
            scheduled_date=scheduled_date,
            duration_minutes=duration_minutes,
            is_recurring=is_recurring
        )
        
        self.db.add(db_event)
        self.db.commit()
        self.db.refresh(db_event)
        
        return db_event
    
    def get_calendar_events(self, user_id: int, start_date: date, end_date: date) -> List[CalendarEvent]:
        """Get calendar events for date range, excluding inactive plans"""
        import logging
        logger = logging.getLogger(__name__)
        
        # Get all matching calendar events
        query = (
            select(CalendarEvent)
            .where(
                and_(
                    CalendarEvent.user_id == user_id,
                    CalendarEvent.scheduled_date >= start_date,
                    CalendarEvent.scheduled_date <= end_date
                )
            )
        )
        all_events = self.db.execute(query).scalars().all()
        logger.info(f"Found {len(all_events)} total calendar events")
        
        # Get all workout IDs that belong to inactive plans (for this user)
        inactive_plan_workout_ids = self.db.execute(
            select(Workout.id)
            .join(WorkoutPlan, Workout.plan_id == WorkoutPlan.id)
            .where(
                and_(
                    WorkoutPlan.user_id == user_id,
                    WorkoutPlan.status != "active"
                )
            )
        ).scalars().all()
        inactive_plan_workout_ids = set(inactive_plan_workout_ids)
        logger.info(f"Found {len(inactive_plan_workout_ids)} workouts from inactive plans: {inactive_plan_workout_ids}")
        
        # Filter events: exclude those with workout_id in inactive plans
        filtered_events = [
            event for event in all_events 
            if event.workout_id is None or event.workout_id not in inactive_plan_workout_ids
        ]
        logger.info(f"Returning {len(filtered_events)} filtered calendar events")
        
        return filtered_events
    
    def get_upcoming_workouts(self, user_id: int, days: int = 7) -> List[Workout]:
        """Get upcoming workouts for the next N days"""
        from datetime import timedelta
        end_date = date.today() + timedelta(days=days)
        
        return self.db.execute(
            select(Workout)
            .where(
                and_(
                    Workout.user_id == user_id,
                    Workout.scheduled_date >= date.today(),
                    Workout.scheduled_date <= end_date,
                    Workout.status == "scheduled"
                )
            )
        ).scalars().all()
    
    def get_workout_plan_with_details(self, plan_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Get workout plan with all workouts, sessions, and Strava details"""
        # Get the plan
        plan = self.get_workout_plan(plan_id, user_id)
        if not plan:
            return None
        
        # Get all workouts for this plan
        workouts = self.db.execute(
            select(Workout)
            .where(and_(Workout.plan_id == plan_id, Workout.user_id == user_id))
            .order_by(Workout.scheduled_date.asc(), Workout.day_number.asc())
        ).scalars().all()
        
        # Get all sessions for these workouts
        workout_ids = [w.id for w in workouts]
        sessions = []
        if workout_ids:
            sessions = self.db.execute(
                select(WorkoutSession)
                .where(WorkoutSession.workout_id.in_(workout_ids))
                .order_by(WorkoutSession.actual_date.desc())
            ).scalars().all()
        
        # Get all Strava activities for these workouts
        strava_activities = []
        if workout_ids:
            strava_activities = self.db.execute(
                select(StravaActivity)
                .where(StravaActivity.workout_id.in_(workout_ids))
            ).scalars().all()
        
        # Organize sessions by workout_id
        sessions_by_workout = {}
        for session in sessions:
            if session.workout_id not in sessions_by_workout:
                sessions_by_workout[session.workout_id] = []
            sessions_by_workout[session.workout_id].append(session)
        
        # Organize Strava activities by workout_id
        strava_by_workout = {}
        for activity in strava_activities:
            if activity.workout_id:
                strava_by_workout[activity.workout_id] = activity
        
        # Build detailed workouts
        detailed_workouts = []
        for workout in workouts:
            workout_detail = {
                "id": workout.id,
                "plan_id": workout.plan_id,
                "user_id": workout.user_id,
                "title": workout.title,
                "type": workout.type,
                "day_number": workout.day_number,
                "scheduled_date": workout.scheduled_date.isoformat() if workout.scheduled_date else None,
                "duration_minutes": workout.duration_minutes,
                "intensity": workout.intensity,
                "zone": workout.zone,
                "structure_json": workout.structure_json,
                "status": workout.status.value if workout.status else None,
                "notes": workout.notes,
                "created_at": workout.created_at.isoformat() if workout.created_at else None,
                "updated_at": workout.updated_at.isoformat() if workout.updated_at else None,
                "sessions": [],
                "strava_activity": None
            }
            
            # Add sessions
            if workout.id in sessions_by_workout:
                for session in sessions_by_workout[workout.id]:
                    workout_detail["sessions"].append({
                        "id": session.id,
                        "workout_id": session.workout_id,
                        "user_id": session.user_id,
                        "actual_date": session.actual_date.isoformat() if session.actual_date else None,
                        "duration_minutes": session.duration_minutes,
                        "avg_hr": session.avg_hr,
                        "max_hr": session.max_hr,
                        "avg_pace": session.avg_pace,
                        "avg_power": session.avg_power,
                        "perceived_exertion": session.perceived_exertion,
                        "notes": session.notes,
                        "created_at": session.created_at.isoformat() if session.created_at else None
                    })
            
            # Add Strava activity
            if workout.id in strava_by_workout:
                activity = strava_by_workout[workout.id]
                workout_detail["strava_activity"] = {
                    "id": activity.id,
                    "strava_activity_id": activity.strava_activity_id,
                    "name": activity.name,
                    "type": activity.type,
                    "sport_type": activity.sport_type,
                    "start_date": activity.start_date.isoformat() if activity.start_date else None,
                    "start_date_local": activity.start_date_local.isoformat() if activity.start_date_local else None,
                    "timezone": activity.timezone,
                    "distance": activity.distance,
                    "moving_time": activity.moving_time,
                    "elapsed_time": activity.elapsed_time,
                    "total_elevation_gain": activity.total_elevation_gain,
                    "average_speed": activity.average_speed,
                    "max_speed": activity.max_speed,
                    "average_heartrate": activity.average_heartrate,
                    "max_heartrate": activity.max_heartrate,
                    "average_watts": activity.average_watts,
                    "max_watts": activity.max_watts,
                    "weighted_average_watts": activity.weighted_average_watts,
                    "average_cadence": activity.average_cadence,
                    "temperature": activity.temperature,
                    "feels_like": activity.feels_like,
                    "calories": activity.calories,
                    "kilojoules": activity.kilojoules,
                    "is_synced": activity.is_synced,
                    "sync_status": activity.sync_status,
                    "splits_metric": activity.splits_metric,
                    "splits_standard": activity.splits_standard,
                    "best_efforts": activity.best_efforts,
                    "segment_efforts": activity.segment_efforts,
                    "raw_data": activity.raw_data,
                    "created_at": activity.created_at.isoformat() if activity.created_at else None
                }
            
            detailed_workouts.append(workout_detail)
        
        # Group workouts by week
        workouts_by_week = {}
        for workout_detail in detailed_workouts:
            if workout_detail["scheduled_date"]:
                scheduled_date = datetime.strptime(workout_detail["scheduled_date"], "%Y-%m-%d").date()
                days_since_start = (scheduled_date - plan.start_date).days
                week_number = (days_since_start // 7) + 1
                
                if week_number not in workouts_by_week:
                    week_start = plan.start_date + timedelta(weeks=week_number - 1)
                    week_end = week_start + timedelta(days=6)
                    workouts_by_week[week_number] = {
                        "week_number": week_number,
                        "week_start_date": week_start.isoformat(),
                        "week_end_date": week_end.isoformat(),
                        "workouts": []
                    }
                
                workouts_by_week[week_number]["workouts"].append(workout_detail)
            else:
                # Workouts without scheduled_date go to week 0
                if 0 not in workouts_by_week:
                    workouts_by_week[0] = {
                        "week_number": 0,
                        "week_start_date": None,
                        "week_end_date": None,
                        "workouts": []
                    }
                workouts_by_week[0]["workouts"].append(workout_detail)
        
        # Convert to list sorted by week number
        workouts_organized = [workouts_by_week[week] for week in sorted(workouts_by_week.keys())]
        
        # Calculate statistics
        total_workouts = len(workouts)
        completed_workouts = len([w for w in workouts if w.status == WorkoutStatus.COMPLETED])
        skipped_workouts = len([w for w in workouts if w.status == WorkoutStatus.SKIPPED])
        scheduled_workouts = len([w for w in workouts if w.status == WorkoutStatus.SCHEDULED])
        workouts_with_strava = len([w for w in workouts if w.id in strava_by_workout])
        
        # Determine if plan is progressive
        is_progressive = self._is_progressive_plan(plan)
        
        # Build plan details
        plan_details = {
            "id": plan.id,
            "user_id": plan.user_id,
            "title": plan.title,
            "description": plan.description,
            "start_date": plan.start_date.isoformat() if plan.start_date else None,
            "end_date": plan.end_date.isoformat() if plan.end_date else None,
            "total_weeks": plan.total_weeks,
            "goal": plan.goal,
            "sport_type": plan.sport_type,
            "level": plan.level,
            "status": plan.status,
            "is_progressive": is_progressive,
            "created_at": plan.created_at.isoformat() if plan.created_at else None,
            "updated_at": plan.updated_at.isoformat() if plan.updated_at else None,
            "workouts": detailed_workouts,  # Array piatto - tutti i workouts
            "workouts_by_week": workouts_organized,  # Array raggruppato per settimana
            "total_workouts": total_workouts,
            "completed_workouts": completed_workouts,
            "skipped_workouts": skipped_workouts,
            "scheduled_workouts": scheduled_workouts,
            "workouts_with_strava": workouts_with_strava
        }
        
        return plan_details
    
    def get_suggested_workout(self, user_id: int, target_date: Optional[date] = None) -> Optional[Dict[str, Any]]:
        """
        Get suggested workout for today based on readiness, CTL/ATL/TSB, and active plan.
        
        Args:
            user_id: User ID
            target_date: Date for suggestion (default: today)
        
        Returns:
            Dict with suggested workout and reasoning, or None if no suggestion
        """
        if target_date is None:
            target_date = date.today()
        
        # Get today's readiness metrics
        readiness = self.db.query(DailyReadinessMetrics).filter(
            DailyReadinessMetrics.user_id == user_id,
            DailyReadinessMetrics.metric_date == target_date
        ).first()
        
        # Get today's performance metrics (CTL/ATL/TSB)
        performance = self.db.query(DailyPerformanceMetrics).filter(
            DailyPerformanceMetrics.user_id == user_id,
            DailyPerformanceMetrics.metric_date == target_date
        ).first()
        
        # Get workouts completed today
        today_workouts = self.db.query(Workout).filter(
            Workout.user_id == user_id,
            Workout.scheduled_date == target_date,
            Workout.status == WorkoutStatus.COMPLETED
        ).all()
        
        # Get active plan
        active_plan = self.db.query(WorkoutPlan).filter(
            WorkoutPlan.user_id == user_id,
            WorkoutPlan.status == "active"
        ).first()
        
        # Determine workout suggestion based on metrics
        suggestion_reason = []
        suggested_intensity = "moderate"
        suggested_zone = "Z2"
        suggested_duration = 60
        suggested_type = "endurance"
        
        # Collect metrics for detailed reasoning
        metrics_details = {}
        
        # Check HRV (Heart Rate Variability)
        hrv_score = None
        if readiness and readiness.hrv_value is not None and readiness.hrv_baseline is not None:
            hrv_ratio = readiness.hrv_value / readiness.hrv_baseline if readiness.hrv_baseline > 0 else 1.0
            metrics_details["hrv_ratio"] = round(hrv_ratio, 2)
            metrics_details["hrv_value"] = readiness.hrv_value
            metrics_details["hrv_baseline"] = readiness.hrv_baseline
            
            if hrv_ratio < 0.85:
                # HRV significantly below baseline - suggest recovery
                suggested_intensity = "easy"
                suggested_zone = "Z1"
                suggested_type = "recovery"
                suggested_duration = min(suggested_duration, 45)
                suggestion_reason.append(f"HRV {hrv_ratio*100:.0f}% del baseline - recupero consigliato")
                hrv_score = 0.3  # Low score
            elif hrv_ratio > 1.1:
                # HRV above baseline - good recovery
                suggested_intensity = "moderate"
                suggested_zone = "Z3"
                suggested_type = "interval"
                suggestion_reason.append(f"HRV {hrv_ratio*100:.0f}% del baseline - forma ottima")
                hrv_score = 0.9  # High score
            else:
                hrv_score = 0.6  # Normal score
        
        # Check sleep quality
        sleep_score = None
        if readiness and readiness.sleep_hours is not None:
            sleep_hours = readiness.sleep_hours
            metrics_details["sleep_hours"] = sleep_hours
            
            if sleep_hours < 6:
                # Poor sleep - suggest easier workout
                suggested_intensity = "easy" if suggested_intensity != "recovery" else "recovery"
                suggested_zone = "Z1" if suggested_zone != "Z1" else "Z1"
                suggested_duration = min(suggested_duration, 45)
                suggestion_reason.append(f"Solo {sleep_hours:.1f}h di sonno - workout leggero consigliato")
                sleep_score = 0.3
            elif sleep_hours >= 8:
                # Good sleep - can do harder workout
                if hrv_score is None or hrv_score > 0.5:
                    suggested_intensity = "moderate"
                    suggested_zone = "Z3" if suggested_zone != "Z1" else "Z2"
                sleep_score = 0.8
            else:
                sleep_score = 0.6
        
        if readiness and readiness.sleep_quality_score is not None:
            metrics_details["sleep_quality"] = readiness.sleep_quality_score
            if readiness.sleep_quality_score < 0.5:
                # Poor sleep quality
                suggested_intensity = "easy" if suggested_intensity != "recovery" else "recovery"
                suggested_zone = "Z1"
                suggestion_reason.append("Qualità del sonno bassa - recupero consigliato")
        
        # Check readiness score (combined with HRV and sleep)
        if readiness and readiness.recovery_index is not None:
            recovery_index = readiness.recovery_index
            metrics_details["recovery_index"] = recovery_index
            
            # Weight recovery_index less if we have HRV and sleep data
            if hrv_score is not None or sleep_score is not None:
                # Use weighted average if we have multiple metrics
                combined_score = recovery_index
                if hrv_score is not None:
                    combined_score = (combined_score * 0.5) + (hrv_score * 0.3)
                if sleep_score is not None:
                    combined_score = (combined_score * 0.7) + (sleep_score * 0.2)
                
                if combined_score < 0.4:
                    suggested_intensity = "easy"
                    suggested_zone = "Z1"
                    suggested_type = "recovery"
                    suggested_duration = 30
                    suggestion_reason.append("Recovery score basso - workout di recupero consigliato")
                elif combined_score > 0.8:
                    suggested_intensity = "moderate"
                    suggested_zone = "Z3"
                    suggested_type = "interval"
                    suggestion_reason.append("Recovery score alto - puoi fare un workout più intenso")
            else:
                # Fallback to original logic if no HRV/sleep
                if recovery_index < 0.4:
                    suggested_intensity = "easy"
                    suggested_zone = "Z1"
                    suggested_type = "recovery"
                    suggested_duration = 30
                    suggestion_reason.append("Recovery score basso - workout di recupero consigliato")
                elif recovery_index > 0.8:
                    suggested_intensity = "moderate"
                    suggested_zone = "Z3"
                    suggested_type = "interval"
                    suggestion_reason.append("Recovery score alto - puoi fare un workout più intenso")
        
        # Check TSB (Training Stress Balance)
        if performance and performance.tsb is not None:
            tsb = performance.tsb
            metrics_details["tsb"] = round(tsb, 1)
            
            if tsb < -10:
                # Negative TSB - fatigued, suggest easy
                suggested_intensity = "easy"
                suggested_zone = "Z1"
                suggested_type = "recovery"
                suggested_duration = min(suggested_duration, 45)
                suggestion_reason.append(f"TSB negativo ({tsb:.1f}) - recupero necessario")
            elif tsb > 10:
                # Positive TSB - fresh, can do harder
                if hrv_score is None or hrv_score > 0.5:
                    suggested_intensity = "moderate"
                    suggested_zone = "Z3"
                    suggested_type = "interval"
                    suggestion_reason.append(f"TSB positivo ({tsb:.1f}) - forma buona per workout intenso")
        
        # Check if already completed workout today
        if today_workouts:
            total_duration = sum(w.duration_minutes or 0 for w in today_workouts)
            if total_duration >= 90:
                # Already did significant workout - suggest rest or very easy
                suggested_intensity = "easy"
                suggested_zone = "Z1"
                suggested_type = "recovery"
                suggested_duration = 20
                suggestion_reason.append(f"Già completato {total_duration} minuti oggi - recupero consigliato")
                return {
                    "workout": None,
                    "suggestion": "rest",
                    "reason": " ".join(suggestion_reason) if suggestion_reason else "Hai già fatto abbastanza oggi",
                    "metrics": {
                        "recovery_index": readiness.recovery_index if readiness else None,
                        "tsb": performance.tsb if performance else None,
                        "workouts_today": len(today_workouts),
                        "total_duration_today": total_duration,
                        **metrics_details
                    }
                }
        
        # Get scheduled workout from active plan for today
        scheduled_workout = None
        if active_plan:
            scheduled_workout = self.db.query(Workout).filter(
                Workout.user_id == user_id,
                Workout.plan_id == active_plan.id,
                Workout.scheduled_date == target_date,
                Workout.status == WorkoutStatus.SCHEDULED
            ).first()
        
        # If there's a scheduled workout, suggest that
        if scheduled_workout:
            return {
                "workout": {
                    "id": scheduled_workout.id,
                    "title": scheduled_workout.title,
                    "type": scheduled_workout.type,
                    "duration_minutes": scheduled_workout.duration_minutes,
                    "zone": scheduled_workout.zone,
                    "intensity": scheduled_workout.intensity,
                    "structure_json": scheduled_workout.structure_json,
                    "plan_id": scheduled_workout.plan_id,
                    "plan_title": active_plan.title if active_plan else None
                },
                "suggestion": "scheduled",
                "reason": "Workout pianificato per oggi dal tuo piano attivo",
                "metrics": {
                    "recovery_index": readiness.recovery_index if readiness else None,
                    "tsb": performance.tsb if performance else None,
                    "workouts_today": len(today_workouts),
                    **metrics_details
                }
            }
        
        # No scheduled workout - suggest based on metrics
        if not suggestion_reason:
            suggestion_reason.append("Nessun workout pianificato per oggi")
        
        # Determine sport type from active plan or default to run
        sport_type = active_plan.sport_type if active_plan else "run"
        
        return {
            "workout": {
                "title": f"Workout {suggested_type.capitalize()} Suggerito",
                "type": suggested_type,
                "sport_type": sport_type,
                "duration_minutes": suggested_duration,
                "zone": suggested_zone,
                "intensity": suggested_intensity,
                "structure_json": None,  # Will be generated if user starts
                "plan_id": None,
                "is_suggested": True
            },
            "suggestion": "generated",
            "reason": " ".join(suggestion_reason) if suggestion_reason else "Workout suggerito basato sulle tue metriche",
            "metrics": {
                "recovery_index": readiness.recovery_index if readiness else None,
                "tsb": performance.tsb if performance else None,
                "ctl": performance.ctl if performance else None,
                "atl": performance.atl if performance else None,
                "workouts_today": len(today_workouts),
                **metrics_details
            }
        }

    def calculate_future_projections(
        self, user_id: int, weeks: int = 12
    ) -> Dict[str, Any]:
        """Project CTL/ATL/TSB into the future based on active plan and scheduled workouts."""
        from app.models.daily_metrics import DailyPerformanceMetrics
        from app.models.training_metrics import TrainingMetrics

        today = date.today()
        current = (
            self.db.query(DailyPerformanceMetrics)
            .filter(
                DailyPerformanceMetrics.user_id == user_id,
                DailyPerformanceMetrics.metric_date == today,
            )
            .first()
        )
        if not current:
            current = (
                self.db.query(DailyPerformanceMetrics)
                .filter(DailyPerformanceMetrics.user_id == user_id)
                .order_by(desc(DailyPerformanceMetrics.metric_date))
                .first()
            )
        if not current:
            return {
                "historical": [],
                "projections": [],
                "current_ctl": None,
                "current_atl": None,
                "current_tsb": None,
                "plan_id": None,
                "plan_title": None,
            }

        plan = (
            self.db.query(WorkoutPlan)
            .filter(
                WorkoutPlan.user_id == user_id,
                WorkoutPlan.status == "active",
            )
            .first()
        )
        if not plan:
            return {
                "historical": [],
                "projections": [],
                "current_ctl": round(current.ctl, 1) if current.ctl is not None else None,
                "current_atl": round(current.atl, 1) if current.atl is not None else None,
                "current_tsb": round(current.tsb, 1) if current.tsb is not None else None,
                "plan_id": None,
                "plan_title": None,
            }

        future = (
            self.db.query(Workout)
            .filter(
                Workout.user_id == user_id,
                Workout.plan_id == plan.id,
                Workout.scheduled_date > today,
                Workout.status == WorkoutStatus.SCHEDULED,
            )
            .order_by(Workout.scheduled_date.asc())
            .all()
        )

        defaults = {"endurance": 50.0, "interval": 80.0, "recovery": 20.0, "strength": 30.0}
        avg_tss: Dict[str, float] = {}
        for wt in ("endurance", "interval", "recovery", "strength"):
            avg = (
                self.db.query(sql_func.avg(TrainingMetrics.tss))
                .join(
                    WorkoutSession,
                    TrainingMetrics.workout_session_id == WorkoutSession.id,
                )
                .join(Workout, WorkoutSession.workout_id == Workout.id)
                .filter(Workout.user_id == user_id, Workout.type == wt)
            ).scalar()
            avg_tss[wt] = float(avg) if avg else defaults.get(wt, 50.0)

        by_date: Dict[str, list] = {}
        for w in future:
            if w.scheduled_date:
                d = w.scheduled_date.isoformat()
                by_date.setdefault(d, []).append(w)

        ctl_tc, atl_tc = 42.0, 7.0
        ctl_decay = 2 ** (-1.0 / ctl_tc)
        atl_decay = 2 ** (-1.0 / atl_tc)

        proj_ctl = float(current.ctl or 0.0)
        proj_atl = float(current.atl or 0.0)
        projections: List[Dict[str, Any]] = []

        for w in range(weeks):
            for d in range(7):
                d_date = today + timedelta(weeks=w, days=d)
                proj_ctl *= ctl_decay
                proj_atl *= atl_decay
                ds = d_date.isoformat()
                daily_tss = sum(
                    avg_tss.get((wkt.type or "endurance"), 50.0)
                    for wkt in by_date.get(ds, [])
                )
                if daily_tss > 0:
                    proj_ctl += daily_tss * (1.0 - ctl_decay)
                    proj_atl += daily_tss * (1.0 - atl_decay)
                if d in (0, 6):
                    projections.append({
                        "date": ds,
                        "ctl": round(proj_ctl, 1),
                        "atl": round(proj_atl, 1),
                        "tsb": round(proj_ctl - proj_atl, 1),
                        "daily_tss": round(daily_tss, 1),
                    })

        four_weeks_ago = today - timedelta(weeks=4)
        hist = (
            self.db.query(DailyPerformanceMetrics)
            .filter(
                DailyPerformanceMetrics.user_id == user_id,
                DailyPerformanceMetrics.metric_date >= four_weeks_ago,
                DailyPerformanceMetrics.metric_date <= today,
            )
            .order_by(DailyPerformanceMetrics.metric_date.asc())
            .all()
        )
        historical = [
            {
                "date": m.metric_date.isoformat(),
                "ctl": round(m.ctl, 1) if m.ctl is not None else None,
                "atl": round(m.atl, 1) if m.atl is not None else None,
                "tsb": round(m.tsb, 1) if m.tsb is not None else None,
                "daily_tss": round(m.daily_tss, 1) if m.daily_tss is not None else None,
            }
            for m in hist
        ]

        return {
            "historical": historical,
            "projections": projections,
            "current_ctl": round(current.ctl, 1) if current.ctl is not None else None,
            "current_atl": round(current.atl, 1) if current.atl is not None else None,
            "current_tsb": round(current.tsb, 1) if current.tsb is not None else None,
            "plan_id": plan.id,
            "plan_title": plan.title,
        }
