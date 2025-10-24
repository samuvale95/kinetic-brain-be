from sqlalchemy.orm import Session
from sqlalchemy import select, and_, func, desc
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta
from app.models.workout import Workout, WorkoutSession, WorkoutPlan
from app.services.ai_service import AIService
from app.schemas.ai import AIRequest, WeeklyPlanRequest, PerformanceAnalysisData
import json
import math


class ProgressiveWorkoutPlanService:
    def __init__(self, db: Session):
        self.db = db
        self.ai_service = AIService()
    
    def generate_weekly_plan(self, 
                           user_id: int, 
                           week_number: int,
                           target_date: str,
                           previous_week_data: Optional[Dict[str, Any]] = None,
                           current_fitness_level: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Genera piano per una settimana specifica basato sui dati precedenti"""
        
        # 1. Raccoglie dati storici dell'utente
        user_history = self._get_user_workout_history(user_id, weeks_back=4)
        performance_trends = self._analyze_performance_trends(user_history)
        
        # 2. Calcola date della settimana
        target_dt = datetime.strptime(target_date, "%Y-%m-%d").date()
        weeks_remaining = self._calculate_weeks_remaining(target_dt, week_number)
        
        # 3. Costruisce prompt contestualizzato
        prompt = self._build_progressive_prompt(
            week_number=week_number,
            weeks_remaining=weeks_remaining,
            target_date=target_date,
            previous_week=previous_week_data,
            user_history=user_history,
            performance_trends=performance_trends,
            current_fitness=current_fitness_level
        )
        
        # 4. Genera piano con AI
        ai_request = AIRequest(
            prompt=prompt,
            max_tokens=2000,
            temperature=0.7
        )
        response = self.ai_service.generate_response(ai_request)
        
        # 5. Parsing e strutturazione della risposta
        try:
            plan_data = json.loads(response.response)
        except json.JSONDecodeError:
            plan_data = self._parse_text_response(response.response, week_number, target_date)
        
        # 6. Aggiunge metadati
        plan_data.update({
            "generated_at": datetime.utcnow().isoformat(),
            "week_start_date": self._get_week_start_date(target_dt, week_number),
            "week_end_date": self._get_week_end_date(target_dt, week_number)
        })
        
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
                "completion_rate": 100,
                "intensity_trend": "stable",
                "fatigue_level": "low",
                "consistency_score": 80,
                "avg_intensity": 5.0
            }
        
        # Calcola completion rate
        total_planned = sum(week.get('planned_workouts', 0) for week in user_history)
        total_completed = sum(week.get('completed_workouts', 0) for week in user_history)
        completion_rate = (total_completed / total_planned * 100) if total_planned > 0 else 100
        
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
        consistency_score = sum(completion_rates) / len(completion_rates) if completion_rates else 80
        
        return {
            "completion_rate": completion_rate,
            "intensity_trend": intensity_trend,
            "fatigue_level": fatigue_level,
            "consistency_score": consistency_score,
            "avg_intensity": avg_rpe,
            "last_week_avg_rpe": recent_rpe[-1] if recent_rpe else 6.0
        }
    
    def _build_progressive_prompt(self, week_number: int, weeks_remaining: int, target_date: str,
                                previous_week: Optional[Dict], user_history: List[Dict],
                                performance_trends: Dict, current_fitness: Optional[Dict]) -> str:
        """Costruisce prompt per generazione progressiva"""
        
        prompt = f"""
        Generate WEEK {week_number} of a progressive training plan.
        
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

