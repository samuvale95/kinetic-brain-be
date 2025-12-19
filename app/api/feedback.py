from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.services.email_service import EmailService
from app.services.auth_service import AuthService
from app.utils.security import verify_token
from loguru import logger

router = APIRouter(prefix="/api", tags=["feedback"])
security = HTTPBearer(auto_error=False)


def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[dict]:
    """Get current user from JWT token if provided, otherwise return None"""
    if credentials is None:
        return None
    
    try:
        token = credentials.credentials
        payload = verify_token(token, "access")
        
        if payload is None:
            return None
        
        user_id = int(payload["sub"])
        auth_service = AuthService(db)
        user = auth_service.get_user_by_id(user_id)
        
        if user is None or not user.is_active:
            return None
        
        return {
            "user_id": user.id,
            "email": user.email
        }
    except Exception as e:
        logger.debug(f"Error getting optional current user: {e}")
        return None


class FeedbackRequest(BaseModel):
    type: str = Field(..., description="Type of feedback: bug, feature, improvement, question, other")
    subject: str = Field(..., min_length=1, description="Feedback subject")
    message: str = Field(..., min_length=1, description="Feedback message")


class FeedbackResponse(BaseModel):
    message: str
    type: str


@router.post("/feedback", response_model=FeedbackResponse, status_code=status.HTTP_200_OK)
async def submit_feedback(
    request: FeedbackRequest,
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_current_user)
):
    """
    Submit feedback. Can be called by authenticated or anonymous users.
    """
    # Validate feedback type
    valid_types = ["bug", "feature", "improvement", "question", "other"]
    if request.type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo feedback non valido. Deve essere uno di: {', '.join(valid_types)}"
        )
    
    # Validate required fields
    if not request.subject or not request.message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Oggetto e messaggio sono obbligatori"
        )
    
    # Get user email if authenticated
    user_email = None
    if current_user:
        user_email = current_user.get("email")
    
    # Send email notification to admin
    try:
        email_service = EmailService(db)
        await email_service.send_feedback_notification_email(
            feedback_type=request.type,
            subject=request.subject,
            message=request.message,
            user_email=user_email
        )
    except Exception as e:
        # Log error but don't fail the request
        logger.error(f"Error sending feedback notification email: {e}")
        # In production, use appropriate logging service
        # Optionally, save feedback to database here
    
    return FeedbackResponse(
        message="Feedback inviato con successo. Grazie per il tuo contributo!",
        type=request.type
    )
