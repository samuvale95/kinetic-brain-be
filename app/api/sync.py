from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_, desc
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel
from app.database import get_db
from app.api.auth import get_current_user
from app.models.workout import Workout, WorkoutSession, WorkoutPlan
from app.models.user import User
from app.services.sync_service import SyncService
from loguru import logger

router = APIRouter(prefix="/sync", tags=["sync"])


@router.get("/status")
async def get_sync_status(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get sync status for the current user.
    Returns last sync timestamp and pending changes count.
    """
    sync_service = SyncService(db)
    
    user_id = current_user["user_id"]
    status_data = sync_service.get_sync_status(user_id)
    
    return {
        "user_id": user_id,
        "last_sync_at": status_data.get("last_sync_at"),
        "pending_changes": status_data.get("pending_changes", 0),
        "conflicts": status_data.get("conflicts", 0),
        "status": "synced" if status_data.get("pending_changes", 0) == 0 else "pending"
    }


class PushChangesRequest(BaseModel):
    workouts: Optional[List[Dict[str, Any]]] = []
    sessions: Optional[List[Dict[str, Any]]] = []
    plans: Optional[List[Dict[str, Any]]] = []
    timestamp: Optional[str] = None


@router.post("/push")
async def push_changes(
    changes: PushChangesRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Push changes from mobile/client to server.
    
    Expected format:
    {
        "workouts": [...],
        "sessions": [...],
        "plans": [...],
        "timestamp": "2024-01-01T00:00:00Z"
    }
    """
    sync_service = SyncService(db)
    user_id = current_user["user_id"]
    
    try:
        result = await sync_service.push_changes(
            user_id=user_id,
            changes=changes.dict()
        )
        
        return {
            "success": True,
            "synced": result.get("synced", 0),
            "conflicts": result.get("conflicts", []),
            "errors": result.get("errors", [])
        }
    except Exception as e:
        logger.error(f"Error pushing changes for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error syncing changes: {str(e)}"
        )


@router.get("/pull")
async def pull_changes(
    since: Optional[str] = Query(None, description="ISO timestamp of last sync"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Pull changes from server since last sync.
    
    Returns all changes (workouts, sessions, plans) that have been
    modified since the provided timestamp.
    """
    sync_service = SyncService(db)
    user_id = current_user["user_id"]
    
    # Parse since timestamp
    since_dt = None
    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid timestamp format. Use ISO 8601 format."
            )
    
    try:
        changes = await sync_service.pull_changes(
            user_id=user_id,
            since=since_dt
        )
        
        return {
            "success": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "changes": changes
        }
    except Exception as e:
        logger.error(f"Error pulling changes for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error pulling changes: {str(e)}"
        )


@router.post("/resolve-conflict")
async def resolve_conflict(
    conflict_id: int,
    resolution: str = Query(..., pattern="^(server|client|merge)$", description="Resolution strategy"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Resolve a sync conflict.
    
    Resolution strategies:
    - server: Use server version
    - client: Use client version
    - merge: Merge both versions (if applicable)
    """
    sync_service = SyncService(db)
    user_id = current_user["user_id"]
    
    try:
        result = await sync_service.resolve_conflict(
            user_id=user_id,
            conflict_id=conflict_id,
            resolution=resolution
        )
        
        return {
            "success": True,
            "resolved": result
        }
    except Exception as e:
        logger.error(f"Error resolving conflict {conflict_id} for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error resolving conflict: {str(e)}"
        )


@router.get("/conflicts")
async def get_conflicts(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all pending conflicts for the current user.
    """
    sync_service = SyncService(db)
    user_id = current_user["user_id"]
    
    conflicts = sync_service.get_conflicts(user_id)
    
    return {
        "conflicts": conflicts,
        "count": len(conflicts)
    }


class BatchSyncRequest(BaseModel):
    workouts: Optional[List[Dict[str, Any]]] = []
    sessions: Optional[List[Dict[str, Any]]] = []
    plans: Optional[List[Dict[str, Any]]] = []
    timestamp: Optional[str] = None


@router.post("/batch")
async def batch_sync(
    batch_data: BatchSyncRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Batch sync operation for initial sync or bulk updates.
    
    Accepts multiple entities in a single request for efficient syncing.
    Format:
    {
        "workouts": [...],
        "sessions": [...],
        "plans": [...],
        "timestamp": "2024-01-01T00:00:00Z"
    }
    """
    sync_service = SyncService(db)
    user_id = current_user["user_id"]
    
    try:
        result = await sync_service.batch_sync(
            user_id=user_id,
            batch_data=batch_data.dict()
        )
        
        return {
            "success": True,
            "synced": result.get("synced", {}),
            "conflicts": result.get("conflicts", []),
            "errors": result.get("errors", [])
        }
    except Exception as e:
        logger.error(f"Error in batch sync for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error in batch sync: {str(e)}"
        )


@router.get("/initial")
async def get_initial_sync_data(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all data for initial sync (first time sync).
    Returns all workouts, sessions, and plans for the user.
    """
    sync_service = SyncService(db)
    user_id = current_user["user_id"]
    
    try:
        data = await sync_service.get_initial_sync_data(user_id)
        
        return {
            "success": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data
        }
    except Exception as e:
        logger.error(f"Error getting initial sync data for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting initial sync data: {str(e)}"
        )
