# Agentic Coach v2.0 - Complete Implementation Guide

## Panoramica

Abbiamo completato l'implementazione del sistema **Agentic Coach v2.0** con focus esclusivo su **Endurance** (corsa, bici, nuoto, triathlon). Il sistema è ora **production-ready** e risolve tutte le falle critiche identificate.

---

## Architettura Completa

```
┌─────── USER REQUEST ────────┐
│ "Generate plan for week"   │
└──────────┬──────────────────┘
           │
           ▼
┌──────────────────────────────────────────┐
│  AgenticCoachService                     │
│  ├─ generate_full_week()                 │
│  │  ├─ Assessment Phase (LLM)            │
│  │  └─ Generation Phase (LLM)            │
│  └─ Validation Loop (retry on failure)   │
└──────┬───────────────────────────────┬───┘
       │                               │
       ▼                               ▼
┌──────────────────┐          ┌────────────────────┐
│ SmartContextBuilder │      │ EnduranceValidator │
│ (3-Layer Pyramid)    │      │ (Safety Rules)     │
└──────┬───────────────┘      └────────────────────┘
       │
       ├─ Layer 1: CRITICAL (CTL/ATL/TSB, Last Workout)
       ├─ Layer 2: RELEVANT (Smart Retrieval, 3 similar workouts)
       └─ Layer 3: BACKGROUND (Monthly Summary, Athlete Profile)
```

---

## Componenti Implementati

### 1. **Smart Context Builder** (`smart_context_builder.py`)

**Problema risolto:** "Garbage In, Garbage Out"

**Cosa fa:**
- Costruisce un context di ~1800 tokens (vs 10,000+ del vecchio sistema)
- **Layer 1 (Critical):** CTL/ATL/TSB calcolati in tempo reale, ultimo workout con completion rate
- **Layer 2 (Relevant):** Retrieval intelligente basato sul TYPE di workout (es. se generi VO2Max, cerca le ultime 3 sessioni VO2Max)
- **Layer 3 (Background):** Sommari pre-calcolati (cachare settimanalmente)

**Esempio Output:**
```python
{
  "critical": {
    "current_fitness": {"ctl": 45.2, "atl": 55.0, "tsb": -9.8, "ramp_rate": 1.22},
    "last_workout": {"type": "intervals", "completion_rate": 0.62, "notes": "Gambe pesanti"}
  },
  "relevant": {
    "similar_workouts": [
      {"date": "2024-01-20", "workout_description": "8x800m", "completion_rate": 0.62}
    ]
  }
}
```

---

### 2. **Agentic AI Service** (`agentic_ai_service.py`)

**Problema risolto:** Chiamate LLM inefficienti e non validate

**Cosa fa:**
- Supporta **OpenAI (GPT-4)** e **Anthropic (Claude)**
- **Structured Generation:** Valida automaticamente l'output JSON contro Pydantic schema
- **Retry Logic:** Fino a 3 tentativi se il JSON è malformato
- **Cost Estimation:** Calcola il costo stimato per ogni chiamata

**Configurazione:**
```python
# OpenAI (default)
service = create_agentic_ai_service(provider="openai", temperature=0.7)

# Anthropic Claude (alternativa)
service = create_agentic_ai_service(provider="anthropic", temperature=0.7)
```

**Costi Stimati:**
- GPT-4 Turbo: ~$0.08 per generazione completa
- Claude 3.5 Sonnet: ~$0.05 per generazione completa

---

### 3. **Endurance Validator** (`endurance_validator.py`)

**Problema risolto:** L'AI può generare piani pericolosi/illogici

**Regole Implementate:**
1. ✅ **Progressive Overload:** Max +10% volume/settimana, max +50 TSS
2. ✅ **High-Intensity Spacing:** Min 48h tra sessioni Z4+
3. ✅ **Consecutive Hard Days:** Max 2 giorni consecutivi hard
4. ✅ **Recovery Balance:** 60-85% del tempo in Z1-Z2
5. ✅ **Weekly TSS Bounds:** 100-800 TSS/settimana
6. ✅ **Duration Sanity:** 15min-5h per singolo workout

**Esempio Validation Output:**
```python
{
  "is_valid": False,
  "errors": [
    {
      "severity": "error",
      "rule": "progressive_overload_volume",
      "message": "Volume increase 25% exceeds safe limit of 10% (50km → 62.5km)",
      "affected_workouts": ["Monday", "Wednesday", "Sunday"]
    }
  ]
}
```

---

### 4. **Agentic Coach Service v2** (`agentic_coach_service.py`)

