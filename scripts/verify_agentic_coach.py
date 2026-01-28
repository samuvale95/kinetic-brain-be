import sys
import os
import datetime
# from loguru import logger

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.agentic_coach_service import AgenticCoachService
from app.schemas.agentic_coach import UnifiedPlanRequest, RecentWorkoutContext, CoachMemoryItem

class MockAIService:
    """Mock AI Service for verification"""
    def generate_raw(self, system: str, user: str) -> str:
        print(f"MOCK AI CALL:\nSYSTEM: {system[:50]}...\nUSER: {user[:50]}...")
        return "{}" # Service mocks the return content anyway

def test_flow():
    # 1. Setup Data
    service = AgenticCoachService(ai_service=MockAIService())
    
    req = UnifiedPlanRequest(
        user_id=1,
        target_week_start=datetime.date.today(),
        goal="Improve 5k time while maintaining strength",
        available_days=["Monday", "Tuesday", "Thursday", "Friday", "Sunday"],
        equipment=["Barbell", "Dumbbells", "Pull-up bar"],
        recent_workouts=[
            RecentWorkoutContext(
                workout_id=101,
                date=datetime.date.today() - datetime.timedelta(days=2),
                type="Intervals",
                sport="run",
                planned_duration=45,
                actual_duration=45,
                rpe=9,
                success_rating=4,
                notes="Hard but managed to finish.",
                failure_point=None
            )
        ],
        coach_memories=[
            CoachMemoryItem(
                key="knee_pain_right",
                value="Right knee hurts on downhills",
                category="injury"
            )
        ]
    )
    
    # 2. Reasoning Phase
    assessment = service.assess_athlete(request=req)
    print(f"\n[ASSESSMENT]: {assessment.focus_for_week}\nReasoning: {assessment.reasoning}")
    
    # 3. Generation Phase
    plan = service.generate_week(request=req, assessment=assessment)
    print(f"\n[PLAN]: Week {plan.week_number} - Phase: {plan.phase}")
    print(f"Summary: {plan.weekly_summary_reasoning}")

if __name__ == "__main__":
    test_flow()
