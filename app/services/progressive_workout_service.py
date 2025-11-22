from sqlalchemy.orm import Session
from sqlalchemy import select, and_, func, desc
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta
from app.models.workout import Workout, WorkoutSession, WorkoutPlan
from app.services.ai_service import AIService
from app.schemas.ai import AIRequest, WeeklyPlanRequest, PerformanceAnalysisData
from app.config import settings
import json
import math
import os
from loguru import logger


class ProgressiveWorkoutPlanService:
    def __init__(self, db: Session):
        self.db = db
        self.ai_service = AIService(db)
        self.mock_mode = settings.mock_llm
    
    def generate_weekly_plan(self, 
                           user_id: int, 
                           week_number: int,
                           target_date: str,
                           previous_week_data: Optional[Dict[str, Any]] = None,
                           current_fitness_level: Optional[Dict[str, Any]] = None,
                           include_stretching: bool = False,
                           include_strength: bool = False,
                           unavailable_days: Optional[List[str]] = None,
                           sport_specific_days: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Genera piano per una settimana specifica basato sui dati precedenti"""
        logger.info(f"[PROGRESSIVE] Generating weekly plan - user_id: {user_id}, week_number: {week_number}, target_date: {target_date}")
        logger.debug(f"[PROGRESSIVE] Input params: user_id={user_id}, week_number={week_number}, target_date={target_date}, has_previous_week={previous_week_data is not None}, has_fitness_level={current_fitness_level is not None}")
        
        # 1. Raccoglie dati storici dell'utente (same for mock and real)
        logger.debug(f"[PROGRESSIVE] Collecting user workout history (weeks_back=4)")
        user_history = self._get_user_workout_history(user_id, weeks_back=4)
        logger.debug(f"[PROGRESSIVE] Collected {len(user_history)} weeks of history")
        
        performance_trends = self._analyze_performance_trends(user_history)
        logger.debug(f"[PROGRESSIVE] Performance trends: completion_rate={performance_trends.get('completion_rate', 0):.1f}%, fatigue_level={performance_trends.get('fatigue_level', 'N/A')}")
        
        # 2. Calcola date della settimana
        target_dt = datetime.strptime(target_date, "%Y-%m-%d").date()
        weeks_remaining = self._calculate_weeks_remaining(target_dt, week_number)
        logger.debug(f"[PROGRESSIVE] Weeks remaining to target: {weeks_remaining}")
        
        # 3. Costruisce prompt contestualizzato (same for mock and real)
        logger.debug(f"[PROGRESSIVE] Building progressive prompt")
        prompt = self._build_progressive_prompt(
            week_number=week_number,
            weeks_remaining=weeks_remaining,
            target_date=target_date,
            previous_week=previous_week_data,
            include_stretching=include_stretching,
            include_strength=include_strength,
            unavailable_days=unavailable_days,
            sport_specific_days=sport_specific_days,
            user_history=user_history,
            performance_trends=performance_trends,
            current_fitness=current_fitness_level
        )
        logger.debug(f"[PROGRESSIVE] Prompt built - length: {len(prompt)} characters")
        
        # 4. Create AIRequest (same for mock and real)
        ai_request = AIRequest(
            prompt=prompt,
            max_tokens=2000,
            temperature=0.7
        )
        
        # Log full data that would be sent to LLM
        mock_data_summary = {
            "week_number": week_number,
            "target_date": target_date,
            "weeks_remaining": weeks_remaining,
            "previous_week_data": previous_week_data,
            "current_fitness_level": current_fitness_level,
            "user_history_count": len(user_history),
            "performance_trends": performance_trends,
            "prompt_length": len(prompt),
            "prompt_preview": prompt[:500] + "..." if len(prompt) > 500 else prompt
        }
        logger.info(f"[PROGRESSIVE] Full data that would be sent to LLM: {json.dumps(mock_data_summary, indent=2, default=str)}")
        
        if self.mock_mode:
            logger.info(f"[PROGRESSIVE] Using MOCK mode for weekly plan generation")
            logger.info(f"[PROGRESSIVE][MOCK] Building same prompt and data as real LLM to validate data flow")
            logger.debug(f"[PROGRESSIVE][MOCK] Full prompt that would be sent to LLM: {prompt[:1000]}...")
            logger.debug(f"[PROGRESSIVE][MOCK] AIRequest - prompt_length: {len(ai_request.prompt)}, max_tokens: {ai_request.max_tokens}, temperature: {ai_request.temperature}")
            
            result = self._generate_mock_weekly_plan(
                week_number, target_date, previous_week_data, current_fitness_level,
                prompt, ai_request, user_history, performance_trends, weeks_remaining
            )
            logger.info(f"[PROGRESSIVE][MOCK] Mock weekly plan generated successfully - week: {result.get('week', 'N/A')}, workouts_count: {len(result.get('workouts', []))}")
            return result
        
        logger.info(f"[PROGRESSIVE] Calling AI service for weekly plan generation")
        response = self.ai_service.generate_response(ai_request)
        
        # 5. Parsing e strutturazione della risposta
        try:
            plan_data = json.loads(response.response)
            logger.info(f"[PROGRESSIVE] Successfully parsed AI response as JSON")
            logger.debug(f"[PROGRESSIVE] Plan data keys: {list(plan_data.keys())}")
            if 'workouts' in plan_data:
                logger.info(f"[PROGRESSIVE] Plan contains {len(plan_data.get('workouts', []))} workouts")
        except json.JSONDecodeError as e:
            logger.warning(f"[PROGRESSIVE] Failed to parse AI response as JSON, using fallback: {str(e)}")
            plan_data = self._parse_text_response(response.response, week_number, target_date)
            logger.info(f"[PROGRESSIVE] Using fallback text response parser")
        
        # 6. Aggiunge metadati
        plan_data.update({
            "generated_at": datetime.utcnow().isoformat(),
            "week_start_date": self._get_week_start_date(target_dt, week_number),
            "week_end_date": self._get_week_end_date(target_dt, week_number)
        })
        
        logger.info(f"[PROGRESSIVE] Weekly plan generated successfully - week: {plan_data.get('week', 'N/A')}, focus: {plan_data.get('focus', 'N/A')}")
        return plan_data
    
    def adapt_next_week_plan(self, user_id: int, target_date: str) -> Dict[str, Any]:
        """Adatta automaticamente la prossima settimana basandosi sulle performance"""
        
        # Ottiene dati della settimana corrente
        current_week_data = self.get_current_week_data(user_id)
        current_fitness_level = self.get_current_fitness_level(user_id)
        
        # Genera prossima settimana adattata
        next_week_number = current_week_data.get("week_number", 1) + 1
        next_week_plan = self.generate_weekly_plan(
            user_id=user_id,
            week_number=next_week_number,
            target_date=target_date,
            previous_week_data=current_week_data,
            current_fitness_level=current_fitness_level
        )
        
        return next_week_plan
    
    def get_current_week_data(self, user_id: int) -> Dict[str, Any]:
        """Ottiene dati della settimana corrente"""
        # Calcola la settimana corrente basandosi sulla data di oggi
        today = date.today()
        
        # Trova il piano attivo dell'utente
        active_plan = self.db.execute(
            select(WorkoutPlan)
            .where(and_(
                WorkoutPlan.user_id == user_id,
                WorkoutPlan.status == "active"
            ))
            .order_by(desc(WorkoutPlan.created_at))
        ).scalar_one_or_none()
        
        if not active_plan:
            return {"week_number": 1, "workouts": [], "performance": {}}
        
        # Calcola settimana corrente
        start_date = active_plan.start_date
        days_since_start = (today - start_date).days
        current_week = (days_since_start // 7) + 1
        
        # Ottiene allenamenti della settimana corrente
        week_start = start_date + timedelta(weeks=current_week-1)
        week_end = week_start + timedelta(days=6)
        
        workouts = self.db.execute(
            select(Workout)
            .where(and_(
                Workout.user_id == user_id,
                Workout.plan_id == active_plan.id,
                Workout.scheduled_date >= week_start,
                Workout.scheduled_date <= week_end
            ))
        ).scalars().all()
        
        # Ottiene performance della settimana
        performance = self._get_week_performance(user_id, week_start, week_end)
        
        return {
            "week_number": current_week,
            "workouts": [self._workout_to_dict(w) for w in workouts],
            "performance": performance,
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat()
        }
    
    def get_current_fitness_level(self, user_id: int) -> Dict[str, Any]:
        """Ottiene il livello di fitness attuale dell'utente"""
        # Analizza le ultime 4 settimane per determinare il livello di fitness
        user_history = self._get_user_workout_history(user_id, weeks_back=4)
        performance_trends = self._analyze_performance_trends(user_history)
        
        return {
            "completion_rate": performance_trends.get("completion_rate", 100),
            "avg_intensity": performance_trends.get("avg_intensity", 5.0),
            "consistency": performance_trends.get("consistency_score", 80),
            "fatigue_level": performance_trends.get("fatigue_level", "low"),
            "performance_trend": performance_trends.get("intensity_trend", "stable"),
            "last_week_rpe": performance_trends.get("last_week_avg_rpe", 6.0)
        }
    
    def _get_user_workout_history(self, user_id: int, weeks_back: int = 4) -> List[Dict[str, Any]]:
        """Ottiene la cronologia degli allenamenti dell'utente"""
        end_date = date.today()
        start_date = end_date - timedelta(weeks=weeks_back)
        
        # Ottiene sessioni di allenamento completate
        sessions = self.db.execute(
            select(WorkoutSession)
            .where(and_(
                WorkoutSession.user_id == user_id,
                WorkoutSession.actual_date >= start_date,
                WorkoutSession.actual_date <= end_date
            ))
            .order_by(WorkoutSession.actual_date)
        ).scalars().all()
        
        # Raggruppa per settimana
        weekly_data = {}
        for session in sessions:
            session_date = session.actual_date.date()
            week_start = session_date - timedelta(days=session_date.weekday())
            week_key = week_start.isoformat()
            
            if week_key not in weekly_data:
                weekly_data[week_key] = {
                    "week_start": week_key,
                    "sessions": [],
                    "total_duration": 0,
                    "avg_rpe": 0,
                    "completed_workouts": 0
                }
            
            weekly_data[week_key]["sessions"].append(self._session_to_dict(session))
            weekly_data[week_key]["total_duration"] += session.duration_minutes
            weekly_data[week_key]["completed_workouts"] += 1
        
        # Calcola RPE medio per settimana
        for week_data in weekly_data.values():
            if week_data["sessions"]:
                rpe_values = [s["perceived_exertion"] for s in week_data["sessions"] if s["perceived_exertion"]]
                week_data["avg_rpe"] = sum(rpe_values) / len(rpe_values) if rpe_values else 0
        
        return list(weekly_data.values())
    
    def _analyze_performance_trends(self, user_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analizza le performance per adattare il piano"""
        if not user_history:
            return {
                "completion_rate": 100.0,
                "intensity_trend": "stable",
                "fatigue_level": "low",
                "consistency_score": 80.0,
                "avg_rpe": 5.0,
                "recovery_indicators": {
                    "avg_sleep_quality": 7.0,
                    "fatigue_score": 3.0,
                    "recovery_time": "normal"
                },
                "performance_improvement": 0.0
            }
        
        # Calcola completion rate
        total_planned = sum(week.get('planned_workouts', 0) for week in user_history)
        total_completed = sum(week.get('completed_workouts', 0) for week in user_history)
        completion_rate = (total_completed / total_planned * 100.0) if total_planned > 0 else 100.0
        
        # Analizza trend intensità
        recent_rpe = [week.get('avg_rpe', 0) for week in user_history[-2:] if week.get('avg_rpe', 0) > 0]
        intensity_trend = "stable"
        if len(recent_rpe) >= 2:
            if recent_rpe[-1] > recent_rpe[-2] + 0.5:
                intensity_trend = "increasing"
            elif recent_rpe[-1] < recent_rpe[-2] - 0.5:
                intensity_trend = "decreasing"
        
        # Calcola fatigue level
        avg_rpe = sum(recent_rpe) / len(recent_rpe) if recent_rpe else 6.0
        if avg_rpe > 8.0:
            fatigue_level = "high"
        elif avg_rpe > 6.5:
            fatigue_level = "moderate"
        else:
            fatigue_level = "low"
        
        # Calcola consistency score
        completion_rates = [week.get('completion_rate', 100) for week in user_history]
        consistency_score = sum(completion_rates) / len(completion_rates) if completion_rates else 80.0
        
        # Calcola recovery indicators
        # Basato su RPE medio e completion rate
        if avg_rpe > 7.5:
            recovery_time = "extended"
            fatigue_score = 7.0
            sleep_quality = 5.0
        elif avg_rpe > 6.0:
            recovery_time = "normal"
            fatigue_score = 5.0
            sleep_quality = 6.5
        else:
            recovery_time = "normal"
            fatigue_score = 3.0
            sleep_quality = 7.5
        
        recovery_indicators = {
            "avg_sleep_quality": sleep_quality,
            "fatigue_score": fatigue_score,
            "recovery_time": recovery_time
        }
        
        # Calcola performance improvement
        # Basato su trend di completion rate e RPE
        if len(user_history) >= 2:
            recent_completion = completion_rates[-1] if completion_rates else 100
            previous_completion = completion_rates[-2] if len(completion_rates) >= 2 else 100
            completion_improvement = recent_completion - previous_completion
            
            # Calcola improvement basato su RPE e completion
            if len(recent_rpe) >= 2:
                rpe_change = recent_rpe[-1] - recent_rpe[-2]
                # Miglioramento se completion aumenta o RPE diminuisce (meno fatica per stesso sforzo)
                performance_improvement = (completion_improvement / 10) - (rpe_change * 2)
            else:
                performance_improvement = completion_improvement / 10
        else:
            performance_improvement = 0.0
        
        # Normalizza improvement tra -50 e 50
        performance_improvement = max(-50.0, min(50.0, performance_improvement))
        
        return {
            "completion_rate": completion_rate,
            "intensity_trend": intensity_trend,
            "fatigue_level": fatigue_level,
            "consistency_score": consistency_score,
            "avg_rpe": avg_rpe,
            "recovery_indicators": recovery_indicators,
            "performance_improvement": performance_improvement
        }
    
    def _build_progressive_prompt(self, week_number: int, weeks_remaining: int, target_date: str,
                                previous_week: Optional[Dict], user_history: List[Dict],
                                performance_trends: Dict, current_fitness: Optional[Dict],
                                include_stretching: bool = False,
                                include_strength: bool = False,
                                unavailable_days: Optional[List[str]] = None,
                                sport_specific_days: Optional[Dict[str, str]] = None) -> str:
        """Costruisce prompt per generazione progressiva"""
        
        prompt = f"""
        Generate WEEK {week_number} of a progressive training plan.
        
        AUTONOMY NOTE: You have full autonomy to determine the optimal number of workouts per week and session durations based on training science. Any user preferences regarding available days or minimum session duration are INDICATIVE ONLY, not constraints. Optimize the plan for best training outcomes.
        
        TARGET DATE: {target_date}
        WEEKS REMAINING: {weeks_remaining}
        
        CONTEXT FROM PREVIOUS WEEK:
        {json.dumps(previous_week, indent=2) if previous_week else "First week - no previous data"}
        
        USER PERFORMANCE HISTORY (Last 4 weeks):
        {json.dumps(user_history, indent=2)}
        
        PERFORMANCE TRENDS:
        {json.dumps(performance_trends, indent=2)}
        
        CURRENT FITNESS LEVEL:
        {json.dumps(current_fitness, indent=2) if current_fitness else "No fitness data available"}
        
        """
        
        # Gestione PERFORMANCE METRICS se presenti nel current_fitness
        if current_fitness:
            has_performance_metrics = any(key in current_fitness for key in [
                'hr_max', 'hr_rest', 'threshold_hr', 'hrr', 'custom_threshold_hr',
                'threshold_pace', 'critical_speed', 'vla',
                'ftp', 'wkg',
                'vo2max',
                'hr_zones', 'pace_zones', 'power_zones',
                'hr_zones_source', 'pace_zones_source', 'power_zones_source'
            ])
            
            if has_performance_metrics:
                prompt += "\n\n=== PERFORMANCE METRICS ==="
                prompt += "\nUSE EXACT ZONE VALUES PROVIDED - do not estimate or approximate."
                
                # HR Metrics (compact)
                if current_fitness.get('hr_zones') or current_fitness.get('threshold_hr') or current_fitness.get('hr_max'):
                    hr_info = []
                    if current_fitness.get('hr_max'):
                        hr_info.append(f"HR Max: {current_fitness.get('hr_max')} bpm")
                    if current_fitness.get('hr_rest'):
                        hr_info.append(f"HR Rest: {current_fitness.get('hr_rest')} bpm")
                    if current_fitness.get('threshold_hr'):
                        hr_info.append(f"Threshold: {current_fitness.get('threshold_hr')} bpm")
                    if current_fitness.get('hr_zones'):
                        zones = current_fitness.get('hr_zones')
                        if isinstance(zones, dict):
                            hr_info.append(f"Zones: {', '.join([f'{k.upper()}={v}' for k, v in zones.items()])}")
                    prompt += f"\nHR: {', '.join(hr_info)}"
                
                # Pace Metrics (compact)
                if current_fitness.get('pace_zones') or current_fitness.get('threshold_pace'):
                    pace_info = []
                    if current_fitness.get('threshold_pace'):
                        pace_info.append(f"Threshold: {current_fitness.get('threshold_pace')} min/km")
                    if current_fitness.get('critical_speed'):
                        pace_info.append(f"Critical Speed: {current_fitness.get('critical_speed')} km/h")
                    if current_fitness.get('pace_zones'):
                        zones = current_fitness.get('pace_zones')
                        if isinstance(zones, dict):
                            pace_info.append(f"Zones: {', '.join([f'{k.upper()}={v}' for k, v in zones.items()])}")
                    prompt += f"\nPace: {', '.join(pace_info)}"
                
                # Power Metrics (compact)
                if current_fitness.get('power_zones') or current_fitness.get('ftp'):
                    power_info = []
                    if current_fitness.get('ftp'):
                        power_info.append(f"FTP: {current_fitness.get('ftp')}W")
                    if current_fitness.get('wkg'):
                        power_info.append(f"W/kg: {current_fitness.get('wkg')}")
                    if current_fitness.get('power_zones'):
                        zones = current_fitness.get('power_zones')
                        if isinstance(zones, dict):
                            power_info.append(f"Zones: {', '.join([f'{k.upper()}={v}W' for k, v in zones.items()])}")
                    prompt += f"\nPower: {', '.join(power_info)}"
                
                # Advanced Metrics
                if current_fitness.get('vo2max'):
                    prompt += f"\nVO2max: {current_fitness.get('vo2max')} ml/kg/min"
                
                # Preferred zone type
                preferred_zone_type = current_fitness.get('preferred_zone_type', 'hr')
                prompt += f"\nPreferred zone type: {preferred_zone_type.upper()} (prioritize this in prescriptions)"
                
                prompt += "\n\nCRITICAL: Use exact zone values from above. For Z4 use threshold values, for Z5 use 105-120% of threshold."
                prompt += "\nAdapt intensities week-by-week based on performance trends, but always within the user's zone definitions."
        
        # Stretching periodization
        if include_stretching:
            prompt += "\n\n=== STRETCHING PERIODIZATION (REQUIRED) ==="
            prompt += "\nYou MUST include stretching sessions following scientific periodization guidelines:"
            
            # Determine phase based on weeks_remaining
            if weeks_remaining > 8:
                phase = "Build"
                freq = "4 days/week"
                duration = "10-12 minutes per session"
            elif weeks_remaining > 4:
                phase = "Peak"
                freq = "4 days/week"
                duration = "8-10 minutes per session"
            else:
                phase = "Taper"
                freq = "2-3 days/week"
                duration = "5-8 minutes per session"
            
            prompt += f"\n\nCURRENT PHASE ({weeks_remaining} weeks remaining): {phase} Phase"
            prompt += f"\n- Frequency: {freq}"
            prompt += f"\n- Duration: {duration}"
            prompt += "\n\nTIMING:"
            prompt += "\n- Post-workout (incorporated in cooldown) OR dedicated morning/evening session"
            prompt += "\n- Can be BOTH incorporated in cooldown AND as separate workout when appropriate"
            prompt += "\n\nSPORT-SPECIFIC FOCUS:"
            prompt += "\n- Running/Trail: Focus on hamstrings, calves, hip flexors, glutes, IT band, lower back (8-10 min total)"
            prompt += "\n- Cycling: Focus on quadriceps, hip flexors, hip adductors, lower back, upper back/chest (8-10 min total)"
            prompt += "\n- Swimming: Focus on shoulders (all angles - internal/external rotation), chest, lats, hip flexors (8-10 min total)"
            prompt += "\n- Triathlon: Combine all three sport focuses - hamstrings, calves, quads, hip flexors, shoulders, chest, lats (10-12 min total)"
            prompt += "\n\nPROTOCOL:"
            prompt += "\n- 30 seconds per hold (standard, not longer)"
            prompt += "\n- 3-4 minutes per major muscle group = 80% of benefits"
            prompt += "\n- Frequency > Duration: 4-5 days/week short sessions > 1 day long session"
            prompt += "\n- Daily brief stretching best for ROM maintenance"
            prompt += "\n\nRACE DAY:"
            prompt += "\n- Dynamic warm-up ONLY, NO static stretching pre-race (causes strength reduction)"
            prompt += "\n\nINTEGRATION:"
            prompt += "\n- Can be incorporated into cooldown segments OR scheduled as separate dedicated workouts"
            prompt += "\n- When incorporated in cooldown, add stretching steps to the cooldown segment"
            prompt += "\n- When separate, create dedicated 'Stretching' workout type with appropriate duration"
        
        # Strength training periodization
        if include_strength:
            prompt += "\n\n=== STRENGTH TRAINING PERIODIZATION (REQUIRED) ==="
            prompt += "\nYou MUST include strength training sessions following scientific periodization based on weeks to target date:"
            
            # Determine strength phase based on weeks_remaining
            if weeks_remaining > 12:
                phase = "Phase 2: MAX STRENGTH"
                freq = "2-3 sessions/week"
                duration = "45-60 minutes per session"
                intensity = "Very High (87-93% 1RM)"
                reps = "3-5 reps per set"
                rest = "3-5 minutes between sets"
                focus = "Max strength development"
                exercises = "Back Squat, RDL, Rows, Bench Press, Dips"
            elif weeks_remaining > 8:
                phase = "Phase 3: POWER/EXPLOSIVITY"
                freq = "1-2 sessions/week"
                duration = "45-50 minutes per session"
                intensity = "Very High (70-90% 1RM, explosive movement)"
                reps = "Fast, ballistic, plyometric"
                rest = "2-3 minutes"
                focus = "Converting strength into sport-specific power"
                exercises = "Explosive Push-ups, Box Jumps, Medicine Ball Throws, Jump Squats, Lateral Bounds"
            elif weeks_remaining > 4:
                phase = "Phase 3: POWER/EXPLOSIVITY (transitioning to Maintenance)"
                freq = "1-2 sessions/week"
                duration = "45-50 minutes per session"
                intensity = "High (70-90% 1RM, explosive)"
                reps = "Explosive movements"
                rest = "2-3 minutes"
                focus = "Power development"
                exercises = "Plyometric and explosive movements"
            else:
                phase = "Phase 4: MAINTENANCE"
                freq = "1 session/week"
                duration = "20-40 minutes per session"
                intensity = "Moderate (60-80% 1RM)"
                reps = "5 reps per set"
                rest = "2 minutes"
                focus = "Minimal Effective Dose (MED) - preservation without fatigue"
                exercises = "Big 5: Squat, Hinge, Push, Pull, Carry"
            
            prompt += f"\n\nCURRENT PHASE ({weeks_remaining} weeks remaining): {phase}"
            prompt += f"\n- Frequency: {freq}"
            prompt += f"\n- Duration: {duration}"
            prompt += f"\n- Intensity: {intensity}"
            if 'reps' in locals() and reps:
                prompt += f"\n- Rep Range: {reps}"
            prompt += f"\n- Rest: {rest}"
            prompt += f"\n- Focus: {focus}"
            if 'exercises' in locals() and exercises:
                prompt += f"\n- Sample exercises: {exercises}"
            
            prompt += "\n\nCRITICAL TIMING RULES:"
            prompt += "\n- Separate days ALWAYS preferred (if possible)"
            prompt += "\n- If same day: Minimum 90 minutes recovery between (strength FIRST, then endurance)"
            prompt += "\n- DO NOT schedule hard endurance + strength on the same day"
            prompt += "\n- Strength should be scheduled on recovery/easy days when possible"
            
            prompt += "\n\nTSS QUANTIFICATION:"
            prompt += "\n- Strength TSS ≈ (Duration (min) × RPE/10 × Movement Complexity) × 0.65"
            prompt += "\n- Complexity factors: Single muscle group = 1.0, 2-3 compound movements = 2.0, Full-body compound + plyos = 3.0"
            
            prompt += "\n\nACWR ADJUSTMENT:"
            prompt += "\n- ACWR_total = (Endurance_ATL + Strength_ATL × 0.7) / CTL"
            prompt += "\n- Strength weighted at 70% because it's muscle-specific, not whole-system stress like endurance"
            
            if weeks_remaining <= 1:
                prompt += "\n\nRACE WEEK: SKIP strength training completely"
            elif weeks_remaining <= 2:
                prompt += "\n\nTAPER WEEK: 1×/week bodyweight only or skip"
            
            prompt += "\n\nWORKOUT STRUCTURE:"
            prompt += "\n- Always create separate 'Strength' workout type"
            prompt += "\n- Include specific exercises, sets, reps, intensity (%1RM or RPE), rest periods"
            prompt += "\n- Focus on compound movements appropriate for the phase"
        
        # Day constraints
        if unavailable_days or sport_specific_days:
            prompt += "\n\n=== TRAINING SCHEDULE CONSTRAINTS (MANDATORY) ==="
            if unavailable_days:
                prompt += f"\n\nUNAVAILABLE DAYS (NO TRAINING ALLOWED):"
                prompt += f"\n- {', '.join(unavailable_days)}"
                prompt += "\n- DO NOT schedule any workouts on these days"
                prompt += "\n- These are complete rest days"
            
            if sport_specific_days:
                prompt += f"\n\nSPORT-SPECIFIC DAYS (ONLY SPECIFIED SPORT ALLOWED):"
                for day, sport in sport_specific_days.items():
                    prompt += f"\n- {day}: ONLY {sport} workouts (no other sports)"
                prompt += "\n- On these days, schedule ONLY the specified sport"
                prompt += "\n- If a day is both unavailable and sport-specific, the sport-specific constraint PREVAILS"
            
            if unavailable_days and sport_specific_days:
                # Check for conflicts
                conflicts = [day for day in sport_specific_days.keys() if day in unavailable_days]
                if conflicts:
                    prompt += f"\n\n⚠️ CONFLICT RESOLUTION:"
                    prompt += f"\n- Days {', '.join(conflicts)} appear in both unavailable_days and sport_specific_days"
                    prompt += "\n- SPORT-SPECIFIC CONSTRAINT PREVAILS - schedule only the specified sport on these days"
        
        prompt += """
        
        ADAPTATION RULES:
        1. If previous week was too easy (RPE < 6), increase intensity by 5-10%
        2. If previous week was too hard (RPE > 8), decrease intensity by 5-10%
        3. If user missed >2 workouts, reduce volume by 20%
        4. If user completed all workouts easily, increase volume by 10%
        5. Adjust based on performance trends and recovery indicators
        6. Consider weeks remaining to target date for peak timing
        
        Generate ONLY this week's plan with:
        - Specific workout details
        - Intensity adjustments based on previous week
        - Volume progression
        - Recovery considerations
        - Adaptation rationale
        
        Format as JSON:
        {{
            "week": {week_number},
            "focus": "Week focus based on progression and weeks remaining",
            "adaptations": {{
                "intensity_change": "+5%",
                "volume_change": "+10%",
                "rationale": "Previous week completed easily, user ready for progression"
            }},
            "workouts": [
                {{
                    "day": "Monday",
                    "type": "Endurance",
                    "duration_minutes": 60,
                    "intensity": "Z2",
                    "target_hr": "140-150",
                    "rpe_target": 6,
                    "description": "Adapted based on previous performance",
                    "key_focus": "Specific focus for this workout"
                }}
            ],
            "recovery_notes": "Specific recovery recommendations based on performance",
            "next_week_preview": "What to expect next week based on this week's plan",
            "adaptation_rationale": "Detailed explanation of why these adaptations were made"
        }}
        """
        return prompt
    
    def _calculate_weeks_remaining(self, target_date: date, current_week: int) -> int:
        """Calcola settimane rimanenti alla data target"""
        today = date.today()
        days_remaining = (target_date - today).days
        weeks_remaining = max(0, days_remaining // 7)
        return weeks_remaining
    
    def _get_week_start_date(self, target_date: date, week_number: int) -> str:
        """Calcola data inizio settimana"""
        # Calcola la data di inizio del piano (assumendo 12 settimane prima del target)
        plan_start = target_date - timedelta(weeks=12)
        week_start = plan_start + timedelta(weeks=week_number-1)
        return week_start.isoformat()
    
    def _get_week_end_date(self, target_date: date, week_number: int) -> str:
        """Calcola data fine settimana"""
        week_start = self._get_week_start_date(target_date, week_number)
        week_start_dt = datetime.strptime(week_start, "%Y-%m-%d").date()
        week_end = week_start_dt + timedelta(days=6)
        return week_end.isoformat()
    
    def _get_week_performance(self, user_id: int, week_start: date, week_end: date) -> Dict[str, Any]:
        """Ottiene performance della settimana specifica"""
        sessions = self.db.execute(
            select(WorkoutSession)
            .where(and_(
                WorkoutSession.user_id == user_id,
                WorkoutSession.actual_date >= week_start,
                WorkoutSession.actual_date <= week_end
            ))
        ).scalars().all()
        
        if not sessions:
            return {"total_sessions": 0, "avg_rpe": 0, "total_duration": 0}
        
        total_duration = sum(s.duration_minutes for s in sessions)
        rpe_values = [s.perceived_exertion for s in sessions if s.perceived_exertion]
        avg_rpe = sum(rpe_values) / len(rpe_values) if rpe_values else 0
        
        return {
            "total_sessions": len(sessions),
            "avg_rpe": avg_rpe,
            "total_duration": total_duration,
            "sessions": [self._session_to_dict(s) for s in sessions]
        }
    
    def _workout_to_dict(self, workout: Workout) -> Dict[str, Any]:
        """Converte workout in dizionario"""
        return {
            "id": workout.id,
            "title": workout.title,
            "type": workout.type,
            "scheduled_date": workout.scheduled_date.isoformat() if workout.scheduled_date else None,
            "duration_minutes": workout.duration_minutes,
            "intensity": workout.intensity,
            "zone": workout.zone,
            "status": workout.status.value if workout.status else "scheduled"
        }
    
    def _session_to_dict(self, session: WorkoutSession) -> Dict[str, Any]:
        """Converte session in dizionario"""
        return {
            "id": session.id,
            "workout_id": session.workout_id,
            "actual_date": session.actual_date.isoformat(),
            "duration_minutes": session.duration_minutes,
            "avg_hr": session.avg_hr,
            "max_hr": session.max_hr,
            "avg_pace": session.avg_pace,
            "avg_power": session.avg_power,
            "perceived_exertion": session.perceived_exertion,
            "notes": session.notes
        }
    
    def _parse_text_response(self, response: str, week_number: int, target_date: str) -> Dict[str, Any]:
        """Parsing di fallback per risposte non JSON"""
        return {
            "week": week_number,
            "focus": f"Week {week_number} - AI Generated Plan",
            "adaptations": {
                "intensity_change": "0%",
                "volume_change": "0%",
                "rationale": "First week or fallback response"
            },
            "workouts": [],
            "recovery_notes": "Follow standard recovery protocols",
            "next_week_preview": "Plan will be adapted based on this week's performance",
            "adaptation_rationale": "Initial plan generation"
        }
    
    def _generate_mock_weekly_plan(self, week_number: int, target_date: str, 
                                 previous_week_data: Optional[Dict[str, Any]] = None,
                                 current_fitness_level: Optional[Dict[str, Any]] = None,
                                 prompt: str = None,
                                 ai_request: AIRequest = None,
                                 user_history: List[Dict[str, Any]] = None,
                                 performance_trends: Dict[str, Any] = None,
                                 weeks_remaining: int = None) -> Dict[str, Any]:
        """Generate mock weekly plan for triathlon progressive training - uses same data as real LLM"""
        logger.info(f"[PROGRESSIVE][MOCK] Generating mock weekly plan")
        logger.debug(f"[PROGRESSIVE][MOCK] Received prompt length: {len(prompt) if prompt else 0}")
        logger.debug(f"[PROGRESSIVE][MOCK] AIRequest details: prompt_length={len(ai_request.prompt) if ai_request else 0}, max_tokens={ai_request.max_tokens if ai_request else None}")
        logger.debug(f"[PROGRESSIVE][MOCK] User history: {len(user_history) if user_history else 0} weeks")
        logger.debug(f"[PROGRESSIVE][MOCK] Performance trends: {json.dumps(performance_trends, indent=2, default=str) if performance_trends else None}")
        logger.debug(f"[PROGRESSIVE][MOCK] Previous week data: {json.dumps(previous_week_data, indent=2, default=str) if previous_week_data else None}")
        logger.debug(f"[PROGRESSIVE][MOCK] Current fitness level: {json.dumps(current_fitness_level, indent=2, default=str) if current_fitness_level else None}")
        logger.debug(f"[PROGRESSIVE][MOCK] Weeks remaining: {weeks_remaining}")
        
        # Log full prompt that would be sent to LLM
        if prompt:
            logger.info(f"[PROGRESSIVE][MOCK] Full prompt that would be sent to LLM: {prompt}")
        
        # Calculate week dates
        start_date = datetime(2025, 10, 25)
        week_start = start_date + timedelta(weeks=week_number-1)
        week_end = week_start + timedelta(days=6)
        
        # Get focus based on week
        focus = self._get_mock_triathlon_focus(week_number)
        logger.debug(f"[PROGRESSIVE][MOCK] Week focus: {focus}")
        
        # Generate workouts for the week
        workouts = self._generate_mock_triathlon_workouts(week_number)
        logger.debug(f"[PROGRESSIVE][MOCK] Generated {len(workouts)} workouts")
        
        # Calculate adaptations based on previous week
        adaptations = self._calculate_mock_adaptations(week_number, previous_week_data)
        logger.debug(f"[PROGRESSIVE][MOCK] Adaptations: {json.dumps(adaptations, indent=2, default=str)}")
        
        return {
            "week": week_number,
            "focus": focus,
            "adaptations": adaptations,
            "workouts": workouts,
            "recovery_notes": self._get_mock_recovery_notes(week_number),
            "next_week_preview": self._get_mock_next_week_preview(week_number),
            "generated_at": datetime.utcnow().isoformat(),
            "adaptation_rationale": self._get_mock_adaptation_rationale(week_number, previous_week_data),
            "week_start_date": week_start.strftime("%Y-%m-%d"),
            "week_end_date": week_end.strftime("%Y-%m-%d"),
            "weeks_remaining": max(0, 8 - week_number)
        }
    
    def _get_mock_triathlon_focus(self, week_number: int) -> str:
        """Get triathlon focus for specific week"""
        focuses = [
            "Base Building", "Base Building", "Brick Training", "Brick Training",
            "Speed Work", "Speed Work", "Taper", "Race Week"
        ]
        return focuses[min(week_number-1, len(focuses)-1)]
    
    def _generate_mock_triathlon_workouts(self, week_number: int) -> list:
        """Generate mock triathlon workouts for a week"""
        workouts = []
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        # Triathlon workouts
        tri_workouts = [
            {"type": "Swim", "duration_minutes": 45, "intensity": "Z2", "description": "Easy swim technique work"},
            {"type": "Bike", "duration_minutes": 60, "intensity": "Z2", "description": "Endurance bike ride"},
            {"type": "Run", "duration_minutes": 30, "intensity": "Z2", "description": "Easy transition run"},
            {"type": "Brick", "duration_minutes": 90, "intensity": "Z3", "description": "Bike + Run brick workout"},
            {"type": "Swim Intervals", "duration_minutes": 60, "intensity": "Z4", "description": "Swim interval training"},
            {"type": "Bike Tempo", "duration_minutes": 45, "intensity": "Z3", "description": "Tempo bike workout"},
            {"type": "Recovery", "duration_minutes": 30, "intensity": "Z1", "description": "Easy recovery workout"}
        ]
        
        # Select workouts based on week
        if week_number <= 2:
            selected = [0, 1, 2, 6]  # Base building
        elif week_number <= 4:
            selected = [0, 1, 3, 2]  # Brick training
        elif week_number <= 6:
            selected = [4, 5, 3, 2]  # Speed work
        else:
            selected = [0, 1, 2, 6]  # Taper
        
        for i, workout_idx in enumerate(selected[:4]):  # Max 4 workouts per week
            workout = tri_workouts[workout_idx].copy()
            workout["day"] = days[i]
            workout["rpe_target"] = 6 + (workout_idx % 3)
            workouts.append(workout)
        
        return workouts
    
    def _calculate_mock_adaptations(self, week_number: int, previous_week_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Calculate mock adaptations based on week and previous data"""
        if week_number == 1:
            return {
                "intensity_change": "0%",
                "volume_change": "0%",
                "rationale": "First week - establishing baseline"
            }
        
        # Simulate adaptations based on previous week performance
        if previous_week_data and previous_week_data.get("completion_rate", 100) > 90:
            intensity_change = "+5%" if week_number <= 4 else "+2%"
            volume_change = "+10%" if week_number <= 4 else "+5%"
            rationale = "Previous week completed successfully, ready for progression"
        else:
            intensity_change = "0%"
            volume_change = "0%"
            rationale = "Maintaining current level due to previous week challenges"
        
        return {
            "intensity_change": intensity_change,
            "volume_change": volume_change,
            "rationale": rationale
        }
    
    def _get_mock_recovery_notes(self, week_number: int) -> str:
        """Get mock recovery notes for specific week"""
        notes = [
            "Focus on sleep and nutrition for base building",
            "Maintain consistent sleep schedule",
            "Monitor fatigue levels during brick training",
            "Prioritize recovery between brick sessions",
            "Increase protein intake for speed work",
            "Monitor recovery between high-intensity sessions",
            "Focus on sleep and light stretching for taper",
            "Minimal activity, focus on race preparation"
        ]
        return notes[min(week_number-1, len(notes)-1)]
    
    def _get_mock_next_week_preview(self, week_number: int) -> str:
        """Get mock next week preview"""
        if week_number >= 8:
            return "Race week - minimal training, focus on preparation"
        
        previews = [
            "Continue base building with slight volume increase",
            "Introduce brick training sessions",
            "Increase brick training intensity",
            "Add speed work elements",
            "Focus on high-intensity intervals",
            "Begin tapering process",
            "Final taper week before race"
        ]
        return previews[min(week_number-1, len(previews)-1)]
    
    def _get_mock_adaptation_rationale(self, week_number: int, previous_week_data: Optional[Dict[str, Any]] = None) -> str:
        """Get mock adaptation rationale"""
        if week_number == 1:
            return "Initial plan generation based on user profile"
        
        if previous_week_data and previous_week_data.get("completion_rate", 100) > 90:
            return "User completed previous week successfully, ready for progression"
        else:
            return "Maintaining current level to ensure proper adaptation"

