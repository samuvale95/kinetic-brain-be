"""
Servizio per gestire query e selezione esercizi dalla tabella exercises
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, text
from app.models.exercise import Exercise
from loguru import logger
import random


class ExerciseService:
    """Servizio per gestire esercizi"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_available_equipment(self) -> List[str]:
        """
        Restituisce lista unica di attrezzi disponibili dalla tabella exercises
        
        Returns:
            Lista di attrezzi (equipmentType enum values)
        """
        try:
            # Query per ottenere tutti i valori unici di equipment
            # Usa cast a text direttamente in SQL per evitare problemi di validazione SQLAlchemy
            # Questo bypassa la validazione enum di SQLAlchemy e legge direttamente dal database
            result = self.db.execute(
                text("SELECT DISTINCT equipment::text FROM exercises WHERE equipment IS NOT NULL")
            )
            equipment = [row[0] for row in result]
            return sorted(equipment)
        except Exception as e:
            logger.error(f"Error getting available equipment: {e}")
            return []
    
    def get_exercises_by_criteria(
        self,
        category: Optional[str] = None,
        level: Optional[str] = None,
        available_equipment: Optional[List[str]] = None,
        target_muscles: Optional[List[str]] = None,
        mechanic: Optional[str] = None,
        force: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Exercise]:
        """
        Query esercizi per criteri multipli
        
        Args:
            category: Categoria (strength, stretching, etc.)
            level: Livello (beginner, intermediate, expert)
            available_equipment: Lista attrezzi disponibili
            target_muscles: Lista gruppi muscolari target
            mechanic: Mechanic type (compound, isolation)
            force: Force type (pull, push, static)
            limit: Limite risultati
        
        Returns:
            Lista di Exercise
        """
        try:
            query = self.db.query(Exercise)
            
            # Filtro categoria
            if category:
                query = query.filter(Exercise.category == category)
            
            # Filtro livello
            if level:
                query = query.filter(Exercise.level == level)
            
            # Filtro attrezzi disponibili
            if available_equipment:
                query = query.filter(Exercise.equipment.in_(available_equipment))
            
            # Filtro gruppi muscolari (primary o secondary)
            if target_muscles:
                # Crea condizioni OR per ogni muscolo (può essere in primary o secondary)
                # Usa l'operatore PostgreSQL @> (contains) per verificare se l'array contiene il muscolo
                from sqlalchemy.dialects.postgresql import ARRAY
                muscle_conditions = []
                for muscle in target_muscles:
                    # Verifica se il muscolo è in primary_muscles o secondary_muscles
                    # Usa cast per convertire il muscolo in array e verifica se è contenuto
                    muscle_conditions.append(
                        Exercise.primary_muscles.contains([muscle])
                    )
                    muscle_conditions.append(
                        Exercise.secondary_muscles.contains([muscle])
                    )
                if muscle_conditions:
                    query = query.filter(or_(*muscle_conditions))
            
            # Filtro mechanic
            if mechanic:
                query = query.filter(Exercise.mechanic == mechanic)
            
            # Filtro force
            if force:
                query = query.filter(Exercise.force == force)
            
            # Limite risultati
            if limit:
                query = query.limit(limit)
            
            return query.all()
        
        except Exception as e:
            logger.error(f"Error querying exercises: {e}")
            return []
    
    def select_exercises_for_workout(
        self,
        category: str,
        level: str,
        available_equipment: List[str],
        target_muscles: List[str],
        num_exercises: int,
        focus_type: str = "sport_plus_balance",
        mechanic: Optional[str] = None,
        exclude_exercise_ids: Optional[List[str]] = None
    ) -> List[Exercise]:
        """
        Logica di selezione bilanciata esercizi (sport-specifico + generale)
        
        Args:
            category: Categoria esercizi (strength, stretching)
            level: Livello utente
            available_equipment: Attrezzi disponibili
            target_muscles: Gruppi muscolari target per lo sport
            num_exercises: Numero esercizi da selezionare
            focus_type: Tipo focus ("sport_specific", "balanced", "sport_plus_balance")
            mechanic: Mechanic type (opzionale, per strength)
            exclude_exercise_ids: Lista ID esercizi da escludere (per varietà)
        
        Returns:
            Lista di Exercise selezionati
        """
        try:
            # Calcola distribuzione esercizi
            if focus_type == "sport_specific":
                sport_specific_ratio = 1.0
                balanced_ratio = 0.0
            elif focus_type == "balanced":
                sport_specific_ratio = 0.0
                balanced_ratio = 1.0
            else:  # sport_plus_balance
                sport_specific_ratio = 0.6
                balanced_ratio = 0.4
            
            num_sport_specific = int(num_exercises * sport_specific_ratio)
            num_balanced = num_exercises - num_sport_specific
            
            selected_exercises = []
            exclude_ids = exclude_exercise_ids or []
            
            # 1. Seleziona esercizi sport-specifici (target muscles)
            if num_sport_specific > 0 and target_muscles:
                sport_specific = self.get_exercises_by_criteria(
                    category=category,
                    level=level,
                    available_equipment=available_equipment,
                    target_muscles=target_muscles,
                    mechanic=mechanic,
                    limit=num_sport_specific * 3  # Prendi più opzioni per varietà
                )
                
                # Filtra esclusi e randomizza
                sport_specific = [e for e in sport_specific if str(e.id) not in exclude_ids]
                random.shuffle(sport_specific)
                selected_exercises.extend(sport_specific[:num_sport_specific])
                exclude_ids.extend([str(e.id) for e in selected_exercises])
            
            # 2. Seleziona esercizi bilanciati (tutti i gruppi muscolari)
            if num_balanced > 0:
                # Per bilanciamento, prendi esercizi che coprono vari gruppi muscolari
                balanced = self.get_exercises_by_criteria(
                    category=category,
                    level=level,
                    available_equipment=available_equipment,
                    target_muscles=None,  # Non filtrare per muscoli specifici
                    mechanic=mechanic,
                    limit=num_balanced * 3
                )
                
                # Filtra esclusi e randomizza
                balanced = [e for e in balanced if str(e.id) not in exclude_ids]
                random.shuffle(balanced)
                selected_exercises.extend(balanced[:num_balanced])
            
            # Se non abbiamo abbastanza esercizi, riempi con qualsiasi disponibile
            if len(selected_exercises) < num_exercises:
                remaining = num_exercises - len(selected_exercises)
                all_available = self.get_exercises_by_criteria(
                    category=category,
                    level=level,
                    available_equipment=available_equipment,
                    mechanic=mechanic,
                    limit=remaining * 2
                )
                all_available = [e for e in all_available if str(e.id) not in exclude_ids]
                random.shuffle(all_available)
                selected_exercises.extend(all_available[:remaining])
            
            # Randomizza ordine finale
            random.shuffle(selected_exercises)
            
            return selected_exercises[:num_exercises]
        
        except Exception as e:
            logger.error(f"Error selecting exercises for workout: {e}")
            return []

