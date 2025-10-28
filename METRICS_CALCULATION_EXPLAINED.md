# Spiegazione Dettagliata del Calcolo CTL/ATL/TSB

## Data: 28 Ottobre 2025

## Situazione Attuale

- **Ultima attività:** 15 Ottobre 2025 (13 giorni fa)
- **Attività negli ultimi 42 giorni:** 15 attività
- **CTL attuale:** 28.26
- **ATL attuale:** 42.45
- **TSB attuale:** -14.19 (status: "fatigued")

## Domanda Chiave

**Perché TSB è -14.19 dopo 13 giorni senza allenamento?**

## Come Funziona il Calcolo

### 1. TSS (Training Stress Score)

Il TSS misura il "carico" di ogni allenamento:

```
TSS = (Durata in ore) × IF² × 100
```

Dove IF (Intensity Factor) è l'intensità dell'allenamento (0.0 - 1.5+).

**Esempio:** 
- Corsa di 1 ora a intensità 0.75 = 1 × 0.75² × 100 = **56.25 TSS**

### 2. CTL (Chronic Training Load) - "Fitness"

CTL rappresenta il tuo livello di fitness a lungo termine.

**Caratteristiche:**
- **Time constant:** 42 giorni (~6 settimane)
- **Decade lentamente** (serve tempo per costruire/far decadere la fitness)
- Si calcola con **esponential moving average**

**Formula:**
```
CTL(t) = CTL(t-1) + (TSS(t) - CTL(t-1)) × λ_ctl
```

Dove `λ_ctl = 1 - e^(-1/6) ≈ 0.153`

Ogni giorno:
- Se fai un allenamento, CTL sale
- Se non fai niente (TSS=0), CTL scende del ~15% del gap verso 0

### 3. ATL (Acute Training Load) - "Fatica"

ATL rappresenta la fatica attuale.

**Caratteristiche:**
- **Time constant:** 7 giorni (1 settimana)
- **Decade velocemente** (la fatica diminuisce in pochi giorni)
- Si calcola con **exponential moving average**

**Formula:**
```
ATL(t) = ATL(t-1) + (TSS(t) - ATL(t-1)) × λ_atl
```

Dove `λ_atl = 1 - e^(-1/1) ≈ 0.632`

Ogni giorno:
- Se fai un allenamento, ATL sale rapidamente
- Se non fai niente, ATL scende velocemente del ~63% verso 0

### 4. TSB (Training Stress Balance) - "Forma/Stato"

TSB rappresenta la tua forma attuale.

**Formula:**
```
TSB = CTL - ATL
```

**Interpretazione:**
- **TSB > 10:** "Fresh" - ben riposato, pronto per allenamenti intensi
- **TSB 0-10:** "Optimal" - equilibrio fitness/fatica
- **TSB < -10:** "Fatigued" - affaticato, serve riposo

## Perché TSB = -14.19 Dopo 13 Giorni?

### Analisi Matematica

Dati attuali:
- **CTL = 28.26** (stato di fitness)
- **ATL = 42.45** (stato di fatica)
- **TSB = -14.19** (ATL > CTL, quindi "fatigued")

**Perché ATL è ancora alto dopo 13 giorni?**

Con `λ_atl = 0.632`, ogni giorno ATL scende del 63% del gap verso 0.

**Simulazione del decadimento:**

```
Giorno 0 (15 Ott): ATL = 100 (assumiamo valore alto dopo carico intenso)
Giorno 1: ATL = 100 × 0.368 ≈ 36.8
Giorno 2: ATL = 36.8 × 0.368 ≈ 13.5
Giorno 3: ATL = 13.5 × 0.368 ≈ 5.0
Giorno 4: ATL = 5.0 × 0.368 ≈ 1.8
...
```

**Ma il problema è che nei giorni precedenti hai fatto allenamenti!**

