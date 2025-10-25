import openai
from typing import Dict, Any, Optional
from app.config import settings
from app.schemas.ai import AIRequest, AIResponse, WorkoutPlanGenerationRequest, WorkoutAnalysisRequest, WorkoutAnalysisResponse
import json
from datetime import datetime, timedelta
import os


class AIService:
    def __init__(self):
        openai.api_key = settings.openai_api_key
        self.client = openai.OpenAI(api_key=settings.openai_api_key)
        self.mock_mode = settings.mock_llm
    
    def generate_response(self, request: AIRequest) -> AIResponse:
        """Generate AI response using OpenAI API"""
        try:
            response = self.client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": "You are a professional sports coach and training expert."},
                    {"role": "user", "content": request.prompt}
                ],
                max_tokens=request.max_tokens or settings.openai_max_tokens,
                temperature=request.temperature or 0.7
            )
            
            return AIResponse(
                response=response.choices[0].message.content,
                usage=response.usage.dict() if response.usage else None,
                model=response.model,
                created_at=datetime.utcnow().isoformat()
            )
        except Exception as e:
            raise Exception(f"AI service error: {str(e)}")
    
    def generate_workout_plan(self, request: WorkoutPlanGenerationRequest) -> Dict[str, Any]:
        """Generate a personalized workout plan using AI"""
        if self.mock_mode:
            return self._generate_mock_workout_plan(request)
        
        prompt = self._build_workout_plan_prompt(request)
        
        ai_request = AIRequest(
            prompt=prompt,
            context=request.user_profile,
            max_tokens=2000,
            temperature=0.7
        )
        
        response = self.generate_response(ai_request)
        
        try:
            # Try to parse as JSON, fallback to text if not valid JSON
            plan_data = json.loads(response.response)
            return plan_data
        except json.JSONDecodeError:
            # Return structured text response
            return {
                "title": f"{request.sport_type.title()} Training Plan - {request.level.title()}",
                "description": response.response,
                "sport_type": request.sport_type,
                "level": request.level,
                "goal": request.goal,
                "duration_weeks": request.duration_weeks,
                "weekly_hours": request.weekly_hours
            }
    
    def analyze_workout(self, request: WorkoutAnalysisRequest) -> WorkoutAnalysisResponse:
        """Analyze workout performance using AI"""
        prompt = self._build_workout_analysis_prompt(request)
        
        ai_request = AIRequest(
            prompt=prompt,
            context=request.workout_data,
            max_tokens=1000,
            temperature=0.5
        )
        
        response = self.generate_response(ai_request)
        
        # Parse AI response to extract structured data
        analysis_data = self._parse_workout_analysis(response.response)
        
        return WorkoutAnalysisResponse(
            analysis=analysis_data.get("analysis", response.response),
            recommendations=analysis_data.get("recommendations", []),
            score=analysis_data.get("score"),
            areas_for_improvement=analysis_data.get("areas_for_improvement", []),
            next_steps=analysis_data.get("next_steps", [])
        )
    
    def _build_workout_plan_prompt(self, request: WorkoutPlanGenerationRequest) -> str:
        """Build prompt for workout plan generation"""
        prompt = f"""
        Create a detailed {request.sport_type} training plan for a {request.level} athlete.
        
        Goal: {request.goal}
        Duration: {request.duration_weeks} weeks
        Weekly training hours: {request.weekly_hours}
        
        Please provide a structured training plan that includes:
        1. Weekly breakdown with specific workouts
        2. Workout types and intensities
        3. Progression over the {request.duration_weeks} weeks
        4. Recovery and rest days
        5. Key training phases
        
        Format the response as a JSON object with the following structure:
        {{
            "title": "Plan title",
            "description": "Brief description",
            "weeks": [
                {{
                    "week": 1,
                    "focus": "Base building",
                    "workouts": [
                        {{
                            "day": "Monday",
                            "type": "Endurance",
                            "duration_minutes": 60,
                            "intensity": "Z2",
                            "description": "Easy aerobic run"
                        }}
                    ]
                }}
            ]
        }}
        """
        
        if request.user_profile:
            prompt += f"\n\nUser Profile:\n{json.dumps(request.user_profile, indent=2)}"
        
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
    
    def _generate_mock_workout_plan(self, request: WorkoutPlanGenerationRequest) -> Dict[str, Any]:
        """Generate mock workout plan for testing"""
        if request.sport_type.lower() == "running":
            return self._generate_mock_running_plan(request)
        elif request.sport_type.lower() == "triathlon":
            return self._generate_mock_triathlon_plan(request)
        else:
            return self._generate_mock_generic_plan(request)
    
    def _generate_mock_running_plan(self, request: WorkoutPlanGenerationRequest) -> Dict[str, Any]:
        """Generate mock running plan (2 months to Dec 24, 2025)"""
        weeks = []
        start_date = datetime(2025, 10, 25)
        
        for week_num in range(1, 9):  # 8 weeks = 2 months
            week_start = start_date + timedelta(weeks=week_num-1)
            week_end = week_start + timedelta(days=6)
            
            week_data = {
                "week": week_num,
                "focus": self._get_running_focus(week_num),
                "total_hours": request.weekly_hours,
                "workouts": self._generate_running_workouts(week_num, request.weekly_hours),
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
            "weekly_hours": request.weekly_hours,
            "start_date": "2025-10-25",
            "end_date": "2025-12-24",
            "weeks": weeks
        }
    
    def _generate_mock_triathlon_plan(self, request: WorkoutPlanGenerationRequest) -> Dict[str, Any]:
        """Generate mock triathlon plan (2 months to Dec 24, 2025)"""
        weeks = []
        start_date = datetime(2025, 10, 25)
        
        for week_num in range(1, 9):  # 8 weeks = 2 months
            week_start = start_date + timedelta(weeks=week_num-1)
            week_end = week_start + timedelta(days=6)
            
            week_data = {
                "week": week_num,
                "focus": self._get_triathlon_focus(week_num),
                "total_hours": request.weekly_hours,
                "workouts": self._generate_triathlon_workouts(week_num, request.weekly_hours),
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
            "weekly_hours": request.weekly_hours,
            "start_date": "2025-10-25",
            "end_date": "2025-12-24",
            "weeks": weeks
        }
    
    def _generate_mock_generic_plan(self, request: WorkoutPlanGenerationRequest) -> Dict[str, Any]:
        """Generate generic mock plan"""
        return {
            "title": f"{request.sport_type.title()} Training Plan - {request.goal}",
            "description": f"Mock training plan for {request.sport_type}",
            "sport_type": request.sport_type,
            "level": request.level,
            "goal": request.goal,
            "duration_weeks": request.duration_weeks,
            "weekly_hours": request.weekly_hours
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