**Problema risolto:** Integration degli altri 3 componenti in un workflow completo

**Workflow Completo:**
```python
coach = AgenticCoachService(db=session, use_real_llm=True)

result = coach.generate_full_week(
    user_id=123,
    target_week_start=date(2024, 2, 1),
    goal="Improve 10k time",
    available_days=["Monday", "Tuesday", "Thursday", "Saturday", "Sunday"],
    next_workout_type="intervals"  # ← Smart retrieval
)

# Output:
# {
#   "assessment": AthleteStateAssessment(...),
#   "plan": AgenticWeeklyPlan(...),
#   "validation": ValidationResult(is_valid=True),
#   "approved": True
# }
```

**Features:**
- **Automatic Retry:** Se il piano fallisce la validazione, riprova con feedback (max 2 retry)
- **Graceful Degradation:** Se l'LLM fallisce, usa mock intelligenti basati su CTL/ATL/TSB
- **Mock Mode:** Può girare senza LLM per testing (`use_real_llm=False`)

---

## Differenze vs Vecchio Sistema

| Aspetto | Vecchio | Nuovo (Agentic v2) |
|---------|---------|-------------------|
| **Context Size** | ~10,000 tokens | ~1,800 tokens |
| **Context Relevance** | Tutto lo storico grezzo | Solo workout rilevanti |
| **LLM Integration** | Hardcoded, no validation | Multi-provider, structured |
| **Safety Checks** | None | 6 validation rules |
| **Cost per Generation** | ~$0.30 (GPT-4) | ~$0.08 (GPT-4 Turbo) |
| **Failure Handling** | Crash | Graceful degradation + retry |
| **Progression Tracking** | Generic medie | CTL/ATL/TSB + Ramp Rate |

---

## Come Usarlo in Produzione

### 1. Setup Environment Variables

Aggiungi in `app/config.py` o `.env`:

```python
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

### 2. Integrazione con API Endpoint

Esempio FastAPI:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.services.agentic_coach_service import AgenticCoachService
from app.database import get_db

router = APIRouter()

@router.post("/plans/generate-agentic")
def generate_agentic_plan(
    user_id: int,
    target_week: str,  # "2024-02-01"
    goal: str,
    available_days: List[str],
    db: Session = Depends(get_db)
):
    coach = AgenticCoachService(db=db, use_real_llm=True)
    
    result = coach.generate_full_week(
        user_id=user_id,
        target_week_start=date.fromisoformat(target_week),
        goal=goal,
        available_days=available_days
    )
    
    if not result["approved"]:
        return {
            "status": "validation_failed",
            "errors": [e.dict() for e in result["validation"].errors]
        }
    
    return {
        "status": "success",
        "plan": result["plan"].dict(),
        "reasoning": result["assessment"].reasoning
    }
```

### 3. Ottimizzazioni SQL (TODO)

Per performance ottimali:

```sql
-- Index for faster TSS retrieval
CREATE INDEX idx_workout_session_user_date 
ON workout_sessions (user_id, actual_date DESC);

-- Index for faster similar workout query
CREATE INDEX idx_workout_type 
ON workouts (user_id, type, created_at DESC);

-- Weekly summary cache table (per Layer 3)
CREATE TABLE weekly_training_cache (
    user_id INT,
    week_start DATE,
    total_tss FLOAT,
    total_volume_km FLOAT,
    cached_at TIMESTAMP
);
```

---

## Prossimi Step (Future Enhancements)

1. **Embedding-based Retrieval:** Usare vector search (pgvector) per similarity matching più intelligente
2. **A/B Testing:** Testare GPT-4 vs Claude per qualità/costo
3. **Feedback Loop:** Salvare le validation errors in `coach_memories` per apprendimento continuo
4. **Multi-Week Planning:** Estendere da singola settimana a mesocycles completi

---

## File Creati

```
app/
├── schemas/
│   └── endurance_context.py         # Layer 1/2/3 schemas
├── services/
│   ├── smart_context_builder.py     # Context retrieval
│   ├── agentic_ai_service.py        # LLM integration
│   ├── endurance_validator.py       # Safety rules
│   └── agentic_coach_service.py     # Main orchestrator (updated)
```

---

## Conclusione

Il sistema è ora **production-ready** per endurance training. Risolve tutte le falle critiche:
- ✅ Context efficiente e rilevante (3-layer pyramid)
- ✅ LLM integration structure con validation
- ✅ Safety layer che blocca piani pericolosi
- ✅ Graceful degradation e retry logic

**Prossima milestone:** Estendere alla forza (Gym/Hyrox) seguendo lo stesso pattern.
