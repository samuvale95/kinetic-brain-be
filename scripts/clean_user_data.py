#!/usr/bin/env python3
"""
Script per pulire tutti i dati di un utente specifico dal database,
preservando solo le tabelle di log (ai_response_logs).

Uso:
    python scripts/clean_user_data.py --utente <email> [--no-confirm]
    python scripts/clean_user_data.py --all [--no-confirm]
    
Opzioni:
    --utente EMAIL  Email dell'utente da pulire (obbligatorio se non si usa --all)
    --all           Cancella TUTTE le righe dal database (tranne ai_response_logs)
    --no-confirm    Esegue la pulizia senza chiedere conferma
"""

import sys
import os
import argparse

# Aggiungi la root del progetto al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import SessionLocal, engine
from app.models import (
    User,
    UserProfile,
    PerformanceMetrics,
    OAuthAccount,
    WorkoutPlan,
    Workout,
    WorkoutSession,
    CalendarEvent,
    StravaAccount,
    StravaActivity,
    StravaWebhook,
    PlanVersion,
    MetricsPendingJob,
    DailyPerformanceMetrics,
    DailyReadinessMetrics,
    TrainingMetrics,
    WeeklyTrainingSummary,
    AIResponseLog,  # Questa NON viene eliminata (tabella di log)
)
from app.models.strava import StravaSyncJob  # Import diretto perché non esportato in __init__.py