Se il 14 ottobre avevi ATL=42.45 e hai fatto un allenamento da 25.23 TSS:
```
ATL = 42.45 + (25.23 - 42.45) × 0.632
ATL = 42.45 + (-17.22) × 0.632
ATL = 42.45 - 10.88 = 31.57
```

Poi nei 13 giorni senza allenamento:
```
Giorno 1: ATL = 31.57 × 0.368 = 11.62
Giorno 2: ATL = 11.62 × 0.368 = 4.28
Giorno 3: ATL = 4.28 × 0.368 = 1.57
Giorno 4: ATL = 1.57 × 0.368 = 0.58
Giorno 5: ATL = 0.58 × 0.368 = 0.21
...
```

**Ma aspetta!** La formula dell'exponential moving average non è solo moltiplicazione.

### Formula Corretta

La formula corretta dell'exponential moving average è:

```
ATL(t) = (1 - λ) × ATL(t-1) + λ × TSS(t)
```

Con TSS=0 (giorni di riposo):
```
ATL(t) = (1 - 0.632) × ATL(t-1) = 0.368 × ATL(t-1)
```

Quindi ogni giorno ATL si riduce al 36.8% del valore precedente.

### Calcolo Effettivo per i Tuoi Dati

Stiamo vedendo TSS degli ultimi 42 giorni, quindi includiamo:

**Ultime attività:**
1. 15 Ott (13 giorni fa): 25.23 TSS
2. 13 Ott (15 giorni fa): 46.61 TSS  
3. 12 Ott (16 giorni fa): 101.28 TSS
4. 9 Ott (19 giorni fa): 46.21 TSS
5. 8 Ott (20 giorni fa): 50.68 TSS

...e altre 10 attività distribuite dal 6 Ottobre al 29 Settembre.

**Problema:** CTL e ATL non sono valori "snapshot" ma sono calcolati sui **42 giorni precedenti**. 

Questo significa che:
- 13 giorni fa hai fatto un allenamento (25.23 TSS)
- 14 giorni fa potresti aver fatto altri allenamenti
- E così via...

Il valore ATL attuale riflette l'effetto di tutti questi allenamenti passati.

## Verifica del Calcolo

Per verificare se il calcolo è corretto, analizziamo cosa succede nel codice:

### File: `app/services/statistics_service.py` (righe 64-101)

```python
# Get activities from last 42 days
activities = self.db.execute(
    select(StravaActivity)
    .where(and_(
        StravaActivity.strava_account_id.in_(strava_account_ids),
        StravaActivity.start_date >= start_date,
        StravaActivity.tss.isnot(None)
    ))
    .order_by(StravaActivity.start_date)
).scalars().all()

# Group TSS by date
daily_tss = {}
for activity in activities:
    activity_date = activity.start_date.date()
    daily_tss[activity_date] = daily_tss.get(activity_date, 0) + (activity.tss or 0)

# Build complete list of ALL days in period (most recent first)
tss_list = []
for i in range(42):
    day_date = end_date - td(days=i)
    tss_for_day = daily_tss.get(day_date, 0)  # 0 for rest days
    tss_list.append(tss_for_day)

# Calculate CTL/ATL/TSB for TODAY
metrics = self.metrics_service.calculate_ctl_atl_tsb(tss_list)
```

**Cosa fa:**
1. Prende tutte le attività degli ultimi 42 giorni
2. Raggruppa per data e somma il TSS
3. Crea una lista di 42 valori TSS (un valore per ogni giorno)
4. Passa questa lista a `calculate_ctl_atl_tsb()`

### File: `app/services/metrics_calculation_service.py` (righe 253-305)

