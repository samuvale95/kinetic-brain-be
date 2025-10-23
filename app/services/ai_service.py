import openai
from typing import Dict, Any, Optional
from app.config import settings
from app.schemas.ai import AIRequest, AIResponse, WorkoutPlanGenerationRequest, WorkoutAnalysisRequest, WorkoutAnalysisResponse
import json
from datetime import datetime


class AIService:
    def __init__(self):
        openai.api_key = settings.openai_api_key
        self.client = openai.OpenAI(api_key=settings.openai_api_key)
    
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
