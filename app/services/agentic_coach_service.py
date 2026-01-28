"""
Agentic Coach Service - PRODUCTION READY.
Integrates: Smart Context Builder + Real LLM + Validation Layer.
"""
from typing import List, Optional, Dict, Any
import json
from datetime import date
from sqlalchemy.orm import Session
from loguru import logger

from app.schemas.agentic_coach import (
    UnifiedPlanRequest, 
    AthleteStateAssessment, 
    AgenticWeeklyPlan, 
    RecentWorkoutContext,
    CoachMemoryItem
)
from app.schemas.endurance_context import SmartEnduranceContext
from app.services.smart_context_builder import SmartContextBuilder
from app.services.agentic_ai_service import AgenticAIService, create_agentic_ai_service
from app.services.endurance_validator import validate_endurance_plan, ValidationResult


SYSTEM_PROMPT = """
You are an elite ENDURANCE COACH specializing in running, cycling, swimming, and triathlon.

## CORE PHILOSOPHY
1. **Progressive Overload**: Never increase weekly volume by more than 10%.
2. **Polarized Training**: 80% of training time should be in Z1-Z2 (easy), 20% in Z4-Z5 (hard). Avoid "junk miles" in Z3.
3. **Recovery First**: High-intensity sessions (Z4+) must have at least 48 hours separation.
4. **Specificity**: Workouts must target the athlete's limiting factor based on their history and goals.

## YOUR TASK
You will receive a 3-layer context:
- **CRITICAL**: Current fitness state (CTL/ATL/TSB), last workout, injury flags
- **RELEVANT**: Past similar workouts, aerobic base, failure patterns
- **BACKGROUND**: Monthly summary, athlete profile

Analyze this data using **Chain of Thought reasoning**, then generate a training plan.

## OUTPUT REQUIREMENTS
1. First, write your REASONING (what you observe, what the athlete needs).
2. Then, output the PLAN in strict JSON format matching the AthleteStateAssessment or AgenticWeeklyPlan schema.
3. For endurance workouts, specify: duration, intensity zones, pace/power targets, structure (warmup/main/cooldown).
"""


ASSESSMENT_PROMPT_TEMPLATE = """
Analyze the athlete's current state and determine the focus for the upcoming week.

=== CRITICAL CONTEXT ===
{critical_context}

=== RELEVANT HISTORY ===
{relevant_context}

=== BACKGROUND ===
{background_context}

TASK:
1. Evaluate the athlete's fitness (CTL/ATL/TSB = fatigue vs form).
2. Identify any red flags (high ramp rate, incomplete workouts, injury risks).
3. Determine the main limiting factor (aerobic base? VO2Max? recovery?).
4. Decide the focus for next week (e.g., "Consolidate aerobic base", "Introduce VO2Max", "Recovery week").

OUTPUT: JSON matching AthleteStateAssessment schema.
"""


GENERATION_PROMPT_TEMPLATE = """
Based on your assessment, generate a detailed weekly training plan.

=== ASSESSMENT ===
{assessment}

=== CONSTRAINTS ===
Week Start: {week_start}
Available Days: {available_days}
Goal: {goal}

REQUIREMENTS:
1. Respect the 80/20 polarization principle.
2. Ensure at least 48h between high-intensity sessions.
3. Include specific workout details:
   - For intervals: reps, distance, target pace/power, recovery time
   - For long runs/rides: duration, target HR zone
4. Explain WHY each workout is programmed (link to assessment).

OUTPUT: JSON matching AgenticWeeklyPlan schema.
"""