```python
def calculate_ctl_atl_tsb(self,
                          daily_tss: List[float],
                          ctl_days: int = 42,
                          atl_days: int = 7,
                          include_rest_days: bool = True) -> Dict[str, float]:
    # Calculate exponential smoothing constants
    ctl_tc = ctl_days / 7.0  # time constant in weeks
    atl_tc = atl_days / 7.0   # time constant in weeks
    
    # Exponential smoothing factor
    ctl_lambda = 1.0 - math.exp(-1.0 / ctl_tc)  # ≈ 0.153
    atl_lambda = 1.0 - math.exp(-1.0 / atl_tc)   # ≈ 0.632
    
    # Initialize with first value (or 0 if list is empty)
    ctl = daily_tss[0] if len(daily_tss) > 0 else 0.0
    atl = daily_tss[0] if len(daily_tss) > 0 else 0.0
    
    # Apply exponential moving average
    for tss in daily_tss[1:]:
        ctl = ctl + (tss - ctl) * ctl_lambda
        atl = atl + (tss - atl) * atl_lambda
    
    # TSB = CTL - ATL
    tsb = ctl - atl
    
    return {
        'ctl': round(ctl, 2),
        'atl': round(atl, 2),
        'tsb': round(tsb, 2)
    }
```

**Cosa fa:**
1. Calcola le costanti `λ_ctl` e `λ_atl`
2. Inizializza CTL e ATL con il primo valore TSS
3. Per ogni giorno successivo, aggiorna CTL e ATL con l'exponential moving average
4. Calcola TSB = CTL - ATL

## Simulazione Manuale

Proviamo a simulare manualmente cosa succede:

**Assumiamo questi TSS per gli ultimi 42 giorni (dal 16 Set al 28 Ott):**

```
Giorno    TSS    ATL (calcolato)
42        0      0
41        0      0
...
13        25.23  25.23  ← ultimo allenamento
12        0      9.54
11        0      3.51
10        0      1.29
...
1         0      0.01
0 (oggi)  0      0.00
```

**Ma questo non è corretto!** 

Il problema è che stiamo guardando i dati dall'inizio della finestra (42 giorni fa) invece che dall'ultimo allenamento.

## Il Vero Problema

Il calcolo **include i giorni senza allenamento** nel periodo di 42 giorni.

**Esempio:**
- Se hai fatto un allenamento intenso il 14 Ottobre (101.28 TSS)
- Poi non hai fatto niente per 13 giorni
- ATL dovrebbe scendere rapidamente

**Ma il calcolo considera:**
1. I giorni PRIMA dell'ultimo allenamento
2. L'ultimo allenamento
3. I 13 giorni di riposo

E l'ATL finale è il risultato dell'exponential moving average su tutti questi giorni.

## Verifica Empirica

Per verificare se il calcolo è corretto, creiamo uno script che:
1. Prende TSS per ogni giorno degli ultimi 42 giorni
2. Calcola ATL manualmente
3. Confronta con il valore del sistema

Vuoi che crei questo script di verifica?

## Conclusioni

**TSB = -14.19 dopo 13 giorni è possibile se:**
1. Hai accumulato fatica significativa nelle settimane precedenti
2. Il calcolo ATL include tutti i 42 giorni precedenti
3. ATL decade più velocemente di CTL, ma CTL è più basso di ATL

**Perché ATL (42.45) > CTL (28.26)?**

Questo significa che hai accumulato più fatica (ATL) che fitness (CTL) nelle ultime settimane. Con 13 giorni di riposo, ATL sta scendendo ma CTL scende ancora più velocemente (perché CTL era già più basso di ATL).

**Quando TSB diventerà positivo?**

Quando ATL scende sotto CTL. Con il decadimento esponenziale:
- ATL scende del 63% ogni giorno
- CTL scende del 15% ogni giorno

Ma poiché ATL è partito più alto, ci vorranno alcuni giorni prima che ATL scenda sotto CTL.

## Prossimi Passi

1. Creare uno script di verifica per controllare i calcoli
2. Mostrare i TSS per ogni giorno degli ultimi 42 giorni
3. Simulare ATL/CTL/TSB manualmente
4. Verificare se c'è un bug nel calcolo

Vuoi che proceda con la creazione di questo script di verifica?

