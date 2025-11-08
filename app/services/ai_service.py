import openai
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.orm import Session
from app.config import settings
from app.schemas.ai import AIRequest, AIResponse, WorkoutPlanGenerationRequest, WorkoutAnalysisRequest, WorkoutAnalysisResponse
from app.models.ai import AIResponseLog
import json
from datetime import datetime, timedelta
import math
import os
from loguru import logger


class PlanGenerationError(Exception):
    """Raised when an AI workout plan chunk cannot be parsed or assembled."""


class AIService:
    def __init__(self, db: Optional[Session] = None):
        self.db = db
        openai.api_key = settings.openai_api_key
        self.client = openai.OpenAI(api_key=settings.openai_api_key)
        self.mock_mode = settings.mock_llm
    
    def generate_response(self, request: AIRequest) -> AIResponse:
        """Generate AI response using OpenAI API"""
        logger.info(f"[AI] Starting OpenAI API call - model: {settings.openai_model}, max_tokens: {request.max_tokens or settings.openai_max_tokens}, temperature: {request.temperature or 0.7}")
        logger.debug(f"[AI] Request prompt length: {len(request.prompt)} characters")
        logger.debug(f"[AI] Request prompt preview: {request.prompt[:200]}...")
        
        try:
            # Log request details (without full prompt to avoid log spam)
            request_summary = {
                "model": settings.openai_model,
                "max_tokens": request.max_tokens or settings.openai_max_tokens,
                "temperature": request.temperature or 0.7,
                "prompt_length": len(request.prompt),
                "has_context": request.context is not None
            }
            logger.debug(f"[AI] OpenAI request details: {json.dumps(request_summary, indent=2)}")
            
            response = self.client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": "You are a professional sports coach and training expert specialized in running, triathlon, cycling, swimming, and trail. You create detailed, scientifically based training plans tailored to athlete level, goals, and time availability. When personal data is unavailable, provide generic yet effective plans. Always structure plans with clear workout types, intensities, progressions, rest days, and phases. Respect privacy preferences and adapt your responses accordingly."},
                    {"role": "user", "content": request.prompt}
                ],
                max_tokens=request.max_tokens or settings.openai_max_tokens,
                temperature=request.temperature or 0.7
            )
            
            # Log response details
            response_content = response.choices[0].message.content
            usage_info = response.usage.dict() if response.usage else None
            
            logger.info(f"[AI] OpenAI API call successful - model: {response.model}, response length: {len(response_content)} characters")
            logger.debug(f"[AI] Response preview: {response_content[:200]}...")
            if usage_info:
                logger.info(f"[AI] Token usage: {json.dumps(usage_info, indent=2)}")
            
            ai_response = AIResponse(
                response=response_content,
                usage=usage_info,
                model=response.model,
                created_at=datetime.utcnow().isoformat()
            )
            
            logger.debug(f"[AI] AIResponse created successfully")
            return ai_response
            
        except Exception as e:
            logger.error(f"[AI] OpenAI API call failed: {str(e)}")
            logger.exception(f"[AI] Full exception traceback:")
            raise Exception(f"AI service error: {str(e)}")
    
    def generate_workout_plan(
        self,
        request: WorkoutPlanGenerationRequest,
        *,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Generate a personalized workout plan using AI"""
        logger.info(f"[WORKOUT_PLAN] Starting workout plan generation - sport: {request.sport_type}, level: {request.level}, goal: {request.goal}")
        logger.debug(f"[WORKOUT_PLAN] Request details: sport_type={request.sport_type}, level={request.level}, duration_weeks={request.duration_weeks}, weekly_hours={request.weekly_hours}, has_user_profile={request.user_profile is not None}, has_preferences={request.preferences is not None}, start_date={request.start_date}, target_date={request.target_date}")

        request_data = {
            "sport_type": request.sport_type,
            "level": request.level,
            "goal": request.goal,
            "duration_weeks": request.duration_weeks,
            "start_date": request.start_date,
            "target_date": request.target_date,
            "weekly_hours": request.weekly_hours,
            "user_profile": request.user_profile,
            "preferences": request.preferences
        }

        try:
            total_weeks = self._resolve_plan_duration(request)
        except ValueError as exc:
            logger.error(f"[WORKOUT_PLAN] Unable to determine plan duration: {exc}")
            raise

        # Update request object/state with resolved duration for downstream usage
        request.duration_weeks = total_weeks
        request_data["resolved_duration_weeks"] = total_weeks

        logger.info(f"[WORKOUT_PLAN] Resolved plan duration: {total_weeks} weeks")
        logger.info(f"[WORKOUT_PLAN] Full request data: {json.dumps(request_data, indent=2, default=str)}")

        if self.mock_mode:
            logger.info(f"[WORKOUT_PLAN] Using MOCK mode for plan generation")
            prompt = self._build_workout_plan_prompt(
                request,
                duration_weeks=total_weeks,
                week_start=1,
                week_end=total_weeks,
                previous_weeks_summary=None,
            )
            logger.info(f"[WORKOUT_PLAN][MOCK] Building same prompt as real LLM to validate data flow")
            logger.debug(f"[WORKOUT_PLAN][MOCK] Prompt that would be sent to LLM: {prompt[:1000]}...")

            ai_request = AIRequest(
                prompt=prompt,
                context=request.user_profile,
                max_tokens=2000,
                temperature=0.7
            )
            logger.info(f"[WORKOUT_PLAN][MOCK] AIRequest created - prompt_length: {len(ai_request.prompt)}, has_context: {ai_request.context is not None}, max_tokens: {ai_request.max_tokens}")

            result = self._generate_mock_workout_plan(request, prompt, ai_request)
            result["duration_weeks"] = total_weeks
            logger.info(f"[WORKOUT_PLAN][MOCK] Mock plan generated successfully - title: {result.get('title', 'N/A')}")
            logger.debug(f"[WORKOUT_PLAN][MOCK] Mock plan keys: {list(result.keys())}")
            return result

        raw_chunks: List[Dict[str, Any]] = []
        parse_success = False
        error_message: Optional[str] = None

        try:
            plan_metadata, combined_weeks, raw_chunks = self._generate_plan_batches(
                request=request,
                total_weeks=total_weeks,
                user_id=user_id,
                base_request_payload=request_data,
            )

            plan_data = self._assemble_plan_data(
                request=request,
                total_weeks=total_weeks,
                plan_metadata=plan_metadata,
                weeks=combined_weeks,
            )

            logger.info(f"[WORKOUT_PLAN] Successfully assembled plan with {len(combined_weeks)} weeks across {len(raw_chunks)} chunk(s)")
            parse_success = True
        except PlanGenerationError as exc:
            error_message = str(exc)
            logger.warning(f"[WORKOUT_PLAN] {error_message} - falling back to text response")
            plan_data = self._build_fallback_plan(request, total_weeks, raw_chunks)
        finally:
            combined_prompt = self._combine_prompts(raw_chunks)
            combined_response = self._combine_raw_chunks(raw_chunks)

            self._log_ai_response(
                request_type="workout_plan",
                user_id=user_id,
                prompt=combined_prompt,
                request_payload={**request_data, "chunk_count": len(raw_chunks)},
                response_text=combined_response,
                model=(raw_chunks[-1]["model"] if raw_chunks else None),
                parse_success=parse_success,
                error_message=error_message,
            )

        return plan_data
    
    def _generate_plan_batches(
        self,
        *,
        request: WorkoutPlanGenerationRequest,
        total_weeks: int,
        user_id: Optional[int],
        base_request_payload: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Call the LLM in chunks and merge their responses."""
        week_ranges = self._build_week_ranges(total_weeks, chunk_size=4)
        logger.info(f"[WORKOUT_PLAN] Generating plan in {len(week_ranges)} chunk(s) of up to 4 weeks")

        combined_weeks: List[Dict[str, Any]] = []
        plan_metadata: Dict[str, Any] = {}
        raw_chunks: List[Dict[str, Any]] = []
        previous_summary: Optional[str] = None

        for index, (week_start, week_end) in enumerate(week_ranges, start=1):
            prompt = self._build_workout_plan_prompt(
                request,
                duration_weeks=total_weeks,
                week_start=week_start,
                week_end=week_end,
                previous_weeks_summary=previous_summary,
            )
            logger.debug(f"[WORKOUT_PLAN][CHUNK {index}] Prompt length: {len(prompt)} characters")
            logger.debug(f"[WORKOUT_PLAN][CHUNK {index}] Prompt preview: {prompt[:600]}...")

            ai_request = AIRequest(
                prompt=prompt,
                context=request.user_profile,
                max_tokens=2000,
                temperature=0.7,
            )

            response = self.generate_response(ai_request)
            response_text = response.response

            chunk_payload = {
                **base_request_payload,
                "chunk_index": index,
                "chunk_week_start": week_start,
                "chunk_week_end": week_end,
                "resolved_duration_weeks": total_weeks,
            }

            raw_chunks.append(
                {
                    "index": index,
                    "week_start": week_start,
                    "week_end": week_end,
                    "prompt": prompt,
                    "response": response_text,
                    "model": response.model,
                }
            )

            try:
                partial_plan = json.loads(response_text)
            except json.JSONDecodeError as exc:
                logger.warning(f"[WORKOUT_PLAN][CHUNK {index}] JSON parsing failed: {exc}")
                self._log_ai_response(
                    request_type=f"workout_plan_chunk_{index}",
                    user_id=user_id,
                    prompt=prompt,
                    request_payload=chunk_payload,
                    response_text=response_text,
                    model=response.model,
                    parse_success=False,
                    error_message=str(exc),
                )
                raise PlanGenerationError(
                    f"Failed to parse AI response for weeks {week_start}-{week_end}: {exc}"
                ) from exc

            weeks = partial_plan.get("weeks")
            if not isinstance(weeks, list) or len(weeks) == 0:
                error_detail = "AI chunk returned no weeks"
                logger.warning(f"[WORKOUT_PLAN][CHUNK {index}] {error_detail}")
                self._log_ai_response(
                    request_type=f"workout_plan_chunk_{index}",
                    user_id=user_id,
                    prompt=prompt,
                    request_payload=chunk_payload,
                    response_text=response_text,
                    model=response.model,
                    parse_success=False,
                    error_message=error_detail,
                )
                raise PlanGenerationError(
                    f"Failed to generate workouts for weeks {week_start}-{week_end}: no weeks returned"
                )

            combined_weeks.extend(weeks)
            plan_metadata = self._merge_plan_metadata(plan_metadata, partial_plan)
            previous_summary = self._summarize_weeks_for_context(combined_weeks)

            self._log_ai_response(
                request_type=f"workout_plan_chunk_{index}",
                user_id=user_id,
                prompt=prompt,
                request_payload=chunk_payload,
                response_text=response_text,
                model=response.model,
                parse_success=True,
                error_message=None,
            )

        return plan_metadata, combined_weeks, raw_chunks

    def _assemble_plan_data(
        self,
        *,
        request: WorkoutPlanGenerationRequest,
        total_weeks: int,
        plan_metadata: Dict[str, Any],
        weeks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Build the final plan payload combining metadata and weeks."""
        default_title = f"{request.sport_type.title()} Training Plan - {request.level.title()}"
        default_description = plan_metadata.get("summary") or ""

        plan_data: Dict[str, Any] = {
            "title": plan_metadata.get("title") or default_title,
            "description": plan_metadata.get("description") or default_description,
            "sport_type": plan_metadata.get("sport_type") or request.sport_type,
            "level": plan_metadata.get("level") or request.level,
            "goal": plan_metadata.get("goal") or request.goal,
            "duration_weeks": total_weeks,
            "weekly_hours": plan_metadata.get("weekly_hours", request.weekly_hours),
            "weeks": weeks,
        }

        if request.start_date:
            plan_data["start_date"] = request.start_date
        if request.target_date:
            plan_data["end_date"] = request.target_date

        for optional_key in ("phases", "plan_summary", "notes", "macrocycles"):
            if plan_metadata.get(optional_key) is not None:
                plan_data[optional_key] = plan_metadata.get(optional_key)

        return plan_data

    def _build_fallback_plan(
        self,
        request: WorkoutPlanGenerationRequest,
        total_weeks: int,
        raw_chunks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Fallback to a text-based plan when JSON parsing fails."""
        combined_text = "\n\n".join(
            chunk["response"] for chunk in raw_chunks if chunk.get("response")
        )
        if not combined_text:
            combined_text = "AI response could not be parsed."

        fallback_data = {
            "title": f"{request.sport_type.title()} Training Plan - {request.level.title()}",
            "description": combined_text,
            "sport_type": request.sport_type,
            "level": request.level,
            "goal": request.goal,
            "duration_weeks": total_weeks,
            "weekly_hours": request.weekly_hours if request.weekly_hours else None,
            "weeks": [],
        }

        if request.start_date:
            fallback_data["start_date"] = request.start_date
        if request.target_date:
            fallback_data["end_date"] = request.target_date

        return fallback_data

    def _combine_prompts(self, raw_chunks: List[Dict[str, Any]]) -> Optional[str]:
        if not raw_chunks:
            return None
        parts = []
        for chunk in raw_chunks:
            prompt = chunk.get("prompt")
            if not prompt:
                continue
            parts.append(
                f"CHUNK {chunk.get('index')} PROMPT (weeks {chunk.get('week_start')}-{chunk.get('week_end')}):\n{prompt}"
            )
        return "\n\n".join(parts) if parts else None

    def _combine_raw_chunks(self, raw_chunks: List[Dict[str, Any]]) -> Optional[str]:
        if not raw_chunks:
            return None
        parts = []
        for chunk in raw_chunks:
            response = chunk.get("response")
            if response is None:
                continue
            parts.append(
                f"CHUNK {chunk.get('index')} RESPONSE (weeks {chunk.get('week_start')}-{chunk.get('week_end')}):\n{response}"
            )
        return "\n\n".join(parts) if parts else None

    def _resolve_plan_duration(self, request: WorkoutPlanGenerationRequest) -> int:
        """Resolve the number of weeks using duration or start/end dates."""
        if request.duration_weeks:
            return request.duration_weeks

        if request.start_date and request.target_date:
            start = datetime.strptime(request.start_date, "%Y-%m-%d").date()
            end = datetime.strptime(request.target_date, "%Y-%m-%d").date()
            delta_days = (end - start).days
            if delta_days < 0:
                raise ValueError("target_date must be after start_date")
            total_weeks = max(1, math.ceil((delta_days + 1) / 7))
            return total_weeks

        raise ValueError("Provide either duration_weeks or both start_date and target_date")

    def _build_week_ranges(self, total_weeks: int, chunk_size: int) -> List[Tuple[int, int]]:
        return [
            (start, min(start + chunk_size - 1, total_weeks))
            for start in range(1, total_weeks + 1, chunk_size)
        ]

    def _summarize_weeks_for_context(self, weeks: List[Dict[str, Any]]) -> Optional[str]:
        if not weeks:
            return None
        summary_weeks = weeks[-2:] if len(weeks) >= 2 else weeks
        lines = []
        for week in summary_weeks:
            focus = week.get("focus", "N/A")
            workout_count = len(week.get("workouts", [])) if isinstance(week.get("workouts"), list) else 0
            lines.append(f"Week {week.get('week')}: focus={focus}, workouts={workout_count}")
        return "\n".join(lines)

    def _extract_plan_metadata(self, partial_plan: Dict[str, Any]) -> Dict[str, Any]:
        keys = [
            "title",
            "description",
            "sport_type",
            "level",
            "goal",
            "duration_weeks",
            "weekly_hours",
            "phases",
            "plan_summary",
            "notes",
            "macrocycles",
            "start_date",
            "end_date",
        ]
        return {key: partial_plan.get(key) for key in keys if partial_plan.get(key) is not None}

    def _merge_plan_metadata(self, base: Dict[str, Any], partial_plan: Dict[str, Any]) -> Dict[str, Any]:
        if not base:
            return self._extract_plan_metadata(partial_plan)

        merged = dict(base)
        partial_metadata = self._extract_plan_metadata(partial_plan)
        for key, value in partial_metadata.items():
            if key not in merged or merged[key] is None:
                merged[key] = value
        return merged

    def analyze_workout(self, request: WorkoutAnalysisRequest) -> WorkoutAnalysisResponse:
        """Analyze workout performance using AI"""
        logger.info(f"[WORKOUT_ANALYSIS] Starting workout analysis - analysis_type: {request.analysis_type}")
        logger.debug(f"[WORKOUT_ANALYSIS] Request details: analysis_type={request.analysis_type}, has_workout_data={request.workout_data is not None}, has_performance_metrics={request.performance_metrics is not None}")
        
        prompt = self._build_workout_analysis_prompt(request)
        logger.debug(f"[WORKOUT_ANALYSIS] Prompt built - length: {len(prompt)} characters")
        
        ai_request = AIRequest(
            prompt=prompt,
            context=request.workout_data,
            max_tokens=1000,
            temperature=0.5
        )
        
        response = self.generate_response(ai_request)
        
        self._log_ai_response(
            request_type="workout_analysis",
            user_id=None,
            prompt=prompt,
            request_payload={
                "analysis_type": request.analysis_type,
                "has_workout_data": request.workout_data is not None,
                "has_performance_metrics": request.performance_metrics is not None,
            },
            response_text=response.response,
            model=response.model,
            parse_success=True,
            error_message=None,
        )

        # Parse AI response to extract structured data
        analysis_data = self._parse_workout_analysis(response.response)
        logger.info(f"[WORKOUT_ANALYSIS] Analysis parsed successfully - has_score={analysis_data.get('score') is not None}, recommendations_count={len(analysis_data.get('recommendations', []))}")
        
        result = WorkoutAnalysisResponse(
            analysis=analysis_data.get("analysis", response.response),
            recommendations=analysis_data.get("recommendations", []),
            score=analysis_data.get("score"),
            areas_for_improvement=analysis_data.get("areas_for_improvement", []),
            next_steps=analysis_data.get("next_steps", [])
        )
        
        logger.info(f"[WORKOUT_ANALYSIS] Workout analysis completed successfully")
        return result

    def _log_ai_response(
        self,
        *,
        request_type: str,
        user_id: Optional[int],
        prompt: Optional[str],
        request_payload: Optional[Dict[str, Any]],
        response_text: Optional[str],
        model: Optional[str],
        parse_success: bool,
        error_message: Optional[str],
    ) -> None:
        if not self.db:
            return

        try:
            log_entry = AIResponseLog(
                user_id=user_id,
                request_type=request_type,
                model=model,
                prompt=prompt,
                request_payload=request_payload,
                response=response_text,
                parse_success=parse_success,
                error_message=error_message,
            )
            self.db.add(log_entry)
            self.db.commit()
            logger.debug(
                f"[AI] Logged response for request_type={request_type}, user_id={user_id}, parse_success={parse_success}"
            )
        except Exception as exc:
            self.db.rollback()
            logger.warning(
                f"[AI] Failed to log AI response for request_type={request_type}: {exc}"
            )
    
    def _build_workout_plan_prompt(
        self,
        request: WorkoutPlanGenerationRequest,
        *,
        duration_weeks: int,
        week_start: Optional[int] = None,
        week_end: Optional[int] = None,
        previous_weeks_summary: Optional[str] = None,
    ) -> str:
        """Build prompt for workout plan generation"""
        weekly_hours_note = f"Weekly training hours: {request.weekly_hours}" if request.weekly_hours else "Weekly training hours: Not specified - YOU decide the optimal training volume based on the athlete's level and goals"
        
        prompt = f"""
        Create a detailed {request.sport_type} training plan for a {request.level} athlete.
        
        Goal: {request.goal}
        Duration: {duration_weeks} weeks
        {weekly_hours_note}
        
        Please provide a structured training plan that includes:
        1. Weekly breakdown with specific workouts
        2. Workout types and intensities (use heart rate zones, power zones, or pace zones as appropriate)
        3. Progression over the {duration_weeks} weeks
        4. Recovery and rest days
        5. Key training phases
        
        """
        if week_start is not None and week_end is not None:
            prompt += f"""
        === GENERATION SCOPE ===
        - Generate ONLY weeks {week_start} through {week_end} (inclusive) of the full {duration_weeks}-week plan.
        - Weeks must be numbered using the absolute plan numbering (do not restart from 1 in each chunk).
        - Ensure continuity with the preceding weeks.
        """
            if previous_weeks_summary:
                prompt += f"""
        === PREVIOUS WEEKS SUMMARY (for continuity) ===
        {previous_weeks_summary}
        """
        
        # Gestione user_profile - può contenere: age, weight, height, experience_years, 
        # threshold_hr, ftp, max_hr, resting_hr, hr_zones, power_zones, pace_zones, 
        # physical_notes (contains any physical notes, injuries, limitations, health conditions, etc.)
        # E metriche di performance: hr_max, hr_rest, threshold_hr, ftp, threshold_pace, vo2max, etc.
        if request.user_profile:
            prompt += "\n\n=== USER PROFILE ==="
            prompt += f"\n{json.dumps(request.user_profile, indent=2)}"
            prompt += "\n\nUse this information to personalize the training plan:"
            prompt += "\n- Adjust intensities based on provided thresholds (HR zones, power zones, pace zones)"
            prompt += "\n- Consider age and experience level for recovery and progression"
            prompt += "\n- Use weight and physical characteristics to adjust volume and intensity recommendations"
            prompt += "\n- Incorporate any existing fitness metrics (threshold values, max values, etc.) into workout prescriptions"
            
            # Gestione PERFORMANCE METRICS se presenti nel user_profile
            has_performance_metrics = any(key in request.user_profile for key in [
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
                if request.user_profile.get('hr_zones') or request.user_profile.get('threshold_hr') or request.user_profile.get('hr_max'):
                    hr_info = []
                    if request.user_profile.get('hr_max'):
                        hr_info.append(f"HR Max: {request.user_profile.get('hr_max')} bpm")
                    if request.user_profile.get('hr_rest'):
                        hr_info.append(f"HR Rest: {request.user_profile.get('hr_rest')} bpm")
                    if request.user_profile.get('threshold_hr'):
                        hr_info.append(f"Threshold: {request.user_profile.get('threshold_hr')} bpm")
                    if request.user_profile.get('hr_zones'):
                        zones = request.user_profile.get('hr_zones')
                        if isinstance(zones, dict):
                            hr_info.append(f"Zones: {', '.join([f'{k.upper()}={v}' for k, v in zones.items()])}")
                    prompt += f"\nHR: {', '.join(hr_info)}"
                
                # Pace Metrics (compact)
                if request.user_profile.get('pace_zones') or request.user_profile.get('threshold_pace'):
                    pace_info = []
                    if request.user_profile.get('threshold_pace'):
                        pace_info.append(f"Threshold: {request.user_profile.get('threshold_pace')} min/km")
                    if request.user_profile.get('critical_speed'):
                        pace_info.append(f"Critical Speed: {request.user_profile.get('critical_speed')} km/h")
                    if request.user_profile.get('pace_zones'):
                        zones = request.user_profile.get('pace_zones')
                        if isinstance(zones, dict):
                            pace_info.append(f"Zones: {', '.join([f'{k.upper()}={v}' for k, v in zones.items()])}")
                    prompt += f"\nPace: {', '.join(pace_info)}"
                
                # Power Metrics (compact)
                if request.user_profile.get('power_zones') or request.user_profile.get('ftp'):
                    power_info = []
                    if request.user_profile.get('ftp'):
                        power_info.append(f"FTP: {request.user_profile.get('ftp')}W")
                    if request.user_profile.get('wkg'):
                        power_info.append(f"W/kg: {request.user_profile.get('wkg')}")
                    if request.user_profile.get('power_zones'):
                        zones = request.user_profile.get('power_zones')
                        if isinstance(zones, dict):
                            power_info.append(f"Zones: {', '.join([f'{k.upper()}={v}W' for k, v in zones.items()])}")
                    prompt += f"\nPower: {', '.join(power_info)}"
                
                # Advanced Metrics
                if request.user_profile.get('vo2max'):
                    prompt += f"\nVO2max: {request.user_profile.get('vo2max')} ml/kg/min"
                
                # Preferred zone type
                preferred_zone_type = request.user_profile.get('preferred_zone_type', 'hr')
                prompt += f"\nPreferred zone type: {preferred_zone_type.upper()} (prioritize this in prescriptions)"
                
                prompt += "\n\nCRITICAL: Use exact zone values from above. For Z4 use threshold values, for Z5 use 105-120% of threshold."
            
            # Gestione specifica per note fisiche e problemi - tutto dentro physical_notes
            if request.user_profile.get("physical_notes"):
                prompt += "\n\n⚠️ IMPORTANT - PHYSICAL NOTES/LIMITATIONS:"
                prompt += f"\n{request.user_profile.get('physical_notes')}"
                prompt += "\n- CRITICAL: Adapt workouts to accommodate any physical limitations, injuries, or health conditions mentioned above"
                prompt += "\n- Modify or replace exercises that may aggravate existing conditions or injuries"
                prompt += "\n- Include appropriate modifications, alternatives, or recovery considerations"
                prompt += "\n- Prioritize safety and injury prevention over intensity"
                prompt += "\n- If unclear about modifications, suggest consulting with a healthcare provider"
                prompt += "\n- Adjust training volume, intensity, and exercise selection based on any physical constraints described"
        else:
            prompt += "\n\n=== USER PROFILE ==="
            prompt += "\nNo specific user profile provided - create a generic plan suitable for the specified level."
            prompt += "\nUse standard zone definitions and progressions appropriate for the level."
        
        # Gestione preferences
        if request.preferences:
            prompt += "\n\n=== USER PREFERENCES (INDICATIVE ONLY) ==="
            prompt += f"\n{json.dumps(request.preferences, indent=2)}"
            prompt += "\n\nIMPORTANT: These preferences are INDICATIVE ONLY, not strict constraints:"
            prompt += "\n- Use preferred training days and schedule constraints as a GUIDELINE, but you have full autonomy to optimize the plan"
            prompt += "\n- Consider intensity preferences, but prioritize optimal training structure"
            prompt += "\n- Equipment availability is a factor, but adapt the plan for best results"
            prompt += "\n- YOU decide the optimal number of workouts per week and session durations based on training science"
            prompt += "\n- Balance different disciplines optimally - don't limit yourself to user preferences"
            
            # Se ci sono giorni disponibili o durata minima, trattali come indicazioni
            if request.preferences.get("available_days_per_week"):
                prompt += f"\n- User indicated ~{request.preferences.get('available_days_per_week')} days/week available - use as REFERENCE, not constraint"
            if request.preferences.get("min_session_duration_minutes"):
                prompt += f"\n- User indicated minimum session duration of ~{request.preferences.get('min_session_duration_minutes')} minutes - use as REFERENCE, but optimize for best training outcomes"
        
        prompt += """
        
        Format the response as a JSON object with the following structure:
        {
            "title": "Plan title",
            "description": "Brief description",
            "weeks": [
                {
                    "week": 1,
                    "focus": "Base building",
                    "workouts": [
                        {
                            "day": "Monday",
                            "type": "Endurance",
                            "duration_minutes": 60,
                            "intensity": "Z2",
                            "target_hr": "140-150 bpm (or power/pace if zones provided)",
                            "rpe_target": 6,
                            "description": "Easy aerobic run",
                            "modifications": "Optional: modifications if physical limitations exist"
                        }
                    ]
                }
            ]
        }
        
        Important:
        - If HR zones are provided in user_profile, use specific HR ranges in target_hr field
        - If power zones are provided, use power targets (e.g., "200-250W")
        - If pace zones are provided, use pace targets (e.g., "5:00-5:30 min/km")
        - Adjust workout prescriptions based on user's physical characteristics and experience
        - Ensure progression is appropriate for the user's level and available training time
        - ALWAYS prioritize safety: if physical_notes are present, carefully read and adapt workouts accordingly
        - Include modifications or alternatives in the description or modifications field when necessary to accommodate physical constraints
        """

        if week_start is not None and week_end is not None:
            prompt += f"""
        - ONLY include weeks {week_start}-{week_end} in the weeks array.
        - Summaries, phases, and other metadata should remain consistent with a {duration_weeks}-week plan.
        """
        
        return prompt
    
    def _build_workout_analysis_prompt(self, request: WorkoutAnalysisRequest) -> str:
        """Build prompt for workout analysis"""
        prompt = f"""
        Analyze this {request.analysis_type} workout data and provide insights:
        
        Workout Data:
        {json.dumps(request.workout_data, indent=2)}
        """
        
        if request.performance_metrics:
            prompt += f"\n\nPerformance Metrics:\n{json.dumps(request.performance_metrics, indent=2)}"
        
        prompt += f"""
        
        Please provide:
        1. Analysis of the workout performance
        2. Specific recommendations for improvement
        3. A performance score (1-10)
        4. Areas that need improvement
        5. Next steps for training
        
        Format as JSON:
        {{
            "analysis": "Detailed analysis text",
            "recommendations": ["rec1", "rec2"],
            "score": 8.5,
            "areas_for_improvement": ["area1", "area2"],
            "next_steps": ["step1", "step2"]
        }}
        """
        
        return prompt
    
    def _parse_workout_analysis(self, response: str) -> Dict[str, Any]:
        """Parse AI response for workout analysis"""
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Fallback parsing for non-JSON responses
            return {
                "analysis": response,
                "recommendations": [],
                "score": None,
                "areas_for_improvement": [],
                "next_steps": []
            }
    
    def _generate_mock_workout_plan(self, request: WorkoutPlanGenerationRequest, prompt: str, ai_request: AIRequest) -> Dict[str, Any]:
        """Generate mock workout plan for testing - uses same data as real LLM"""
        logger.info(f"[WORKOUT_PLAN][MOCK] Generating mock workout plan")
        logger.debug(f"[WORKOUT_PLAN][MOCK] Received prompt length: {len(prompt)}")
        logger.debug(f"[WORKOUT_PLAN][MOCK] AIRequest details: prompt_length={len(ai_request.prompt)}, context_type={type(ai_request.context).__name__ if ai_request.context else None}")
        
        # Log all data that would be sent to LLM
        mock_request_summary = {
            "sport_type": request.sport_type,
            "level": request.level,
            "goal": request.goal,
            "duration_weeks": request.duration_weeks,
            "weekly_hours": request.weekly_hours,
            "user_profile_keys": list(request.user_profile.keys()) if request.user_profile else None,
            "user_profile": request.user_profile,
            "preferences": request.preferences,
            "prompt_length": len(prompt),
            "ai_request_context": ai_request.context
        }
        logger.info(f"[WORKOUT_PLAN][MOCK] Full request data that would be sent to LLM: {json.dumps(mock_request_summary, indent=2, default=str)}")
        
        if request.sport_type.lower() == "running":
            result = self._generate_mock_running_plan(request, prompt, ai_request)
        elif request.sport_type.lower() == "triathlon":
            result = self._generate_mock_triathlon_plan(request, prompt, ai_request)
        else:
            result = self._generate_mock_generic_plan(request, prompt, ai_request)
        
        logger.debug(f"[WORKOUT_PLAN][MOCK] Mock plan generated - result keys: {list(result.keys())}")
        return result
    
    def _generate_mock_running_plan(self, request: WorkoutPlanGenerationRequest, prompt: str, ai_request: AIRequest) -> Dict[str, Any]:
        """Generate mock running plan (2 months to Dec 24, 2025) - uses same data as real LLM"""
        logger.info(f"[WORKOUT_PLAN][MOCK][RUNNING] Generating mock running plan")
        logger.debug(f"[WORKOUT_PLAN][MOCK][RUNNING] Prompt received: {len(prompt)} chars")
        logger.debug(f"[WORKOUT_PLAN][MOCK][RUNNING] User profile: {json.dumps(request.user_profile, indent=2, default=str) if request.user_profile else None}")
        logger.debug(f"[WORKOUT_PLAN][MOCK][RUNNING] Preferences: {json.dumps(request.preferences, indent=2, default=str) if request.preferences else None}")
        
        # Use default weekly hours if not specified (based on level)
        default_hours = {
            "beginner": 4.0,
            "intermediate": 6.0,
            "advanced": 8.0
        }
        weekly_hours = request.weekly_hours or default_hours.get(request.level.lower(), 6.0)
        logger.debug(f"[WORKOUT_PLAN][MOCK][RUNNING] Using weekly_hours: {weekly_hours} (from request: {request.weekly_hours})")
        
        weeks = []
        start_date = datetime(2025, 10, 25)
        
        for week_num in range(1, 9):  # 8 weeks = 2 months
            week_start = start_date + timedelta(weeks=week_num-1)
            week_end = week_start + timedelta(days=6)
            
            week_data = {
                "week": week_num,
                "focus": self._get_running_focus(week_num),
                "total_hours": weekly_hours,
                "workouts": self._generate_running_workouts(week_num, weekly_hours),
                "week_start": week_start.strftime("%Y-%m-%d"),
                "week_end": week_end.strftime("%Y-%m-%d")
            }
            weeks.append(week_data)
        
        return {
            "title": f"Running Training Plan - {request.goal}",
            "description": f"8-week running plan to achieve {request.goal} by December 24, 2025",
            "sport_type": "running",
            "level": request.level,
            "goal": request.goal,
            "duration_weeks": 8,
            "weekly_hours": weekly_hours,
            "start_date": "2025-10-25",
            "end_date": "2025-12-24",
            "weeks": weeks
        }
    
    def _generate_mock_triathlon_plan(self, request: WorkoutPlanGenerationRequest, prompt: str, ai_request: AIRequest) -> Dict[str, Any]:
        """Generate mock triathlon plan (2 months to Dec 24, 2025) - uses same data as real LLM"""
        logger.info(f"[WORKOUT_PLAN][MOCK][TRIATHLON] Generating mock triathlon plan")
        logger.debug(f"[WORKOUT_PLAN][MOCK][TRIATHLON] Prompt received: {len(prompt)} chars")
        logger.debug(f"[WORKOUT_PLAN][MOCK][TRIATHLON] User profile: {json.dumps(request.user_profile, indent=2, default=str) if request.user_profile else None}")
        logger.debug(f"[WORKOUT_PLAN][MOCK][TRIATHLON] Preferences: {json.dumps(request.preferences, indent=2, default=str) if request.preferences else None}")
        
        # Use default weekly hours if not specified (based on level)
        default_hours = {
            "beginner": 6.0,
            "intermediate": 10.0,
            "advanced": 14.0
        }
        weekly_hours = request.weekly_hours or default_hours.get(request.level.lower(), 10.0)
        logger.debug(f"[WORKOUT_PLAN][MOCK][TRIATHLON] Using weekly_hours: {weekly_hours} (from request: {request.weekly_hours})")
        
        weeks = []
        start_date = datetime(2025, 10, 25)
        
        for week_num in range(1, 9):  # 8 weeks = 2 months
            week_start = start_date + timedelta(weeks=week_num-1)
            week_end = week_start + timedelta(days=6)
            
            week_data = {
                "week": week_num,
                "focus": self._get_triathlon_focus(week_num),
                "total_hours": weekly_hours,
                "workouts": self._generate_triathlon_workouts(week_num, weekly_hours),
                "week_start": week_start.strftime("%Y-%m-%d"),
                "week_end": week_end.strftime("%Y-%m-%d")
            }
            weeks.append(week_data)
        
        return {
            "title": f"Triathlon Training Plan - {request.goal}",
            "description": f"8-week triathlon plan to achieve {request.goal} by December 24, 2025",
            "sport_type": "triathlon",
            "level": request.level,
            "goal": request.goal,
            "duration_weeks": 8,
            "weekly_hours": weekly_hours,
            "start_date": "2025-10-25",
            "end_date": "2025-12-24",
            "weeks": weeks
        }
    
    def _generate_mock_generic_plan(self, request: WorkoutPlanGenerationRequest, prompt: str, ai_request: AIRequest) -> Dict[str, Any]:
        """Generate generic mock plan - uses same data as real LLM"""
        logger.info(f"[WORKOUT_PLAN][MOCK][GENERIC] Generating mock generic plan")
        logger.debug(f"[WORKOUT_PLAN][MOCK][GENERIC] Prompt received: {len(prompt)} chars")
        logger.debug(f"[WORKOUT_PLAN][MOCK][GENERIC] User profile: {json.dumps(request.user_profile, indent=2, default=str) if request.user_profile else None}")
        logger.debug(f"[WORKOUT_PLAN][MOCK][GENERIC] Preferences: {json.dumps(request.preferences, indent=2, default=str) if request.preferences else None}")
        
        # Use default weekly hours if not specified
        default_hours = {
            "beginner": 4.0,
            "intermediate": 6.0,
            "advanced": 8.0
        }
        weekly_hours = request.weekly_hours or default_hours.get(request.level.lower(), 6.0)
        logger.debug(f"[WORKOUT_PLAN][MOCK][GENERIC] Using weekly_hours: {weekly_hours} (from request: {request.weekly_hours})")
        
        return {
            "title": f"{request.sport_type.title()} Training Plan - {request.goal}",
            "description": f"Mock training plan for {request.sport_type}",
            "sport_type": request.sport_type,
            "level": request.level,
            "goal": request.goal,
            "duration_weeks": request.duration_weeks,
            "weekly_hours": weekly_hours
        }
    
    def _get_running_focus(self, week_num: int) -> str:
        """Get running focus for specific week"""
        focuses = [
            "Base Building", "Base Building", "Endurance", "Endurance",
            "Speed Work", "Speed Work", "Taper", "Race Week"
        ]
        return focuses[min(week_num-1, len(focuses)-1)]
    
    def _get_triathlon_focus(self, week_num: int) -> str:
        """Get triathlon focus for specific week"""
        focuses = [
            "Base Building", "Base Building", "Brick Training", "Brick Training",
            "Speed Work", "Speed Work", "Taper", "Race Week"
        ]
        return focuses[min(week_num-1, len(focuses)-1)]
    
    def _generate_running_workouts(self, week_num: int, weekly_hours: float) -> list:
        """Generate running workouts for a week"""
        workouts = []
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        # Base workouts
        base_workouts = [
            {"type": "Easy Run", "duration_minutes": 45, "intensity": "Z2", "description": "Easy aerobic run"},
            {"type": "Tempo Run", "duration_minutes": 30, "intensity": "Z3", "description": "Comfortably hard pace"},
            {"type": "Long Run", "duration_minutes": 90, "intensity": "Z2", "description": "Long endurance run"},
            {"type": "Recovery Run", "duration_minutes": 30, "intensity": "Z1", "description": "Easy recovery run"},
            {"type": "Interval Training", "duration_minutes": 60, "intensity": "Z4", "description": "High intensity intervals"}
        ]
        
        # Select workouts based on week and hours
        if week_num <= 2:
            selected = [0, 1, 2, 3]  # Base building
        elif week_num <= 4:
            selected = [0, 1, 2, 4]  # Endurance + speed
        elif week_num <= 6:
            selected = [0, 1, 2, 4]  # Speed work
        else:
            selected = [0, 2, 3]  # Taper
        
        for i, workout_idx in enumerate(selected[:4]):  # Max 4 workouts per week
            workout = base_workouts[workout_idx].copy()
            workout["day"] = days[i]
            workout["rpe_target"] = 6 + (workout_idx % 3)
            workouts.append(workout)
        
        return workouts
    
    def _generate_triathlon_workouts(self, week_num: int, weekly_hours: float) -> list:
        """Generate triathlon workouts for a week"""
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
        if week_num <= 2:
            selected = [0, 1, 2, 6]  # Base building
        elif week_num <= 4:
            selected = [0, 1, 3, 2]  # Brick training
        elif week_num <= 6:
            selected = [4, 5, 3, 2]  # Speed work
        else:
            selected = [0, 1, 2, 6]  # Taper
        
        for i, workout_idx in enumerate(selected[:4]):  # Max 4 workouts per week
            workout = tri_workouts[workout_idx].copy()
            workout["day"] = days[i]
            workout["rpe_target"] = 6 + (workout_idx % 3)
            workouts.append(workout)
        
        return workouts
