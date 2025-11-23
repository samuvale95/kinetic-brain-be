# Guida Completa: Sessioni di Allenamento per Triathlon per Livelli
## Struttura per LLM - Principiante, Intermedio, Avanzato, Elite

---

## Table of Contents

1. [Introduzione](#introduzione)
2. [Definizione dei 4 Livelli](#definizione-dei-4-livelli)
3. [Sessioni Settimanali per Distanza](#sessioni-settimanali-per-distanza)
4. [Strutture Settimanali Tipo](#strutture-settimanali-tipo)
5. [Distribuzione Discipline](#distribuzione-discipline)
6. [Logica LLM - Pseudocodice](#logica-llm---pseudocodice)
7. [Raccomandazioni Pratiche](#raccomandazioni-pratiche)

---

## Introduzione

Questo documento definisce il **numero di sessioni settimanali** consigliate per atleti di triathlon in **4 categorie di livello**:
- **Principiante**: 0-1 stagione, nessuna gara completata
- **Intermedio**: 1-3 stagioni, gare Sprint/Olympic completate
- **Avanzato**: 3+ stagioni, gare lunghe (Olympic/70.3), atleta competitivo
- **Elite**: Top age group, semi-pro/federale, podio come target

L'obiettivo è fornire **strutture realistiche** che un'app LLM possa generare automaticamente.

---

## Definizione dei 4 Livelli

### Principiante
- **Esperienza**: < 1 stagione, oppure ritorno dopo pausa > 2 anni
- **Competizioni**: Nessuna completata, oppure 1-2 Sprint
- **Allenamento**: Irregolare prima del programma
- **Obiettivo Gara**: Completare Sprint/Olympic
- **Tempo Disponibile**: 4-6 ore/settimana
- **Mentalità**: "Voglio finire sano e divertirmi"

### Intermedio
- **Esperienza**: 1-3 stagioni complete
- **Competizioni**: Completate 2-5 gare (Sprint e Olympic)
- **Allenamento**: Regolare in tutte e 3 le discipline
- **Obiettivo Gara**: Finire Olympic in ~2:45-3:00; Sprint sub 1:30
- **Tempo Disponibile**: 6-8 ore/settimana
- **Mentalità**: "Voglio migliorare il mio tempo e posizionamento"

### Avanzato
- **Esperienza**: 3-5+ stagioni, noto nel circolo locale
- **Competizioni**: Completate 10+ gare, incluse 70.3
- **Allenamento**: Strutturato, prioritizzate discipline
- **Obiettivo Gara**: Podio locale Olympic; Top 20% 70.3
- **Tempo Disponibile**: 8-12 ore/settimana
- **Mentalità**: "Voglio performance competitive, potenziale podio"

### Elite
- **Esperienza**: 5+ stagioni, atleta noto a livello regionale/nazionale
- **Competizioni**: Podium finisher in gare di qualità
- **Allenamento**: Professionalmente strutturato, periodizzazione spinta
- **Obiettivo Gara**: Podio assoluto, qualificazione Ironman, mondiale age group
- **Tempo Disponibile**: 14-20+ ore/settimana
- **Mentalità**: "Performance massimale, goal podio/qualificazione"

---

## Sessioni Settimanali per Distanza

### SPRINT (750m swim / 20km bike / 5km run)

| Livello | Nuoto | Bici | Corsa | Strength | Brick | Total Sessioni |
|---------|-------|------|-------|----------|-------|----------------|
| **Principiante** | 2 | 2 | 2 | 0-1 | 0 | 4-6 |
| **Intermedio** | 2-3 | 2-3 | 2-3 | 1 | 0-1 | 6-8 |
| **Avanzato** | 3 | 3 | 3 | 1 | 1 | 8-10 |
| **Elite** | 4-5 | 4 | 4 | 1-2 | 1-2 | 11-15 |

### OLYMPIC (1.5km swim / 40km bike / 10km run)

| Livello | Nuoto | Bici | Corsa | Strength | Brick | Total Sessioni |
|---------|-------|------|-------|----------|-------|----------------|
| **Principiante** | 2 | 2 | 2 | 0-1 | 0-1 | 4-6 |
| **Intermedio** | 2-3 | 2-3 | 2-3 | 1 | 1 | 7-9 |
| **Avanzato** | 3-4 | 3-4 | 3-4 | 1 | 1-2 | 9-12 |
| **Elite** | 5-6 | 5-6 | 4-5 | 1-2 | 2 | 14-18 |

### 70.3 (1.9km swim / 90km bike / 21km run)

| Livello | Nuoto | Bici | Corsa | Strength | Brick | Total Sessioni |
|---------|-------|------|-------|----------|-------|----------------|
| **Principiante** | 2-3 | 3 | 2-3 | 0-1 | 0-1 | 5-8 |
| **Intermedio** | 3 | 3-4 | 3 | 1 | 1 | 8-11 |
| **Avanzato** | 3-4 | 4-5 | 4 | 1 | 2 | 11-15 |
| **Elite** | 5-6 | 6-7 | 5-6 | 2 | 2-3 | 16-21 |

### IRONMAN (3.8km swim / 180km bike / 42km run)

| Livello | Nuoto | Bici | Corsa | Strength | Brick | Total Sessioni |
|---------|-------|------|-------|----------|-------|----------------|
| **Principiante** | 2-3 | 3-4 | 2-3 | 0-1 | 0-1 | 5-10 |
| **Intermedio** | 3-4 | 4-5 | 3-4 | 1 | 1-2 | 10-15 |
| **Avanzato** | 4-5 | 5-6 | 4-5 | 1 | 2-3 | 14-19 |
| **Elite** | 6-7 | 7-8 | 5-6 | 2 | 3 | 20-26 |

---

## Strutture Settimanali Tipo

### PRINCIPIANTE - SPRINT (4-6 ore/settimana)

```
LUNEDI: RIPOSO o Mobilità (15 min)

MARTEDI: Nuoto (45 min)
- Tecnica e volume base
- 2000m total
- Sessione: Warm + Main + Cool (facile)

MERCOLEDI: Bici (50 min)
- Zone 1-2 facile
- No intensità

GIOVEDI: Corsa (35 min)
- Molto facile
- Forma, non velocità

VENERDI: RIPOSO

SABATO: Nuoto (45 min)
- Secondo toucamento
- Focus tecnica

DOMENICA: Bici (50 min) OR Corsa (40 min)
- Facile, recupero
- Sceglierne uno

TOTALE SESSIONI: 5 (2 nuoto, 2 bici, 1 corsa)
TOTALE ORE: 4.5-5.5h
CARATTERISTICHE:
- Niente intensità
- Niente brick
- Niente strength formale
- Goal: Adattamento, ritmo costante
```

### INTERMEDIO - OLYMPIC (6-8 ore/settimana)

```
LUNEDI: RIPOSO

MARTEDI: Bici Intervals (90 min)
- Warm 15 min
- Main: 3×8' @ Threshold
- Cool 15 min
- Sessione qualità

MERCOLEDI: Nuoto (50 min) + Strength (30 min)
- AM: Strength (squat, RDL, plank)
- RECOVERY 3h
- PM: Nuoto facile 1800m
- Double session

GIOVEDI: Corsa (40 min)
- Zone 2, facile

VENERDI: RIPOSO o Mobility (15 min)

SABATO: BRICK (90 min total)
- Bici 60 min Zone 2
- Corsa 25 min Tempo
- Sessione specifica gara

DOMENICA: Nuoto Lungo (60 min)
- 3000m easy
- Costruzione volume

TOTALE SESSIONI: 7 (2 nuoto, 2 bici, 1 corsa, 1 strength, 1 brick)
TOTALE ORE: 6.8-7.5h
CARATTERISTICHE:
- 1 sessione qualità per disciplina (es: bici intervals martedì)
- 1 brick settimanale
- 1 strength 1×/settimana
- Inizio distribuzione volume multi-sport
```

### AVANZATO - OLYMPIC (8-12 ore/settimana)

```
LUNEDI: RIPOSO

MARTEDI: Bici Intervals (100 min)
- 3×10' @ Threshold
- Plus warm/cool
- TSS ~120

MERCOLEDI: Corsa Intervalli (50 min)
- 4×5' @ 10K pace
- Plus warm/cool

GIOVEDI: Nuoto (60 min)
- 2500m con sessione qualità
- 6×100m race pace

VENERDI: RIPOSO o Mobilità (20 min)

SABATO: BRICK LUNGO (130 min total)
- Bici 80 min Zone 2-3
- Corsa 40 min Tempo
- Transizione pratica

DOMENICA: Nuoto + Corsa (oppure doppia)
- Nuoto 45 min easy, OR
- Corsa 60 min easy

MARTEDI ALT: Strength (35 min)
- OPPURE martedì doppio (bici intervals + corsa easy dopo)

TOTALE SESSIONI: 9-10 (3-4 nuoto, 3 bici, 3-4 corsa, 1 strength, 1-2 brick)
TOTALE ORE: 9-10.5h
CARATTERISTICHE:
- 2 sessioni qualità (bici + corsa)
- Nuoto frequente (3-4 toucamenti)
- Brick doppi possibili (ogni 2 settimane)
- 1 strength maintenance
- Inizia doppia sessione su giorni bassi-bassi (non hard+hard)
```

### AVANZATO - 70.3 (10-14 ore/settimana)

```
LUNEDI: RIPOSO

MARTEDI: Bici Intervals (110 min)
- 3×12' @ Threshold
- TSS ~140

MERCOLEDI: Strength (35 min) + Nuoto (50 min)
- AM: Strength full body
- RECOVERY 4h
- PM: Nuoto easy 2000m

GIOVEDI: Corsa Intervalli (60 min)
- 5×6' @ tempo
- TSS ~75

VENERDI: Bici Facile (50 min)
- Recovery Zone 1-2
- TSS ~35

SABATO: BRICK DOPPIO (150 min total)
- Bici 100 min Zone 2-3
- Corsa 45 min Tempo/medio
- TSS ~160

DOMENICA: Nuoto Lungo (75 min)
- 4000m easy
- Costruzione volume specifico 70.3

MERCOLEDI ALT: Corsa Facile (40 min)
- Se non fatta martedì

TOTALE SESSIONI: 11 (3-4 nuoto, 4 bici, 3-4 corsa, 1 strength, 1-2 brick)
TOTALE ORE: 10.5-12h
CARATTERISTICHE:
- 2 sessioni qualità dure (bici + corsa)
- Volume bici aumenta significativamente (70.3 specifico)
- 3-4 nuoto mantenuti (frequenza)
- 1 brick doppio principale
- 1 strength 1×/settimana
- Doppia sessione 1-2 giorni/settimana (strength+nuoto easy, bici+corsa)
```

### ELITE - OLYMPIC (14-18 ore/settimana)

```
LUNEDI: Nuoto (60 min) + Corsa (30 min)
- AM: Nuoto qualità 2500m (6×100m race pace)
- RECOVERY 3h
- PM: Corsa easy 30 min
- Double session

MARTEDI: Bici Intervals (120 min)
- Hard day
- 3×12' @ Threshold
- Plus warm/cool
- TSS ~150

MERCOLEDI: Strength (45 min) + Nuoto (45 min)
- AM: Strength power focus
- RECOVERY 4h
- PM: Nuoto easy 2000m

GIOVEDI: Corsa Intervalli (60 min)
- 6×5' @ 10K pace
- Plus warm/cool

VENERDI: Bici Facile (60 min) + Nuoto (45 min)
- AM: Bici recovery
- RECOVERY 3h
- PM: Nuoto technique

SABATO: BRICK DOPPIO (160 min total)
- Bici 100 min moderate (Zone 2-3)
- Corsa 50 min race pace equivalent
- TSS ~180

DOMENICA: Nuoto Lungo (90 min)
- 4500m steady
- Costruzione aerobica

MARTEDI ALT: Secondo Strength (30 min)
- Oppure bici doppio

TOTALE SESSIONI: 14-16 (5-6 nuoto, 5-6 bici, 4-5 corsa, 1-2 strength, 2 brick)
TOTALE ORE: 14-16h
CARATTERISTICHE:
- 2-3 sessioni qualità hard (bici intervals, corsa intervals)
- Nuoto frequentissimo (5-6 toucamenti)
- 2 brick settimanali (uno doppio, uno singles)
- 1-2 strength
- 4-5 doppi session giorni/settimana
- Back-to-back possibili su giorni low-low (easy bici + nuoto, nuoto + corsa easy)
```

### ELITE - 70.3 (16-22 ore/settimana)

```
LUNEDI: Nuoto (70 min) + Corsa (35 min)
- AM: Nuoto intervalli
- RECOVERY 3h
- PM: Corsa easy

MARTEDI: Bici Intervals (130 min)
- Hard session
- 4×12' @ Threshold
- TSS ~160

MERCOLEDI: Strength (45 min) + Nuoto (50 min)
- AM: Strength full complex
- RECOVERY 4-5h
- PM: Nuoto technique

GIOVEDI: Corsa Intervalli (70 min)
- 6×6' @ tempo
- TSS ~85

VENERDI: Bici (90 min)
- Moderate intensity
- Zone 2-3
- TSS ~100

SABATO: BRICK DOPPIO (180 min total)
- Bici 120 min (variato: base + tempo blocks)
- Corsa 55 min (race pace equivalent)
- TSS ~200+

DOMENICA: Nuoto Lungo (90 min)
- 4500m steady aerobico
- OU Doppio mattina: Nuoto (60 min) + Corsa (45 min)

TOTALE SESSIONI: 16-18 (6-7 nuoto, 5-6 bici, 4-5 corsa, 1-2 strength, 2-3 brick)
TOTALE ORE: 17-19h
CARATTERISTICHE:
- 2-3 sessioni hard (bici intervals, corsa intervals)
- Nuoto 6-7 toucamenti settimanali
- 2-3 brick (uno doppio lungo, altri singoli)
- 1-2 strength
- 5-6 doppi session giorni
- Back-to-back frequenti (3 coppie di doppi sessioni/settimana)
```

---

## Distribuzione Discipline

### Principi di Distribuzione per Livello

#### PRINCIPIANTE
**Priorità**: Uguaglianza freccia, adattamento corpo
- Nuoto: 2× settimanali (frequenza critica per tecnica)
- Bici: 2× settimanali
- Corsa: 1-2× settimanali
- Strength: 0 (opzionale mobilità)
- Rapporto: 40% nuoto, 40% bici, 20% corsa (per tempo/settimana)

#### INTERMEDIO
**Priorità**: Equilibrio con lieve focalizzazione su punti deboli
- Nuoto: 2-3× settimanali (minimo 2, frequenza)
- Bici: 2-3× settimanali
- Corsa: 2-3× settimanali
- Strength: 1× settimanale (obbligatorio)
- Rapporto volume: 25-30% nuoto, 40-45% bici, 25-30% corsa
- Brick: 0-1× (introduzione)

#### AVANZATO
**Priorità**: Volume bici massimizzato, frequenza nuoto mantenuta, qualità corsa
- Nuoto: 3-4× settimanali (frequenza critica, tecnica)
- Bici: 3-4× settimanali (volume massimo per distanza)
- Corsa: 3-4× settimanali (qualità + volume)
- Strength: 1-2× settimanali (manutenzione)
- Rapporto volume: 20% nuoto, 50% bici, 30% corsa
- Brick: 1-2× (pratica transizioni)

#### ELITE
**Priorità**: Massimizzazione volume tutte le discipline, periodizzazione spinta
- Nuoto: 5-7× settimanali (frequenza altissima, tecnica elite)
- Bici: 5-7× settimanali (volume massimo)
- Corsa: 4-6× settimanali (qualità > volume)
- Strength: 1-2× settimanali (specifico performance)
- Rapporto volume: 18-22% nuoto, 48-52% bici, 28-32% corsa
- Brick: 2-3× (race-specific)

---

## Logica LLM - Pseudocodice

### Input Required

```python
{
  "athlete_level": "PRINCIPIANTE|INTERMEDIO|AVANZATO|ELITE",
  "race_distance": "SPRINT|OLYMPIC|70.3|IRONMAN",
  "weeks_to_race": integer (4-52),
  "weekly_hours_available": float (4-25),
  "current_phase": "BASE|BUILD|PEAK|TAPER",
  "injury_constraints": list,
  "preference_strength": "YES|NO|MINIMAL",
  "preference_brick": "LOW|MEDIUM|HIGH"
}
```

### Generation Algorithm

```python
def generate_triathlon_plan(athlete_input):
    """
    Generate realistic triathlon training plan by level
    """
    
    # 1. VALIDATE inputs
    validate_time_available(athlete_input.level, 
                           athlete_input.weekly_hours,
                           athlete_input.race_distance)
    
    # 2. GET SESSION MATRIX for level+distance
    session_counts = get_session_matrix(
        level=athlete_input.athlete_level,
        distance=athlete_input.race_distance,
        phase=athlete_input.current_phase
    )
    # Returns: {swim: 2-3, bike: 3, run: 3, strength: 1, brick: 1}
    
    # 3. CALCULATE TIME PER SESSION (average)
    session_durations = allocate_time_per_session(
        total_hours=athlete_input.weekly_hours,
        session_counts=session_counts,
        level=athlete_input.athlete_level,
        distance=athlete_input.race_distance
    )
    # Returns: {swim_min: 50, bike_min: 75, run_min: 45, strength_min: 30, brick_min: 100}
    
    # 4. BUILD WEEK STRUCTURE
    week_skeleton = {
        'mon': ['REST'],
        'tue': ['BIKE_INTERVALS'],
        'wed': ['STRENGTH', 'SWIM_EASY'],
        'thu': ['RUN_INTERVALS'],
        'fri': ['REST'],
        'sat': ['BRICK'],
        'sun': ['SWIM_LONG']
    }
    
    # 5. ASSIGN INTENSITY per phase
    intensity_map = get_phase_intensity(
        phase=athlete_input.current_phase,
        level=athlete_input.athlete_level
    )
    # Returns: {BIKE_INTERVALS: 'THRESHOLD', RUN_INTERVALS: '10K_PACE', ...}
    
    # 6. ADD SESSION DETAILS
    for day, sessions in week_skeleton.items():
        for session_type in sessions:
            if session_type != 'REST':
                session_detail = build_session(
                    session_type=session_type,
                    duration_min=session_durations.get(session_type),
                    intensity=intensity_map.get(session_type),
                    level=athlete_input.athlete_level,
                    phase=athlete_input.current_phase
                )
                week_skeleton[day][session_type] = session_detail
    
    # 7. VALIDATE PLAN
    validation = validate_plan(
        plan=week_skeleton,
        total_hours=athlete_input.weekly_hours,
        level=athlete_input.athlete_level,
        acwr_target=get_acwr_target(athlete_input.current_phase)
    )
    
    if not validation.is_feasible:
        # Reduce strength or sessions if needed
        week_skeleton = adjust_plan(week_skeleton, validation.alerts)
    
    # 8. ADD RECOMMENDATIONS
    recommendations = generate_contextual_recommendations(
        level=athlete_input.athlete_level,
        phase=athlete_input.current_phase,
        weekly_hours=athlete_input.weekly_hours
    )
    
    return {
        'weekly_plan': week_skeleton,
        'total_sessions': sum([len(s) for s in week_skeleton.values() if s != ['REST']]),
        'total_hours': calculate_total_hours(week_skeleton),
        'analysis': {
            'swim_sessions': session_counts['swim'],
            'bike_sessions': session_counts['bike'],
            'run_sessions': session_counts['run'],
            'strength_sessions': session_counts['strength'],
            'brick_sessions': session_counts['brick']
        },
        'alerts': validation.alerts,
        'recommendations': recommendations
    }

def get_session_matrix(level, distance, phase):
    """
    Look-up table for session counts
    """
    
    matrix = {
        'PRINCIPIANTE': {
            'SPRINT': {
                'BASE': {'swim': 2, 'bike': 2, 'run': 2, 'strength': 0, 'brick': 0},
                'BUILD': {'swim': 2, 'bike': 2, 'run': 2, 'strength': 1, 'brick': 1},
                'PEAK': {'swim': 2, 'bike': 2, 'run': 2, 'strength': 0, 'brick': 1},
                'TAPER': {'swim': 2, 'bike': 1, 'run': 1, 'strength': 0, 'brick': 0}
            },
            'OLYMPIC': {
                'BASE': {'swim': 2, 'bike': 2, 'run': 2, 'strength': 0, 'brick': 0},
                'BUILD': {'swim': 2, 'bike': 2, 'run': 2, 'strength': 1, 'brick': 1},
                'PEAK': {'swim': 2, 'bike': 2, 'run': 2, 'strength': 0, 'brick': 1},
                'TAPER': {'swim': 2, 'bike': 1, 'run': 1, 'strength': 0, 'brick': 0}
            }
        },
        'INTERMEDIO': {
            'SPRINT': {
                'BASE': {'swim': 2, 'bike': 2, 'run': 2, 'strength': 1, 'brick': 0},
                'BUILD': {'swim': 3, 'bike': 3, 'run': 3, 'strength': 1, 'brick': 1},
                'PEAK': {'swim': 2, 'bike': 2, 'run': 2, 'strength': 1, 'brick': 1},
                'TAPER': {'swim': 2, 'bike': 1, 'run': 1, 'strength': 0, 'brick': 1}
            },
            'OLYMPIC': {
                'BASE': {'swim': 2, 'bike': 2, 'run': 2, 'strength': 1, 'brick': 0},
                'BUILD': {'swim': 3, 'bike': 3, 'run': 3, 'strength': 1, 'brick': 1},
                'PEAK': {'swim': 2, 'bike': 2, 'run': 2, 'strength': 1, 'brick': 1},
                'TAPER': {'swim': 2, 'bike': 1, 'run': 1, 'strength': 0, 'brick': 1}
            }
        },
        'AVANZATO': {
            'OLYMPIC': {
                'BASE': {'swim': 3, 'bike': 3, 'run': 3, 'strength': 1, 'brick': 1},
                'BUILD': {'swim': 4, 'bike': 4, 'run': 4, 'strength': 1, 'brick': 2},
                'PEAK': {'swim': 3, 'bike': 3, 'run': 3, 'strength': 1, 'brick': 1},
                'TAPER': {'swim': 2, 'bike': 2, 'run': 2, 'strength': 0, 'brick': 0}
            },
            '70.3': {
                'BASE': {'swim': 3, 'bike': 4, 'run': 3, 'strength': 1, 'brick': 1},
                'BUILD': {'swim': 4, 'bike': 5, 'run': 4, 'strength': 1, 'brick': 2},
                'PEAK': {'swim': 3, 'bike': 4, 'run': 3, 'strength': 1, 'brick': 2},
                'TAPER': {'swim': 2, 'bike': 2, 'run': 2, 'strength': 0, 'brick': 1}
            }
        },
        'ELITE': {
            'OLYMPIC': {
                'BASE': {'swim': 5, 'bike': 5, 'run': 4, 'strength': 1, 'brick': 1},
                'BUILD': {'swim': 6, 'bike': 6, 'run': 5, 'strength': 2, 'brick': 2},
                'PEAK': {'swim': 5, 'bike': 5, 'run': 4, 'strength': 1, 'brick': 2},
                'TAPER': {'swim': 3, 'bike': 3, 'run': 2, 'strength': 0, 'brick': 1}
            },
            '70.3': {
                'BASE': {'swim': 6, 'bike': 6, 'run': 5, 'strength': 1, 'brick': 2},
                'BUILD': {'swim': 7, 'bike': 7, 'run': 5, 'strength': 2, 'brick': 3},
                'PEAK': {'swim': 6, 'bike': 6, 'run': 5, 'strength': 1, 'brick': 3},
                'TAPER': {'swim': 4, 'bike': 4, 'run': 3, 'strength': 0, 'brick': 1}
            }
        }
    }
    
    return matrix[level][distance][phase]

def validate_plan(plan, total_hours, level, acwr_target):
    """
    Validate plan is realistic and safe
    """
    
    alerts = []
    
    # Check 1: Total hours
    plan_hours = calculate_total_hours(plan)
    if plan_hours > total_hours * 1.1:
        alerts.append({
            'severity': 'CRITICAL',
            'message': f'Plan {plan_hours:.1f}h exceeds budget {total_hours}h',
            'action': 'REDUCE sessions or intensity'
        })
    
    # Check 2: Swim frequency (frequency-dependent)
    swim_sessions = count_sessions(plan, 'SWIM')
    if swim_sessions < 2:
        alerts.append({
            'severity': 'WARNING',
            'message': f'Swim {swim_sessions}× is minimal; <2× risks technique loss',
            'action': 'Add 1 swim session if possible'
        })
    
    # Check 3: Brick presence (levels intermediate+)
    brick_sessions = count_sessions(plan, 'BRICK')
    if level in ['INTERMEDIO', 'AVANZATO', 'ELITE'] and brick_sessions == 0:
        alerts.append({
            'severity': 'WARNING',
            'message': f'No brick workouts; race-specific practice missing',
            'action': 'Add 1 brick/fortnight at minimum'
        })
    
    # Check 4: Rest days
    rest_days = count_rest_days(plan)
    if rest_days < 1:
        alerts.append({
            'severity': 'WARNING',
            'message': 'No complete rest days; recovery compromised',
            'action': 'Add 1 rest day minimum'
        })
    
    is_feasible = len([a for a in alerts if a['severity'] == 'CRITICAL']) == 0
    
    return {
        'is_feasible': is_feasible,
        'alerts': alerts,
        'plan_hours': plan_hours,
        'summary': {
            'swim_freq': swim_sessions,
            'rest_days': rest_days,
            'brick_sessions': brick_sessions
        }
    }

def generate_contextual_recommendations(level, phase, weekly_hours):
    """
    Generate personalized recommendations for athlete
    """
    
    recommendations = []
    
    # Message 1: Time constraint reality
    if weekly_hours < 6:
        recommendations.append({
            'type': 'ENCOURAGEMENT',
            'message': 'Consistency > perfection. 1 doable sprint plan per week beats abandoning an 8-hour plan.',
            'priority': 'HIGH'
        })
    
    # Message 2: Level transition
    if level == 'PRINCIPIANTE':
        recommendations.append({
            'type': 'INFO',
            'message': 'Principiante: Focus on regular training in all 3 sports. Intensity comes after consistency.',
            'priority': 'HIGH'
        })
    elif level == 'INTERMEDIO':
        recommendations.append({
            'type': 'INFO',
            'message': 'Intermedio: Introduci brick workout settimanale e 1 sessione qualità per disciplina.',
            'priority': 'MEDIUM'
        })
    elif level == 'AVANZATO':
        recommendations.append({
            'type': 'INFO',
            'message': 'Avanzato: Periodizzazione spinta con 2 sessioni hard (bici+corsa intervals), doppi 1-2 giorni.',
            'priority': 'MEDIUM'
        })
    elif level == 'ELITE':
        recommendations.append({
            'type': 'INFO',
            'message': 'Elite: Frequenza nuoto 5-7×/settimana, back-to-back possibili. Monitoraggio ACWR critico.',
            'priority': 'HIGH'
        })
    
    # Message 3: Phase-specific focus
    if phase == 'BASE':
        recommendations.append({
            'type': 'ACTION',
            'message': 'Base phase: Build volume gradualmente, 80% easy. No brick intensity yet.',
            'priority': 'MEDIUM'
        })
    elif phase == 'BUILD':
        recommendations.append({
            'type': 'ACTION',
            'message': 'Build phase: Introduce 1-2 hard sessions/settimana. Brick settimanale. CTL climbs.',
            'priority': 'HIGH'
        })
    elif phase == 'PEAK':
        recommendations.append({
            'type': 'ACTION',
            'message': 'Peak phase: Volume stabile, intensità massima. Race-specific prep. TSB trending negative.',
            'priority': 'HIGH'
        })
    elif phase == 'TAPER':
        recommendations.append({
            'type': 'ACTION',
            'message': 'Taper: Volume -40-50%, intensità mantenuta. Sleep priorità assoluta. Resting well = winning well.',
            'priority': 'HIGH'
        })
    
    # Message 4: Strength
    if level in ['PRINCIPIANTE', 'INTERMEDIO']:
        recommendations.append({
            'type': 'SUGGESTION',
            'message': f'Strength 1×/settimana è minimo efficace. Mantieni base for injury prevention.',
            'priority': 'MEDIUM'
        })
    
    # Message 5: Swim frequency
    if level in ['INTERMEDIO', 'AVANZATO', 'ELITE']:
        recommendations.append({
            'type': 'CRUCIAL',
            'message': f'Swim frequenza ≥ 3×/settimana (levels intermedio+). Tecnica dipende da touch frequenti.',
            'priority': 'HIGH'
        })
    
    return recommendations
```

---

## Raccomandazioni Pratiche

### Per Principiante
- ✅ **Essenziale**: Tutte e 3 le discipline 2×/settimana minimo
- ✅ **Consigliato**: 1 riposo settimanale completo
- ⚠️ **Evitare**: Intensità alta; focus su frequenza e forma
- 📊 **Metriche**: Volume che aumenta 10% ogni 3-4 settimane

### Per Intermedio
- ✅ **Essenziale**: Nuoto 2-3× (freccia tecnica); 1 sessione qualità per bici e corsa
- ✅ **Consigliato**: 1 brick/settimana in Build+Peak
- ✅ **Consigliato**: 1 strength session/settimana
- ⚠️ **Attenzione**: Double session solo easy+easy (non hard+anything)
- 📊 **Target ACWR**: 0.7-0.9 (healthy build)

### Per Avanzato
- ✅ **Essenziale**: Nuoto 3-4× settimanali (frequenza critica)
- ✅ **Essenziale**: 2 sessioni hard (bici intervals + corsa intervals)
- ✅ **Essenziale**: 1-2 brick settimanali
- ✅ **Consigliato**: 1 strength 1×/settimana (manutenzione)
- ✅ **Consigliato**: 2-3 doppi sessioni/settimana (easy pairs)
- 📊 **Target ACWR**: 0.75-1.0 (accumulation phase)

### Per Elite
- ✅ **Essenziale**: Nuoto 5-7× settimanali (max frequenza)
- ✅ **Essenziale**: 2-3 hard session/settimana (bici, corsa, possibile plyos)
- ✅ **Essenziale**: 2-3 brick settimanali (uno doppio lungo)
- ✅ **Essenziale**: Back-to-back 3-4 giorni/settimana (easy pairs)
- ✅ **Consigliato**: 1-2 strength sessioni
- 📊 **Monitor ACWR**: Continuamente; target 0.8-1.2 (managed accumulation)
- 📊 **Monitor HRV**: Daily; calo > 15% = recovery day imminente

---

## Checklist per LLM Implementation

Quando generi un piano, verifica:

- [ ] Nuoto frequenza ≥ 2× (principiante), ≥ 3× (intermedio+)
- [ ] Brick presenti? (0 principiante, ≥1 intermedio, ≥1 avanzato, ≥2 elite)
- [ ] Strength sessions = 0-1 principiante, 1 intermedio/avanzato, 1-2 elite
- [ ] Total ore ≤ available hours × 1.05 (max 5% over)
- [ ] Rest days ≥ 1 (principiante/intermedio), ≥ 1 (avanzato), adaptivo (elite)
- [ ] Double sessions solo easy+easy (no hard+hard per non-pro)
- [ ] ACWR stimato < 1.3 (unless peak/taper)
- [ ] Messaggio personalizzato per livello + fase

---

## Conclusione

Questa guida fornisce un **framework chiaro e scientifico** per generare automaticamente piani di triathlon per 4 livelli, considerando le constraint di tempo e il realismo della pratica. L'app LLM può utilizzare le tabelle e il pseudocodice per generare piani coerenti, progressivi e sicuri.

**Principio Fondamentale**: Un piano coerente a 6 ore che l'atleta completa al 100% batte un piano "ideale" a 12 ore che viene abbandonato al 50%.

---

**Documento creato per implementazione LLM - Triathlon Training Periodization v1.0 (2025)**