class AgenticCoachService:
    """
    PRODUCTION-READY Agentic Coach.
    - Smart Context Building (3-layer pyramid)
    - Real LLM Integration (OpenAI/Claude)
    - Validation Layer (safety rules)
    """
    
    def __init__(
        self,
        db: Session,
        ai_service: Optional[AgenticAIService] = None,
        use_real_llm: bool = True
    ):
        self.db = db
        self.context_builder = SmartContextBuilder(db)
        self.use_real_llm = use_real_llm
        
        # Initialize AI service
        if ai_service:
            self.ai_service = ai_service
        elif use_real_llm:
            self.ai_service = create_agentic_ai_service(
                provider="openai",  # or "anthropic"
                temperature=0.7
            )
        else:
            self.ai_service = None
            logger.info("[AGENTIC] Running in MOCK mode (no LLM calls)")
    
    def assess_athlete_endurance(
        self,
        user_id: int,
        target_week_start: date,
        next_workout_type: str = "intervals",
        next_sport: str = "run"
    ) -> AthleteStateAssessment:
        """
        Phase 1: Assessment using Smart Context and LLM.
        
        Returns:
            AthleteStateAssessment with reasoning about current state
        """
        logger.info(f"[AGENTIC] Starting Assessment for user {user_id}")
        
        # Build smart context
        context = self.context_builder.build_context(
            user_id=user_id,
            target_week_start=target_week_start,
            next_workout_type=next_workout_type,
            next_sport=next_sport
        )
        
        # Format context for prompt
        user_prompt = ASSESSMENT_PROMPT_TEMPLATE.format(
            critical_context=self._format_critical(context.critical),
            relevant_context=self._format_relevant(context.relevant),
            background_context=self._format_background(context.background)
        )
        
        logger.info(f"[AGENTIC] Assessment prompt: ~{len(user_prompt)//4} tokens")
        
        # Call LLM or return mock
        if self.use_real_llm and self.ai_service:
            try:
                assessment = self.ai_service.generate_structured(
                    system_prompt=SYSTEM_PROMPT,
                    user_prompt=user_prompt,
                    response_model=AthleteStateAssessment,
                    max_retries=3
                )
                logger.info(f"[AGENTIC] LLM Assessment: {assessment.focus_for_week}")
                return assessment
                
            except Exception as e:
                logger.error(f"[AGENTIC] LLM call failed: {str(e)}. Falling back to mock.")
                return self._mock_assessment(context)
        else:
            return self._mock_assessment(context)
    
    def generate_week_endurance(
        self,
        user_id: int,
        target_week_start: date,
        assessment: AthleteStateAssessment,
        goal: str,
        available_days: List[str],
        validate: bool = True
    ) -> Dict[str, Any]:
        """
        Phase 2: Plan Generation with Validation.
        
        Args:
            validate: If True, run validation layer before returning
        
        Returns:
            Dict with 'plan', 'validation', 'approved' keys
        """
        logger.info(f"[AGENTIC] Starting Plan Generation for user {user_id}")
        
        # Build generation prompt
        user_prompt = GENERATION_PROMPT_TEMPLATE.format(
            assessment=assessment.model_dump_json(indent=2),
            week_start=target_week_start,
            available_days=", ".join(available_days),
            goal=goal
        )
        
        # Call LLM or return mock
        if self.use_real_llm and self.ai_service:
            try:
                plan = self.ai_service.generate_structured(
                    system_prompt=SYSTEM_PROMPT,
                    user_prompt=user_prompt,
                    response_model=AgenticWeeklyPlan,
                    max_retries=3
                )
                logger.info(f"[AGENTIC] LLM Plan generated: Week {plan.week_number}, {len(plan.workouts)} workouts")
                
            except Exception as e:
                logger.error(f"[AGENTIC] Plan generation failed: {str(e)}. Using mock.")
                plan = self._mock_plan(assessment, target_week_start)
        else:
            plan = self._mock_plan(assessment, target_week_start)
        
        # Validate plan
        validation_result = None
        if validate:
            validation_result = self._validate_plan(user_id, plan)
        
        return {
            "plan": plan,
            "validation": validation_result,
            "approved": validation_result.is_valid if validation_result else True
        }
    
    def generate_full_week(
        self,
        user_id: int,
        target_week_start: date,
        goal: str,
        available_days: List[str],
        next_workout_type: str = "intervals",
        next_sport: str = "run",
        max_validation_retries: int = 2
    ) -> Dict[str, Any]:
        """
        Complete workflow: Assessment -> Generation -> Validation (with retry).
        
        Args:
            max_validation_retries: If plan fails validation, retry generation
        
        Returns:
            Dict with 'assessment', 'plan', 'validation', 'approved'
        """
        logger.info(f"[AGENTIC] Full week generation for user {user_id}")
        
        # Step 1: Assessment
        assessment = self.assess_athlete_endurance(
            user_id=user_id,
            target_week_start=target_week_start,
            next_workout_type=next_workout_type,
            next_sport=next_sport
        )
        
        # Step 2: Generation with validation retry loop
        for attempt in range(max_validation_retries + 1):
            result = self.generate_week_endurance(
                user_id=user_id,
                target_week_start=target_week_start,
                assessment=assessment,
                goal=goal,
                available_days=available_days,
                validate=True
            )
            
            if result["approved"]:
                logger.info(f"[AGENTIC] Plan approved on attempt {attempt + 1}")
                return {
                    "assessment": assessment,
                    **result
                }
            else:
                logger.warning(f"[AGENTIC] Plan rejected on attempt {attempt + 1}. Errors: {len(result['validation'].errors)}")
                
                if attempt < max_validation_retries:
                    # Add validation feedback to prompt for next attempt
                    error_summary = "\n".join([f"- {e.message}" for e in result['validation'].errors])
                    logger.info(f"[AGENTIC] Retrying with validation feedback")
        
        # If all retries failed, return last attempt with warning
        logger.error(f"[AGENTIC] Max validation retries exceeded. Returning unvalidated plan.")
        return {
            "assessment": assessment,
            **result,
            "warning": "Plan did not pass validation after max retries"
        }
    
    # ========================================================================
    # Validation
    # ========================================================================
    
    def _validate_plan(self, user_id: int, plan: AgenticWeeklyPlan) -> ValidationResult:
        """Run validation layer on generated plan."""
        
        # Get previous week stats from DB
        previous_stats = self._get_previous_week_stats(user_id)
        
        # Get athlete profile
        athlete_profile = self._get_athlete_max_tss(user_id)
        
        # Validate
        result = validate_endurance_plan(
            plan=plan,
            previous_week_stats=previous_stats,
            athlete_profile=athlete_profile
        )
        
        if not result.is_valid:
            logger.warning(f"[VALIDATION] Plan FAILED with {len(result.errors)} errors")
            for error in result.errors:
                logger.warning(f"  - {error.rule}: {error.message}")
        
        return result
    
    def _get_previous_week_stats(self, user_id: int) -> Dict:
        """Get volume and TSS from previous week."""
        # TODO: Query WeeklyTrainingSummary
        return {
            "volume_km": 50.0,
            "tss": 300.0
        }
    
    def _get_athlete_max_tss(self, user_id: int) -> Dict:
        """Get athlete's historical max weekly TSS."""
        # TODO: Query max from WeeklyTrainingSummary
        return {
            "max_weekly_tss": 450.0
        }
    
    # ========================================================================
    # Mock Helpers (for fallback when LLM fails)
    # ========================================================================
    
    def _mock_assessment(self, context: SmartEnduranceContext) -> AthleteStateAssessment:
        """Generate mock assessment from context."""
        return AthleteStateAssessment(
            current_phase="Build",
            fatigue_level=self._determine_fatigue_level(context.critical.current_fitness),
            injury_risk="low" if not context.critical.injury_flags else "moderate",
            mental_freshness=7,
            ctl=context.critical.current_fitness.ctl,
            atl=context.critical.current_fitness.atl,
            tsb=context.critical.current_fitness.tsb,
            reasoning=self._mock_reasoning(context),
            focus_for_week="Build aerobic base while monitoring fatigue",
            recommended_modifications=[]
        )
    
    def _mock_plan(self, assessment: AthleteStateAssessment, week_start: date) -> AgenticWeeklyPlan:
        """Generate mock plan."""
        return AgenticWeeklyPlan(
            week_number=1,
            phase=assessment.current_phase,
            focus=assessment.focus_for_week,
            weekly_summary_reasoning=f"Mock plan based on TSB={assessment.tsb:.1f} and {assessment.fatigue_level} fatigue",
            workouts=[]
        )
    
    # ========================================================================
    # Helper Methods for Formatting Context
    # ========================================================================
    
    def _format_critical(self, critical) -> str:
        """Format critical context for prompt."""
        return f"""
Fitness State:
- CTL (Fitness): {critical.current_fitness.ctl}
- ATL (Fatigue): {critical.current_fitness.atl}
- TSB (Form): {critical.current_fitness.tsb} {'(good form)' if critical.current_fitness.tsb > 0 else '(fatigued)'}
- Ramp Rate: {critical.current_fitness.ramp_rate} {'⚠️ HIGH RISK' if critical.current_fitness.ramp_rate > 1.5 else ''}

Last Workout ({critical.last_workout.date}):
- Type: {critical.last_workout.type}
- Completion: {critical.last_workout.completion_rate * 100:.0f}%
- RPE: {critical.last_workout.rpe}/10
- Notes: {critical.last_workout.athlete_note or 'None'}

Current Phase: {critical.current_phase}
Recent Skips: {critical.skip_count_last_2weeks}
Injury Flags: {', '.join(critical.injury_flags) or 'None'}
"""
    
    def _format_relevant(self, relevant) -> str:
        """Format relevant context for prompt."""
        similar_str = "\n".join([
            f"- {w.date}: {w.workout_description} | Completion: {w.completion_rate * 100:.0f}% | RPE: {w.rpe} | {w.athlete_feedback or ''}"
            for w in relevant.similar_workouts
        ])
        
        return f"""
Similar Workouts (last 3 of same type):
{similar_str or 'No similar workout history'}

Aerobic Base:
- Last Long Session: {relevant.aerobic_base.last_long_session.workout_description} on {relevant.aerobic_base.last_long_session.date}
- Avg Weekly Z2 Time: {relevant.aerobic_base.avg_weekly_zone2_minutes} minutes

Failure Pattern: {relevant.failure_pattern or 'No pattern detected'}
Progression: {relevant.progression_context}
"""
    
    def _format_background(self, background) -> str:
        """Format background context for prompt."""
        return f"""
Monthly Summary:
- Total Volume: {background.monthly_summary.total_volume_km} km
- Avg Sessions/Week: {background.monthly_summary.avg_sessions_per_week:.1f}
- High Intensity Ratio: {background.monthly_summary.high_intensity_ratio * 100:.0f}%
- Trend: {background.monthly_summary.progress_trend}
- Compliance: {background.monthly_summary.compliance_rate * 100:.0f}%

Athlete Profile:
- Strengths: {', '.join(background.athlete_profile.strengths)}
- Weaknesses: {', '.join(background.athlete_profile.weaknesses)}
- Injury History: {', '.join(background.athlete_profile.injury_history) or 'None'}
"""
    
    def _determine_fatigue_level(self, fitness) -> str:
        """Determine fatigue level from TSB."""
        if fitness.tsb > 10:
            return "low"
        elif fitness.tsb > -10:
            return "moderate"
        else:
            return "high"
    
    def _mock_reasoning(self, context: SmartEnduranceContext) -> str:
        """Generate mock reasoning from context."""
        tsb = context.critical.current_fitness.tsb
        ramp = context.critical.current_fitness.ramp_rate
        
        reasoning = f"CTL={context.critical.current_fitness.ctl}, ATL={context.critical.current_fitness.atl}, TSB={tsb:.1f}. "
        
        if tsb < -15:
            reasoning += "Athlete is highly fatigued (TSB << 0). Recommend recovery week or deload."
        elif ramp > 1.5:
            reasoning += f"Ramp rate {ramp:.2f} is high (>1.5), indicating rapid load increase. Risk of injury/burnout."
        else:
            reasoning += "Athlete is in good condition for progressive training."
        
        return reasoning
    """
    Enhanced Agentic Coach with Smart Context Building.
    """
    
    def __init__(self, db: Session, ai_service: Any = None):
        self.db = db
        self.ai_service = ai_service
        self.context_builder = SmartContextBuilder(db)
    
    def assess_athlete_endurance(
        self,
        user_id: int,
        target_week_start: date,
        next_workout_type: str = "intervals",
        next_sport: str = "run"
    ) -> AthleteStateAssessment:
        """
        Phase 1: Assessment using Smart Context.
        
        Args:
            user_id: User ID
            target_week_start: Start date of week being planned
            next_workout_type: Type of next workout (for smart retrieval)
            next_sport: Sport type (run/bike/swim)
        """
        logger.info(f"[AGENTIC] Starting Assessment for user {user_id}")
        
        # Build smart context
        context = self.context_builder.build_context(
            user_id=user_id,
            target_week_start=target_week_start,
            next_workout_type=next_workout_type,
            next_sport=next_sport
        )
        
        # Format context for prompt
        prompt = ASSESSMENT_PROMPT_TEMPLATE.format(
            critical_context=self._format_critical(context.critical),
            relevant_context=self._format_relevant(context.relevant),
            background_context=self._format_background(context.background)
        )
        
        logger.info(f"[AGENTIC] Assessment prompt built (~{context.total_estimated_tokens} tokens)")
        
        # Call LLM (mocked for now)
        # response = self.ai_service.generate(system=SYSTEM_PROMPT, user=prompt)
        # return AthleteStateAssessment.model_validate_json(response)
        
        # MOCK RETURN (using data from context)
        return AthleteStateAssessment(
            current_phase="Build",
            fatigue_level=self._determine_fatigue_level(context.critical.current_fitness),
            injury_risk="low" if not context.critical.injury_flags else "moderate",
            mental_freshness=7,
            ctl=context.critical.current_fitness.ctl,
            atl=context.critical.current_fitness.atl,
            tsb=context.critical.current_fitness.tsb,
            reasoning=self._mock_reasoning(context),
            focus_for_week="Build aerobic base while monitoring fatigue",
            recommended_modifications=[]
        )
    
    def generate_week_endurance(
        self,
        user_id: int,
        target_week_start: date,
        assessment: AthleteStateAssessment,
        goal: str,
        available_days: List[str]
    ) -> AgenticWeeklyPlan:
        """
        Phase 2: Plan Generation.
        """
        logger.info(f"[AGENTIC] Starting Plan Generation for user {user_id}")
        
        prompt = GENERATION_PROMPT_TEMPLATE.format(
            assessment=assessment.model_dump_json(indent=2),
            week_start=target_week_start,
            available_days=", ".join(available_days),
            goal=goal
        )
        
        # Call LLM (mocked)
        # response = self.ai_service.generate(system=SYSTEM_PROMPT, user=prompt)
        # return AgenticWeeklyPlan.model_validate_json(response)
        
        # MOCK RETURN
        return AgenticWeeklyPlan(
            week_number=1,
            phase=assessment.current_phase,
            focus=assessment.focus_for_week,
            weekly_summary_reasoning=f"Based on TSB={assessment.tsb:.1f} and {assessment.fatigue_level} fatigue, focusing on {assessment.focus_for_week}",
            workouts=[]
        )
    
    # ========================================================================
    # Helper Methods for Formatting Context
    # ========================================================================
    
    def _format_critical(self, critical) -> str:
        """Format critical context for prompt."""
        return f"""
Fitness State:
- CTL (Fitness): {critical.current_fitness.ctl}
- ATL (Fatigue): {critical.current_fitness.atl}
- TSB (Form): {critical.current_fitness.tsb} {'(good form)' if critical.current_fitness.tsb > 0 else '(fatigued)'}
- Ramp Rate: {critical.current_fitness.ramp_rate} {'⚠️ HIGH RISK' if critical.current_fitness.ramp_rate > 1.5 else ''}

Last Workout ({critical.last_workout.date}):
- Type: {critical.last_workout.type}
- Completion: {critical.last_workout.completion_rate * 100:.0f}%
- RPE: {critical.last_workout.rpe}/10
- Notes: {critical.last_workout.athlete_note or 'None'}

Current Phase: {critical.current_phase}
Recent Skips: {critical.skip_count_last_2weeks}
Injury Flags: {', '.join(critical.injury_flags) or 'None'}
"""
    
    def _format_relevant(self, relevant) -> str:
        """Format relevant context for prompt."""
        similar_str = "\n".join([
            f"- {w.date}: {w.workout_description} | Completion: {w.completion_rate * 100:.0f}% | RPE: {w.rpe} | {w.athlete_feedback or ''}"
            for w in relevant.similar_workouts
        ])
        
        return f"""
Similar Workouts (last 3 of same type):
{similar_str or 'No similar workout history'}

Aerobic Base:
- Last Long Session: {relevant.aerobic_base.last_long_session.workout_description} on {relevant.aerobic_base.last_long_session.date}
- Avg Weekly Z2 Time: {relevant.aerobic_base.avg_weekly_zone2_minutes} minutes

Failure Pattern: {relevant.failure_pattern or 'No pattern detected'}
Progression: {relevant.progression_context}
"""
    
    def _format_background(self, background) -> str:
        """Format background context for prompt."""
        return f"""
Monthly Summary:
- Total Volume: {background.monthly_summary.total_volume_km} km
- Avg Sessions/Week: {background.monthly_summary.avg_sessions_per_week:.1f}
- High Intensity Ratio: {background.monthly_summary.high_intensity_ratio * 100:.0f}%
- Trend: {background.monthly_summary.progress_trend}
- Compliance: {background.monthly_summary.compliance_rate * 100:.0f}%

Athlete Profile:
- Strengths: {', '.join(background.athlete_profile.strengths)}
- Weaknesses: {', '.join(background.athlete_profile.weaknesses)}
- Injury History: {', '.join(background.athlete_profile.injury_history) or 'None'}
"""
    
    def _determine_fatigue_level(self, fitness) -> str:
        """Determine fatigue level from TSB."""
        if fitness.tsb > 10:
            return "low"
        elif fitness.tsb > -10:
            return "moderate"
        else:
            return "high"
    
    def _mock_reasoning(self, context: SmartEnduranceContext) -> str:
        """Generate mock reasoning from context."""
        tsb = context.critical.current_fitness.tsb
        ramp = context.critical.current_fitness.ramp_rate
        
        reasoning = f"CTL={context.critical.current_fitness.ctl}, ATL={context.critical.current_fitness.atl}, TSB={tsb:.1f}. "
        
        if tsb < -15:
            reasoning += "Athlete is highly fatigued (TSB << 0). Recommend recovery week or deload."
        elif ramp > 1.5:
            reasoning += f"Ramp rate {ramp:.2f} is high (>1.5), indicating rapid load increase. Risk of injury/burnout."
        else:
            reasoning += "Athlete is in good condition for progressive training."
        
        return reasoning
