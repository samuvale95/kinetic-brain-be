# Guida Completa: Sessioni di Allenamento per CYCLING per Livelli
## Struttura per LLM - Principiante, Intermedio, Avanzato, Elite

---

## Table of Contents

1. [Introduzione](#introduzione)
2. [Definizione dei 4 Livelli](#definizione-dei-4-livelli)
3. [Sessioni Settimanali per Distanza](#sessioni-settimanali-per-distanza)
4. [Metriche Critiche Cycling](#metriche-critiche-cycling)
5. [Strutture Settimanali Tipo](#strutture-settimanali-tipo)
6. [Logica LLM - Pseudocodice](#logica-llm---pseudocodice)
7. [Raccomandazioni Pratiche](#raccomandazioni-pratiche)

---

## Introduzione

Questa guida definisce il **numero di sessioni settimanali** consigliate per atleti di ciclismo in **4 categorie di livello**:
- **Principiante**: <1 stagione, nessuna competizione ciclistica
- **Intermedio**: 1-3 stagioni, gare locali completate (gran fondo, cicloturismo)
- **Avanzato**: 3+ stagioni, competitivo su corse amatoriali, podio locale realistico
- **Elite**: Podium finisher corse amatoriali, aspirante cicloturismo competitive, cicloamatori avanzati

A differenza di running e trail, **il ciclismo permette volume molto alto** grazie al minor impatto articolare. L'app deve monitorare **TSS (Training Stress Score)** e **potenza (Watts)** come metriche primarie.

---

## Definizione dei 4 Livelli

| Livello | Esperienza | Competizioni | Obiettivo | Tempo/Sett | Mentalità |
|---------|-----------|--------------|-----------|-----------|-----------|
| **Principiante** | <1 anno | 0-2 | Completare gran fondo 150km | 5-7h | Sviluppare resistenza |
| **Intermedio** | 1-3 anni | 3-8 | Competitivo gran fondo, podio locale | 7-10h | Specializzazione strada |
| **Avanzato** | 3+ anni | 10+ | Podio gare amatoriali, CX/MTB base | 10-15h | Versatilità multi-discipline |
| **Elite** | 5+ anni | 20+ | Podio nazionale, cicloturismo competitive | 15-20h+ | Performance massimale |

---

## Sessioni Settimanali per Distanza / Specialità

### CICLOTURISMO / GRAN FONDO (150-200 km in 1 day)

| Livello | Sessioni | TSS Sett | Durata Media | Focus |
|---------|----------|----------|------------|--------|
| **Principiante** | 3-4 | 250-350 | 5-7h | Base aerobica, resistenza |
| **Intermedio** | 4-5 | 350-500 | 7-10h | Velocità sostenuta, pacing |
| **Avanzato** | 5-6 | 500-700 | 10-15h | Specifico gara power |
| **Elite** | 6-8 | 700-1000 | 15-20h+ | Performance massimale |

### CICLOTURISMO COMPETITIVO / XC (Ciclocross/MTB)

| Livello | Sessioni | TSS Sett | Durata Media | Focus |
|---------|----------|----------|------------|--------|
| **Principiante** | 2-3 | 200-300 | 4-6h | Tecnica, agilità |
| **Intermedio** | 3-4 | 300-450 | 6-9h | Velocità trail, power |
| **Avanzato** | 4-5 | 450-650 | 9-13h | Racing specifico |
| **Elite** | 5-7 | 650-950 | 13-18h | Elite competition |

### VELOCITÀ PURA / CICLISMO SU STRADA AGONISTICO

| Livello | Sessioni | TSS Sett | Durata Media | Focus |
|---------|----------|----------|------------|--------|
| **Principiante** | 3-4 | 280-400 | 6-9h | Velocità base |
| **Intermedio** | 4-5 | 400-600 | 9-12h | Potenza sprint, ritmo |
| **Avanzato** | 5-7 | 600-900 | 12-18h | VO2max, potenza picco |
| **Elite** | 6-9 | 900-1400 | 18-25h+ | Elite racing |

---

## Metriche Critiche Cycling

### Metriche Primarie

| Metrica | Descrizione | Range Principiante | Range Elite |
|---------|-----------|---------|---------|
| **FTP (Watts)** | Functional Threshold Power, max 60 min | 150-200W | 350-500W |
| **TSS/day** | Training Stress Score giornaliero | 40-60 | 120-200 |
| **IF (Intensity Factor)** | Normalized Power / FTP | 0.5-0.7 | 0.7-1.2 |
| **Watts/kg** | Potenza relativa al peso | 2.5-3.5 | 5.5-7.5+ |
| **Cadenza (RPM)** | Pedalate al minuto | 85-95 | 90-100 |

### Validazione Metriche

**FTP Estimation** (Se power meter non disponibile):
```
FTP ≈ Max average power over 60 minutes continuous
OR
FTP ≈ Max average power over 20 min × 0.95
```

**TSS Calculation**:
```
TSS = (Secondi × NP × IF) / (FTP × 3600) × 100

Esempio:
- Durata 90 min = 5400 sec
- NP (Normalized Power) = 220W
- FTP = 250W
- IF = 220/250 = 0.88
- TSS = (5400 × 220 × 0.88) / (250 × 3600) × 100 = 117 TSS
```

---

## Strutture Settimanali Tipo

### Principiante - Cicloturismo (6-8h/settimana, 250-350 TSS)

```
LUNEDI: RIPOSO

MARTEDI: Bike Facile (90 min, 40-50 km)
- Zone 1-2, conversazione comoda
- Cadenza 85-95 RPM
- TSS ~50-60
- Focus: Aerobica base

MERCOLEDI: Bike Intervalli Brevi (75 min, 35-40 km)
- Warm: 15 min
- Main: 5×4' @ Zone 3-4, 3' rec
- Cool: 15 min
- TSS ~70-80
- Focus: Velocità sostenuta

GIOVEDI: RIPOSO

VENERDI: Bike Facile (60 min, 30-35 km)
- Very easy, cambio ritmo
- Zone 1-2
- TSS ~35-40

SABATO: RIPOSO

DOMENICA: Long Bike (150 min, 65-75 km)
- Zone 1-2 steady
- Nutrimento pratica
- TSS ~100-120
- Focus: Resistenza, distanza

TOTALE: 4 sessioni, 220-250 km, 6h
TSS TOTALE: ~300-330
CARATTERISTICHE:
- 80% volume facile
- 1 sessione qualità intervalli brevi
- 1 long steady domenica
- Stretching 10-15 min post
- Goal: Base gran fondo, resistenza
```

### Intermedio - Gran Fondo (8-11h/settimana, 400-550 TSS)

```
LUNEDI: RIPOSO

MARTEDI: Bike Threshold (100 min, 50-60 km)
- Warm: 15 min
- Main: 3×10' @ Threshold (90% FTP), 3' rec
- Cool: 15 min
- TSS ~110-130
- Focus: Ritmo gara sostenuto

MERCOLEDI: Bike Facile (75 min, 40-45 km)
- Zone 1-2 recovery
- Nutrimento light
- TSS ~45-55

GIOVEDI: RIPOSO o Strength (30 min)
- Core, leg press, squats (cycling-specific)

VENERDI: Bike Tempo (90 min, 45-50 km)
- Warm: 15 min
- Main: 30 min @ Zone 3 (85% FTP)
- Cool: 15 min
- TSS ~85-95
- Focus: Potenza sostenuta

SABATO: RIPOSO

DOMENICA: Long Steady (180 min, 80-90 km)
- Zone 2 moderate aerobico
- Nutrimento completa pratica
- TSS ~130-150
- Focus: Gran fondo specifico pacing

TOTALE: 5 sessioni, 280-330 km, 8-9h
TSS TOTALE: ~420-470
CARATTERISTICHE:
- 65% volume facile
- 2 sessioni hard (threshold + tempo)
- 1 long gran fondo prep
- 1 strength opcional
- Stretching 12-15 min post
- Goal: Gran fondo competitive performance
```

### Avanzato - Cicloturismo Competitivo (11-16h/settimana, 550-800 TSS)

```
LUNEDI: RIPOSO

MARTEDI: VO2max Intervals (110 min, 55-65 km)
- Warm: 20 min
- Main: 6×5' @ VO2max (120-130% FTP), 3' rec
- Cool: 15 min
- TSS ~130-150
- Focus: Potenza massimale

MERCOLEDI: Bike Facile (80 min, 45-50 km)
- Zone 1-2 recovery attivo
- TSS ~50-60

GIOVEDI: Threshold Long (120 min, 60-70 km)
- Warm: 20 min
- Main: 2×15' @ Threshold, 5' rec
- Cool: 20 min
- TSS ~120-140
- Focus: Resistenza threshold

VENERDI: Strength + Easy Bike
- AM: Strength 40 min (glute, core, quads)
- RECOVERY 3h
- PM: Easy spin 60 min, 35 km
- TSS ~60-70
- Double day

SABATO: RIPOSO o Cross-training

DOMENICA: Long Gran Fondo Simulation (220+ min, 100-120 km)
- Mixed intensity: 60% Zone 2, 30% Zone 3, 10% Zone 4
- Nutrimento reale scenario
- TSS ~180-220
- Focus: Performance gran fondo

TOTALE: 5-6 sessioni, 330-400 km, 12-13h
TSS TOTALE: ~650-750
CARATTERISTICHE:
- 55% volume facile
- 2-3 sessioni hard (VO2max, threshold long, simulazione)
- 1 long gran fondo specifico
- 1-2 strength
- 1-2 doppi sessioni (strength+easy)
- Stretching daily 15 min
- Goal: Gran fondo podio, cicloturismo competitive
```

### Elite - Cicloturismo + Agonismo (16-22h/settimana, 900-1300 TSS)

```
LUNEDI: Easy Bike (80 min, 45-50 km) + Strength (45 min)
- AM: Recovery Zone 1-2
- RECOVERY 4h
- PM: Strength (glute, core, quads, triceps, back)
- TSS ~70 (bike) + strength
- Double day

MARTEDI: VO2max Hard (130 min, 65-75 km)
- Warm: 20 min
- Main: 7×5' @ VO2max (130-140% FTP), 2.5' rec
- Cool: 20 min
- TSS ~160-180
- Focus: Massimale potenza

MERCOLEDI: Moderate Bike (100 min, 55-65 km)
- Warm: 15 min
- Main: 45 min @ Zone 3 (85-90% FTP), variato
- Cool: 15 min
- TSS ~95-110
- Focus: Potenza sostenuta

GIOVEDI: RIPOSO o Mobility (30 min)

VENERDI: Threshold Multiple (140 min, 70-80 km)
- Warm: 20 min
- Main: 3×12' @ Threshold, 4' rec
- Cool: 20 min
- TSS ~140-160
- Focus: Resistenza threshold power

SABATO: Sprint / Race Simulation (120 min, 60-70 km)
- Reps of 8×30sec sprints @ max power, long rec
- OR: Brick session (bike + corsa breve)
- TSS ~110-130
- Focus: Agilità, potenza picco, cambio velocità

DOMENICA: Long Endurance (260+ min, 120-140 km)
- Steady Zone 1-2 + moderate blocks Zone 3
- Real nutrition scenario, hydration testing
- TSS ~200-250
- Focus: Ultra-endurance, pacing strategy

TOTALE: 6-7 sessioni, 450-550 km, 16-18h
TSS TOTALE: ~1000-1200
CARATTERISTICHE:
- 50% volume facile
- 3-4 sessioni hard (VO2max, threshold, sprint/race sim)
- 1 long ultra-endurance
- 1-2 strength
- 3-4 doppi sessioni
- Back-to-back hard possible (same day easy+hard, or consecutive VO2max/threshold with 48h+)
- Stretching daily 15-20 min
- Periodizzazione spinta (microcicli hard/easy strutturati)
- Goal: Elite performance cicloturismo/agonismo

```

---

## Logica LLM - Pseudocodice

```python
def generate_cycling_plan(athlete_input):
    """
    Generate cycling training plan using TSS and power metrics
    """
    
    # 1. VALIDATE FTP/Power data
    if athlete_input.ftp is None:
        athlete_input.ftp = estimate_ftp_from_history(athlete_input)
    
    # 2. GET SESSION MATRIX (TSS-based)
    session_counts = get_session_matrix_cycling(
        level=athlete_input.level,
        specialty=athlete_input.specialty,  # GRAN_FONDO, ROAD_RACE, XC, etc
        phase=athlete_input.phase
    )
    
    # 3. CALCULATE WEEKLY TSS BUDGET
    weekly_tss_target = calculate_tss_budget(
        level=athlete_input.level,
        hours_available=athlete_input.weekly_hours,
        specialty=athlete_input.specialty,
        phase=athlete_input.phase
    )
    
    # 4. BUILD WEEK STRUCTURE
    week_skeleton = {
        'mon': {'type': 'REST'},
        'tue': {'type': 'HARD_SESSION_1', 'target_tss': weekly_tss_target * 0.25},
        'wed': {'type': 'EASY', 'target_tss': weekly_tss_target * 0.10},
        'thu': {'type': 'REST_or_STRENGTH', 'target_tss': 0 or 40},
        'fri': {'type': 'HARD_SESSION_2', 'target_tss': weekly_tss_target * 0.22},
        'sat': {'type': 'EASY_or_SPRINT', 'target_tss': weekly_tss_target * 0.10},
        'sun': {'type': 'LONG', 'target_tss': weekly_tss_target * 0.33}
    }
    
    # 5. ASSIGN POWER/INTENSITY for each session
    for day, session_data in week_skeleton.items():
        if session_data['type'] != 'REST':
            power_profile = calculate_power_targets(
                session_type=session_data['type'],
                ftp=athlete_input.ftp,
                target_tss=session_data['target_tss'],
                level=athlete_input.level
            )
            week_skeleton[day]['power'] = power_profile
            week_skeleton[day]['duration_min'] = estimate_duration_from_tss(
                tss=session_data['target_tss'],
                intensity_factor=get_if_for_type(session_data['type'])
            )
    
    # 6. ADD STRENGTH if applicable
    if athlete_input.level in ['INTERMEDIO', 'AVANZATO', 'ELITE']:
        strength_day = allocate_strength_day_cycling(level=athlete_input.level)
        week_skeleton[strength_day]['strength'] = {
            'focus': 'CYCLING_SPECIFIC',
            'duration': 30-45,
            'muscles': ['GLUTES', 'QUADS', 'CORE']
        }
    
    # 7. VALIDATE TSS and ACWR
    validation = validate_cycling_plan(
        plan=week_skeleton,
        total_tss=sum([s.get('target_tss', 0) for s in week_skeleton.values()]),
        level=athlete_input.level,
        phase=athlete_input.phase
    )
    
    # 8. ADJUST if needed
    if not validation.is_feasible:
        week_skeleton = adjust_cycling_plan(week_skeleton, validation.alerts)
    
    # 9. RECOMMENDATIONS
    recommendations = generate_cycling_recommendations(
        level=athlete_input.level,
        specialty=athlete_input.specialty,
        weekly_tss=sum([s.get('target_tss', 0) for s in week_skeleton.values()]),
        phase=athlete_input.phase
    )
    
    return {
        'weekly_plan': week_skeleton,
        'total_sessions': count_cycling_sessions(week_skeleton),
        'weekly_tss': sum([s.get('target_tss', 0) for s in week_skeleton.values()]),
        'estimated_km': estimate_km_from_tss(weekly_tss, athlete_input.level),
        'ftp': athlete_input.ftp,
        'recommendations': recommendations
    }

def get_session_matrix_cycling(level, specialty, phase):
    """
    Look-up table for cycling sessions and TSS targets
    """
    
    matrix = {
        'PRINCIPIANTE': {
            'GRAN_FONDO': {
                'BASE': {'easy': 2, 'moderate': 1, 'hard': 0, 'long': 1},
                'BUILD': {'easy': 2, 'moderate': 1, 'hard': 1, 'long': 1},
                'PEAK': {'easy': 1, 'moderate': 1, 'hard': 1, 'long': 1},
                'TAPER': {'easy': 2, 'moderate': 0, 'hard': 0, 'long': 1}
            }
        },
        'INTERMEDIO': {
            'GRAN_FONDO': {
                'BASE': {'easy': 2, 'moderate': 1, 'hard': 1, 'long': 1},
                'BUILD': {'easy': 2, 'moderate': 1, 'hard': 2, 'long': 1},
                'PEAK': {'easy': 1, 'moderate': 1, 'hard': 2, 'long': 1},
                'TAPER': {'easy': 2, 'moderate': 0, 'hard': 1, 'long': 1}
            },
            'ROAD_RACE': {
                'BASE': {'easy': 2, 'moderate': 1, 'hard': 1, 'long': 1},
                'BUILD': {'easy': 2, 'moderate': 1, 'hard': 2, 'long': 1},
                'PEAK': {'easy': 1, 'moderate': 1, 'hard': 2, 'long': 0},
                'TAPER': {'easy': 2, 'moderate': 0, 'hard': 1, 'long': 0}
            }
        },
        'AVANZATO': {
            'GRAN_FONDO': {
                'BASE': {'easy': 2, 'moderate': 1, 'hard': 2, 'long': 1},
                'BUILD': {'easy': 2, 'moderate': 1, 'hard': 3, 'long': 1},
                'PEAK': {'easy': 1, 'moderate': 1, 'hard': 3, 'long': 1},
                'TAPER': {'easy': 2, 'moderate': 0, 'hard': 1, 'long': 1}
            },
            'ROAD_RACE': {
                'BASE': {'easy': 2, 'moderate': 1, 'hard': 2, 'long': 1},
                'BUILD': {'easy': 2, 'moderate': 1, 'hard': 3, 'long': 1},
                'PEAK': {'easy': 1, 'moderate': 1, 'hard': 3, 'sprint': 1},
                'TAPER': {'easy': 2, 'moderate': 0, 'hard': 1, 'sprint': 1}
            }
        },
        'ELITE': {
            'GRAN_FONDO': {
                'BASE': {'easy': 2, 'moderate': 1, 'hard': 2, 'long': 1, 'strength': 1},
                'BUILD': {'easy': 2, 'moderate': 1, 'hard': 3, 'long': 1, 'strength': 1},
                'PEAK': {'easy': 1, 'moderate': 1, 'hard': 4, 'long': 1, 'strength': 1},
                'TAPER': {'easy': 2, 'moderate': 0, 'hard': 1, 'long': 1, 'strength': 0}
            },
            'ROAD_RACE': {
                'BASE': {'easy': 2, 'moderate': 1, 'hard': 2, 'sprint': 1, 'strength': 1},
                'BUILD': {'easy': 2, 'moderate': 1, 'hard': 3, 'sprint': 2, 'strength': 1},
                'PEAK': {'easy': 1, 'moderate': 1, 'hard': 3, 'sprint': 2, 'strength': 0},
                'TAPER': {'easy': 2, 'moderate': 0, 'hard': 1, 'sprint': 1, 'strength': 0}
            }
        }
    }
    
    return matrix[level][specialty][phase]
```

---

## Raccomandazioni Pratiche

### Principiante
- ✅ **Essenziale**: 3-4 sessioni/settimana
- ✅ **Essenziale**: FTP determinato tramite test o stima
- ✅ **Consigliato**: 1 sessione qualità + 1 long settimanale
- ⚠️ **Evitare**: >5 sessioni/settimana (rischio di overtraining)
- 📊 **Metriche**: Monitorare cadenza (85-95 RPM), watts per zona

### Intermedio
- ✅ **Essenziale**: 4-5 sessioni/settimana
- ✅ **Essenziale**: 2 sessioni hard (threshold + intervalli/tempo)
- ✅ **Essenziale**: 1 long steady domenica
- ✅ **Consigliato**: 1 strength ciclo-specifico
- 📊 **Target ACWR**: 0.8-1.0
- 📊 **Weekly TSS**: 400-550

### Avanzato
- ✅ **Essenziale**: 5-6 sessioni/settimana
- ✅ **Essenziale**: 2-3 sessioni hard (VO2max, threshold, tempo/moderato)
- ✅ **Essenziale**: 1 long gran fondo spec
- ✅ **Essenziale**: 1-2 strength
- ✅ **Consigliato**: 2-3 doppi sessioni/settimana (easy pair)
- 📊 **Target ACWR**: 0.75-1.0
- 📊 **Weekly TSS**: 600-800

### Elite
- ✅ **Essenziale**: 6-8 sessioni/settimana
- ✅ **Essenziale**: 3-4 hard sessions (VO2max, threshold, sprint, race sim)
- ✅ **Essenziale**: 1 long ultra-endurance (200+ km)
- ✅ **Essenziale**: 1-2 strength
- ✅ **Essenziale**: 3-4 doppi sessioni/settimana
- ✅ **Essenziale**: Back-to-back hard possibili con recupero adeguato
- 📊 **Monitor**: FTP progress, watts/kg trend, cadenza consistency
- 📊 **Target ACWR**: 0.85-1.15
- 📊 **Weekly TSS**: 1000-1400

---

## Checklist per LLM Implementation

- [ ] FTP validato/stimato
- [ ] Sessioni allineate con livello
- [ ] TSS settimanale coerente con ore disponibili
- [ ] Hard sessions non back-to-back (max stesso giorno easy+hard)
- [ ] Long ride settimanale presente (tutte fasi)
- [ ] Strength sessioni per intermedio+
- [ ] IF e NP calcolati accuratamente
- [ ] ACWR stimato < 1.2 build, < 1.0 peak
- [ ] Rest days presenti (principiante+intermedio)
- [ ] Messaggi personalizzati per specialty

---

**Documento creato per implementazione LLM - Cycling Training Periodization v1.0 (2025)**