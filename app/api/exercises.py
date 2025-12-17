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
    print(f"[EXERCISES] ===== GET AVAILABLE EQUIPMENT START =====")
    try:
        exercise_service = ExerciseService(db)
        print(f"[EXERCISES] ExerciseService initialized")
        equipment = exercise_service.get_available_equipment()
        print(f"[EXERCISES] Found {len(equipment)} equipment types: {equipment}")
        print(f"[EXERCISES] ===== GET AVAILABLE EQUIPMENT SUCCESS =====")
        return equipment
    except Exception as e:
        print(f"[EXERCISES] ✗ Error getting available equipment: {type(e).__name__}: {e}")
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
    print(f"[EXERCISES] ===== GET EXERCISES START =====")
    print(f"[EXERCISES] Query parameters:")
    print(f"[EXERCISES]   - category: {category}")
    print(f"[EXERCISES]   - level: {level}")
    print(f"[EXERCISES]   - equipment: {equipment}")
    print(f"[EXERCISES]   - limit: {limit}")
    try:
        exercise_service = ExerciseService(db)
        print(f"[EXERCISES] ExerciseService initialized")
        
        available_equipment = [equipment] if equipment else None
        print(f"[EXERCISES] Available equipment filter: {available_equipment}")
        
        exercises = exercise_service.get_exercises_by_criteria(
            category=category,
            level=level,
            available_equipment=available_equipment,
            limit=limit
        )
        print(f"[EXERCISES] Found {len(exercises)} exercises matching criteria")
        
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
        
        print(f"[EXERCISES] Returning {len(result)} exercises")
        print(f"[EXERCISES] ===== GET EXERCISES SUCCESS =====")
        return result
    except Exception as e:
        print(f"[EXERCISES] ✗ Error querying exercises: {type(e).__name__}: {e}")
        logger.error(f"Error querying exercises: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving exercises"
        )


