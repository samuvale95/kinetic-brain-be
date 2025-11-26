"""
API endpoints per gestire esercizi
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.services.exercise_service import ExerciseService
from loguru import logger

router = APIRouter(prefix="/exercises", tags=["exercises"])


@router.get("/equipment", response_model=List[str])
async def get_available_equipment(
    db: Session = Depends(get_db)
):
    """
    Restituisce lista di attrezzi disponibili dalla tabella exercises
    
    Returns:
        Lista di attrezzi (equipmentType enum values)
    """
    try:
        exercise_service = ExerciseService(db)
        equipment = exercise_service.get_available_equipment()
        return equipment
    except Exception as e:
        logger.error(f"Error getting available equipment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving available equipment"
        )


@router.get("")
async def get_exercises(
    category: str = None,
    level: str = None,
    equipment: str = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Query esercizi con filtri opzionali (endpoint per debug/admin)
    
    Query Parameters:
        category: Categoria (strength, stretching, etc.)
        level: Livello (beginner, intermediate, expert)
        equipment: Attrezzo specifico
        limit: Limite risultati (default: 100)
    
    Returns:
        Lista di esercizi
    """
    try:
        exercise_service = ExerciseService(db)
        
        available_equipment = [equipment] if equipment else None
        
        exercises = exercise_service.get_exercises_by_criteria(
            category=category,
            level=level,
            available_equipment=available_equipment,
            limit=limit
        )
        
        # Converti in dict per serializzazione
        result = []
        for exercise in exercises:
            result.append({
                "id": str(exercise.id),
                "name": exercise.name,
                "category": str(exercise.category) if exercise.category else None,
                "level": str(exercise.level) if exercise.level else None,
                "equipment": str(exercise.equipment) if exercise.equipment else None,
                "primary_muscles": [str(m) for m in (exercise.primary_muscles or [])],
                "secondary_muscles": [str(m) for m in (exercise.secondary_muscles or [])],
                "instructions": exercise.instructions or []
            })
        
        return result
    except Exception as e:
        logger.error(f"Error querying exercises: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving exercises"
        )


