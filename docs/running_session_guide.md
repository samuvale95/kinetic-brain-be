# Guida Completa: Sessioni di Allenamento per RUNNING per Livelli
## Struttura per LLM - Principiante, Intermedio, Avanzato, Elite

---

## Table of Contents

1. [Introduzione](#introduzione)
2. [Definizione dei 4 Livelli](#definizione-dei-4-livelli)
3. [Sessioni Settimanali per Distanza](#sessioni-settimanali-per-distanza)
4. [Strutture Settimanali Tipo](#strutture-settimanali-tipo)
5. [Logica LLM - Pseudocodice](#logica-llm---pseudocodice)
6. [Raccomandazioni Pratiche](#raccomandazioni-pratiche)

---

## Introduzione

Questa guida definisce il **numero di sessioni settimanali** consigliate per atleti di running su strada in **4 categorie di livello**:
- **Principiante**: <1 stagione, nessuna gara completata (o rientro)
- **Intermedio**: 1-3 stagioni, completate 5K-HM con costanza
- **Avanzato**: 3+ stagioni, competitivo su HM/Maratona
- **Elite**: Podium finisher, specializzazione periodizzata, maratona competitiva

L'obiettivo è fornire **strutture realistiche** che un'app LLM possa generare automaticamente.

---

## Definizione dei 4 Livelli

| Livello | Esperienza | Competizioni | Obiettivo | Tempo/Sett | Mentalità |
|---------|-----------|--------------|-----------|-----------|-----------|
| **Principiante** | <1 anno | 0-2 | Completare 5K-10K | 3-5h | Sviluppare base |
| **Intermedio** | 1-3 anni | 3-8 | HM competitive, sub 2h | 5-7h | Migliorare PB |
| **Avanzato** | 3+ anni | 10+ | Podio locale HM, sub 90' | 7-9h | Specializzazione |
| **Elite** | 5+ anni | 20+ | Podio assoluto, maratona sub 3h | 9-12h | Performance massimale |

---

## Sessioni Settimanali per Distanza

### 5K (Sprint)

| Livello | Sessioni | Volume Sett | Focus |
|---------|----------|------------|--------|
| **Principiante** | 3-4 | 15-20 km | Base aerobica |
| **Intermedio** | 4-5 | 25-30 km | Velocità 5K |
| **Avanzato** | 5-6 | 35-45 km | Specifico velocità |
| **Elite** | 6-7 | 50-65 km | VO2max + sprint |

### 10K (Short Distance)

| Livello | Sessioni | Volume Sett | Focus |
|---------|----------|------------|--------|
| **Principiante** | 3-4 | 20-25 km | Resistenza base |
| **Intermedio** | 4-5 | 30-40 km | Ritmo gara sostenuto |
| **Avanzato** | 5-6 | 45-60 km | Threshold + VO2max |
| **Elite** | 6-8 | 65-85 km | Periodizzazione spinta |

### Half Marathon (21km)

| Livello | Sessioni | Volume Sett | Focus |
|---------|----------|------------|--------|
| **Principiante** | 3-4 | 25-35 km | Resistenza aerobica |
| **Intermedio** | 4-5 | 40-50 km | Tempo sostenuto + lungo |
| **Avanzato** | 5-6 | 60-75 km | Threshold high volume |
| **Elite** | 6-8 | 80-110 km | Massimal volume + specifico |

### Maratona (42.2km)

| Livello | Sessioni | Volume Sett | Focus |
|---------|----------|------------|--------|
| **Principiante** | 3-4 | 30-45 km | Base long slow |
| **Intermedio** | 4-5 | 50-65 km | Lungo + ritmo sostenuto |
| **Avanzato** | 5-6 | 75-100 km | Lungo maratona + qualità |
| **Elite** | 6-8 | 110-150 km | Volume massimale + specifico |

---

## Strutture Settimanali Tipo

### Principiante - 5K Prep (3-5h/settimana, 18-22 km/sett)

```
LUNEDI: RIPOSO o Easy Walk

MARTEDI: Corsa Facile (30-35 min, 4-5 km)
- Zone 1-2, conversazione comoda
- Focus: volume consistente

MERCOLEDI: Tempo Run (25-30 min, 3.5-4 km)
- Warm: 5 min facile
- Main: 15 min @ ritmo gara-30sec
- Cool: 5 min
- Focus: velocità controllata

GIOVEDI: RIPOSO

VENERDI: Easy Run (25 min, 3 km)
- Recupero attivo
- Very easy conversazione

SABATO: RIPOSO o Stretching (15 min)

DOMENICA: Long Easy Run (50 min, 6-7 km)
- Zona 1-2
- Focus: resistenza aerobica

TOTALE: 4 sessioni, 20 km, 2-2.5 ore run
CARATTERISTICHE:
- 80% volume facile
- 1 sessione qualità/sett
- 1 rest day completo
- Stretching post-sessione
- Goal: Adattamento, base aerobica
```

### Intermedio - Half Marathon Prep (5-7h/settimana, 45-50 km/sett)

```
LUNEDI: RIPOSO

MARTEDI: Easy Run (40 min, 6 km)
- Zone 1-2 conversazione
- No intensità

MERCOLEDI: Corsa Intervalli (50 min, 7 km)
- Warm: 10 min facile
- Main: 5×3' @ 10K pace, 2' rec
- Cool: 10 min
- Focus: VO2max, velocità

GIOVEDI: Riposo o Mobility (15 min)

VENERDI: Tempo Run (45 min, 7 km)
- Warm: 10 min
- Main: 20 min @ ritmo HM-10sec
- Cool: 10 min
- Focus: threshold sostenuto

SABATO: Easy Run (35 min, 5 km)
- Recupero attivo
- Pre-long run prep

DOMENICA: Long Slow Distance (90 min, 12-13 km)
- Zona 1-2 steady
- Focus: endurance, adattamento a lungo termine

TOTALE: 5 sessioni, 45 km, 5-5.5 ore run
CARATTERISTICHE:
- 70% volume facile
- 2 sessioni qualità (intervalli+tempo)
- 1 rest day
- 1 long run settimanale
- Stretching 10-15 min post ogni sessione
- Goal: Performance HM competitive
```

### Avanzato - Maratona Prep (7-9h/settimana, 75-90 km/sett)

```
LUNEDI: RIPOSO

MARTEDI: Easy Run (45 min, 7 km)
- Recovery attivo
- Zone 1-2

MERCOLEDI: VO2max Intervals (60 min, 9 km)
- Warm: 15 min
- Main: 6×4' @ 5K pace, 2' rec
- Cool: 10 min
- TSS: ~85-90
- Focus: velocità massimale

GIOVEDI: Riposo o Strength (35 min)
- Core, glute, stabilità caviglie

VENERDI: Threshold Run (50 min, 8 km)
- Warm: 10 min
- Main: 25 min @ ritmo maratona+15sec
- Cool: 10 min
- TSS: ~75-80
- Focus: ritmo sostenuto maratona

SABATO: Facile corta (30 min, 5 km)
- Recovery prima long run

DOMENICA: Long Run (140 min, 18-20 km)
- Steady moderate pace (maratona pace)
- Focus: resistenza, adattamento psicologico

TOTALE: 5 sessioni, 75 km, 7.5-8 ore run
CARATTERISTICHE:
- 65% volume facile
- 2 sessioni hard (VO2max+threshold)
- 1 long run settimanale (18-20 km)
- 1 strength core/glute
- 1 rest day
- Stretching+mobilità 15-20 min daily
- Goal: Maratona competitiva
```

### Elite - Maratona Competitive (9-12h/settimana, 120-150 km/sett)

```
LUNEDI: Easy Run (45 min, 7 km) + Strength (35 min)
- AM: Recovery attivo
- RECOVERY 4h
- PM: Strength (glute, core, stabilità)
- Double day

MARTEDI: VO2max Intervals (75 min, 11 km)
- Warm: 15 min
- Main: 7×5' @ 5K pace, 2' rec
- Cool: 10 min
- TSS: ~100
- Focus: velocità massimale power

MERCOLEDI: Easy Run (40 min, 6 km)
- Recovery fra hard sessions

GIOVEDI: Threshold + Marathon Pace (70 min, 11 km)
- Warm: 10 min
- Main: 15' @ threshold + 15' @ maratona pace
- Cool: 10 min
- TSS: ~90
- Focus: ritmo sostenuto maratona specifico

VENERDI: Easy Run (35 min, 5 km) + Mobility (20 min)
- Pre-long run recovery

SABATO: Long Marathon Pace Run (180 min, 25-27 km)
- Steady state maratona pace
- Focus: endurance psicologica, fuel strategy

DOMENICA: Recovery Easy (30 min, 4 km)
- Very easy recupero post-lungo

LUNEDI ALT: 2a sessione hard
- Possibile 2a VO2max mid-week in early build

TOTALE: 6-7 sessioni, 130 km, 10-11 ore run
CARATTERISTICHE:
- 60% volume facile
- 2 sessioni hard (VO2max, threshold)
- 1 long run settimanale 25-27 km
- 1-2 strength sessions
- 3-4 doppi sessioni/settimana (easy pair, strength+easy)
- Stretching+mobilità daily 15-20 min
- Back-to-back hard sessions rarissimo (max ogni 10-14 giorni)
- Goal: Maratona elite podio
```

---

## Distribuzione Intensità per Running

### Principiante
- **Easy (Zone 1-2)**: 90% volume
- **Moderate (Zone 3)**: 10% volume
- **Hard (Zone 4-5)**: 0%

### Intermedio
- **Easy (Zone 1-2)**: 70% volume
- **Moderate (Zone 3)**: 20% volume
- **Hard (Zone 4-5)**: 10% volume

### Avanzato
- **Easy (Zone 1-2)**: 65% volume
- **Moderate (Zone 3)**: 20% volume
- **Hard (Zone 4-5)**: 15% volume

### Elite
- **Easy (Zone 1-2)**: 60% volume
- **Moderate (Zone 3)**: 20% volume
- **Hard (Zone 4-5)**: 20% volume

---

## Logica LLM - Pseudocodice

```python
def generate_running_plan(athlete_input):
    """
    Generate realistic running training plan by level
    """
    
    # 1. VALIDATE inputs
    validate_running_inputs(athlete_input)
    
    # 2. GET SESSION MATRIX
    session_counts = get_session_matrix_running(
        level=athlete_input.level,
        distance=athlete_input.race_distance,
        phase=athlete_input.phase
    )
    # Returns: {easy: 2-3, moderate: 0-1, hard: 0-2, long: 1}
    
    # 3. CALCULATE WEEKLY VOLUME
    weekly_volume_km = calculate_target_volume_running(
        level=athlete_input.level,
        race_distance=athlete_input.race_distance,
        phase=athlete_input.phase
    )
    
    # 4. BUILD WEEK STRUCTURE
    week_skeleton = {
        'mon': {'type': 'REST'},
        'tue': {'type': 'EASY', 'km': weekly_volume_km * 0.15},
        'wed': {'type': 'HARD_INTERVALS', 'km': weekly_volume_km * 0.20},
        'thu': {'type': 'REST_or_EASY', 'km': 0 or weekly_volume_km * 0.12},
        'fri': {'type': 'TEMPO', 'km': weekly_volume_km * 0.18},
        'sat': {'type': 'EASY', 'km': weekly_volume_km * 0.12},
        'sun': {'type': 'LONG', 'km': weekly_volume_km * 0.25}
    }
    
    # 5. ADD SPECIFICS
    for day, session_data in week_skeleton.items():
        if session_data['type'] != 'REST':
            session_detail = build_running_session(
                session_type=session_data['type'],
                km=session_data['km'],
                intensity=get_intensity_running(session_data['type']),
                level=athlete_input.level,
                phase=athlete_input.phase,
                race_distance=athlete_input.race_distance
            )
            week_skeleton[day].update(session_detail)
    
    # 6. ADD STRENGTH if applicable
    if athlete_input.level in ['INTERMEDIO', 'AVANZATO', 'ELITE']:
        strength_day = allocate_strength_day(level=athlete_input.level)
        week_skeleton[strength_day]['strength'] = {
            'focus': 'CORE_GLUTE_STABILITY',
            'duration': 30-40,
            'when': 'PM' if same_day_as_run else 'DEDICATED'
        }
    
    # 7. VALIDATE
    validation = validate_running_plan(week_skeleton, athlete_input)
    
    if not validation.is_feasible:
        week_skeleton = adjust_running_plan(week_skeleton, validation.alerts)
    
    # 8. RECOMMENDATIONS
    recommendations = generate_running_recommendations(
        level=athlete_input.level,
        phase=athlete_input.phase,
        volume=weekly_volume_km
    )
    
    return {
        'weekly_plan': week_skeleton,
        'total_sessions': count_running_sessions(week_skeleton),
        'total_volume_km': weekly_volume_km,
        'long_run_km': weekly_volume_km * 0.25,
        'recommendations': recommendations
    }

def get_session_matrix_running(level, distance, phase):
    """
    Look-up for running sessions
    """
    
    matrix = {
        'PRINCIPIANTE': {
            '5K': {
                'BASE': {'easy': 3, 'moderate': 0, 'hard': 0, 'long': 1},
                'BUILD': {'easy': 2, 'moderate': 1, 'hard': 0, 'long': 1},
                'PEAK': {'easy': 2, 'moderate': 0, 'hard': 1, 'long': 1},
                'TAPER': {'easy': 2, 'moderate': 0, 'hard': 0, 'long': 0}
            }
        },
        'INTERMEDIO': {
            'HM': {
                'BASE': {'easy': 2, 'moderate': 1, 'hard': 0, 'long': 1},
                'BUILD': {'easy': 2, 'moderate': 1, 'hard': 1, 'long': 1},
                'PEAK': {'easy': 1, 'moderate': 1, 'hard': 1, 'long': 1},
                'TAPER': {'easy': 2, 'moderate': 0, 'hard': 0, 'long': 1}
            }
        },
        'AVANZATO': {
            'MARATHON': {
                'BASE': {'easy': 2, 'moderate': 1, 'hard': 1, 'long': 1},
                'BUILD': {'easy': 2, 'moderate': 1, 'hard': 2, 'long': 1},
                'PEAK': {'easy': 1, 'moderate': 1, 'hard': 2, 'long': 1},
                'TAPER': {'easy': 2, 'moderate': 0, 'hard': 1, 'long': 1}
            }
        },
        'ELITE': {
            'MARATHON': {
                'BASE': {'easy': 2, 'moderate': 1, 'hard': 2, 'long': 1},
                'BUILD': {'easy': 2, 'moderate': 1, 'hard': 3, 'long': 1},
                'PEAK': {'easy': 1, 'moderate': 1, 'hard': 3, 'long': 1},
                'TAPER': {'easy': 2, 'moderate': 0, 'hard': 1, 'long': 1}
            }
        }
    }
    
    return matrix[level][distance][phase]
```

---

## Raccomandazioni Pratiche

### Principiante
- ✅ **Essenziale**: 3-4 sessioni/settimana (inclusa 1 long)
- ✅ **Consigliato**: Incremento volume 10% ogni 2-3 settimane
- ⚠️ **Evitare**: >4 sessioni/settimana (rischio infortuni)
- 📊 **Metriche**: Tracciare tempo 5K standard ogni 3-4 settimane

### Intermedio
- ✅ **Essenziale**: 4-5 sessioni/settimana
- ✅ **Essenziale**: 2 sessioni qualità (1 intervalli, 1 tempo)
- ✅ **Consigliato**: 1 strength core/glute 1×/settimana
- 📊 **Target ACWR**: 0.75-0.95

### Avanzato
- ✅ **Essenziale**: 5-6 sessioni/settimana
- ✅ **Essenziale**: 2 sessioni hard (VO2max + threshold)
- ✅ **Essenziale**: Long run 1× weekly (25-40 km progression)
- ✅ **Consigliato**: 1-2 strength sessions
- 📊 **Target ACWR**: 0.80-1.0

### Elite
- ✅ **Essenziale**: 6-8 sessioni/settimana
- ✅ **Essenziale**: 2-3 hard sessions (VO2max, threshold, marathon pace)
- ✅ **Essenziale**: Long run 25-27 km settimanale in build/peak
- ✅ **Essenziale**: 1-2 strength sessions
- ✅ **Essenziale**: Back-to-back possibili ma rari (easy+easy, no hard+hard)
- 📊 **Monitor**: ACWR, HRV, RPE; trend velocità per livello
- 📊 **Target ACWR**: 0.85-1.1

---

## Checklist per LLM Implementation

- [ ] Numero sessioni coerente con livello
- [ ] Long run settimanale presente (tutte le fasi)
- [ ] Sessioni qualità appropriate per fase
- [ ] Rest days ≥ 1 (principiante/intermedio), ≥ 0 (avanzato)
- [ ] Strength per livelli intermedio+
- [ ] Volume incrementa max 10% settimanale
- [ ] ACWR stimato < 1.2 build, < 1.0 peak
- [ ] Messaggi personalizzati per livello

---

**Documento creato per implementazione LLM - Running Training Periodization v1.0 (2025)**