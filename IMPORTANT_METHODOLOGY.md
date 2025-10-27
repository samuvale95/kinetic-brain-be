# TrainingPeaks Methodology - Important Notes

## 🎯 Gestione dei Giorni di Riposo

### Perché è Cruciale

Il sistema di calcolo CTL/ATL/TSB di TrainingPeaks **include TUTTI i giorni nel periodo**, anche quelli senza allenamento (TSS=0). Questo è fondamentale perché:

### 1. Exponential Decay

L'algoritmo di **moving average esponenziale** applica il decadimento **ogni singolo giorno**, inclusi i giorni di riposo:

```
CTL_domani = CTL_oggi + (TSS_oggi - CTL_oggi) × λ
```

- Se oggi è un giorno di riposo (TSS=0), la CTL **diminuisce** leggermente
- Se oggi è un giorno di allenamento, la CTL **aumenta** proporzionalmente
- Dopo 42 giorni di assoluto riposo, la CTL scende a ~0 (perdita quasi totale di fitness)

### 2. Completezza del Dataset

**SBAGLIATO:**
```python
daily_tss = [100, 120, 110, 85]  # Solo giorni con attività
```

**CORRETTO:**
```python
daily_tss = [100, 0, 120, 0, 110, 85, 0]  # Tutti i giorni, zero per riposo
```

### 3. Esempio Pratico

**Scenario:** Allenamento ogni 2 giorni per 14 giorni

```
Giorno  TSS  CTL (lambda=0.1)
------  ---  ---------------
  1     100      10.0         ← primo allenamento
  2       0       9.0         ← riposo (decay!)
  3     100      17.1         ← allenamento
  4       0      15.4         ← riposo (decay!)
  5     100      23.9         ← allenamento
  6       0      21.5         ← riposo (decay!)
...
```

**Nota:** Anche quando TSS=0, la CTL continua a muoversi (decade). Questo è corretto!

## 📊 Implementazione nel Codice

### `metrics_calculation_service.py`

```python
def calculate_ctl_atl_tsb(self,
                          daily_tss: List[float],
                          include_rest_days: bool = True):
    """
    IMPORTANT: If include_rest_days=True, the algorithm considers ALL days,
    including days with 0 TSS (rest days), which is crucial for decay.
    """
    for tss in daily_tss[1:]:
        # Apply decay even on rest days (TSS=0)
        ctl = ctl + (tss - ctl) * ctl_lambda
        atl = atl + (tss - atl) * atl_lambda
```

### `strava_service.py`

```python
def _calculate_initial_fitness_metrics(self, user_id: int):
    """
    Build complete list of ALL days in period (most recent first).
    This is critical: we include days with 0 TSS (rest days).
    """
    # Get activities in last 42 days
    daily_tss = {}  # Only days with activity
    
    # Build COMPLETE list of all 42 days
    tss_list = []
    for i in range(42):
        day_date = end_date - timedelta(days=i)
        tss_for_day = daily_tss.get(day_date, 0)  # 0 for rest days
        tss_list.append(tss_for_day)
    
    # Calculate metrics with ALL days (including zeros)
    metrics = self.metrics_service.calculate_ctl_atl_tsb(tss_list)
```

## 🔍 Verifica

Per verificare che i riposi siano considerati:

1. **Controlla il log dei calcoli:**
```bash
# Dovrebbe mostrare tutti i giorni, non solo quelli con attività
daily_tss = [100, 0, 0, 120, 0, 85, ...]  # ✅
```

2. **Test:**
```python
# Test con riposi frequenti
daily_tss = [100, 0, 100, 0, 100, 0]  # 3 giorni di allenamento, 3 di riposo
metrics = service.calculate_ctl_atl_tsb(daily_tss)

# TSB dovrebbe essere più negativo (più faticato)
# perché 3 allenamenti intensi in 6 giorni
assert metrics['atl'] > 50  # Fatigue alta
assert metrics['tsb'] < -10  # Forma negativa
```

## ⚠️ Errori Comuni da Evitare

### ❌ Errore 1: Filtrare i giorni di riposo
```python
# SBAGLIATO
daily_tss = [tss for tss in all_days if tss > 0]
```

### ❌ Errore 2: Usare solo giorni con attività
```python
# SBAGLIATO
activities = get_activities_in_period()
daily_tss = [activity.tss for activity in activities]
```

### ✅ Corretto
```python
# CORRETTO
for day in all_days_in_period:
    tss = activities.get(day, 0)  # 0 per riposo
    daily_tss.append(tss)
```

## 📈 Esempio: Atleta Che Si Allena Ogni Altro Giorno

**Periodo:** 14 giorni
**Pattern:** Allenamento ogni 2 giorni

```
Giorno 01: TSS = 80   → CTL aumenta
Giorno 02: TSS = 0    → CTL DECADE
Giorno 03: TSS = 90   → CTL aumenta
Giorno 04: TSS = 0    → CTL DECADE
Giorno 05: TSS = 75   → CTL aumenta
Giorno 06: TSS = 0    → CTL DECADE
...
```

**Risultato finale:** CTL sarà significativamente diversa rispetto a se avessimo ignorato i giorni di riposo!

## 🎓 Conclusione

**Il decadimento esponenziale funziona OGNI GIORNO**, inclusi i riposi. Questo è:
- Matematicamente corretto
- Fisiologicamente realistico
- Coerente con TrainingPeaks
- Essenziale per TSB accurati

**Non ignorare mai i giorni di riposo nel calcolo di CTL/ATL/TSB!**

