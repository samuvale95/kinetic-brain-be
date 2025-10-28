# Come Sono Definite le Zone Cardiache

## Metodi di Definizione Zone

Ci sono diversi metodi per definire le zone di frequenza cardiaca personalizzate:

### 1. **Percentuali di Max HR (quello che stiamo usando)**

Il metodo più semplice. Le zone sono definite come percentuale del HR massimo.

**Formula:**
```
Z1: 50-60% di max HR
Z2: 60-70% di max HR  
Z3: 70-80% di max HR
Z4: 80-90% di max HR
Z5: 90-100% di max HR
```

**Esempio con max HR = 190 bpm:**
- Z1: 95-114 bpm
- Z2: 114-133 bpm
- Z3: 133-152 bpm
- Z4: 152-171 bpm
- Z5: 171-190 bpm

**Vantaggi:** Semplice, non richiede test
**Svantaggi:** Meno preciso, max HR varia per età/genere

### 2. **Zone di Frequenza Cardiaca a Riserva (Heart Rate Reserve - HRR)**

Più preciso perché considera anche il resting HR.

**Formula:**
```
HRR = Max HR - Resting HR
Zone = Resting HR + (HRR × Percentuale)

Z1: Resting HR + (HRR × 50-60%)
Z2: Resting HR + (HRR × 60-70%)
Z3: Resting HR + (HRR × 70-80%)
Z4: Resting HR + (HRR × 80-90%)
Z5: Resting HR + (HRR × 90-100%)
```

**Esempio con max HR = 190, resting HR = 50:**
- HRR = 140
- Z1: 50 + (140 × 0.50-0.60) = 120-134 bpm
- Z2: 50 + (140 × 0.60-0.70) = 134-148 bpm
- Z3: 50 + (140 × 0.70-0.80) = 148-162 bpm
- Z4: 50 + (140 × 0.80-0.90) = 162-176 bpm
- Z5: 50 + (140 × 0.90-1.00) = 176-190 bpm

**Vantaggi:** Più accurato per persone diverse
**Svantaggi:** Richiede conoscere resting HR

### 3. **Zone Basate su LTHR (Lactate Threshold HR)**

Il metodo **più preciso** per atleti seri. Basato su un test di sforzo.

**Famosa formula di Joe Friel (Training Bible):**

```
Zone 1: 65-80% di LTHR
Zone 2: 81-90% di LTHR
Zone 3: 91-100% di LTHR  
Zone 4: 101-105% di LTHR
Zone 5a: 106-115% di LTHR
Zone 5b: 116-125% di LTHR
Zone 5c: >126% di LTHR
```

**Esempio con LTHR = 165 bpm:**
- Z1: 107-132 bpm
- Z2: 134-149 bpm
- Z3: 150-165 bpm
- Z4: 167-173 bpm
- Z5a: 175-190 bpm
- Z5b: 191-206 bpm
- Z5c: >208 bpm

**Come trovare il tuo LTHR:**
- Test in laboratorio (lattatemia)
- Test sul campo: 30 min a sforzo massimo sostenibile, LTHR = avg degli ultimi 20 min
- Test di 8 min: LTHR ≈ 90-95% di HR finale

**Vantaggi:** Molto accurato, basato sulla fisiologia reale
**Svantaggi:** Richiede un test

### 4. **Formula di Tanaka (stima Max HR)**

Stima il max HR basato sull'età:

```
Max HR = 208 - (0.7 × age)
```

Poi usa % di questo max HR come nel metodo 1.

**Esempio 35 anni:**
- Max HR stimato = 208 - (0.7 × 35) = 183.5 bpm

**Vantaggi:** Più accurato della vecchia formula 220-age
**Svantaggi:** Ancora solo una stima

---

## Come Noi Abbiamo Configurato le Zone

### Metodo Attuale (Stimato)

Abbiamo calcolato il max HR basandoci sull'HR medio delle tue attività:

```
Max HR stimato = Average HR + offset

Dove offset dipende dall'average HR:
- Se avg HR > 150 → +40 (giovane, intenso)
- Se avg HR > 130 → +50 (moderato)  
- Se avg HR < 130 → +60 (più anziano)
```

Poi abbiamo applicato le % standard del max HR.

### Zone Create:

```
Max HR stimato: 168 bpm
Resting HR: 60 bpm (default)

Z1: 84-100 bpm   (50-60%)
Z2: 100-117 bpm  (60-70%)
Z3: 117-134 bpm  (70-80%)
Z4: 134-151 bpm  (80-90%)
Z5: 151-168 bpm  (90-100%)
```

---

## Come Personalizzare le Zone

### Opzione 1: Modificare PerformanceMetrics nel Database

```sql
UPDATE performance_metrics
SET zones_json = '{
  "z1": {"min": 90, "max": 108},
  "z2": {"min": 108, "max": 126},
  "z3": {"min": 126, "max": 144},
  "z4": {"min": 144, "max": 162},
  "z5": {"min": 162, "max": 180}
}'
WHERE user_id = 1 AND metric_type = 'hr';
```

### Opzione 2: Fare un Test Reale

1. **Test LTHR (raccomandato):**
   - 10 min warm-up
   - 30 min alla massima velocità sostenibile
   - Prendi l'HR medio degli ultimi 20 min = LTHR
   - Usa le % di Friel sopra

2. **Test Max HR (meno raccomandato):**
   - Warm-up
   - Sforzi incrementali
   - Ultimo sforzo massimo = max HR

3. **Resting HR:**
   - Misura al mattino dopo almeno 7 giorni di training normale
   - Prendi la media di 5 giorni

### Opzione 3: Aggiornare tramite API

Creare un endpoint per impostare le zone personalizzate:

```python
@router.post("/user/zones")
async def set_user_zones(zones: ZoneConfig, ...):
    # Salva zones personalizzate
    pass
```

---

## Raccomandazione

Per la maggior parte delle persone, **le zone basate su % di max HR funzionano bene**.

Se sei un atleta serio o vuoi massima precisione, fai un **test LTHR** e usa quelle zone.

---

## Fonti

- **Training Bible** - Joe Friel (LTHR)
- **Training Zones** - Garmin, Wahoo, etc.
- **Research** - Stephen Seiler (polarized training)
