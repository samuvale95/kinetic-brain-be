from sqlalchemy.orm import Session
from sqlalchemy import select, and_, func, desc
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta
import time
from app.models.workout import Workout, WorkoutSession, WorkoutPlan
from app.services.ai_service import AIService
from app.services.claude_review_service import ClaudeReviewService
from app.services.plan_validator import WorkoutPlanValidator, PlanValidationError
from app.services.stretching_workout_service import StretchingWorkoutService
from app.services.strength_workout_service import StrengthWorkoutService
from app.services.workout_config_service import WorkoutConfigService
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
        self.claude_review_service = ClaudeReviewService(db)
        self.plan_validator = WorkoutPlanValidator()
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
                           sport_specific_days: Optional[Dict[str, str]] = None,
                           start_date: Optional[str] = None,
                           sport_type: Optional[str] = None,
                           level: Optional[str] = None,
                           goal: Optional[str] = None,
                           weekly_hours: Optional[float] = None,
                           available_equipment: Optional[List[str]] = None) -> Dict[str, Any]:
        """Genera piano per una settimana specifica basato sui dati precedenti"""
        generation_start_time = time.time()
        logger.info(f"[PROGRESSIVE][START] Generating weekly plan - user_id: {user_id}, week_number: {week_number}, target_date: {target_date}, start_date: {start_date}, include_stretching: {include_stretching}, include_strength: {include_strength}, timestamp: {datetime.utcnow().isoformat()}")
        logger.debug(f"[PROGRESSIVE] Input params: user_id={user_id}, week_number={week_number}, target_date={target_date}, start_date={start_date}, has_previous_week={previous_week_data is not None}, has_fitness_level={current_fitness_level is not None}")
        
        # 1. Raccoglie dati storici dell'utente (same for mock and real)
        step_start = time.time()
        logger.info(f"[PROGRESSIVE][STEP 1] Collecting user workout history (weeks_back=4) - timestamp: {datetime.utcnow().isoformat()}")
        user_history = self._get_user_workout_history(user_id, weeks_back=4)
        step_duration = time.time() - step_start
        logger.info(f"[PROGRESSIVE][STEP 1] Collected {len(user_history)} weeks of history - duration: {step_duration:.2f}s")
        
        step_start = time.time()
        logger.info(f"[PROGRESSIVE][STEP 2] Analyzing performance trends - timestamp: {datetime.utcnow().isoformat()}")
        performance_trends = self._analyze_performance_trends(user_history)
        step_duration = time.time() - step_start
        logger.info(f"[PROGRESSIVE][STEP 2] Performance trends: completion_rate={performance_trends.get('completion_rate', 0):.1f}%, fatigue_level={performance_trends.get('fatigue_level', 'N/A')} - duration: {step_duration:.2f}s")
        
        # 2. Calcola date della settimana e giorni disponibili per prima settimana
        target_dt = datetime.strptime(target_date, "%Y-%m-%d").date()
        weeks_remaining = self._calculate_weeks_remaining(target_dt, week_number)
        logger.debug(f"[PROGRESSIVE] Weeks remaining to target: {weeks_remaining}")
        
        # Calcola giorni disponibili per la prima settimana se start_date è fornito
        available_days_in_week: Optional[List[str]] = None
        plan_start_date: Optional[date] = None
        if week_number == 1 and start_date:
            plan_start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            # Calcola giorni disponibili dalla data di inizio fino a domenica
            start_weekday = plan_start_date.weekday()  # 0=lunedì, 6=domenica
            day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            available_days_in_week = day_names[start_weekday:]
            logger.info(f"[PROGRESSIVE] First week partial: start_date={start_date}, available_days={available_days_in_week}")
        
        # 3. Costruisce prompt contestualizzato (same for mock and real)
        step_start = time.time()
        logger.info(f"[PROGRESSIVE][STEP 3] Building progressive prompt - timestamp: {datetime.utcnow().isoformat()}")
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
            current_fitness=current_fitness_level,
            available_days_in_week=available_days_in_week,
            sport_type=sport_type,
            level=level,
            goal=goal,
            weekly_hours=weekly_hours
        )
        step_duration = time.time() - step_start
        logger.info(f"[PROGRESSIVE][STEP 3] Prompt built - length: {len(prompt)} chars - duration: {step_duration:.2f}s")
        logger.debug(f"[PROGRESSIVE] Prompt built - length: {len(prompt)} characters")
        
        # 4. Create AIRequest (same for mock and real)
        ai_request = AIRequest(
            prompt=prompt,
            max_tokens=4000,
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
            
            plan_data = self._generate_mock_weekly_plan(
                week_number, target_date, previous_week_data, current_fitness_level,
                prompt, ai_request, user_history, performance_trends, weeks_remaining
            )
            logger.info(f"[PROGRESSIVE][MOCK] Mock weekly plan generated successfully - week: {plan_data.get('week', 'N/A')}, workouts_count: {len(plan_data.get('workouts', []))}")
            # NOTE: Non ritorniamo qui - continuiamo con validazione e generazione stretching/strength
            # così anche in modalità mock, stretching e strength vengono generati realmente
            logger.info(f"[PROGRESSIVE][MOCK] Continuing with validation and stretching/strength generation (if requested)")
            # Salta la chiamata AI reale (step 4 e 5) in modalità mock
            response = None
        else:
            # 4. Chiamata AI (solo se NON siamo in modalità mock)
            step_start = time.time()
            logger.info(f"[PROGRESSIVE][STEP 4] Calling AI service for weekly plan generation - timestamp: {datetime.utcnow().isoformat()}")
            logger.info(f"[PROGRESSIVE][STEP 4] AI Request params - prompt_length: {len(prompt)}, max_tokens: {ai_request.max_tokens}, temperature: {ai_request.temperature}")
            response = self.ai_service.generate_response(ai_request)
            step_duration = time.time() - step_start
            logger.info(f"[PROGRESSIVE][STEP 4] AI service call completed - duration: {step_duration:.2f}s, response_length: {len(response.response) if response and response.response else 0}")
        
        # 5. Parsing della risposta AI (solo se non siamo in modalità mock)
        if self.mock_mode:
            # In modalità mock, plan_data è già stato generato, saltiamo il parsing
            logger.info(f"[PROGRESSIVE][MOCK] Skipping AI response parsing (using mock plan_data)")
        elif not response or not response.response:
            # Check if response is valid
            error_msg = "AI service returned empty or None response"
            logger.error(f"[PROGRESSIVE] {error_msg}")
            self.ai_service._log_ai_response(
                request_type="progressive_weekly_plan",
                user_id=user_id,
                prompt=prompt,
                request_payload={
                    "week_number": week_number,
                    "target_date": target_date,
                    "weeks_remaining": weeks_remaining,
                    "has_previous_week": previous_week_data is not None,
                    "has_fitness_level": current_fitness_level is not None,
                },
                response_text="",
                model=getattr(response, 'model', 'unknown') if response else 'unknown',
                parse_success=False,
                error_message=error_msg,
            )
            plan_data = self._parse_text_response("", week_number, target_date)
            logger.info(f"[PROGRESSIVE] Using fallback parser due to empty response")
        else:
            # 5. Parsing e strutturazione della risposta
            step_start = time.time()
            logger.info(f"[PROGRESSIVE][STEP 5] Parsing AI response - timestamp: {datetime.utcnow().isoformat()}")
            try:
                # Strip any markdown code blocks if present
                response_text = response.response.strip()
                if response_text.startswith("```json"):
                    response_text = response_text[7:]  # Remove ```json
                if response_text.startswith("```"):
                    response_text = response_text[3:]  # Remove ```
                if response_text.endswith("```"):
                    response_text = response_text[:-3]  # Remove trailing ```
                response_text = response_text.strip()
                
                parse_start = time.time()
                plan_data = json.loads(response_text)
                parse_duration = time.time() - parse_start
                logger.info(f"[PROGRESSIVE][STEP 5] Successfully parsed AI response as JSON - duration: {parse_duration:.2f}s")
                logger.debug(f"[PROGRESSIVE] Plan data keys: {list(plan_data.keys())}")
                if 'workouts' in plan_data:
                    logger.info(f"[PROGRESSIVE] Plan contains {len(plan_data.get('workouts', []))} workouts")
                
                # Log successo nel database
                self.ai_service._log_ai_response(
                    request_type="progressive_weekly_plan",
                    user_id=user_id,
                    prompt=prompt,
                    request_payload={
                        "week_number": week_number,
                        "target_date": target_date,
                        "weeks_remaining": weeks_remaining,
                        "has_previous_week": previous_week_data is not None,
                        "has_fitness_level": current_fitness_level is not None,
                    },
                    response_text=response.response,
                    model=response.model,
                    parse_success=True,
                    error_message=None,
                )
            except json.JSONDecodeError as e:
                error_msg = f"Failed to parse AI response as JSON: {str(e)}"
                logger.warning(f"[PROGRESSIVE] {error_msg}, using fallback")
                
                # Log errore nel database
                self.ai_service._log_ai_response(
                    request_type="progressive_weekly_plan",
                    user_id=user_id,
                    prompt=prompt,
                    request_payload={
                        "week_number": week_number,
                        "target_date": target_date,
                        "weeks_remaining": weeks_remaining,
                        "has_previous_week": previous_week_data is not None,
                        "has_fitness_level": current_fitness_level is not None,
                    },
                    response_text=response.response,
                    model=response.model,
                    parse_success=False,
                    error_message=error_msg,
                )
                
                plan_data = self._parse_text_response(response.response, week_number, target_date)
                logger.info(f"[PROGRESSIVE] Using fallback text response parser")
        
        # 6. Validator deterministico
        step_start = time.time()
        logger.info(f"[PROGRESSIVE][STEP 6] Running deterministic validator - timestamp: {datetime.utcnow().isoformat()}")
        validator_has_errors = False
        validator_has_warnings = False
        validator_results = None
        
        try:
            # Build user state for validator
            user_state = None
            if current_fitness_level:
                user_state = {
                    "readiness_state": current_fitness_level.get("readiness_state"),
                    "recovery_index": current_fitness_level.get("recovery_index"),
                    "injury_risk_score": current_fitness_level.get("injury_risk_score"),
                    "hydration_score": current_fitness_level.get("hydration_score"),
                }
            
            # Validate the plan
            self.plan_validator.validate(plan_data, user_state=user_state)
            step_duration = time.time() - step_start
            logger.info(f"[PROGRESSIVE][STEP 6] Plan passed deterministic validator - duration: {step_duration:.2f}s")
            validator_results = {"status": "passed", "violations": []}
            
        except PlanValidationError as e:
            step_duration = time.time() - step_start
            validator_has_errors = True
            validator_results = {
                "status": "failed",
                "violations": e.violations,
            }
            logger.warning(f"[PROGRESSIVE][STEP 6] Plan validation failed after {step_duration:.2f}s: {e.violations}")
            # Continue anyway - we'll let Claude review it
        
        # Check for missing required workouts (strength/stretching)
        # Recalculate strength_freq and stretching_freq for checking
        weeks_remaining = self._calculate_weeks_remaining(target_dt, week_number)
        
        check_strength_freq = '0'
        if include_strength:
            if weeks_remaining > 12:
                check_strength_freq = "2-3x/week"
            elif weeks_remaining > 8:
                check_strength_freq = "1-2x/week"
            elif weeks_remaining > 4:
                check_strength_freq = "1-2x/week"
            elif weeks_remaining > 1:
                check_strength_freq = "1x/week"
            else:
                check_strength_freq = "skip"
        
        check_stretching_freq = 0
        if include_stretching:
            if weeks_remaining > 8:
                check_stretching_freq = 4
            elif weeks_remaining > 4:
                check_stretching_freq = 4
            else:
                check_stretching_freq = 2
        
        check_results = self._check_required_workouts(
            plan_data=plan_data,
            include_strength=include_strength,
            include_stretching=include_stretching,
            strength_freq=check_strength_freq,
            stretching_freq=check_stretching_freq,
        )
        
        if check_results["has_missing"]:
            logger.warning(
                f"[PROGRESSIVE] Missing required workouts: "
                f"strength={check_results['missing_strength']} (found {check_results['strength_count']}, required {check_results['required_strength']}), "
                f"stretching={check_results['missing_stretching']} (found {check_results['stretching_count']}, required {check_results['required_stretching']})"
            )
            # Force Claude review to fix missing workouts
            validator_has_errors = True  # Force review
            if "missing_workouts" not in validator_results:
                validator_results["missing_workouts"] = {}
            validator_results["missing_workouts"] = {
                "strength": check_results["missing_strength"],
                "stretching": check_results["missing_stretching"],
                "required_strength": check_results["required_strength"],
                "required_stretching": check_results["required_stretching"],
            }
        
        # 7. Claude review (se abilitato)
        if settings.enable_claude_review:
            logger.info(f"[PROGRESSIVE] Claude review enabled, checking if review is needed")
            
            should_review = self.claude_review_service.should_review_plan(
                validator_has_errors=validator_has_errors,
                validator_has_warnings=validator_has_warnings,
            )
            
            if should_review:
                logger.info(f"[PROGRESSIVE] Claude review triggered (validator_errors={validator_has_errors}, validator_warnings={validator_has_warnings})")
                
                try:
                    claude_review = self.claude_review_service.review_plan(
                        plan=plan_data,
                        validator_results=validator_results,
                        user_id=user_id,
                        week_number=week_number,
                    )
                    
                    logger.info(f"[PROGRESSIVE] Claude review completed - approved: {claude_review.approved}")
                    
                    if not claude_review.approved and claude_review.improved_plan:
                        logger.info("[PROGRESSIVE] Using Claude's improved plan")
                        plan_data = claude_review.improved_plan
                        # Preserve metadata
                        plan_data.update({
                            "generated_at": datetime.utcnow().isoformat(),
                            "week_start_date": self._get_week_start_date(target_dt, week_number, plan_start_date),
                            "week_end_date": self._get_week_end_date(target_dt, week_number, plan_start_date),
                            "_claude_reviewed": True,
                            "_claude_changelog": claude_review.changelog,
                        })
                        
                        # Verify that Claude added the missing workouts
                        if check_results.get("has_missing"):
                            post_claude_check = self._check_required_workouts(
                                plan_data=plan_data,
                                include_strength=include_strength,
                                include_stretching=include_stretching,
                                strength_freq=check_strength_freq,
                                stretching_freq=check_stretching_freq,
                            )
                            if post_claude_check["has_missing"]:
                                logger.warning(
                                    f"[PROGRESSIVE] Claude's improved plan still missing workouts: "
                                    f"strength={post_claude_check['missing_strength']}, "
                                    f"stretching={post_claude_check['missing_stretching']}"
                                )
                            else:
                                logger.info("[PROGRESSIVE] Claude successfully added all missing workouts")
                        
                        # Re-validate the improved plan
                        try:
                            user_state = None
                            if current_fitness_level:
                                user_state = {
                                    "readiness_state": current_fitness_level.get("readiness_state"),
                                    "recovery_index": current_fitness_level.get("recovery_index"),
                                    "injury_risk_score": current_fitness_level.get("injury_risk_score"),
                                    "hydration_score": current_fitness_level.get("hydration_score"),
                                }
                            self.plan_validator.validate(plan_data, user_state=user_state)
                            logger.info("[PROGRESSIVE] Claude's improved plan passed validator")
                        except PlanValidationError as e:
                            logger.warning(f"[PROGRESSIVE] Claude's improved plan still has validation issues: {e.violations}")
                            # Continue with improved plan anyway - Claude reviewed it
                    elif not claude_review.approved and not claude_review.improved_plan:
                        # Claude rejected the plan but didn't provide an improved version
                        if validator_has_errors:
                            # Both validator and Claude rejected - this is problematic
                            error_msg = f"Plan rejected by both validator and Claude. Validator errors: {validator_results.get('violations', [])}. Claude notes: {claude_review.review_notes}"
                            logger.error(f"[PROGRESSIVE] {error_msg}")
                            # Continue with original plan but log the issue
                            plan_data["_claude_reviewed"] = True
                            plan_data["_claude_approved"] = False
                            plan_data["_validation_warnings"] = error_msg
                        else:
                            # Only Claude rejected, validator passed - log but continue
                            logger.warning(f"[PROGRESSIVE] Claude rejected plan but validator passed. Notes: {claude_review.review_notes}")
                            plan_data["_claude_reviewed"] = True
                            plan_data["_claude_approved"] = False
                    elif claude_review.approved:
                        logger.info("[PROGRESSIVE] Claude approved the plan")
                        plan_data["_claude_reviewed"] = True
                        plan_data["_claude_approved"] = True
                        
                        # Verify that required workouts are present even if Claude approved
                        if check_results.get("has_missing"):
                            post_approval_check = self._check_required_workouts(
                                plan_data=plan_data,
                                include_strength=include_strength,
                                include_stretching=include_stretching,
                                strength_freq=check_strength_freq,
                                stretching_freq=check_stretching_freq,
                            )
                            if post_approval_check["has_missing"]:
                                logger.warning(
                                    f"[PROGRESSIVE] Claude approved plan but still missing workouts: "
                                    f"strength={post_approval_check['missing_strength']}, "
                                    f"stretching={post_approval_check['missing_stretching']}"
                                )
                    
                except Exception as e:
                    logger.warning(f"[PROGRESSIVE] Claude review failed: {e}, using original plan")
                    # Continue with original plan if Claude fails
                    # If validator also failed, this could be problematic but we continue anyway
            else:
                logger.info(f"[PROGRESSIVE] Claude review skipped (percentage threshold or no errors)")
        else:
            logger.debug("[PROGRESSIVE] Claude review disabled")
        
        # 8. Genera stretching e strength workouts se richiesti
        if include_stretching or include_strength:
            step_start = time.time()
            logger.info(f"[PROGRESSIVE][STEP 8][START] Generating stretching/strength workouts - include_stretching: {include_stretching}, include_strength: {include_strength}, timestamp: {datetime.utcnow().isoformat()}")
            try:
                # Calcola weeks_remaining
                weeks_remaining = self._calculate_weeks_remaining(target_dt, week_number)
                
                # Determina fase
                config_service = WorkoutConfigService()
                week_phase = config_service.determine_phase(weeks_remaining)
                logger.info(f"[PROGRESSIVE][STEP 8] Phase determined: {week_phase}, weeks_remaining: {weeks_remaining}")
                
                # Default equipment se non specificato
                if available_equipment is None:
                    eq_start = time.time()
                    logger.info(f"[PROGRESSIVE][STEP 8] Fetching available equipment - timestamp: {datetime.utcnow().isoformat()}")
                    from app.services.exercise_service import ExerciseService
                    exercise_service = ExerciseService(self.db)
                    available_equipment = exercise_service.get_available_equipment()
                    eq_duration = time.time() - eq_start
                    logger.info(f"[PROGRESSIVE][STEP 8] Equipment fetched - count: {len(available_equipment) if available_equipment else 0}, duration: {eq_duration:.2f}s")
                    # Se ancora None o vuoto, usa "body only" come default
                    if not available_equipment:
                        available_equipment = ["body only"]
                        logger.info(f"[PROGRESSIVE][STEP 8] Using default equipment: ['body only']")
                
                # Normalizza sport_type
                if not sport_type:
                    sport_type = "running"  # Default
                
                # Normalizza level
                if not level:
                    level = "intermediate"  # Default
                
                # Ottieni giorni disponibili per stretching/strength
                all_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                
                # 1. Determina se è prima settimana e calcola scaling factor
                is_first_week = (week_number == 1 and available_days_in_week)
                if is_first_week:
                    actual_days_count = len(available_days_in_week)
                    scaling_factor = actual_days_count / 7.0
                    logger.info(f"[PROGRESSIVE][STEP 8] First week detected: actual_days={actual_days_count}, scaling_factor={scaling_factor:.2f}")
                else:
                    actual_days_count = 7
                    scaling_factor = 1.0
                    logger.info(f"[PROGRESSIVE][STEP 8] Full week: actual_days={actual_days_count}, scaling_factor={scaling_factor:.2f}")
                
                # 2. Calcola giorni base disponibili (escludendo unavailable_days)
                if is_first_week:
                    base_available_days = [d for d in available_days_in_week if not unavailable_days or d not in unavailable_days]
                    logger.info(f"[PROGRESSIVE][STEP 8] First week partial - starting with available_days_in_week: {base_available_days}")
                else:
                    base_available_days = [d for d in all_days if not unavailable_days or d not in unavailable_days]
                    logger.info(f"[PROGRESSIVE][STEP 8] Full week - starting with all days (excluding unavailable): {base_available_days}")
                
                # 3. Escludi giorni già occupati da workout sport-specific generati dall'AI
                if sport_specific_days:
                    occupied_days = set(sport_specific_days.keys())
                    base_available_days = [d for d in base_available_days if d not in occupied_days]
                    logger.info(f"[PROGRESSIVE][STEP 8] After excluding sport_specific_days ({len(occupied_days)} days): {base_available_days}")
                
                # 4. Escludi giorni già occupati dai workout nel plan_data (workouts generati dall'AI)
                existing_workout_days = set()
                if plan_data and "workouts" in plan_data:
                    existing_workout_days = {w.get("day") for w in plan_data["workouts"] if w.get("day")}
                    if existing_workout_days:
                        base_available_days = [d for d in base_available_days if d not in existing_workout_days]
                        logger.info(f"[PROGRESSIVE][STEP 8] After excluding existing AI workout days ({len(existing_workout_days)} days): {base_available_days}")
                
                # 5. Prepara giorni disponibili per strength (solo giorni liberi)
                available_days_for_strength = base_available_days.copy()
                
                # 6. Prepara giorni disponibili per stretching
                # Settimana 1: solo giorni liberi (per non sovraccaricare)
                # Settimana 2+: può usare tutti i giorni (anche occupati) - stretching può essere "on top"
                if is_first_week:
                    available_days_for_stretching = base_available_days.copy()
                else:
                    # Settimana 2+: stretching può essere aggiunto anche su giorni occupati
                    # Usa tutti i giorni della settimana (escludendo solo unavailable_days)
                    available_days_for_stretching = [d for d in all_days if not unavailable_days or d not in unavailable_days]
                
                # Inizializza giorni usati (per tracking)
                used_days_strength = set()
                strength_workouts = []
                
                # 7. GENERA STRENGTH PRIMA (priorità più alta)
                if include_strength:
                    strength_start = time.time()
                    logger.info(f"[PROGRESSIVE][STEP 8][STRENGTH][START] Starting strength workout generation - timestamp: {datetime.utcnow().isoformat()}")
                    strength_service = StrengthWorkoutService(self.db)
                    strength_config = config_service.get_workout_config(
                        sport_type=sport_type,
                        phase=week_phase,
                        workout_type="strength"
                    )
                    
                    if strength_config:
                        # Calcola target sessioni per settimana piena
                        target_sessions_full_week = strength_config.frequency.preferred_sessions
                        
                        # Scala per settimana 1
                        if is_first_week:
                            target_sessions_scaled = round(target_sessions_full_week * scaling_factor)
                            # Applica minimo sensato: almeno 1 se BASE/BUILD
                            if week_phase in ["BASE", "BUILD"]:
                                target_sessions_scaled = max(1, target_sessions_scaled)
                            logger.info(f"[PROGRESSIVE][STEP 8][STRENGTH] First week scaling: {target_sessions_full_week} -> {target_sessions_scaled} (factor={scaling_factor:.2f})")
                        else:
                            target_sessions_scaled = target_sessions_full_week
                        
                        # Limita ai giorni disponibili (solo giorni liberi)
                        num_strength_sessions = min(target_sessions_scaled, len(available_days_for_strength))
                        
                        logger.info(f"[PROGRESSIVE][STEP 8][STRENGTH] Generating {num_strength_sessions} strength workouts (target: {target_sessions_scaled}, available days: {len(available_days_for_strength)})")
                        
                        # Genera workout per ogni sessione su giorni liberi
                        days_for_strength = available_days_for_strength[:num_strength_sessions]
                        
                        for idx, day in enumerate(days_for_strength, 1):
                            workout_start = time.time()
                            logger.info(f"[PROGRESSIVE][STEP 8][STRENGTH][{idx}/{num_strength_sessions}] Generating workout for {day} - timestamp: {datetime.utcnow().isoformat()}")
                            
                            workout = strength_service.generate_strength_workout(
                                sport_type=sport_type,
                                level=level,
                                available_equipment=available_equipment,
                                week_phase=week_phase,
                                weeks_remaining=weeks_remaining
                            )
                            workout["day"] = day
                            strength_workouts.append(workout)
                            used_days_strength.add(day)
                            workout_duration = time.time() - workout_start
                            logger.info(f"[PROGRESSIVE][STEP 8][STRENGTH][{idx}/{num_strength_sessions}] Workout generated for {day} - duration: {workout_duration:.2f}s")
                        
                        # Aggiungi alla lista workouts
                        if "workouts" not in plan_data:
                            plan_data["workouts"] = []
                        plan_data["workouts"].extend(strength_workouts)
                        strength_duration = time.time() - strength_start
                        logger.info(f"[PROGRESSIVE][STEP 8][STRENGTH][END] Added {len(strength_workouts)} strength workouts to plan - total duration: {strength_duration:.2f}s")
                
                # 8. GENERA STRETCHING DOPO (può essere "on top" dalla settimana 2+)
                if include_stretching:
                    stretch_start = time.time()
                    logger.info(f"[PROGRESSIVE][STEP 8][STRETCHING][START] Starting stretching workout generation - timestamp: {datetime.utcnow().isoformat()}")
                    stretching_service = StretchingWorkoutService(self.db)
                    stretching_config = config_service.get_workout_config(
                        sport_type=sport_type,
                        phase=week_phase,
                        workout_type="stretching"
                    )
                    
                    if stretching_config:
                        # Calcola target sessioni per settimana piena
                        target_sessions_full_week = stretching_config.frequency.preferred_sessions
                        
                        # Scala per settimana 1
                        if is_first_week:
                            target_sessions_scaled = max(2, round(target_sessions_full_week * scaling_factor))
                            logger.info(f"[PROGRESSIVE][STEP 8][STRETCHING] First week scaling: {target_sessions_full_week} -> {target_sessions_scaled} (factor={scaling_factor:.2f}, min=2)")
                        else:
                            target_sessions_scaled = target_sessions_full_week
                        
                        # Determina giorni per stretching
                        if is_first_week:
                            # Settimana 1: solo giorni liberi (non sovraccaricare)
                            num_stretching_sessions = min(target_sessions_scaled, len(available_days_for_stretching))
                            days_for_stretching = available_days_for_stretching[:num_stretching_sessions]
                            logger.info(f"[PROGRESSIVE][STEP 8][STRETCHING] First week: generating {num_stretching_sessions} workouts on free days only")
                        else:
                            # Settimana 2+: può aggiungere stretching anche su giorni occupati
                            # Preferisci giorni liberi, poi riempi con giorni occupati
                            free_days = [d for d in available_days_for_stretching if d not in used_days_strength and d not in existing_workout_days]
                            occupied_days_for_stretching = [d for d in available_days_for_stretching if d in used_days_strength or d in existing_workout_days]
                            
                            # Prendi prima giorni liberi, poi giorni occupati fino al target
                            days_for_stretching = (free_days + occupied_days_for_stretching)[:target_sessions_scaled]
                            num_stretching_sessions = len(days_for_stretching)
                            logger.info(f"[PROGRESSIVE][STEP 8][STRETCHING] Full week: generating {num_stretching_sessions} workouts (free days: {len(free_days)}, can use occupied: {len(occupied_days_for_stretching)})")
                        
                        logger.info(f"[PROGRESSIVE][STEP 8][STRETCHING] Generating {num_stretching_sessions} stretching workouts (target: {target_sessions_scaled})")
                        
                        # Genera workout per ogni sessione
                        stretching_workouts = []
                        
                        for idx, day in enumerate(days_for_stretching, 1):
                            workout_start = time.time()
                            logger.info(f"[PROGRESSIVE][STEP 8][STRETCHING][{idx}/{num_stretching_sessions}] Generating workout for {day} - timestamp: {datetime.utcnow().isoformat()}")
                            
                            workout = stretching_service.generate_stretching_workout(
                                sport_type=sport_type,
                                level=level,
                                available_equipment=available_equipment,
                                week_phase=week_phase
                            )
                            workout["day"] = day
                            stretching_workouts.append(workout)
                            workout_duration = time.time() - workout_start
                            logger.info(f"[PROGRESSIVE][STEP 8][STRETCHING][{idx}/{num_stretching_sessions}] Workout generated for {day} - duration: {workout_duration:.2f}s")
                        
                        # Aggiungi alla lista workouts
                        if "workouts" not in plan_data:
                            plan_data["workouts"] = []
                        plan_data["workouts"].extend(stretching_workouts)
                        stretch_duration = time.time() - stretch_start
                        logger.info(f"[PROGRESSIVE][STEP 8][STRETCHING][END] Added {len(stretching_workouts)} stretching workouts to plan - total duration: {stretch_duration:.2f}s")
                
                step_duration = time.time() - step_start
                logger.info(f"[PROGRESSIVE][STEP 8][END] Stretching/strength generation completed - total duration: {step_duration:.2f}s")
            
            except Exception as e:
                step_duration = time.time() - step_start
                logger.error(f"[PROGRESSIVE][STEP 8][ERROR] Error generating stretching/strength workouts after {step_duration:.2f}s: {e}", exc_info=True)
                # Continue without stretching/strength if generation fails
        
        # 9. Aggiunge metadati
        plan_data.update({
            "generated_at": datetime.utcnow().isoformat(),
            "week_start_date": self._get_week_start_date(target_dt, week_number, plan_start_date),
            "week_end_date": self._get_week_end_date(target_dt, week_number, plan_start_date)
        })
        
        generation_duration = time.time() - generation_start_time
        logger.info(f"[PROGRESSIVE][END] Weekly plan generated successfully - week: {plan_data.get('week', 'N/A')}, focus: {plan_data.get('focus', 'N/A')}, total_workouts: {len(plan_data.get('workouts', []))}, total_duration: {generation_duration:.2f}s, timestamp: {datetime.utcnow().isoformat()}")
        return plan_data
    
    def adapt_next_week_plan(self, user_id: int, target_date: str) -> Dict[str, Any]:
        """Adatta automaticamente la prossima settimana basandosi sulle performance"""
        
        # Ottiene dati della settimana corrente
        current_week_data = self.get_current_week_data(user_id)
        current_fitness_level = self.get_current_fitness_level(user_id)
        
        # Recupera piano attivo per ottenere sport_type, level, goal
        active_plan = self.db.execute(
            select(WorkoutPlan)
            .where(and_(
                WorkoutPlan.user_id == user_id,
                WorkoutPlan.status == "active"
            ))
            .order_by(desc(WorkoutPlan.created_at))
        ).scalar_one_or_none()
        
        sport_type = active_plan.sport_type if active_plan else None
        level = active_plan.level if active_plan else None
        goal = active_plan.goal if active_plan else None
        
        # Genera prossima settimana adattata
        next_week_number = current_week_data.get("week_number", 1) + 1
        next_week_plan = self.generate_weekly_plan(
            user_id=user_id,
            week_number=next_week_number,
            target_date=target_date,
            previous_week_data=current_week_data,
            current_fitness_level=current_fitness_level,
            sport_type=sport_type,
            level=level,
            goal=goal,
            weekly_hours=None
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
                                sport_specific_days: Optional[Dict[str, str]] = None,
                                available_days_in_week: Optional[List[str]] = None,
                                sport_type: Optional[str] = None,
                                level: Optional[str] = None,
                                goal: Optional[str] = None,
                                weekly_hours: Optional[float] = None) -> str:
        """Costruisce prompt ottimizzato per generazione progressiva - compatto e strutturato"""
        
        # Determina fase
        if weeks_remaining > 12:
            phase = "BASE"
        elif weeks_remaining > 4:
            phase = "BUILD"
        elif weeks_remaining > 1:
            phase = "PEAK"
        else:
            phase = "TAPER"
        
        # Parametri essenziali (variabili compatte)
        prompt = f"""Generate WEEK {week_number} progressive training plan.

PARAMETERS:
- week_number: {week_number}
- weeks_remaining: {weeks_remaining}
- target_date: {target_date}
- phase: {phase}
- sport_type: {sport_type or 'not specified'}
- level: {level or 'not specified'}
- goal: {goal or 'not specified'}
- weekly_hours: {weekly_hours or 'not specified'}
- performance_trends: {json.dumps(performance_trends) if performance_trends else 'improving'}

"""
        
        # [MANDATORY] Prima settimana parziale
        if available_days_in_week and week_number == 1:
            all_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            unavailable_days_before_start = [day for day in all_days if day not in available_days_in_week]
            prompt += f"[MANDATORY] FIRST WEEK PARTIAL: Generate workouts ONLY for {', '.join(available_days_in_week)}. DO NOT generate for {', '.join(unavailable_days_before_start) if unavailable_days_before_start else 'none'}.\n\n"
        
        # Context data (compatto)
        if previous_week:
            prompt += f"PREVIOUS_WEEK: {json.dumps(previous_week)}\n"
        if user_history:
            prompt += f"USER_HISTORY: {json.dumps(user_history)}\n"
        if current_fitness:
            prompt += f"CURRENT_FITNESS: {json.dumps(current_fitness)}\n"
            prompt += "\n"
        
        # [MANDATORY] Performance Metrics (compatto)
        if current_fitness:
            metrics = []
            if current_fitness.get('hr_max') or current_fitness.get('hr_zones'):
                hr_parts = []
                if current_fitness.get('hr_max'): hr_parts.append(f"max={current_fitness.get('hr_max')}")
                if current_fitness.get('hr_rest'): hr_parts.append(f"rest={current_fitness.get('hr_rest')}")
                if current_fitness.get('threshold_hr'): hr_parts.append(f"thr={current_fitness.get('threshold_hr')}")
                if current_fitness.get('hr_zones'):
                    zones = current_fitness.get('hr_zones')
                    if isinstance(zones, dict):
                        hr_parts.append(f"zones={','.join([f'{k}={v}' for k, v in zones.items()])}")
                if hr_parts: metrics.append(f"HR: {', '.join(hr_parts)}")
            
            if current_fitness.get('pace_zones') or current_fitness.get('threshold_pace'):
                pace_parts = []
                if current_fitness.get('threshold_pace'): pace_parts.append(f"thr={current_fitness.get('threshold_pace')}")
                if current_fitness.get('critical_speed'): pace_parts.append(f"cs={current_fitness.get('critical_speed')}")
                if current_fitness.get('pace_zones'):
                    zones = current_fitness.get('pace_zones')
                    if isinstance(zones, dict):
                        pace_parts.append(f"zones={','.join([f'{k}={v}' for k, v in zones.items()])}")
                if pace_parts: metrics.append(f"Pace: {', '.join(pace_parts)}")
            
            if current_fitness.get('power_zones') or current_fitness.get('ftp'):
                power_parts = []
                if current_fitness.get('ftp'): power_parts.append(f"ftp={current_fitness.get('ftp')}W")
                if current_fitness.get('wkg'): power_parts.append(f"wkg={current_fitness.get('wkg')}")
                if current_fitness.get('power_zones'):
                    zones = current_fitness.get('power_zones')
                    if isinstance(zones, dict):
                        power_parts.append(f"zones={','.join([f'{k}={v}W' for k, v in zones.items()])}")
                if power_parts: metrics.append(f"Power: {', '.join(power_parts)}")
            
            if current_fitness.get('vo2max'):
                metrics.append(f"VO2max: {current_fitness.get('vo2max')}")
            
            if metrics:
                preferred_zone = current_fitness.get('preferred_zone_type', 'hr').upper()
                prompt += f"[MANDATORY] PERFORMANCE_METRICS: {', '.join(metrics)}. Preferred: {preferred_zone}. Use EXACT values provided.\n\n"
        
        # Triathlon-specific guidelines based on triathlon_session_guide.md
        if sport_type and sport_type.lower() == "triathlon" and level and goal:
            # Normalizza level
            level_map = {
                "beginner": "PRINCIPIANTE",
                "intermediate": "INTERMEDIO", 
                "advanced": "AVANZATO",
                "elite": "ELITE"
            }
            normalized_level = level_map.get(level.lower(), "INTERMEDIO")
            
            # Estrai race distance dal goal
            goal_lower = goal.lower()
            if "sprint" in goal_lower:
                race_distance = "SPRINT"
            elif "olympic" in goal_lower or "olimpico" in goal_lower:
                race_distance = "OLYMPIC"
            elif "70.3" in goal_lower or "half" in goal_lower or "half-ironman" in goal_lower:
                race_distance = "70.3"
            elif "ironman" in goal_lower and "70.3" not in goal_lower and "half" not in goal_lower:
                race_distance = "IRONMAN"
            else:
                race_distance = "OLYMPIC"  # default
            
            # Determina fase basata su weeks_remaining
            if weeks_remaining > 12:
                phase = "BASE"
            elif weeks_remaining > 4:
                phase = "BUILD"
            elif weeks_remaining > 1:
                phase = "PEAK"
            else:
                phase = "TAPER"
            
            # Sessioni target per livello+distanza+fase (dal documento triathlon_session_guide.md)
            session_matrix = {
                "PRINCIPIANTE": {
                    "SPRINT": {"BASE": {"swim": 2, "bike": 2, "run": 2, "strength": 0, "brick": 0},
                              "BUILD": {"swim": 2, "bike": 2, "run": 2, "strength": 1, "brick": 1},
                              "PEAK": {"swim": 2, "bike": 2, "run": 2, "strength": 0, "brick": 1},
                              "TAPER": {"swim": 2, "bike": 1, "run": 1, "strength": 0, "brick": 0}},
                    "OLYMPIC": {"BASE": {"swim": 2, "bike": 2, "run": 2, "strength": 0, "brick": 0},
                               "BUILD": {"swim": 2, "bike": 2, "run": 2, "strength": 1, "brick": 1},
                               "PEAK": {"swim": 2, "bike": 2, "run": 2, "strength": 0, "brick": 1},
                               "TAPER": {"swim": 2, "bike": 1, "run": 1, "strength": 0, "brick": 0}}},
                "INTERMEDIO": {
                    "SPRINT": {"BASE": {"swim": 2, "bike": 2, "run": 2, "strength": 1, "brick": 0},
                              "BUILD": {"swim": 3, "bike": 3, "run": 3, "strength": 1, "brick": 1},
                              "PEAK": {"swim": 2, "bike": 2, "run": 2, "strength": 1, "brick": 1},
                              "TAPER": {"swim": 2, "bike": 1, "run": 1, "strength": 0, "brick": 1}},
                    "OLYMPIC": {"BASE": {"swim": 2, "bike": 2, "run": 2, "strength": 1, "brick": 0},
                               "BUILD": {"swim": 3, "bike": 3, "run": 3, "strength": 1, "brick": 1},
                               "PEAK": {"swim": 2, "bike": 2, "run": 2, "strength": 1, "brick": 1},
                               "TAPER": {"swim": 2, "bike": 1, "run": 1, "strength": 0, "brick": 1}}},
                "AVANZATO": {
                    "OLYMPIC": {"BASE": {"swim": 3, "bike": 3, "run": 3, "strength": 1, "brick": 1},
                               "BUILD": {"swim": 4, "bike": 4, "run": 4, "strength": 1, "brick": 2},
                               "PEAK": {"swim": 3, "bike": 3, "run": 3, "strength": 1, "brick": 1},
                               "TAPER": {"swim": 2, "bike": 2, "run": 2, "strength": 0, "brick": 0}},
                    "70.3": {"BASE": {"swim": 3, "bike": 4, "run": 3, "strength": 1, "brick": 1},
                            "BUILD": {"swim": 4, "bike": 5, "run": 4, "strength": 1, "brick": 2},
                            "PEAK": {"swim": 3, "bike": 4, "run": 3, "strength": 1, "brick": 2},
                            "TAPER": {"swim": 2, "bike": 2, "run": 2, "strength": 0, "brick": 1}}},
                "ELITE": {
                    "OLYMPIC": {"BASE": {"swim": 5, "bike": 5, "run": 4, "strength": 1, "brick": 1},
                               "BUILD": {"swim": 6, "bike": 6, "run": 5, "strength": 2, "brick": 2},
                               "PEAK": {"swim": 5, "bike": 5, "run": 4, "strength": 1, "brick": 2},
                               "TAPER": {"swim": 3, "bike": 3, "run": 2, "strength": 0, "brick": 1}},
                    "70.3": {"BASE": {"swim": 6, "bike": 6, "run": 5, "strength": 1, "brick": 2},
                            "BUILD": {"swim": 7, "bike": 7, "run": 5, "strength": 2, "brick": 3},
                            "PEAK": {"swim": 6, "bike": 6, "run": 5, "strength": 1, "brick": 3},
                            "TAPER": {"swim": 4, "bike": 4, "run": 3, "strength": 0, "brick": 1}}}}
            
            target_sessions = session_matrix.get(normalized_level, {}).get(race_distance, {}).get(phase, {})
            
            if target_sessions:
                # Calculate CORE sessions (sport-specific only)
                core_sessions = sum([target_sessions.get("swim", 0), target_sessions.get("bike", 0), 
                                   target_sessions.get("run", 0), target_sessions.get("brick", 0)])
                
                prompt += f"\n\n=== TRIATHLON TRAINING GUIDELINES (MANDATORY) ==="
                prompt += f"\nBased on scientific triathlon training guide for {normalized_level} level, {race_distance} distance, {phase} phase:"
                prompt += f"\n\nTARGET SESSIONS PER WEEK (MUST FOLLOW):"
                prompt += f"\n- Swim: {target_sessions.get('swim', 0)} sessions/week (minimum)"
                prompt += f"\n- Bike: {target_sessions.get('bike', 0)} sessions/week"
                prompt += f"\n- Run: {target_sessions.get('run', 0)} sessions/week"
                if target_sessions.get('brick', 0) > 0:
                    prompt += f"\n- Brick workouts: {target_sessions.get('brick', 0)} session(s)/week"
                prompt += f"\n- CORE SPORT SESSIONS TOTAL: {core_sessions} minimum per week (swim+bike+run+brick only)"
                
                prompt += f"\n\n[MANDATORY] SESSION COUNTING LOGIC:"
                prompt += f"\nYou MUST generate the sport-specific minimums:"
                prompt += f"\n- Swim: AT LEAST {target_sessions.get('swim', 0)} sessions/week"
                prompt += f"\n- Bike: AT LEAST {target_sessions.get('bike', 0)} sessions/week"
                prompt += f"\n- Run: AT LEAST {target_sessions.get('run', 0)} sessions/week"
                if target_sessions.get('brick', 0) > 0:
                    prompt += f"\n- Brick: AT LEAST {target_sessions.get('brick', 0)} session(s)/week"
                prompt += f"\n\nCRITICAL: Focus ONLY on core sport-specific sessions."
                
                prompt += f"\n\nCRITICAL RULES:"
                prompt += f"\n- Swim frequency is CRITICAL: minimum {target_sessions.get('swim', 0)}×/week (technique-dependent)"
                prompt += f"\n- Distribution: Swim 15-20%, Bike 45-55%, Run 25-35% of total volume"
                if target_sessions.get('brick', 0) > 0:
                    prompt += f"\n- MUST include {target_sessions.get('brick', 0)} brick workout(s) (bike+run same day)"
                    if weeks_remaining <= 8:
                        prompt += f"\n- Brick workouts should be race-specific practice"
                if normalized_level in ["INTERMEDIO", "AVANZATO", "ELITE"]:
                    prompt += f"\n- Include 1-2 quality sessions per discipline (intervals/tempo)"
                if normalized_level == "ELITE":
                    prompt += f"\n- Double sessions allowed (easy+easy pairs, minimum 3h recovery between)"
                    prompt += f"\n- Back-to-back days possible for easy sessions"
                
                prompt += f"\n\nWEEK STRUCTURE GUIDELINES:"
                if normalized_level == "PRINCIPIANTE":
                    prompt += f"\n- No intensity sessions, focus on consistency"
                    prompt += f"\n- No brick workouts in BASE phase"
                elif normalized_level == "INTERMEDIO":
                    prompt += f"\n- 1 quality session per discipline (bike intervals, run tempo)"
                    prompt += f"\n- 1 brick workout/week in BUILD+PEAK phases"
                    prompt += f"\n- Double sessions only easy+easy (not hard+anything)"
                elif normalized_level == "AVANZATO":
                    prompt += f"\n- 2 hard sessions/week (bike intervals + run intervals)"
                    prompt += f"\n- 1-2 brick workouts/week"
                    prompt += f"\n- 2-3 double sessions/week (easy pairs)"
                elif normalized_level == "ELITE":
                    prompt += f"\n- 2-3 hard sessions/week"
                    prompt += f"\n- 2-3 brick workouts/week (one long double)"
                    prompt += f"\n- 4-5 double sessions/week"
                    prompt += f"\n- Back-to-back days for easy sessions"
                
                prompt += f"\n\nMANDATORY: Generate {core_sessions} CORE sport workouts minimum this week (swim+bike+run+brick only)."
                prompt += f"\n"
        
        # Running-specific guidelines based on running_session_guide.md
        if sport_type and sport_type.lower() == "running" and level and goal:
            level_map = {
                "beginner": "PRINCIPIANTE",
                "intermediate": "INTERMEDIO", 
                "advanced": "AVANZATO",
                "elite": "ELITE"
            }
            normalized_level = level_map.get(level.lower(), "INTERMEDIO")
            
            # Estrai race distance dal goal
            goal_lower = goal.lower()
            if "5k" in goal_lower or "5 k" in goal_lower:
                race_distance = "5K"
            elif "10k" in goal_lower or "10 k" in goal_lower:
                race_distance = "10K"
            elif "half" in goal_lower or "hm" in goal_lower or "21" in goal_lower:
                race_distance = "HM"
            elif "marathon" in goal_lower or "maratona" in goal_lower or "42" in goal_lower:
                race_distance = "MARATHON"
            else:
                race_distance = "10K"  # default
            
            # Determina fase
            if weeks_remaining > 12:
                phase = "BASE"
            elif weeks_remaining > 4:
                phase = "BUILD"
            elif weeks_remaining > 1:
                phase = "PEAK"
            else:
                phase = "TAPER"
            
            # Matrice sessioni running
            session_matrix = {
                "PRINCIPIANTE": {
                    "5K": {"BASE": {"easy": 3, "moderate": 0, "hard": 0, "long": 1},
                          "BUILD": {"easy": 2, "moderate": 1, "hard": 0, "long": 1},
                          "PEAK": {"easy": 2, "moderate": 0, "hard": 1, "long": 1},
                          "TAPER": {"easy": 2, "moderate": 0, "hard": 0, "long": 0}},
                    "10K": {"BASE": {"easy": 3, "moderate": 0, "hard": 0, "long": 1},
                           "BUILD": {"easy": 2, "moderate": 1, "hard": 0, "long": 1},
                           "PEAK": {"easy": 2, "moderate": 0, "hard": 1, "long": 1},
                           "TAPER": {"easy": 2, "moderate": 0, "hard": 0, "long": 0}},
                    "HM": {"BASE": {"easy": 3, "moderate": 0, "hard": 0, "long": 1},
                          "BUILD": {"easy": 2, "moderate": 1, "hard": 0, "long": 1},
                          "PEAK": {"easy": 2, "moderate": 0, "hard": 1, "long": 1},
                          "TAPER": {"easy": 2, "moderate": 0, "hard": 0, "long": 1}},
                    "MARATHON": {"BASE": {"easy": 3, "moderate": 0, "hard": 0, "long": 1},
                                "BUILD": {"easy": 2, "moderate": 1, "hard": 0, "long": 1},
                                "PEAK": {"easy": 2, "moderate": 0, "hard": 1, "long": 1},
                                "TAPER": {"easy": 2, "moderate": 0, "hard": 0, "long": 1}}},
                "INTERMEDIO": {
                    "5K": {"BASE": {"easy": 2, "moderate": 1, "hard": 0, "long": 1},
                          "BUILD": {"easy": 2, "moderate": 1, "hard": 1, "long": 1},
                          "PEAK": {"easy": 1, "moderate": 1, "hard": 1, "long": 1},
                          "TAPER": {"easy": 2, "moderate": 0, "hard": 0, "long": 1}},
                    "10K": {"BASE": {"easy": 2, "moderate": 1, "hard": 0, "long": 1},
                           "BUILD": {"easy": 2, "moderate": 1, "hard": 1, "long": 1},
                           "PEAK": {"easy": 1, "moderate": 1, "hard": 1, "long": 1},
                           "TAPER": {"easy": 2, "moderate": 0, "hard": 0, "long": 1}},
                    "HM": {"BASE": {"easy": 2, "moderate": 1, "hard": 0, "long": 1},
                          "BUILD": {"easy": 2, "moderate": 1, "hard": 1, "long": 1},
                          "PEAK": {"easy": 1, "moderate": 1, "hard": 1, "long": 1},
                          "TAPER": {"easy": 2, "moderate": 0, "hard": 0, "long": 1}},
                    "MARATHON": {"BASE": {"easy": 2, "moderate": 1, "hard": 0, "long": 1},
                                "BUILD": {"easy": 2, "moderate": 1, "hard": 1, "long": 1},
                                "PEAK": {"easy": 1, "moderate": 1, "hard": 1, "long": 1},
                                "TAPER": {"easy": 2, "moderate": 0, "hard": 0, "long": 1}}},
                "AVANZATO": {
                    "HM": {"BASE": {"easy": 2, "moderate": 1, "hard": 1, "long": 1},
                          "BUILD": {"easy": 2, "moderate": 1, "hard": 2, "long": 1},
                          "PEAK": {"easy": 1, "moderate": 1, "hard": 2, "long": 1},
                          "TAPER": {"easy": 2, "moderate": 0, "hard": 1, "long": 1}},
                    "MARATHON": {"BASE": {"easy": 2, "moderate": 1, "hard": 1, "long": 1},
                                "BUILD": {"easy": 2, "moderate": 1, "hard": 2, "long": 1},
                                "PEAK": {"easy": 1, "moderate": 1, "hard": 2, "long": 1},
                                "TAPER": {"easy": 2, "moderate": 0, "hard": 1, "long": 1}}},
                "ELITE": {
                    "HM": {"BASE": {"easy": 2, "moderate": 1, "hard": 2, "long": 1},
                          "BUILD": {"easy": 2, "moderate": 1, "hard": 3, "long": 1},
                          "PEAK": {"easy": 1, "moderate": 1, "hard": 3, "long": 1},
                          "TAPER": {"easy": 2, "moderate": 0, "hard": 1, "long": 1}},
                    "MARATHON": {"BASE": {"easy": 2, "moderate": 1, "hard": 2, "long": 1},
                                "BUILD": {"easy": 2, "moderate": 1, "hard": 3, "long": 1},
                                "PEAK": {"easy": 1, "moderate": 1, "hard": 3, "long": 1},
                                "TAPER": {"easy": 2, "moderate": 0, "hard": 1, "long": 1}}}}
            
            target_sessions = session_matrix.get(normalized_level, {}).get(race_distance, {}).get(phase, {})
            
            if target_sessions:
                total_sessions = sum([target_sessions.get("easy", 0), target_sessions.get("moderate", 0), 
                                     target_sessions.get("hard", 0), target_sessions.get("long", 0)])
                
                prompt += f"\n\n=== RUNNING TRAINING GUIDELINES (MANDATORY) ==="
                prompt += f"\nBased on scientific running training guide for {normalized_level} level, {race_distance} distance, {phase} phase:"
                prompt += f"\n\nTARGET SESSIONS PER WEEK (MUST FOLLOW):"
                prompt += f"\n- Easy runs (Zone 1-2): {target_sessions.get('easy', 0)} sessions/week"
                if target_sessions.get('moderate', 0) > 0:
                    prompt += f"\n- Moderate runs (Zone 3): {target_sessions.get('moderate', 0)} session(s)/week"
                if target_sessions.get('hard', 0) > 0:
                    prompt += f"\n- Hard runs (Zone 4-5): {target_sessions.get('hard', 0)} session(s)/week (intervals/tempo)"
                prompt += f"\n- Long run: {target_sessions.get('long', 0)} session(s)/week"
                prompt += f"\n- CORE RUNNING SESSIONS TOTAL: {total_sessions} per week (easy+moderate+hard+long only)"
                
                prompt += f"\n\n[MANDATORY] SESSION COUNTING LOGIC:"
                prompt += f"\nYou MUST generate the running minimums:"
                prompt += f"\n- Easy runs: AT LEAST {target_sessions.get('easy', 0)} sessions/week"
                if target_sessions.get('moderate', 0) > 0:
                    prompt += f"\n- Moderate runs: AT LEAST {target_sessions.get('moderate', 0)} session(s)/week"
                if target_sessions.get('hard', 0) > 0:
                    prompt += f"\n- Hard runs: AT LEAST {target_sessions.get('hard', 0)} session(s)/week"
                prompt += f"\n- Long run: AT LEAST {target_sessions.get('long', 0)} session(s)/week"
                prompt += f"\n\nCRITICAL: Focus ONLY on running-specific sessions."
                
                prompt += f"\n\nINTENSITY DISTRIBUTION:"
                if normalized_level == "PRINCIPIANTE":
                    prompt += f"\n- Easy (Zone 1-2): 90% volume"
                    prompt += f"\n- Moderate (Zone 3): 10% volume"
                    prompt += f"\n- Hard (Zone 4-5): 0%"
                elif normalized_level == "INTERMEDIO":
                    prompt += f"\n- Easy (Zone 1-2): 70% volume"
                    prompt += f"\n- Moderate (Zone 3): 20% volume"
                    prompt += f"\n- Hard (Zone 4-5): 10% volume"
                elif normalized_level == "AVANZATO":
                    prompt += f"\n- Easy (Zone 1-2): 65% volume"
                    prompt += f"\n- Moderate (Zone 3): 20% volume"
                    prompt += f"\n- Hard (Zone 4-5): 15% volume"
                elif normalized_level == "ELITE":
                    prompt += f"\n- Easy (Zone 1-2): 60% volume"
                    prompt += f"\n- Moderate (Zone 3): 20% volume"
                    prompt += f"\n- Hard (Zone 4-5): 20% volume"
                
                prompt += f"\n\nWEEK STRUCTURE GUIDELINES:"
                if normalized_level == "PRINCIPIANTE":
                    prompt += f"\n- Focus on consistency and base building"
                    prompt += f"\n- 1 rest day minimum"
                    prompt += f"\n- Long run 25-40% of weekly volume"
                elif normalized_level == "INTERMEDIO":
                    prompt += f"\n- 2 quality sessions (1 intervals, 1 tempo)"
                    prompt += f"\n- 1 long run weekly"
                elif normalized_level == "AVANZATO":
                    prompt += f"\n- 2 hard sessions (VO2max + threshold)"
                    prompt += f"\n- 1 long run 18-20 km weekly"
                elif normalized_level == "ELITE":
                    prompt += f"\n- 2-3 hard sessions (VO2max, threshold, marathon pace)"
                    prompt += f"\n- 1 long run 25-27 km weekly"
                    prompt += f"\n- Back-to-back easy sessions possible"
                
                prompt += f"\n\nMANDATORY: Generate {total_sessions} running workouts minimum this week (easy+moderate+hard+long only)."
                prompt += f"\n"
        
        # Trail Running-specific guidelines based on trail_running_session_guide.md
        if sport_type and sport_type.lower() in ["trail running", "trail"] and level and goal:
            level_map = {
                "beginner": "PRINCIPIANTE",
                "intermediate": "INTERMEDIO", 
                "advanced": "AVANZATO",
                "elite": "ELITE"
            }
            normalized_level = level_map.get(level.lower(), "INTERMEDIO")
            
            # Estrai race distance dal goal
            goal_lower = goal.lower()
            if "short" in goal_lower or "10" in goal_lower or "20" in goal_lower:
                race_distance = "SHORT"
            elif "middle" in goal_lower or "30" in goal_lower or "40" in goal_lower:
                race_distance = "MIDDLE"
            elif "ultra" in goal_lower or "50" in goal_lower or "100" in goal_lower:
                race_distance = "ULTRA"
            else:
                race_distance = "MIDDLE"  # default
            
            # Determina fase
            if weeks_remaining > 12:
                phase = "BASE"
            elif weeks_remaining > 4:
                phase = "BUILD"
            elif weeks_remaining > 1:
                phase = "PEAK"
            else:
                phase = "TAPER"
            
            prompt += f"\n\n=== TRAIL RUNNING TRAINING GUIDELINES (MANDATORY) ==="
            prompt += f"\nBased on scientific trail running training guide for {normalized_level} level, {race_distance} trail distance, {phase} phase:"
            prompt += f"\n\nCRITICAL: Trail running differs from road - elevation gain significantly increases load."
            prompt += f"\n- Dislivello (D+) increases physiological stress"
            prompt += f"\n- Downhills cause eccentric fatigue, require longer recovery"
            prompt += f"\n- Max +15% D+ increase week-to-week"
            prompt += f"\n- Never 2 consecutive days with >500m D- (downhill focus)"
            
            prompt += f"\n\nTARGET SESSIONS PER WEEK:"
            if normalized_level == "PRINCIPIANTE":
                prompt += f"\n- 2-3 trail sessions/week"
                prompt += f"\n- Focus on uphill technique (walking is OK)"
                prompt += f"\n- Max 600m D+ per session initially"
            elif normalized_level == "INTERMEDIO":
                prompt += f"\n- 3-4 trail sessions/week"
                prompt += f"\n- 1 uphill power session"
                prompt += f"\n- 1 long slow trail"
            elif normalized_level == "AVANZATO":
                prompt += f"\n- 4-5 trail sessions/week"
                prompt += f"\n- 2 hard sessions (uphill power + trail threshold)"
                prompt += f"\n- 1 downhill technique session weekly"
                prompt += f"\n- 1 long skyrace prep"
            elif normalized_level == "ELITE":
                prompt += f"\n- 5-7 trail sessions/week"
                prompt += f"\n- 2-3 hard sessions (VO2max, threshold, downhill reps)"
                prompt += f"\n- 1-2 downhill technique sessions"
                prompt += f"\n- 1 long ultra prep (25-30 km, 1500m+ D+)"
            
            prompt += f"\n\n[MANDATORY] SESSION COUNTING LOGIC:"
            prompt += f"\nYou MUST generate the trail running minimums INDEPENDENTLY of strength and stretching:"
            if normalized_level == "PRINCIPIANTE":
                prompt += f"\n- Trail sessions: AT LEAST 2-3 sessions/week (do NOT count strength/stretching toward this)"
            elif normalized_level == "INTERMEDIO":
                prompt += f"\n- Trail sessions: AT LEAST 3-4 sessions/week (do NOT count strength/stretching toward this)"
            elif normalized_level == "AVANZATO":
                prompt += f"\n- Trail sessions: AT LEAST 4-5 sessions/week (do NOT count strength/stretching toward this)"
            elif normalized_level == "ELITE":
                prompt += f"\n- Trail sessions: AT LEAST 5-7 sessions/week (do NOT count strength/stretching toward this)"
            prompt += f"\n\nCRITICAL: Focus ONLY on trail running sessions."
            
            prompt += f"\n\nELEVATION SAFETY RULES:"
            prompt += f"\n- Max D+ per session: PRINCIPIANTE=600m, INTERMEDIO=1000m, AVANZATO=1500m, ELITE=2500m"
            prompt += f"\n- No 2 consecutive days with high D+"
            prompt += f"\n- +1-2 days extra recovery after >1500m D+ session"
            prompt += f"\n- Monitor DOMS (especially posterior chain)"
            
            prompt += f"\n\nMANDATORY: Generate trail workouts with appropriate elevation gain for {normalized_level} level."
            prompt += f"\n"
        
        # Swimming-specific guidelines based on swimming_session_guide.md
        if sport_type and sport_type.lower() in ["swimming", "swim"] and level and goal:
            level_map = {
                "beginner": "PRINCIPIANTE",
                "intermediate": "INTERMEDIO", 
                "advanced": "AVANZATO",
                "elite": "ELITE"
            }
            normalized_level = level_map.get(level.lower(), "INTERMEDIO")
            
            # Estrai race distance dal goal
            goal_lower = goal.lower()
            if "sprint" in goal_lower or "50" in goal_lower or "100" in goal_lower or "200" in goal_lower:
                race_distance = "SPRINT"
            elif "middle" in goal_lower or "400" in goal_lower or "800" in goal_lower:
                race_distance = "MIDDLE"
            elif "distance" in goal_lower or "1500" in goal_lower or "open water" in goal_lower or "ow" in goal_lower:
                race_distance = "DISTANCE"
            else:
                race_distance = "MIDDLE"  # default
            
            # Determina fase
            if weeks_remaining > 12:
                phase = "BASE"
            elif weeks_remaining > 4:
                phase = "BUILD"
            elif weeks_remaining > 1:
                phase = "PEAK"
            else:
                phase = "TAPER"
            
            prompt += f"\n\n=== SWIMMING TRAINING GUIDELINES (MANDATORY) ==="
            prompt += f"\nBased on scientific swimming training guide for {normalized_level} level, {race_distance} distance, {phase} phase:"
            prompt += f"\n\nCRITICAL: FREQUENCY > VOLUME for swimming."
            prompt += f"\n- Technique is frequency-dependent"
            prompt += f"\n- 3× weekly minimum (even for beginners)"
            prompt += f"\n- Better 3× short sessions than 1× long session"
            
            prompt += f"\n\nTARGET SESSIONS PER WEEK:"
            if normalized_level == "PRINCIPIANTE":
                prompt += f"\n- 2-3 sessions/week MINIMUM"
                prompt += f"\n- Focus on technique, no intensity"
                prompt += f"\n- Volume: 3-5 km/week"
            elif normalized_level == "INTERMEDIO":
                prompt += f"\n- 3-4 sessions/week"
                prompt += f"\n- 1 quality session (race pace)"
                prompt += f"\n- Volume: 7-10 km/week"
            elif normalized_level == "AVANZATO":
                prompt += f"\n- 4-5 sessions/week"
                prompt += f"\n- 2 hard sessions (threshold + VO2max)"
                prompt += f"\n- 1 long/OW session"
                prompt += f"\n- Volume: 12-18 km/week"
            elif normalized_level == "ELITE":
                prompt += f"\n- 6-7 sessions/week"
                prompt += f"\n- 3 hard sessions (threshold, VO2max, sprint)"
                prompt += f"\n- 1-2 OW sessions weekly (in season)"
                prompt += f"\n- Volume: 18-28 km/week"
            
            prompt += f"\n\n[MANDATORY] SESSION COUNTING LOGIC:"
            prompt += f"\nYou MUST generate the swimming minimums INDEPENDENTLY of strength and stretching:"
            if normalized_level == "PRINCIPIANTE":
                prompt += f"\n- Swim sessions: AT LEAST 2-3 sessions/week (do NOT count strength/stretching toward this)"
            elif normalized_level == "INTERMEDIO":
                prompt += f"\n- Swim sessions: AT LEAST 3-4 sessions/week (do NOT count strength/stretching toward this)"
            elif normalized_level == "AVANZATO":
                prompt += f"\n- Swim sessions: AT LEAST 4-5 sessions/week (do NOT count strength/stretching toward this)"
            elif normalized_level == "ELITE":
                prompt += f"\n- Swim sessions: AT LEAST 6-7 sessions/week (do NOT count strength/stretching toward this)"
            prompt += f"\n\nCRITICAL: Focus ONLY on swimming sessions."
            
            prompt += f"\n\nINTENSITY DISTRIBUTION:"
            if normalized_level == "PRINCIPIANTE":
                prompt += f"\n- Easy (Zone 1-2): 90% volume"
                prompt += f"\n- Moderate (Zone 3): 10% volume"
                prompt += f"\n- Hard (Zone 4-5): 0%"
            elif normalized_level == "INTERMEDIO":
                prompt += f"\n- Easy (Zone 1-2): 60% volume"
                prompt += f"\n- Moderate (Zone 3): 25% volume"
                prompt += f"\n- Hard (Zone 4-5): 15% volume"
            elif normalized_level == "AVANZATO":
                prompt += f"\n- Easy (Zone 1-2): 50% volume"
                prompt += f"\n- Moderate (Zone 3): 25% volume"
                prompt += f"\n- Hard (Zone 4-5): 25% volume"
            elif normalized_level == "ELITE":
                prompt += f"\n- Easy (Zone 1-2): 45% volume"
                prompt += f"\n- Moderate (Zone 3): 20% volume"
                prompt += f"\n- Hard (Zone 4-5): 35% volume"
            
            prompt += f"\n\nSPECIFIC RULES:"
            prompt += f"\n- Always include warm-up (400-600m) and cool-down (300-600m)"
            prompt += f"\n- Include drills for technique (kick, pull, stroke focus)"
            if race_distance == "DISTANCE" and normalized_level in ["AVANZATO", "ELITE"]:
                prompt += f"\n- Include 1-2 open water sessions/week in season"
            
            prompt += f"\n\nMANDATORY: Generate swimming workouts with proper technique focus and appropriate volume for {normalized_level} level."
            prompt += f"\n"
        
        # Cycling-specific guidelines based on cycling_session_guide.md
        if sport_type and sport_type.lower() in ["cycling", "bike", "bicycle"] and level and goal:
            level_map = {
                "beginner": "PRINCIPIANTE",
                "intermediate": "INTERMEDIO", 
                "advanced": "AVANZATO",
                "elite": "ELITE"
            }
            normalized_level = level_map.get(level.lower(), "INTERMEDIO")
            
            # Estrai specialty dal goal
            goal_lower = goal.lower()
            if "gran fondo" in goal_lower or "granfondo" in goal_lower or "fond" in goal_lower:
                specialty = "GRAN_FONDO"
            elif "race" in goal_lower or "agon" in goal_lower or "velocit" in goal_lower:
                specialty = "ROAD_RACE"
            elif "xc" in goal_lower or "ciclocross" in goal_lower or "mtb" in goal_lower:
                specialty = "XC"
            else:
                specialty = "GRAN_FONDO"  # default
            
            # Determina fase
            if weeks_remaining > 12:
                phase = "BASE"
            elif weeks_remaining > 4:
                phase = "BUILD"
            elif weeks_remaining > 1:
                phase = "PEAK"
            else:
                phase = "TAPER"
            
            prompt += f"\n\n=== CYCLING TRAINING GUIDELINES (MANDATORY) ==="
            prompt += f"\nBased on scientific cycling training guide for {normalized_level} level, {specialty} specialty, {phase} phase:"
            prompt += f"\n\nCRITICAL METRICS:"
            prompt += f"\n- Use TSS (Training Stress Score) and Power (Watts) as primary metrics"
            prompt += f"\n- FTP (Functional Threshold Power) required for intensity prescription"
            prompt += f"\n- Cadence: 85-95 RPM (beginner), 90-100 RPM (elite)"
            
            prompt += f"\n\nTARGET SESSIONS PER WEEK:"
            if normalized_level == "PRINCIPIANTE":
                prompt += f"\n- 3-4 sessions/week"
                prompt += f"\n- 1 quality session + 1 long weekly"
                prompt += f"\n- Weekly TSS: 250-350"
            elif normalized_level == "INTERMEDIO":
                prompt += f"\n- 4-5 sessions/week"
                prompt += f"\n- 2 hard sessions (threshold + intervals/tempo)"
                prompt += f"\n- 1 long steady weekly"
                prompt += f"\n- Weekly TSS: 400-550"
            elif normalized_level == "AVANZATO":
                prompt += f"\n- 5-6 sessions/week"
                prompt += f"\n- 2-3 hard sessions (VO2max, threshold, tempo)"
                prompt += f"\n- 1 long gran fondo specific"
                prompt += f"\n- Weekly TSS: 600-800"
            elif normalized_level == "ELITE":
                prompt += f"\n- 6-8 sessions/week"
                prompt += f"\n- 3-4 hard sessions (VO2max, threshold, sprint, race sim)"
                prompt += f"\n- 1 long ultra-endurance (200+ km)"
                prompt += f"\n- Weekly TSS: 1000-1400"
            
            prompt += f"\n\n[MANDATORY] SESSION COUNTING LOGIC:"
            prompt += f"\nYou MUST generate the cycling minimums INDEPENDENTLY of strength and stretching:"
            if normalized_level == "PRINCIPIANTE":
                prompt += f"\n- Bike sessions: AT LEAST 3-4 sessions/week (do NOT count strength/stretching toward this)"
            elif normalized_level == "INTERMEDIO":
                prompt += f"\n- Bike sessions: AT LEAST 4-5 sessions/week (do NOT count strength/stretching toward this)"
            elif normalized_level == "AVANZATO":
                prompt += f"\n- Bike sessions: AT LEAST 5-6 sessions/week (do NOT count strength/stretching toward this)"
            elif normalized_level == "ELITE":
                prompt += f"\n- Bike sessions: AT LEAST 6-8 sessions/week (do NOT count strength/stretching toward this)"
            prompt += f"\n\nCRITICAL: Focus ONLY on cycling sessions."
            
            prompt += f"\n\nINTENSITY DISTRIBUTION:"
            if normalized_level == "PRINCIPIANTE":
                prompt += f"\n- Easy (Zone 1-2): 80% volume"
                prompt += f"\n- Moderate (Zone 3): 15% volume"
                prompt += f"\n- Hard (Zone 4-5): 5% volume"
            elif normalized_level == "INTERMEDIO":
                prompt += f"\n- Easy (Zone 1-2): 65% volume"
                prompt += f"\n- Moderate (Zone 3): 20% volume"
                prompt += f"\n- Hard (Zone 4-5): 15% volume"
            elif normalized_level == "AVANZATO":
                prompt += f"\n- Easy (Zone 1-2): 55% volume"
                prompt += f"\n- Moderate (Zone 3): 25% volume"
                prompt += f"\n- Hard (Zone 4-5): 20% volume"
            elif normalized_level == "ELITE":
                prompt += f"\n- Easy (Zone 1-2): 50% volume"
                prompt += f"\n- Moderate (Zone 3): 25% volume"
                prompt += f"\n- Hard (Zone 4-5): 25% volume"
            
            prompt += f"\n\nSPECIFIC RULES:"
            prompt += f"\n- Hard sessions should not be back-to-back (max same day easy+hard)"
            prompt += f"\n- Long ride weekly in all phases"
            if normalized_level == "ELITE":
                prompt += f"\n- 3-4 double sessions/week possible"
                prompt += f"\n- Back-to-back hard possible with adequate recovery (48h+)"
            
            prompt += f"\n\nMANDATORY: Generate cycling workouts with TSS targets and power zones for {normalized_level} level."
            prompt += f"\n"
        
        # Stretching and strength are handled algorithmically, not by the AI model
        # Removed stretching and strength prompt sections
        
        # [MANDATORY] Day constraints
        if unavailable_days:
            prompt += f"[MANDATORY] UNAVAILABLE_DAYS: {', '.join(unavailable_days)}. NO workouts on these days.\n"
        if sport_specific_days:
            sport_days_list = [f"{day}:{sport}" for day, sport in sport_specific_days.items()]
            prompt += f"[MANDATORY] SPORT_SPECIFIC_DAYS: {', '.join(sport_days_list)}. MUST generate workout for each.\n"
            if unavailable_days:
                conflicts = [day for day in sport_specific_days.keys() if day in unavailable_days]
                if conflicts:
                    prompt += f"CONFLICT: {', '.join(conflicts)} in both lists. SPORT_SPECIFIC prevails.\n"
            
        # [MANDATORY] Output requirements
        prompt += f"""
[MANDATORY] OUTPUT_REQUIREMENTS:

[MANDATORY] SESSION COUNTING RULES:
- Core sport sessions (run/bike/swim/triathlon-specific) must be generated to meet the MINIMUM requirements specified in the sport-specific guidelines above.
- Focus ONLY on the core sport-specific training.

1. GENERAL: Every step MUST have step_type, duration, target (for endurance), notes. Target is REQUIRED for all endurance steps (run/bike/swim). Format: {{"type": "zone", "zone": "Z1-Z7"}}. NEVER put structure only in notes - each step must be a complete JSON object.

2. INTERVALLI (CRITICAL): Use step_type "repeat" with repeat: N and steps: [interval_step, recovery_step]. Each interval step: step_type "interval", duration {{"type": "time", "seconds": X}}, target {{"type": "zone", "zone": "Z4"}}. Each recovery: step_type "recovery", duration {{"type": "time", "seconds": X}}, target {{"type": "zone", "zone": "Z1"}}. Example "5min Z4/3min Z1 x4": {{"step_type": "repeat", "repeat": 4, "steps": [{{"step_type": "interval", "duration": {{"type": "time", "seconds": 300}}, "target": {{"type": "zone", "zone": "Z4"}}}}, {{"step_type": "recovery", "duration": {{"type": "time", "seconds": 180}}, "target": {{"type": "zone", "zone": "Z1"}}}}]}}.

3. BRICK: Create TWO separate workouts on same day (bike first, then run). Both need complete structure (warmup/main/cooldown). NO transition steps.

4. SWIM: Use duration {{"type": "distance", "meters": X}} when distance is known. Drills need name field. Main set with repeats: use step_type "repeat" with swim steps. Example "4x200m": {{"step_type": "repeat", "repeat": 4, "steps": [{{"step_type": "swim", "duration": {{"type": "distance", "meters": 200}}, "target": {{"type": "zone", "zone": "Z3"}}}}]}}.

5. BIKE POWER: Use ONLY target {{"type": "zone", "zone": "Z2-Z7"}}. System calculates watts from FTP. DO NOT specify watts explicitly. Zones: Z2=55-75% FTP, Z3=75-90%, Z4=90-105%, Z5=105-120%, Z6=120-150%, Z7=150%+ FTP.

MINIMUM REQUIREMENTS:
- Minimum 1 rest day if weekly_hours allows
- ALL workouts MUST have complete 'structure' field: {{sport, segments: [{{segment_type, steps: [...]}}], metadata}}
- Structure: warmup, main, cooldown segments required
- Focus ONLY on core sport-specific workouts
"""
        
        prompt += f"""
[STRONGLY RECOMMENDED] ADAPTATION_RULES:
- RPE < 6: +5-10% intensity
- RPE > 8: -5-10% intensity
- Missed >2 workouts: -20% volume
- All completed easily: +10% volume
- Adjust based on performance_trends and weeks_remaining

[OPTIONAL] General guidelines: optimal distribution, recovery considerations, peak timing

OUTPUT_FORMAT (JSON only, no markdown):
        {{
            "week": {week_number},
            "focus": "Week focus description",
            "adaptations": {{"intensity_change": "+5%", "volume_change": "+10%", "rationale": "..."}},
            "workouts": [
                {{
                    "day": "Monday",
                    "type": "Intervals",
                    "duration_minutes": 45,
                    "intensity": "Z4",
                    "target_hr": "162-169",
                    "rpe_target": 7,
                    "description": "Interval training",
                    "key_focus": "Speed development",
                    "structure": {{
                        "sport": "run",
                        "segments": [
                            {{"segment_type": "warmup", "steps": [{{"step_type": "steady", "duration": {{"type": "time", "seconds": 600}}, "target": {{"type": "zone", "zone": "Z2"}}, "notes": "Warm-up"}}]}},
                            {{"segment_type": "main", "steps": [{{"step_type": "repeat", "repeat": 4, "steps": [{{"step_type": "interval", "duration": {{"type": "time", "seconds": 300}}, "target": {{"type": "zone", "zone": "Z4"}}, "notes": "Fast pace"}}, {{"step_type": "recovery", "duration": {{"type": "time", "seconds": 180}}, "target": {{"type": "zone", "zone": "Z1"}}, "notes": "Recovery"}}]}}]}},
                            {{"segment_type": "cooldown", "steps": [{{"step_type": "steady", "duration": {{"type": "time", "seconds": 600}}, "target": {{"type": "zone", "zone": "Z1"}}, "notes": "Cool-down"}}]}}
                        ],
                        "metadata": {{"focus": "Speed", "rpe_target": 7}}
                    }}
                }},
                {{
                    "day": "Friday",
                    "type": "Swim",
                    "duration_minutes": 60,
                    "intensity": "Mixed",
                    "target_hr": "N/A",
                    "rpe_target": 6,
                    "description": "Swim with drills",
                    "key_focus": "Technique",
                    "structure": {{
                        "sport": "swim",
                        "segments": [
                            {{"segment_type": "warmup", "steps": [{{"step_type": "swim", "duration": {{"type": "distance", "meters": 200}}, "target": {{"type": "zone", "zone": "Z1"}}, "notes": "Easy swim"}}]}},
                            {{"segment_type": "main", "steps": [{{"step_type": "swim", "name": "Kick Drill", "duration": {{"type": "distance", "meters": 100}}, "target": {{"type": "zone", "zone": "Z1"}}, "notes": "Kick focus"}}, {{"step_type": "repeat", "repeat": 4, "steps": [{{"step_type": "swim", "duration": {{"type": "distance", "meters": 200}}, "target": {{"type": "zone", "zone": "Z3"}}, "notes": "Main set"}}]}}]}},
                            {{"segment_type": "cooldown", "steps": [{{"step_type": "swim", "duration": {{"type": "distance", "meters": 200}}, "target": {{"type": "zone", "zone": "Z1"}}, "notes": "Easy swim"}}]}}
                        ],
                        "metadata": {{"focus": "Swim technique", "rpe_target": 6}}
                    }}
                }}
            ],
            "recovery_notes": "...",
            "next_week_preview": "...",
            "adaptation_rationale": "..."
        }}

NOTE: For brick workouts, create TWO separate workouts on the same day (bike first, then run). For bike, use zone-based target only.

ERROR_HANDLING: If constraints impossible (too few days, insufficient weekly_hours), return:
{{"error": true, "reason": "...", "suggestion": "..."}}

Generate ONLY this week's plan. Output JSON only, no explanations.
        """
        return prompt
    
    def _calculate_weeks_remaining(self, target_date: date, current_week: int) -> int:
        """Calcola settimane rimanenti alla data target"""
        today = date.today()
        days_remaining = (target_date - today).days
        weeks_remaining = max(0, days_remaining // 7)
        return weeks_remaining
    
    def _get_week_start_date(self, target_date: date, week_number: int, plan_start_date: Optional[date] = None) -> str:
        """Calcola data inizio settimana"""
        if week_number == 1 and plan_start_date:
            # Prima settimana: usa la data di inizio fornita
            return plan_start_date.isoformat()
        else:
            # Settimane successive: calcola dalla data di inizio del piano o assume 12 settimane prima del target
            if plan_start_date:
                # Calcola dalla data di inizio del piano
                # La settimana 2 inizia il lunedì successivo alla domenica della settimana 1
                week1_end = plan_start_date + timedelta(days=(6 - plan_start_date.weekday()))
                week_start = week1_end + timedelta(days=1)  # Lunedì successivo
                if week_number > 2:
                    week_start = week_start + timedelta(weeks=week_number - 2)
            else:
                # Fallback: calcola assumendo 12 settimane prima del target
                plan_start = target_date - timedelta(weeks=12)
                week_start = plan_start + timedelta(weeks=week_number-1)
                # Assicurati che inizi da lunedì per settimane successive
                if week_number > 1:
                    # Trova il lunedì della settimana
                    days_since_monday = week_start.weekday()
                    week_start = week_start - timedelta(days=days_since_monday)
            return week_start.isoformat()
    
    def _get_week_end_date(self, target_date: date, week_number: int, plan_start_date: Optional[date] = None) -> str:
        """Calcola data fine settimana"""
        week_start = self._get_week_start_date(target_date, week_number, plan_start_date)
        week_start_dt = datetime.strptime(week_start, "%Y-%m-%d").date()
        
        if week_number == 1 and plan_start_date:
            # Prima settimana: finisce sempre domenica
            days_to_sunday = 6 - week_start_dt.weekday()
            week_end = week_start_dt + timedelta(days=days_to_sunday)
        else:
            # Settimane successive: sempre domenica (6 giorni dopo il lunedì)
            week_end = week_start_dt + timedelta(days=6)
        
        return week_end.isoformat()
    
    def _check_required_workouts(
        self,
        plan_data: Dict[str, Any],
        include_strength: bool,
        include_stretching: bool,
        strength_freq: str,
        stretching_freq: int,
    ) -> Dict[str, Any]:
        """Check if required strength/stretching workouts are present in the plan"""
        workouts = plan_data.get("workouts", [])
        
        strength_count = 0
        stretching_count = 0
        
        for workout in workouts:
            workout_type = (workout.get("type") or "").lower()
            sport = (workout.get("structure", {}).get("sport") or "").lower()
            
            if "strength" in workout_type or sport == "strength":
                strength_count += 1
            elif "stretching" in workout_type or sport == "stretching":
                stretching_count += 1
        
        # Parse strength_freq (e.g., "2-3x/week" -> 2, "1x/week" -> 1)
        required_strength = 0
        if include_strength and strength_freq != 'skip':
            if "2-3" in strength_freq:
                required_strength = 2  # Minimum
            elif "1-2" in strength_freq:
                required_strength = 1  # Minimum
            elif "1x" in strength_freq or "1 x" in strength_freq:
                required_strength = 1
            elif "2x" in strength_freq or "2 x" in strength_freq:
                required_strength = 2
            elif "3x" in strength_freq or "3 x" in strength_freq:
                required_strength = 3
        
        required_stretching = stretching_freq if include_stretching else 0
        
        missing_strength = max(0, required_strength - strength_count)
        missing_stretching = max(0, required_stretching - stretching_count)
        
        return {
            "missing_strength": missing_strength,
            "missing_stretching": missing_stretching,
            "has_missing": missing_strength > 0 or missing_stretching > 0,
            "strength_count": strength_count,
            "stretching_count": stretching_count,
            "required_strength": required_strength,
            "required_stretching": required_stretching,
        }
    
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