def clean_user_data(db: Session, user_id: int):
    """
    Elimina tutti i dati dell'utente specificato, preservando i log.
    L'ordine di eliminazione rispetta le foreign key constraints.
    """
    print(f"Pulizia dati per utente ID: {user_id}")
    
    # Contatori per statistiche
    deleted_counts = {}
    
    # 1. Elimina TrainingMetrics (collegati a workout_sessions o strava_activities)
    # Prima eliminiamo quelli collegati a workout_sessions
    training_metrics = db.query(TrainingMetrics).join(
        WorkoutSession, TrainingMetrics.workout_session_id == WorkoutSession.id
    ).filter(WorkoutSession.user_id == user_id).all()
    deleted_counts['training_metrics'] = len(training_metrics)
    for tm in training_metrics:
        db.delete(tm)
    
    # Poi quelli collegati a strava_activities
    training_metrics_strava = db.query(TrainingMetrics).join(
        StravaActivity, TrainingMetrics.strava_activity_id == StravaActivity.id
    ).join(
        StravaAccount, StravaActivity.strava_account_id == StravaAccount.id
    ).filter(StravaAccount.user_id == user_id).all()
    deleted_counts['training_metrics'] += len(training_metrics_strava)
    for tm in training_metrics_strava:
        db.delete(tm)
    
    # 2. Elimina WorkoutSessions
    workout_sessions = db.query(WorkoutSession).filter(WorkoutSession.user_id == user_id).all()
    deleted_counts['workout_sessions'] = len(workout_sessions)
    for ws in workout_sessions:
        db.delete(ws)
    
    # 3. Elimina StravaActivities (prima di eliminare StravaAccount)
    strava_activities = db.query(StravaActivity).join(
        StravaAccount, StravaActivity.strava_account_id == StravaAccount.id
    ).filter(StravaAccount.user_id == user_id).all()
    deleted_counts['strava_activities'] = len(strava_activities)
    for sa in strava_activities:
        db.delete(sa)
    
    # 4. Elimina StravaSyncJobs
    strava_sync_jobs = db.query(StravaSyncJob).filter(StravaSyncJob.user_id == user_id).all()
    deleted_counts['strava_sync_jobs'] = len(strava_sync_jobs)
    for sj in strava_sync_jobs:
        db.delete(sj)
    
    # 5. Elimina StravaAccount
    strava_accounts = db.query(StravaAccount).filter(StravaAccount.user_id == user_id).all()
    deleted_counts['strava_accounts'] = len(strava_accounts)
    for sa in strava_accounts:
        db.delete(sa)
    
    # 6. Elimina CalendarEvents
    calendar_events = db.query(CalendarEvent).filter(CalendarEvent.user_id == user_id).all()
    deleted_counts['calendar_events'] = len(calendar_events)
    for ce in calendar_events:
        db.delete(ce)
    
    # 7. Elimina Workouts (dopo aver eliminato le sessioni)
    workouts = db.query(Workout).filter(Workout.user_id == user_id).all()
    deleted_counts['workouts'] = len(workouts)
    for w in workouts:
        db.delete(w)
    
    # 8. Elimina PlanVersions
    plan_versions = db.query(PlanVersion).filter(PlanVersion.user_id == user_id).all()
    deleted_counts['plan_versions'] = len(plan_versions)
    for pv in plan_versions:
        db.delete(pv)
    
    # 9. Elimina WorkoutPlans (dopo aver eliminato workouts e plan_versions)
    workout_plans = db.query(WorkoutPlan).filter(WorkoutPlan.user_id == user_id).all()
    deleted_counts['workout_plans'] = len(workout_plans)
    for wp in workout_plans:
        db.delete(wp)
    
    # 10. Elimina WeeklyTrainingSummaries
    weekly_summaries = db.query(WeeklyTrainingSummary).filter(
        WeeklyTrainingSummary.user_id == user_id
    ).all()
    deleted_counts['weekly_training_summaries'] = len(weekly_summaries)
    for wts in weekly_summaries:
        db.delete(wts)
    
    # 11. Elimina DailyReadinessMetrics
    daily_readiness = db.query(DailyReadinessMetrics).filter(
        DailyReadinessMetrics.user_id == user_id
    ).all()
    deleted_counts['daily_readiness_metrics'] = len(daily_readiness)
    for drm in daily_readiness:
        db.delete(drm)
    
    # 12. Elimina DailyPerformanceMetrics
    daily_performance = db.query(DailyPerformanceMetrics).filter(
        DailyPerformanceMetrics.user_id == user_id
    ).all()
    deleted_counts['daily_performance_metrics'] = len(daily_performance)
    for dpm in daily_performance:
        db.delete(dpm)
    
    # 13. Elimina MetricsPendingJob
    metrics_jobs = db.query(MetricsPendingJob).filter(
        MetricsPendingJob.user_id == user_id
    ).all()
    deleted_counts['metrics_pending_jobs'] = len(metrics_jobs)
    for mj in metrics_jobs:
        db.delete(mj)
    
    # 14. Elimina PerformanceMetrics
    performance_metrics = db.query(PerformanceMetrics).filter(
        PerformanceMetrics.user_id == user_id
    ).all()
    deleted_counts['performance_metrics'] = len(performance_metrics)
    for pm in performance_metrics:
        db.delete(pm)
    
    # 15. Elimina OAuthAccount
    oauth_accounts = db.query(OAuthAccount).filter(OAuthAccount.user_id == user_id).all()
    deleted_counts['oauth_accounts'] = len(oauth_accounts)
    for oa in oauth_accounts:
        db.delete(oa)
    
    # 16. Elimina UserProfile
    user_profiles = db.query(UserProfile).filter(UserProfile.user_id == user_id).all()
    deleted_counts['user_profiles'] = len(user_profiles)
    for up in user_profiles:
        db.delete(up)
    
    # NOTA: Non eliminiamo l'utente stesso (User) né i log (AIResponseLog)
    # L'utente rimane nel database, solo i suoi dati vengono puliti
    
    return deleted_counts


