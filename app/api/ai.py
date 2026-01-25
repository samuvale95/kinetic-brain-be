from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.schemas.ai import (
    AIRequest, AIResponse, WorkoutPlanGenerationRequest,
    WorkoutAnalysisRequest, WorkoutAnalysisResponse, SuggestionRequest
)
from app.services.ai_service import AIService
from app.api.auth import get_current_user

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/generate", response_model=AIResponse)
async def generate_ai_response(request: AIRequest,
                              current_user: dict = Depends(get_current_user),
                              db: Session = Depends(get_db)):
    """Generate AI response for general queries"""
    ai_service = AIService(db)
    
    try:
        response = ai_service.generate_response(request)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI service error: {str(e)}"
        )


@router.post("/generate-plan", response_model=dict)
async def generate_workout_plan(request: WorkoutPlanGenerationRequest,
                               current_user: dict = Depends(get_current_user),
                               db: Session = Depends(get_db)):
    """Generate personalized workout plan using AI"""
    ai_service = AIService(db)
    
    try:
        plan_data = ai_service.generate_workout_plan(
            request,
            user_id=current_user["user_id"],
        )
        return {"plan": plan_data}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI plan generation error: {str(e)}"
        )


@router.post("/analyze-workout", response_model=WorkoutAnalysisResponse)
async def analyze_workout(request: WorkoutAnalysisRequest,
                         current_user: dict = Depends(get_current_user),
                         db: Session = Depends(get_db)):
    """Analyze workout performance using AI"""
    ai_service = AIService(db)
    
    try:
        analysis = ai_service.analyze_workout(request)
        return analysis
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI workout analysis error: {str(e)}"
        )


@router.post("/suggest", response_model=AIResponse)
async def get_suggestions(request: SuggestionRequest,
                         current_user: dict = Depends(get_current_user),
                         db: Session = Depends(get_db)):
    """Get AI suggestions based on context"""
    ai_service = AIService(db)
    
    # Build context-specific prompt
    prompt = f"""
    Based on the following context, provide helpful suggestions for {request.suggestion_type}:
    
    Context: {request.context}
    
    Please provide practical, actionable advice.
    """
    
    if request.user_profile:
        prompt += f"\n\nUser Profile: {request.user_profile}"
    
    ai_request = AIRequest(
        prompt=prompt,
        context=request.user_profile,
        max_tokens=1000,
        temperature=0.7
    )
    
    try:
        response = ai_service.generate_response(ai_request)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI suggestion error: {str(e)}"
        )


@router.post("/chat", response_model=dict)
async def chat_with_ai(
    message: str = Body(..., embed=True, description="User message"),
    workout_id: Optional[int] = Body(None, embed=True, description="Optional workout ID for context"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Real-time AI coaching chat: workout explanations, adaptations, advice."""
    ai_service = AIService(db)
    try:
        return ai_service.chat_coach(
            user_id=current_user["user_id"],
            message=message,
            workout_id=workout_id,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore AI chat: {str(e)}",
        )
