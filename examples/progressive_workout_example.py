#!/usr/bin/env python3
"""
Esempio di utilizzo delle API per piani di allenamento progressivi
"""

import httpx
import asyncio
from typing import Dict, Any
from datetime import datetime, date, timedelta


class ProgressiveWorkoutExample:
    def __init__(self, base_url: str = "http://localhost:8000", access_token: str = None):
        self.base_url = base_url
        self.access_token = access_token
        self.client = httpx.AsyncClient()
    
    def set_auth_token(self, token: str):
        """Imposta il token di autenticazione"""
        self.access_token = token
    
    def get_headers(self) -> Dict[str, str]:
        """Ottiene gli header per le richieste autenticate"""
        if not self.access_token:
            raise ValueError("Access token not set. Call set_auth_token() first.")
        return {"Authorization": f"Bearer {self.access_token}"}
    
    async def create_progressive_plan(self, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """Crea un piano di allenamento progressivo"""
        response = await self.client.post(
            f"{self.base_url}/workouts/plans/generate-progressive",
            json=plan_data,
            headers=self.get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def generate_weekly_plan(self, week_data: Dict[str, Any]) -> Dict[str, Any]:
        """Genera piano per una settimana specifica"""
        response = await self.client.post(
            f"{self.base_url}/workouts/plans/generate-weekly",
            json=week_data,
            headers=self.get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def adapt_next_week(self, target_date: str, specific_focus: str = None) -> Dict[str, Any]:
        """Adatta automaticamente la prossima settimana"""
        request_data = {
            "target_date": target_date,
            "force_regeneration": False,
            "specific_focus": specific_focus
        }
        
        response = await self.client.post(
            f"{self.base_url}/workouts/plans/adapt-next-week",
            json=request_data,
            headers=self.get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def get_current_week_data(self) -> Dict[str, Any]:
        """Ottiene dati della settimana corrente"""
        response = await self.client.get(
            f"{self.base_url}/workouts/plans/current-week",
            headers=self.get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def get_performance_analysis(self, weeks_back: int = 4) -> Dict[str, Any]:
        """Ottiene analisi delle performance"""
        response = await self.client.get(
            f"{self.base_url}/workouts/plans/performance-analysis",
            params={"weeks_back": weeks_back},
            headers=self.get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def complete_workout(self, workout_id: int, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Completa un allenamento"""
        response = await self.client.post(
            f"{self.base_url}/workouts/{workout_id}/complete",
            json=session_data,
            headers=self.get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        """Chiude il client HTTP"""
        await self.client.aclose()


async def main():
    """Esempio completo di utilizzo"""
    example = ProgressiveWorkoutExample()
    
    try:
        # 1. Autenticazione (sostituisci con il tuo token)
        print("1. Impostando token di autenticazione...")
        example.set_auth_token("your-access-token-here")
        
        # 2. Crea piano progressivo
        print("\n2. Creando piano progressivo...")
        plan_data = {
            "sport_type": "running",
            "level": "intermediate",
            "goal": "Maratona di Roma",
            "target_date": "2024-04-21",
            "start_date": "2024-01-15",
            "weekly_hours": 8.0,
            "user_profile": {
                "age": 30,
                "experience_years": 3,
                "weekly_hours": 8.0,
                "weight": 70,
                "height": 175
            }
        }
        
        plan_result = await example.create_progressive_plan(plan_data)
        print(f"Piano creato: {plan_result['plan']['title']}")
        print(f"Prima settimana: {plan_result['first_week']['focus']}")
        
        # 3. Ottieni dati settimana corrente
        print("\n3. Ottenendo dati settimana corrente...")
        current_week = await example.get_current_week_data()
        print(f"Settimana corrente: {current_week['current_week']['week_number']}")
        print(f"Livello fitness: {current_week['fitness_level']['fatigue_level']}")
        
        # 4. Simula completamento allenamenti della settimana
        print("\n4. Simulando completamento allenamenti...")
        workouts = current_week['current_week']['workouts']
        for workout in workouts[:2]:  # Simula primi 2 allenamenti
            session_data = {
                "workout_id": workout['id'],
                "actual_date": datetime.now().isoformat(),
                "duration_minutes": workout['duration_minutes'],
                "avg_hr": 150.0,
                "max_hr": 165.0,
                "perceived_exertion": 6,
                "notes": "Allenamento completato con successo"
            }
            
            try:
                result = await example.complete_workout(workout['id'], session_data)
                print(f"Allenamento {workout['id']} completato")
            except Exception as e:
                print(f"Errore completamento allenamento {workout['id']}: {e}")
        
        # 5. Ottieni analisi performance
        print("\n5. Analizzando performance...")
        performance = await example.get_performance_analysis()
        print(f"Completion rate: {performance['completion_rate']}%")
        print(f"Fatigue level: {performance['fatigue_level']}")
        print(f"Intensity trend: {performance['intensity_trend']}")
        
        # 6. Adatta prossima settimana
        print("\n6. Adattando prossima settimana...")
        next_week = await example.adapt_next_week("2024-04-21")
        print(f"Prossima settimana: {next_week['focus']}")
        print(f"Adattamenti: {next_week['adaptations']['rationale']}")
        
        # 7. Genera settimana specifica
        print("\n7. Generando settimana specifica...")
        week_data = {
            "week_number": 5,
            "target_date": "2024-04-21",
            "previous_week_data": {
                "week": 4,
                "completion_rate": 100,
                "avg_rpe": 6.5,
                "workouts_completed": 4
            },
            "current_fitness_level": {
                "completion_rate": 95,
                "avg_intensity": 6.2,
                "consistency": 90,
                "fatigue_level": "low"
            }
        }
        
        specific_week = await example.generate_weekly_plan(week_data)
        print(f"Settimana {specific_week['week']}: {specific_week['focus']}")
        print(f"Workouts: {len(specific_week['workouts'])}")
        
    except Exception as e:
        print(f"Errore: {e}")
    
    finally:
        await example.close()


if __name__ == "__main__":
    print("=== Esempio Piani di Allenamento Progressivi ===")
    print("Assicurati di aver configurato il token di accesso!")
    print("Modifica 'your-access-token-here' con un token valido")
    print()
    
    asyncio.run(main())

