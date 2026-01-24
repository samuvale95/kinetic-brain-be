from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_, desc, func
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from app.models.workout import Workout, WorkoutSession, WorkoutPlan, WorkoutStatus
from app.models.sync import SyncConflict, SyncHistory
from loguru import logger


class SyncService:
    """Service for handling real-time synchronization between web and mobile"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_sync_status(self, user_id: int) -> Dict[str, Any]:
        """
        Get sync status for a user.
        
        Returns:
            Dict with last_sync_at, pending_changes count, conflicts count
        """
        # Get last sync timestamp
        last_sync = self.db.execute(
            select(SyncHistory)
            .where(SyncHistory.user_id == user_id)
            .order_by(desc(SyncHistory.synced_at))
            .limit(1)
        ).scalar_one_or_none()
        
        last_sync_at = last_sync.synced_at if last_sync else None
        
        # Count pending conflicts
        conflicts_count = self.db.execute(
            select(func.count(SyncConflict.id))
            .where(
                and_(
                    SyncConflict.user_id == user_id,
                    SyncConflict.resolved == False
                )
            )
        ).scalar() or 0
        
        # Estimate pending changes (workouts/sessions modified since last sync)
        pending_changes = 0
        if last_sync_at:
            # Count workouts modified since last sync
            workouts_count = self.db.execute(
                select(func.count(Workout.id))
                .where(
                    and_(
                        Workout.user_id == user_id,
                        Workout.updated_at > last_sync_at
                    )
                )
            ).scalar() or 0
            
            # Count sessions created/modified since last sync
            sessions_count = self.db.execute(
                select(func.count(WorkoutSession.id))
                .where(
                    and_(
                        WorkoutSession.user_id == user_id,
                        WorkoutSession.created_at > last_sync_at
                    )
                )
            ).scalar() or 0
            
            pending_changes = workouts_count + sessions_count
        
        return {
            "last_sync_at": last_sync_at.isoformat() if last_sync_at else None,
            "pending_changes": pending_changes,
            "conflicts": conflicts_count
        }
    
    async def push_changes(
        self,
        user_id: int,
        changes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Push changes from client to server.
        
        Args:
            user_id: User ID
            changes: Dict with changes to sync
                - workouts: List of workout changes
                - sessions: List of session changes
                - plans: List of plan changes
                - timestamp: Client timestamp
        
        Returns:
            Dict with sync results
        """
        synced = 0
        conflicts = []
        errors = []
        
        client_timestamp = changes.get("timestamp")
        if client_timestamp:
            try:
                client_dt = datetime.fromisoformat(client_timestamp.replace('Z', '+00:00'))
            except:
                client_dt = datetime.now(timezone.utc)
        else:
            client_dt = datetime.now(timezone.utc)
        
        # Process workout changes
        for workout_data in changes.get("workouts", []):
            try:
                workout_id = workout_data.get("id")
                if not workout_id:
                    continue
                
                # Get existing workout
                workout = self.db.execute(
                    select(Workout)
                    .where(
                        and_(
                            Workout.id == workout_id,
                            Workout.user_id == user_id
                        )
                    )
                ).scalar_one_or_none()
                
                if not workout:
                    errors.append(f"Workout {workout_id} not found")
                    continue
                
                # Check for conflicts (timestamp-based)
                if workout.updated_at and workout_data.get("updated_at"):
                    server_updated = workout.updated_at
                    client_updated = datetime.fromisoformat(
                        workout_data["updated_at"].replace('Z', '+00:00')
                    )
                    
                    # If client version is older, there's a conflict
                    if client_updated < server_updated:
                        conflict = SyncConflict(
                            user_id=user_id,
                            entity_type="workout",
                            entity_id=workout_id,
                            server_version=workout.updated_at.isoformat(),
                            client_version=workout_data.get("updated_at"),
                            server_data=self._serialize_workout(workout),
                            client_data=workout_data,
                            resolved=False
                        )
                        self.db.add(conflict)
                        conflicts.append({
                            "type": "workout",
                            "id": workout_id,
                            "conflict_id": None  # Will be set after commit
                        })
                        continue
                
                # Apply changes (simple merge for now)
                if "status" in workout_data:
                    workout.status = WorkoutStatus(workout_data["status"])
                if "scheduled_date" in workout_data:
                    workout.scheduled_date = datetime.fromisoformat(workout_data["scheduled_date"]).date()
                
                workout.updated_at = datetime.now(timezone.utc)
                synced += 1
                
            except Exception as e:
                logger.error(f"Error syncing workout {workout_data.get('id')}: {e}")
                errors.append(f"Workout {workout_data.get('id')}: {str(e)}")
        
        # Process session changes
        for session_data in changes.get("sessions", []):
            try:
                session_id = session_data.get("id")
                if session_id:
                    # Update existing session
                    session = self.db.execute(
                        select(WorkoutSession)
                        .where(
                            and_(
                                WorkoutSession.id == session_id,
                                WorkoutSession.user_id == user_id
                            )
                        )
                    ).scalar_one_or_none()
                    
                    if session:
                        # Apply updates
                        if "duration_minutes" in session_data:
                            session.duration_minutes = session_data["duration_minutes"]
                        if "avg_hr" in session_data:
                            session.avg_hr = session_data["avg_hr"]
                        if "notes" in session_data:
                            session.notes = session_data["notes"]
                        synced += 1
                else:
                    # Create new session
                    session = WorkoutSession(
                        user_id=user_id,
                        workout_id=session_data.get("workout_id"),
                        actual_date=datetime.fromisoformat(session_data["actual_date"].replace('Z', '+00:00')) if session_data.get("actual_date") else datetime.now(timezone.utc),
                        duration_minutes=session_data.get("duration_minutes", 0),
                        avg_hr=session_data.get("avg_hr"),
                        notes=session_data.get("notes")
                    )
                    self.db.add(session)
                    synced += 1
                    
            except Exception as e:
                logger.error(f"Error syncing session {session_data.get('id')}: {e}")
                errors.append(f"Session {session_data.get('id')}: {str(e)}")
        
        # Record sync history
        sync_history = SyncHistory(
            user_id=user_id,
            synced_at=datetime.now(timezone.utc),
            changes_count=synced,
            conflicts_count=len(conflicts),
            client_timestamp=client_dt
        )
        self.db.add(sync_history)
        
        # Commit all changes
        self.db.commit()
        
        # Update conflict IDs
        for conflict in conflicts:
            if conflict["conflict_id"] is None:
                # Find the conflict we just created
                db_conflict = self.db.execute(
                    select(SyncConflict)
                    .where(
                        and_(
                            SyncConflict.user_id == user_id,
                            SyncConflict.entity_type == conflict["type"],
                            SyncConflict.entity_id == conflict["id"],
                            SyncConflict.resolved == False
                        )
                    )
                    .order_by(desc(SyncConflict.created_at))
                    .limit(1)
                ).scalar_one_or_none()
                
                if db_conflict:
                    conflict["conflict_id"] = db_conflict.id
        
        return {
            "synced": synced,
            "conflicts": conflicts,
            "errors": errors
        }
    
    async def pull_changes(
        self,
        user_id: int,
        since: Optional[datetime] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Pull changes from server since last sync.
        
        Args:
            user_id: User ID
            since: Timestamp to get changes since (None = all)
        
        Returns:
            Dict with lists of changed entities
        """
        changes = {
            "workouts": [],
            "sessions": [],
            "plans": []
        }
        
        # Get modified workouts
        workout_query = select(Workout).where(Workout.user_id == user_id)
        if since:
            workout_query = workout_query.where(Workout.updated_at > since)
        
        workouts = self.db.execute(workout_query).scalars().all()
        for workout in workouts:
            changes["workouts"].append(self._serialize_workout(workout))
        
        # Get new/modified sessions
        session_query = select(WorkoutSession).where(WorkoutSession.user_id == user_id)
        if since:
            session_query = session_query.where(WorkoutSession.created_at > since)
        
        sessions = self.db.execute(session_query).scalars().all()
        for session in sessions:
            changes["sessions"].append({
                "id": session.id,
                "workout_id": session.workout_id,
                "actual_date": session.actual_date.isoformat() if session.actual_date else None,
                "duration_minutes": session.duration_minutes,
                "avg_hr": session.avg_hr,
                "notes": session.notes,
                "created_at": session.created_at.isoformat() if session.created_at else None
            })
        
        # Get modified plans
        plan_query = select(WorkoutPlan).where(WorkoutPlan.user_id == user_id)
        if since:
            plan_query = plan_query.where(WorkoutPlan.updated_at > since)
        
        plans = self.db.execute(plan_query).scalars().all()
        for plan in plans:
            changes["plans"].append({
                "id": plan.id,
                "title": plan.title,
                "status": plan.status,
                "start_date": plan.start_date.isoformat() if plan.start_date else None,
                "end_date": plan.end_date.isoformat() if plan.end_date else None,
                "updated_at": plan.updated_at.isoformat() if plan.updated_at else None
            })
        
        return changes
    
    async def resolve_conflict(
        self,
        user_id: int,
        conflict_id: int,
        resolution: str
    ) -> Dict[str, Any]:
        """
        Resolve a sync conflict.
        
        Args:
            user_id: User ID
            conflict_id: Conflict ID
            resolution: "server", "client", or "merge"
        
        Returns:
            Dict with resolution result
        """
        conflict = self.db.execute(
            select(SyncConflict)
            .where(
                and_(
                    SyncConflict.id == conflict_id,
                    SyncConflict.user_id == user_id,
                    SyncConflict.resolved == False
                )
            )
        ).scalar_one_or_none()
        
        if not conflict:
            raise ValueError(f"Conflict {conflict_id} not found or already resolved")
        
        if resolution == "server":
            # Keep server version, do nothing
            conflict.resolved = True
            conflict.resolution = "server"
            conflict.resolved_at = datetime.now(timezone.utc)
        
        elif resolution == "client":
            # Apply client version
            if conflict.entity_type == "workout":
                workout = self.db.execute(
                    select(Workout)
                    .where(
                        and_(
                            Workout.id == conflict.entity_id,
                            Workout.user_id == user_id
                        )
                    )
                ).scalar_one_or_none()
                
                if workout:
                    client_data = conflict.client_data
                    if "status" in client_data:
                        workout.status = WorkoutStatus(client_data["status"])
                    if "scheduled_date" in client_data:
                        workout.scheduled_date = datetime.fromisoformat(client_data["scheduled_date"]).date()
                    workout.updated_at = datetime.now(timezone.utc)
            
            conflict.resolved = True
            conflict.resolution = "client"
            conflict.resolved_at = datetime.now(timezone.utc)
        
        elif resolution == "merge":
            # Merge both versions (simplified - prefer server for most fields)
            if conflict.entity_type == "workout":
                workout = self.db.execute(
                    select(Workout)
                    .where(
                        and_(
                            Workout.id == conflict.entity_id,
                            Workout.user_id == user_id
                        )
                    )
                ).scalar_one_or_none()
                
                if workout:
                    client_data = conflict.client_data
                    # Merge: take client notes if present, keep server status
                    if "notes" in client_data and client_data["notes"]:
                        # Update notes if workout has a notes field
                        pass  # Workout doesn't have notes field, skip
                    
                    workout.updated_at = datetime.now(timezone.utc)
            
            conflict.resolved = True
            conflict.resolution = "merge"
            conflict.resolved_at = datetime.now(timezone.utc)
        
        self.db.commit()
        
        return {
            "conflict_id": conflict_id,
            "resolution": resolution,
            "resolved_at": conflict.resolved_at.isoformat()
        }
    
    def get_conflicts(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Get all pending conflicts for a user.
        
        Returns:
            List of conflict dicts
        """
        conflicts = self.db.execute(
            select(SyncConflict)
            .where(
                and_(
                    SyncConflict.user_id == user_id,
                    SyncConflict.resolved == False
                )
            )
            .order_by(desc(SyncConflict.created_at))
        ).scalars().all()
        
        return [
            {
                "id": c.id,
                "entity_type": c.entity_type,
                "entity_id": c.entity_id,
                "server_version": c.server_version,
                "client_version": c.client_version,
                "created_at": c.created_at.isoformat() if c.created_at else None
            }
            for c in conflicts
        ]
    
    async def batch_sync(
        self,
        user_id: int,
        batch_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Batch sync operation for efficient bulk updates.
        
        Args:
            user_id: User ID
            batch_data: Dict with batches of entities to sync
        
        Returns:
            Dict with sync results
        """
        result = {
            "synced": {
                "workouts": 0,
                "sessions": 0,
                "plans": 0
            },
            "conflicts": [],
            "errors": []
        }
        
        # Process workouts batch
        if "workouts" in batch_data:
            for workout_data in batch_data["workouts"]:
                try:
                    workout_id = workout_data.get("id")
                    if not workout_id:
                        continue
                    
                    workout = self.db.execute(
                        select(Workout)
                        .where(
                            and_(
                                Workout.id == workout_id,
                                Workout.user_id == user_id
                            )
                        )
                    ).scalar_one_or_none()
                    
                    if workout:
                        # Apply updates
                        if "status" in workout_data:
                            workout.status = WorkoutStatus(workout_data["status"])
                        if "scheduled_date" in workout_data:
                            workout.scheduled_date = datetime.fromisoformat(workout_data["scheduled_date"]).date()
                        workout.updated_at = datetime.now(timezone.utc)
                        result["synced"]["workouts"] += 1
                except Exception as e:
                    result["errors"].append(f"Workout {workout_data.get('id')}: {str(e)}")
        
        # Process sessions batch
        if "sessions" in batch_data:
            for session_data in batch_data["sessions"]:
                try:
                    session_id = session_data.get("id")
                    if session_id:
                        session = self.db.execute(
                            select(WorkoutSession)
                            .where(
                                and_(
                                    WorkoutSession.id == session_id,
                                    WorkoutSession.user_id == user_id
                                )
                            )
                        ).scalar_one_or_none()
                        
                        if session:
                            if "duration_minutes" in session_data:
                                session.duration_minutes = session_data["duration_minutes"]
                            if "avg_hr" in session_data:
                                session.avg_hr = session_data["avg_hr"]
                            if "notes" in session_data:
                                session.notes = session_data["notes"]
                            result["synced"]["sessions"] += 1
                    else:
                        # Create new session
                        session = WorkoutSession(
                            user_id=user_id,
                            workout_id=session_data.get("workout_id"),
                            actual_date=datetime.fromisoformat(session_data["actual_date"].replace('Z', '+00:00')) if session_data.get("actual_date") else datetime.now(timezone.utc),
                            duration_minutes=session_data.get("duration_minutes", 0),
                            avg_hr=session_data.get("avg_hr"),
                            notes=session_data.get("notes")
                        )
                        self.db.add(session)
                        result["synced"]["sessions"] += 1
                except Exception as e:
                    result["errors"].append(f"Session {session_data.get('id')}: {str(e)}")
        
        # Process plans batch
        if "plans" in batch_data:
            for plan_data in batch_data["plans"]:
                try:
                    plan_id = plan_data.get("id")
                    if not plan_id:
                        continue
                    
                    plan = self.db.execute(
                        select(WorkoutPlan)
                        .where(
                            and_(
                                WorkoutPlan.id == plan_id,
                                WorkoutPlan.user_id == user_id
                            )
                        )
                    ).scalar_one_or_none()
                    
                    if plan:
                        if "status" in plan_data:
                            plan.status = plan_data["status"]
                        if "title" in plan_data:
                            plan.title = plan_data["title"]
                        plan.updated_at = datetime.now(timezone.utc)
                        result["synced"]["plans"] += 1
                except Exception as e:
                    result["errors"].append(f"Plan {plan_data.get('id')}: {str(e)}")
        
        self.db.commit()
        
        return result
    
    async def get_initial_sync_data(self, user_id: int) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all data for initial sync (first time sync).
        
        Returns all workouts, sessions, and plans for the user.
        """
        data = {
            "workouts": [],
            "sessions": [],
            "plans": []
        }
        
        # Get all workouts
        workouts = self.db.execute(
            select(Workout)
            .where(Workout.user_id == user_id)
        ).scalars().all()
        
        for workout in workouts:
            data["workouts"].append(self._serialize_workout(workout))
        
        # Get all sessions
        sessions = self.db.execute(
            select(WorkoutSession)
            .where(WorkoutSession.user_id == user_id)
        ).scalars().all()
        
        for session in sessions:
            data["sessions"].append({
                "id": session.id,
                "workout_id": session.workout_id,
                "actual_date": session.actual_date.isoformat() if session.actual_date else None,
                "duration_minutes": session.duration_minutes,
                "avg_hr": session.avg_hr,
                "notes": session.notes,
                "created_at": session.created_at.isoformat() if session.created_at else None
            })
        
        # Get all plans
        plans = self.db.execute(
            select(WorkoutPlan)
            .where(WorkoutPlan.user_id == user_id)
        ).scalars().all()
        
        for plan in plans:
            data["plans"].append({
                "id": plan.id,
                "title": plan.title,
                "description": plan.description,
                "status": plan.status,
                "start_date": plan.start_date.isoformat() if plan.start_date else None,
                "end_date": plan.end_date.isoformat() if plan.end_date else None,
                "total_weeks": plan.total_weeks,
                "goal": plan.goal,
                "sport_type": plan.sport_type,
                "level": plan.level,
                "created_at": plan.created_at.isoformat() if plan.created_at else None,
                "updated_at": plan.updated_at.isoformat() if plan.updated_at else None
            })
        
        return data
    
    def _serialize_workout(self, workout: Workout) -> Dict[str, Any]:
        """Serialize workout to dict for sync"""
        return {
            "id": workout.id,
            "title": workout.title,
            "status": workout.status.value if workout.status else None,
            "scheduled_date": workout.scheduled_date.isoformat() if workout.scheduled_date else None,
            "duration_minutes": workout.duration_minutes,
            "type": workout.type,
            "intensity": workout.intensity,
            "zone": workout.zone,
            "updated_at": workout.updated_at.isoformat() if workout.updated_at else None
        }