def clean_all_data(db: Session):
    """
    Elimina TUTTE le righe da tutte le tabelle del database,
    preservando solo i log (ai_response_logs).
    L'ordine di eliminazione rispetta le foreign key constraints.
    """
    print("Pulizia COMPLETA del database (tutte le tabelle)")
    
    # Contatori per statistiche
    deleted_counts = {}
    
    # Ordine di eliminazione rispettando le foreign key constraints
    
    # 1. Elimina TrainingMetrics (collegati a workout_sessions o strava_activities)
    training_metrics = db.query(TrainingMetrics).all()
    deleted_counts['training_metrics'] = len(training_metrics)
    for tm in training_metrics:
        db.delete(tm)
    
    # 2. Elimina WorkoutSessions
    workout_sessions = db.query(WorkoutSession).all()
    deleted_counts['workout_sessions'] = len(workout_sessions)
    for ws in workout_sessions:
        db.delete(ws)
    
    # 3. Elimina StravaActivities
    strava_activities = db.query(StravaActivity).all()
    deleted_counts['strava_activities'] = len(strava_activities)
    for sa in strava_activities:
        db.delete(sa)
    
    # 4. Elimina StravaSyncJobs
    strava_sync_jobs = db.query(StravaSyncJob).all()
    deleted_counts['strava_sync_jobs'] = len(strava_sync_jobs)
    for sj in strava_sync_jobs:
        db.delete(sj)
    
    # 5. Elimina StravaWebhooks
    strava_webhooks = db.query(StravaWebhook).all()
    deleted_counts['strava_webhooks'] = len(strava_webhooks)
    for sw in strava_webhooks:
        db.delete(sw)
    
    # 6. Elimina StravaAccount
    strava_accounts = db.query(StravaAccount).all()
    deleted_counts['strava_accounts'] = len(strava_accounts)
    for sa in strava_accounts:
        db.delete(sa)
    
    # 7. Elimina CalendarEvents
    calendar_events = db.query(CalendarEvent).all()
    deleted_counts['calendar_events'] = len(calendar_events)
    for ce in calendar_events:
        db.delete(ce)
    
    # 8. Elimina Workouts
    workouts = db.query(Workout).all()
    deleted_counts['workouts'] = len(workouts)
    for w in workouts:
        db.delete(w)
    
    # 9. Elimina PlanVersions
    plan_versions = db.query(PlanVersion).all()
    deleted_counts['plan_versions'] = len(plan_versions)
    for pv in plan_versions:
        db.delete(pv)
    
    # 10. Elimina WorkoutPlans
    workout_plans = db.query(WorkoutPlan).all()
    deleted_counts['workout_plans'] = len(workout_plans)
    for wp in workout_plans:
        db.delete(wp)
    
    # 11. Elimina WeeklyTrainingSummaries
    weekly_summaries = db.query(WeeklyTrainingSummary).all()
    deleted_counts['weekly_training_summaries'] = len(weekly_summaries)
    for wts in weekly_summaries:
        db.delete(wts)
    
    # 12. Elimina DailyReadinessMetrics
    daily_readiness = db.query(DailyReadinessMetrics).all()
    deleted_counts['daily_readiness_metrics'] = len(daily_readiness)
    for drm in daily_readiness:
        db.delete(drm)
    
    # 13. Elimina DailyPerformanceMetrics
    daily_performance = db.query(DailyPerformanceMetrics).all()
    deleted_counts['daily_performance_metrics'] = len(daily_performance)
    for dpm in daily_performance:
        db.delete(dpm)
    
    # 14. Elimina MetricsPendingJob
    metrics_jobs = db.query(MetricsPendingJob).all()
    deleted_counts['metrics_pending_jobs'] = len(metrics_jobs)
    for mj in metrics_jobs:
        db.delete(mj)
    
    # 15. Elimina PerformanceMetrics
    performance_metrics = db.query(PerformanceMetrics).all()
    deleted_counts['performance_metrics'] = len(performance_metrics)
    for pm in performance_metrics:
        db.delete(pm)
    
    # 16. Elimina OAuthAccount
    oauth_accounts = db.query(OAuthAccount).all()
    deleted_counts['oauth_accounts'] = len(oauth_accounts)
    for oa in oauth_accounts:
        db.delete(oa)
    
    # 17. Elimina UserProfile
    user_profiles = db.query(UserProfile).all()
    deleted_counts['user_profiles'] = len(user_profiles)
    for up in user_profiles:
        db.delete(up)
    
    # 18. Elimina User (ultimo, dopo tutte le dipendenze)
    users = db.query(User).all()
    deleted_counts['users'] = len(users)
    for u in users:
        db.delete(u)
    
    # NOTA: Non eliminiamo i log (AIResponseLog)
    # I log vengono preservati per audit e debugging
    
    return deleted_counts


def main():
    """Funzione principale"""
    parser = argparse.ArgumentParser(
        description='Pulisce i dati dal database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi:
  # Cancella dati di un utente specifico
  python scripts/clean_user_data.py --utente user@example.com
  
  # Cancella dati di un utente senza conferma
  python scripts/clean_user_data.py --utente user@example.com --no-confirm
  
  # Cancella TUTTO il database
  python scripts/clean_user_data.py --all
  
  # Cancella TUTTO il database senza conferma
  python scripts/clean_user_data.py --all --no-confirm
        """
    )
    parser.add_argument('--utente', type=str, metavar='EMAIL',
                       help='Email dell\'utente da pulire (obbligatorio se non si usa --all)')
    parser.add_argument('--all', action='store_true',
                       help='Cancella TUTTE le righe dal database (tranne ai_response_logs)')
    parser.add_argument('--no-confirm', action='store_true', 
                       help='Esegue la pulizia senza chiedere conferma')
    args = parser.parse_args()
    
    # Validazione argomenti
    if not args.all and not args.utente:
        parser.error("Devi specificare --utente EMAIL oppure --all")
    
    if args.all and args.utente:
        parser.error("Non puoi usare --all e --utente insieme")
    
    db = SessionLocal()
    try:
        if args.all:
            # Modalità cancellazione completa
            print("=" * 60)
            print("⚠️  CANCELLAZIONE COMPLETA DATABASE")
            print("=" * 60)
            print("Questa operazione eliminerà TUTTE le righe da TUTTE le tabelle")
            print("(tranne ai_response_logs che vengono preservati)")
            print()
            
            # Chiedi conferma (se non è stata passata l'opzione --no-confirm)
            if not args.no_confirm:
                response = input("⚠️  Sei ASSOLUTAMENTE sicuro di voler eliminare TUTTO? (scrivi 'ELIMINA TUTTO' per confermare): ")
                if response != 'ELIMINA TUTTO':
                    print("Operazione annullata.")
                    return 0
            
            print()
            print("Inizio cancellazione completa...")
            print("-" * 60)
            
            # Esegui la pulizia completa
            deleted_counts = clean_all_data(db)
            
            # Commit delle modifiche
            db.commit()
            
            print("-" * 60)
            print("✅ Cancellazione completa terminata!")
            print()
            print("Statistiche eliminazioni:")
            print("-" * 60)
            total = 0
            for table, count in deleted_counts.items():
                if count > 0:
                    print(f"  {table}: {count}")
                    total += count
            print("-" * 60)
            print(f"  TOTALE: {total} record eliminati")
            print()
            print("ℹ️  NOTA: I log (ai_response_logs) sono stati preservati.")
            
        else:
            # Modalità cancellazione utente specifico
            user_email = args.utente
            
            print("=" * 60)
            print("PULIZIA DATI UTENTE")
            print("=" * 60)
            print(f"Email utente: {user_email}")
            print()
            
            # Trova l'utente
            user = db.query(User).filter(User.email == user_email).first()
            
            if not user:
                print(f"❌ ERRORE: Utente con email '{user_email}' non trovato nel database.")
                return 1
            
            print(f"✅ Utente trovato: {user.name} (ID: {user.id})")
            print()
            
            # Chiedi conferma (se non è stata passata l'opzione --no-confirm)
            if not args.no_confirm:
                response = input("⚠️  Sei sicuro di voler eliminare TUTTI i dati di questo utente? (sì/no): ")
                if response.lower() not in ['sì', 'si', 'yes', 'y', 's']:
                    print("Operazione annullata.")
                    return 0
            
            print()
            print("Inizio pulizia dati...")
            print("-" * 60)
            
            # Esegui la pulizia
            deleted_counts = clean_user_data(db, user.id)
            
            # Commit delle modifiche
            db.commit()
            
            print("-" * 60)
            print("✅ Pulizia completata!")
            print()
            print("Statistiche eliminazioni:")
            print("-" * 60)
            total = 0
            for table, count in deleted_counts.items():
                if count > 0:
                    print(f"  {table}: {count}")
                    total += count
            print("-" * 60)
            print(f"  TOTALE: {total} record eliminati")
            print()
            print("ℹ️  NOTA: L'utente e i log (ai_response_logs) sono stati preservati.")
        
        return 0
        
    except Exception as e:
        db.rollback()
        print(f"❌ ERRORE durante la pulizia: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    finally:
        db.close()


if __name__ == "__main__":
    exit(main())

