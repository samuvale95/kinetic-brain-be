# Guida Completa alla Gestione dei Carichi di Allenamento per Sport di Endurance
## Applicazioni LLM per Allenamenti Personalizzati

---

## Indice

1. [Introduzione](#introduzione)
2. [Metriche Essenziali di Monitoraggio](#metriche-essenziali-di-monitoraggio)
3. [Sport Specifici: Gestione dei Carichi](#sport-specifici-gestione-dei-carichi)
4. [Triathlon: Integrazione Multi-Disciplinare](#triathlon-integrazione-multi-disciplinare)
5. [Progressione e Periodizzazione](#progressione-e-periodizzazione)
6. [Implementazione LLM](#implementazione-llm)
7. [Considerazioni per l'Applicazione](#considerazioni-per-lapplicazione)

---

## Introduzione

La gestione del carico di allenamento negli sport di endurance rappresenta una delle sfide più critiche per atleti e coach. A differenza di quanto si pensasse nel passato, non esiste un incremento universale valido per tutti gli sport e i livelli di esperienza. La progressione del carico dipende da fattori interconnessi che includono:

- **Sport specifico** (running, cycling, trail running, nuoto)
- **Livello dell'atleta** (principiante, intermedio, avanzato)
- **Carico cronico di partenza** (adattamenti pregressi dell'organismo)
- **Obiettivi della stagione** (base building, peak, competizione)
- **Capacità individuale di recupero** (sonno, stress, nutrizione)

Un'applicazione LLM deve integrarsi con dati oggettivi provenienti da wearable e tracker per generare piani di allenamento realmente personalizzati e sicuri.

---

## Metriche Essenziali di Monitoraggio

Per progettare un sistema LLM efficace nella generazione di allenamenti, sono necessarie metriche specifiche che quantifichino il carico di allenamento sia dal punto di vista **esterno** (ciò che l'atleta fa) che **interno** (come l'organismo risponde).

### 1. Metriche di Carico Esterno

#### 1.1 Durata e Volume
- **Tempo di allenamento (minuti)**: Fundamental ma insufficiente da solo
- **Distanza (km)**: Per running e cycling
- **Volume d'acqua (m/km)**: Per il nuoto
- **Dislivello positivo (m)**: Cruciale per trail running e cycling in montagna

**Nota importante**: 100 m di dislivello positivo nel trail running equivale approssimativamente a 1 km in pianura in termini di carico energetico.

#### 1.2 Intensità e Potenza

**Per il Ciclismo:**
- **Functional Threshold Power (FTP)**: Massima potenza sostenibile per ~60 minuti, misurata in Watt
- **Normalized Power (NP)**: Potenza ponderata che riflette la variabilità dello sforzo
- **Intensity Factor (IF)**: Rapporto tra NP e FTP (IF = NP/FTP)
- **Cadenza**: Giri di pedali al minuto (RPM), indicatore di efficienza neuromuscolare

**Per Running e Trail Running:**
- **Threshold Pace (TP)**: Velocità mantenibile per ~60 minuti
- **Normalized Pace (NP)**: Velocità ponderata sul terreno (terreno pianeggiante equivalente)
- **Pace per Zona di Allenamento**: Velocità specifica per ogni zona HR
- **Grade-Adjusted Pace**: Velocità corretta per pendenze e terreno (essenziale per trail)

**Per il Nuoto:**
- **Swim FTP**: Distance per minuto sostenibile (~75 m/min è riferimento)
- **Normalized Swim Pace**: Velocità media ponderata per serie
- **Intensity Factor per il Nuoto**: IF = (Normalized Pace) / (Swim FTP)

#### 1.3 Metriche di Gravosità Relativa

**Rating of Perceived Exertion (RPE) Borg 1-10:**
- **RPE 1-2**: Riposo completo/molto facile
- **RPE 3-4**: Facile (conversazione comoda)
- **RPE 5-6**: Moderato (conversazione breve)
- **RPE 7-8**: Difficile (parole isolate)
- **RPE 9**: Molto difficile (no talking)
- **RPE 10**: Massimo sforzo

---

### 2. Metriche di Carico Interno (Stress Fisiologico)

#### 2.1 Training Stress Score (TSS)

**Applicabile a**: Ciclismo, running (con power meter), nuoto (con metriche normalizzate)

**Formula TSS:**
```
TSS = ((Secondi × NP × IF) / (FTP × 3600)) × 100
```

**Interpretazione:**
- **0-50 TSS**: Allenamento di recupero, affaticamento minimo
- **50-100 TSS**: Allenamento moderato, affaticamento gestibile
- **100-150 TSS**: Allenamento impegnativo, richiede recupero
- **150-200 TSS**: Sessione molto intensa, richiede 1-2 giorni di recupero
- **>200 TSS**: Estremamente demanding, affaticamento residuo per giorni

**Esempio pratico:**
Un ciclista con FTP 250W che svolge un'uscita di 90 minuti a 220W di potenza normalizzata:
- NP = 220W
- IF = 220/250 = 0.88
- TSS = ((5400 × 220 × 0.88) / (250 × 3600)) × 100 = 117 TSS

#### 2.2 Training Impulse (TRIMP)

**Applicabile a**: Running, nuoto, sport in cui i dati di potenza non sono disponibili

**Formula base TRIMP:**
```
TRIMP = Durata (min) × Intensità × Fattore di Pesatura
```

**Dove:**
- **Intensità** = (HR media - HR riposo) / (HR max - HR riposo)
- **Fattore di Pesatura** = varia da 0.75 a 1.97 a seconda dell'intensità

**Metodo semplificato (Lucia):**
```
TRIMP = Durata (min) × % della FC di Soglia
```

Per un runner che corre per 45 minuti a FC 165 bpm con FC Soglia 170 bpm:
- TRIMP = 45 × (165/170) = 43.6

#### 2.3 Performance Management Chart (PMC)

Il PMC integra i dati di TSS/TRIMP in tre metriche aggregate:

**Chronic Training Load (CTL) - "Fitness"**
- Media pesata dei TSS degli ultimi **42 giorni**
- Rappresenta la **capacità di lavoro accumulata** e l'adattamento
- Range tipico: 40-100 per principianti; 100-250+ per atleti avanzati
- Crescita ottimale: **5-10% settimanale massimo** per evitare plateau di adattamento

**Acute Training Load (ATL) - "Fatica"**
- Media dei TSS degli ultimi **7 giorni**
- Rappresenta lo **stress fisiologico recente** e il bisogno di recupero
- Range sano: ATL < CTL + 50% per minimizzare infortuni

**Training Stress Balance (TSB) - "Forma"**
```
TSB = CTL - ATL
```

**Interpretazione:**
- **TSB > +10**: Fresco, pronto per sforzi intensi (ideale per competizioni)
- **TSB +5 a +10**: Forma ottimale, pronto per allenamenti qualità
- **TSB 0 a -5**: Forma buona, affaticamento leggero accumulo
- **TSB -5 a -20**: Affaticamento cumulativo, adattamento in corso (necessario ma richiede equilibrio)
- **TSB < -20**: Sovrallenamento imminente, rischio infortuni elevato

---

### 3. Rapporto Acute:Chronic Workload (ACWR)

```
ACWR = ATL (7 giorni) / CTL (42 giorni media)
```

**Interpretazione scientifica:**
- **ACWR 0.8-1.3**: Range ottimale per adattamento e prestazioni senza eccesso di rischio
- **ACWR 1.5-1.8 con basso CTL**: Rischio infortuni aumentato di 2.5-3.3x
- **ACWR > 2.0**: Altissimo rischio di infortuni, overreaching acuto
- **ACWR < 0.8**: Sotto-preparazione, mancanza di stimolo allenante

**Implicazione pratica:** Se l'ATL sale troppo rapidamente rispetto al CTL (aumento settimana su settimana > 10%), il sistema aumenta il rischio di infortuni anche se i numeri assoluti non sono elevati.

---

### 4. Metriche di Recupero e Readiness

#### 4.1 Variabilità della Frequenza Cardiaca (HRV)

**Definizione**: Variazione dei tempi tra battiti cardiaci consecutivi, misura dell'attività nervosa autonoma.

**Parametri principali:**
- **RMSSD** (Root Mean Square of Successive Differences): Parametro principale, in millisecondi
- **LF/HF Ratio**: Rapporto tra attività simpatica (stress) e parasimpatica (recupero)

**Interpretazione per allenamento:**
- **HRV normale o in aumento**: Recupero adeguato, pronto per stimoli intensi
- **HRV in calo consistente**: Segnale di affaticamento, ridurre intensità
- **HRV aumenta dopo riposo**: Indicazione di supercompensazione iniziata
- **Soglia personale**: Ogni atleta ha baseline propria; monitorare le **tendenze** più che i numeri assoluti

**Soglia di allerta generale:**
- Calo HRV > 10% dal baseline per 2+ giorni = considerare scarico o sessione leggera

#### 4.2 Frequenza Cardiaca a Riposo (RHR)

- **RHR elevata (>5-10 bpm dalla baseline)**: Segnale di affaticamento accumulato
- **RHR stabile o in calo**: Indicazione di buon recupero
- **Variabilità giornaliera > 5 bpm**: Fattore confondente (stress, infezione, sonno povero)

#### 4.3 Excess Post-Exercise Oxygen Consumption (EPOC)

**Utilizzato da**: Garmin, Coros

- Stima il metabolismo post-esercizio
- Correlato al "costo" della sessione
- Valori più alti = maggiore stress fisiologico = più recupero necessario
- Integra automaticamente intensità e durata

---

### 5. Metriche Sport-Specifiche Critiche

#### Running:
- **Lactate Threshold Pace (LTP)**: Velocità di soglia, ~90% del massimo
- **VO2max equivalent pace**: Velocità a massimo consumo ossigeno, ~100-110% del massimo
- **Ground Contact Time (GCT)**: Tempo di contatto al suolo (millisecondi) - diminuisce con velocità e affaticamento
- **Vertical Oscillation**: Movimento verticale, indicatore di efficienza

#### Cycling:
- **Watts/kg**: Potenza relativa al peso corporeo (discriminante in salite)
- **95% Peak Power (5s-10s)**: Potenza di sprint, indicatore di capacità neuromuscolare
- **Variability Index**: Indicatore di stabilità sforzo, importante per gare

#### Nuoto:
- **Stroke Rate (SR)**: Bracciate per minuto
- **Stroke Length (SL)**: Distanza coperta per bracciate
- **Swim Index (SI)**: SI = Velocità × Lunghezza bracciate (km/h × m)

#### Trail Running:
- **Power**:Watt sviluppati considerando terreno e pendenza (se calcolato)
- **Injury Risk Index**: Tempo in discesa sostenuto, fattore di rischio aumentato
- **Vertical Kilometer (VK)**: Dislivello in km equivalente

---

## Sport Specifici: Gestione dei Carichi

### RUNNING (Strada)

#### Caratteristiche di Progressione

**Carico esterno misurato come:**
- Km settimanali + intensità (velocità media)
- TRIMP settimanale totale
- TSS equivalente (con conversione da TRIMP)

#### Incrementi Settimanali Raccomandati

| Livello | Incremento Settimanale | Note |
|---------|----------------------|-------|
| **Principiante** | 10-15% per 3-4 settimane | Tollerano più variabilità, adattamento neuromuscolare rapido |
| **Intermedio** | 7-10% per 4-6 settimane | Carico cronico più elevato, margini ridotti |
| **Avanzato** | 5% massimo | Alto CTL preesistente, ridotta tolleranza a salti |

#### Distribuzione dell'Intensità (80/20)

- **80% del volume**: Zone 1-3 (aerobica leggera), FC 60-75% del max
- **20% del volume**: Zone 4-5 (tempi + intervalli), FC 85-100% del max
- **Sessioni ad alta intensità**: 2 al massimo settimanali

#### Esempio di Progressione 12 Settimane (Principiante)

```
Settimana 1-2: 25 km/settimana, ~150 TRIMP totale
  - 3 uscite da 7-8 km aerobica
  - 1 uscita da 5 km con ritmo variabile (50 TRIMP)

Settimana 3-4: 28 km/settimana (~165 TRIMP) +12% volume
  - 3 uscite aerobica estese: 8-9 km
  - 1 sessione qualità: 5×4' a tempo (80 TRIMP)

Settimana 5-6: 32 km/settimana (~185 TRIMP) +14% volume
  - Uscite aerobica: 9-10 km
  - Sessione qualità: 6×5' + medio di 4' (95 TRIMP)

Settimana 7: SCARICO - 18 km/settimana (~110 TRIMP) -45%
  - Tutte aerobica leggera, focus recupero

Settimana 8-10: 36 km/settimana (~215 TRIMP)
  - Incrementi riprendono da nuova baseline

Settimana 11: SCARICO - 21 km (~130 TRIMP)

Settimana 12: COMPETIZIONE - target specifico
```

#### Fattori Critici per Monitoraggio

1. **ACWR**: Mantenerlo 0.8-1.3, particolarmente in fasi di salita
2. **HRV**: Calo > 10% suggerisce scarico imminente
3. **RPE delle uscite**: Se RPE richiesto sale per stesse velocità = affaticamento
4. **Dolori ricorrenti**: Qualsiasi area con fastidio ripetuto = ridurre carico immediato

---

### CICLISMO (Strada)

#### Carico Esterno

Misurato in **Training Stress Score (TSS)** o **Chronic Training Load (CTL)**

#### CTL Target per Livello

| Livello | CTL Tipico | TSS Settimanale | Sessioni/Settimana |
|---------|-----------|-----------------|-------------------|
| **Principiante** | 40-60 | 180-280 | 3-4 |
| **Intermedio** | 60-100 | 300-450 | 4-5 |
| **Avanzato** | 100-150+ | 500-700+ | 5-6 |

#### Incrementi Settimanali

- **CTL ideale**: Crescita di 5-10 punti settimanali massimo
- **ATL**: Variare tra 40-60% del CTL per evitare overreaching
- **TSB**:Mantenere TSB positivo (0 a +20) nelle fasi di costruzione, -10 a -20 solo in microblock intensi

#### Distribuzione Sessioni Settimanali

**Per atleta intermedio (CTL ~80):**
- **1 sessione lunga aerobica**: 2-3 ore, IF 0.6-0.75, TSS 120-180
- **2 sessioni medie**: 1.5-2 ore, IF 0.7-0.85, TSS 90-130
- **1 sessione qualità (intervalli)**: 1-1.5 ore, IF 0.85-1.2, TSS 100-150
- **1-2 uscite corte di recupero**: <1 ora, IF 0.5-0.6, TSS 20-40

**Incremento settimanale**: Aggiungere 30-50 TSS per settimana per 4-6 settimane, poi scarico

#### Monitoraggio TSS per Sessione

**Esempio pratico:**
- Uscita di 90' a 220W (FTP 250W): TSS ~117
- Intervalli 5×5' a 300W (FTP 250W): TSS ~130-140 (più concentrato, più affaticante mentale)
- Recupero 30' a 150W: TSS ~15

---

### TRAIL RUNNING

#### Specificità del Trail

Il trail running presenta complicazioni rispetto alla strada:

1. **Dislivello**: Aumenta significativamente carico muscolare ed energetico
2. **Terreno variabile**: Richiede maggior controllo neuromuscolare, isterico muscolare più elevata
3. **Impatto eccentrinico (discese)**: Può causare DOMS (Delayed Onset Muscle Soreness) significativo
4. **Variabilità di velocità**: Difficile mantenere ritmo costante, maggior variabilità TRIMP

#### Conversione del Carico

**Metodo di normalizzazione:**
```
Carico equivalente pianura = Km × Fattore Dislivello + Km Dislivello × 10

Dove Fattore Dislivello = 1.5-2.0 (dipende da pendenza media)
```

**Esempio:**
- 15 km con 1000 m D+
- Carico equivalente = 15 × 1.5 + 100 × 10 = 22.5 + 100 = 122.5 km equivalenti in pianura

#### Incrementi Raccomandati

| Parametro | Incremento Massimo Settimanale |
|-----------|--------------------------------|
| Km totali | 10% |
| Dislivello totale | 15% |
| Km equivalenti pianura | 10% |

**Perché più conservativi?** Il rischio di infortuni da sovraccarico è significativamente più alto nel trail a causa dell'impatto eccentrico delle discese.

#### Progressione Specifica per Trail

**Fasi di progressione (12 settimane):**

1. **Settimane 1-3 (Base)**: Focus su tecnica e frequenza
   - 2-3 uscite/settimana su trail facili
   - Distanze corte: 8-12 km
   - Mantenere dislivello < 400 m/uscita
   - 1 uscita strada per base aerobica

2. **Settimane 4-5**: Introdurre dislivello
   - Aumentare a 12-15 km con 600-800 m D+
   - Aggiungere 1 sessione di tecnica in discesa controllata
   - 1 sessione intervalli in salita (6-8' ripetute su pendenza 8-10%)

3. **Settimana 6 (Scarico)**: Ridurre del 30-40%
   - 2 uscite facili, corte
   - Focus recupero mentale

4. **Settimane 7-9**: Costruzione secondaria
   - Uscite di 15-18 km con dislivello progressivo
   - Max 1000 m per singola uscita
   - 1-2 sessioni intensità: intervalli discesa, salite ripetute, fartlek

5. **Settimana 10 (Scarico)**

6. **Settimane 11-12**: Peak specifico
   - 1 uscita con distanze di gara o superiori
   - Mantenere tecnica nelle discese, non forzare velocità
   - Qualità su salite critiche

#### HRV e Recupero nel Trail

- **Discese**: Danno affaticamento eccentrinico → richiede 48-72h di recupero
- **Monitoraggio HRV critico** dopo sessioni pesanti
- Se HRV cala > 15% dopo sessione discesa, scaricare il successivo

---

### NUOTO

#### Specificità del Nuoto

- **Carico neuro-specifico**: Tecnica è fondamentale, non è solo resistenza
- **Minor impatto sui joint**: Permette carico maggiore in volumi assoluti
- **Ambiente:** Temperatura acqua influenza recupero (acqua fredda = stress aggiuntivo)
- **Meno variabilità meteorologica**: Programmazione più prevedibile

#### Metriche di Carico

**TSS per il Nuoto:**
```
Swim TSS = (IF^3) × (Ore di nuoto) × 100

Dove:
IF = Normalized Swim Pace / Swim FTP
Swim FTP ≈ 75 m/min (riferimento) o testato individualmente
```

#### Incrementi Settimanali

| Livello | Volume Settimanale | Incremento | Frequenza |
|---------|-------------------|-----------|----------|
| **Principiante** | 4-6 km | 10-15% | 2-3 sessioni |
| **Intermedio** | 8-12 km | 7-10% | 3-4 sessioni |
| **Avanzato** | 15-25+ km | 5% | 5-6 sessioni |

#### Struttura Settimanale

**Per nuotatore intermedio (10 km/settimana):**

| Sessione | Volume | Intensità | TSS Equiv. | Note |
|----------|--------|-----------|-----------|------|
| **Lunedì** | 2.5 km | Facile aerobica | 35 | 10×250 easy rec 30" |
| **Mercoledì** | 3 km | Qualità | 60 | Warm 500, 10×100 a ritmo + 500 cool |
| **Venerdì** | 2 km | Molto facile | 25 | Recupero con focus tecnica |
| **Sabato** | 2.5 km | Medio-lungo | 45 | Nuoto continuo + variazioni ritmo |
| **TOTALE** | 10 km | | 165 TSS | |

#### Progressione 8 Settimane

```
Week 1-2: 6 km/settimana, 90 TSS/week, 2 sessioni
Week 3: AUMENTO a 6.8 km (+13%), 105 TSS, aggiungi 3a sessione
Week 4: 7.5 km, mantieni frequenza, aumenta qualità
Week 5: SCARICO, 4.5 km, solo facile
Week 6-7: 8.5 km nuova baseline
Week 8: Target specifico gara
```

#### Fattori Critici

1. **Tecnica stale**: Fatica tecnica si accumula rapidamente, richiedere 1 sessione/settimana recovery
2. **Spalle**: Area critica, monitorare ROM e dolore specifico
3. **Pool vs Open Water**: Transizione richiede 2-3 settimane adattamento
4. **Temperatura**: Acqua < 16°C aumenta stress, richiedere scarico aggiuntivo

---

## TRIATHLON: Integrazione Multi-Disciplinare

### Sfide Specifiche del Triathlon

A differenza degli sport singoli, il triathlon presenta:

1. **Interferenza tra discipline**: Cumul affaticamento neuromuscolare specifico + generale
2. **Prioritizzazione variabile**: Può variare per fase della stagione
3. **Interferenza cronico-atletica**: Sessioni su 3 discipline riducono recupero tra sessioni
4. **Fattore transizioni**: Recovery ridotto tra sport

### CTL Totale e Distribuzione

**CTL Totale Raccomandato per Distanza:**

| Distanza | CTL Totale | TSS Settimanale | Sessioni/Settimana |
|----------|-----------|-----------------|-------------------|
| **Sprint** | 50-80 | 250-350 | 6-8 |
| **Olympic** | 80-120 | 350-500 | 8-12 |
| **Half-Iron** | 120-180 | 500-800 | 10-14 |
| **Full Iron** | 180-250+ | 800-1200+ | 12-18 |

### Modello di Periodizzazione per Triathlon

#### Macrociclo: 16-20 Settimane (Olympic Distance)

**Fase 1: Base (6 settimane)**
- Costruire volume in tutte e 3 le discipline
- Incremento settimanale: 8-10%
- Intensità bassa: 80% volume < 75% max HR
- TSS breakdown: Swim 25%, Bike 45%, Run 30%
- Esempio Week 1: Swim 1800m, Bike 6h, Run 20 km = ~250 TSS totale

**Fase 2: Accumulo (6 settimane)**
- Introdurre intensità specifica per gara
- Incremento: 5-8% (volume limitato, intensità aumenta)
- Sessioni diventano race-specific
- TSS breakdown: Swim 20%, Bike 50%, Run 30%
- Esempio Week 1: Swim 2000m + qualità, Bike 7h con intervalli, Run 22 km con tempo

**Settimana Scarico (dopo Week 6 e 12)**
- Ridurre volume del 40-50%
- Mantenere intensità e frequenza
- Focus recupero fisiologico e mentale
- TSS: 50-60% della normal week

**Fase 3: Peak (4 settimane)**
- Volume ridotto, intensità elevata
- Brick workout: Bike + Run nello stesso giorno
- Pratica nuoto in open water se necessario
- TSS simile a settimane precedenti ma concentrato in pochi giorni
- Esempio: Mon sprint intervals swim, Tue bike + run, Wed easy, Thu tempo swim, Fri long bike, Sat brick, Sun easy

**Settimana Taper (1 settimana prima gara)**
- Volume ridotto 50-60%
- Intensità mantenuta ma durata ridotta
- 1-2 giorni riposo completo
- TSB positivo: +5 a +15

#### Microciclo: Settimana Tipica

**Settimana Tipo - Olympic Distance, Fase Accumulo:**

```
LUNEDI:
  - AM: Nuoto 2000m (Warm 400, 10×100 race pace, Cool 400) - 45 TRIMP
  - PM: Corsa 30' easy - 25 TRIMP
  - Totale: 70 TRIMP

MARTEDI:
  - Bike 2 ore, zone 2-3, 85% bike threshold - 120 TSS
  - Focus: costruzione aerobica

MERCOLEDI:
  - Corsa 45' con 8×3' a tempo (1' rec) - 65 TRIMP
  - Qualità in corsa

GIOVEDI:
  - Nuoto 2500m (Warm 500, 8×150 a ritmo, 6×100 facile, Cool 500) - 65 TRIMP

VENERDI:
  - Riposo o cross-training molto leggero (yoga 20')

SABATO (BRICK):
  - Bike 1.5 ore zona 3 - 85 TSS
  - SUBITO Corsa 30' tempo race pace - 50 TRIMP
  - Pratica transizioni

DOMENICA:
  - Long slow distance: Nuoto 3km OR Bike 3 ore OR Corsa 1h+
  - Rotazione tra discipline

TOTALE SETTIMANA: ~550 TSS (Swim 100, Bike 205, Run 140, Cross 5)
CTL atteso: incremento di ~20-25 punti se partito da 100
```

### Distribuzione Ottimale TSS per Triathlon (Fase Accumulo)

**Principio**: Running ha minor carico TRIMP ma alto infortunio risk, Bike ha alta TSS.

| Disciplina | % del Totale | Priorità nella Stagione | Note |
|-----------|------------|------------------------|------|
| **Nuoto** | 15-20% | Costante | Tecnica complessa, necessita frequenza |
| **Bike** | 45-55% | Variabile | Sport che permette maggior volume |
| **Corsa** | 25-35% | Fase specificità | Sport con rischio infortunio massimo |

### Monitoraggio Integrato per Triathlon

#### Metriche Critiche

1. **CTL Totale**: Somma dei TSS/TRIMP da tutte e 3 le discipline
2. **ACWR per disciplina**: Valutare singolarmente running (infortunio risk) e bike
3. **HRV Trending**: Calo importante = scarico imminente per tutte le discipline
4. **Dual ACWR**: ACWR tra running sostenuto e bike sostenuto (il run è spesso limitante)

#### Adattamenti Speciali

**Per il Running nel Triathlon:**
- Tolleranza carico ridotta rispetto a monodisciplina
- ACWR per running alone deve rimanere < 1.2
- Sessioni corse lunghe: 1 volta ogni 10-14 giorni max (non settimanale)
- Giorni tra sessione bike-long e run-long: minimo 48 ore

**Per il Nuoto:**
- Frequenza più importante di volume (tecnica specifico)
- 3 sessioni/settimana minimo, 4-5 ideale
- Mix: 1 tecnica, 1 velocità, 1-2 aerobica, 1 recupero

**Per il Bike:**
- Supporto al volume running e nuoto
- 1-2 sessioni lunghe settimanali (6-8 ore in peak)
- Brick workout aggiunto 1 volta/settimana da week 8

### Interruzione Gare nelle Fasi

**Sprint Distance (1h45'):**
- Priorità: Velocità in tutte le discipline
- Phase Peak: 2-3 settimane
- Competizioni test: 3-4 settimane prima gara obiettivo

**Olympic Distance (2h15'-2h45'):**
- Priorità: Capacità aerobica sostenuta + velocità
- Phase Peak: 3-4 settimane
- Competizioni test: 4-5 settimane prima

**Half-Ironman (5h-6h30'):**
- Priorità: Resistenza muscolare + gestione mentale
- Phase Peak: 4-6 settimane
- Competizioni test: 2-3 mesi prima

**Full Ironman (11h-17h):**
- Priorità: Resistenza estrema + nutrizione pratica
- Phase Peak: 6-8 settimane
- Competizioni test: 2-4 mesi prima

---

## Progressione e Periodizzazione

### Modello di Progressione Universale

Indipendentemente dallo sport specifico, il modello AGSITC (Accumulate-Grow-Sustain-Intensify-Taper-Compete) fornisce un framework robusto:

#### Fase Accumulate (4-6 settimane)
- **Obiettivo**: Costruire volume totale
- **Volume**: Aumenta 8-12% settimanale
- **Intensità**: Rimane bassa (>90% volume < LT)
- **Frequenza**: Aumentare numero sessioni
- **TSB**: Negativo progressivamente (-5 a -15)
- **HRV**: Generalmente in calo, normale per fase

#### Fase Grow (4-6 settimane)
- **Obiettivo**: Mantenere volume, aumentare capacità
- **Volume**: Stabile o +5% massimo
- **Intensità**: Iniziare a introdurre zone 4-5
- **Sessioni**: 1-2 qualità a settimana
- **TSB**: Oscillare tra -5 e 0 con micro-scarichi
- **Segnale**: Se ACWR supera 1.3 → ridurre

#### Fase Sustain (2-3 settimane)
- **Obiettivo**: Consolidare adattamenti
- **Volume**: Stabile, nessun aumento
- **Intensità**: Mantenere sessioni qualità
- **Frequenza**: Ridotta di 10-20%
- **TSB**: Tornare positivo (0 a +10)
- **Recovery focus**: HRV deve risalire

#### Fase Intensify (3-4 settimane)
- **Obiettivo**: Specifico gara, carico peak
- **Volume**: Ridotto 20-30% dalla Sustain
- **Intensità**: Sessions specifico race intensity
- **Durata sessioni**: Ridotta, qualità mantenuta/aumentata
- **TSB**: Oscillare -10 a +5
- **Frequenza**: Mantenerla, ridurre durata

#### Fase Taper (7-14 giorni prima gara)
- **Obiettivo**: Freschezza massima + Preparedness
- **Volume**: Ridotto 40-60%
- **Intensità**: Mantenuta, durata ridotta
- **Sessioni**: 4-5 al massimo
- **TSB**: Raggiungere +10 a +20
- **Pattern giornaliero**: Short + fast → Easy → Very short + taper → Riposo

#### Fase Compete (Gara)
- **Performance test**
- **Data point** per modello successivo
- **Recovery post-gara**: 3-7 giorni molto leggero

#### Fase Post-Compete (1-2 settimane)
- **Volume**: Ridotto 50-60%
- **Intensità**: Solo aerobica facile
- **Mentale**: Break da struttura
- **Ciclo successivo**: Restart dal nuovo baseline

### Incrementi Settimanali: Regole Empiriche

#### Regola del 10%
**Originaria regola**: Non aumentare volume > 10% settimanale

**Realtà moderna:**
- Troppo conservativa per principianti (possono tollerare 15-20%)
- Insufficiente per atleti avanzati con adattamento cronicamente elevato
- Meglio: **Monitorare ACWR** che non percentuale grezza

#### Regola dell'ACWR
```
Se ACWR < 0.8: Sottostimolato, aumentare 8-10%
Se ACWR 0.8-1.3: Optimal zone, mantenere
Se ACWR 1.3-1.5: Cauto, monitorare strettamente
Se ACWR > 1.5: Ridurre immediatamente, rischio altissimo
```

#### Regola della Percezione
```
Se RPE per stesse intensità aumenta progressivamente:
  Week 1: RPE 5 per 10 km
  Week 2: RPE 6 per 10 km
  Week 3: RPE 6.5 per 10 km
  → Segno di overreach, scarica Week 4
```

### Scarico (Deload)

**Quando scaricano?**
1. Ogni 4-6 settimane programmato
2. Se TSB < -25 per 3+ giorni
3. Se HRV cala > 15% e non risale in 2-3 giorni
4. Se ACWR > 1.5
5. Se atleta riporta PRE aumentato per allenamenti normali

**Come strutturare scarico:**
- **Durata**: 4-7 giorni
- **Volume**: 40-50% della normal week
- **Intensità**: Solo aerobica Zone 1-2
- **Frequenza**: Mantenerla (stesso numero sessioni, durata ridotta)
- **Psicologico**: Può essere utile cambiare location/sport complementari

**Effetto fisiologico:**
- CTL cala lievemente (accettabile)
- ATL cala significativamente
- TSB ritorna positivo
- HRV tipicamente risale nei giorni 2-3
- Sessione successiva dopo scarico: performance spesso elevata (supercompensazione)

---

## Implementazione LLM

### Architettura del Sistema LLM

Una applicazione LLM per allenamenti personalizzati deve integrare:

#### Input del Sistema

1. **Dati Biografici Atleta**
   - Età, sesso, peso, altezza
   - Anni di esperienza
   - Sport praticati
   - Livello precedente (Beginner/Intermediate/Advanced)

2. **Metriche Attuali**
   - CTL attuale (fitness)
   - ATL attuale (7-day load)
   - TSB attuale (form)
   - ACWR corrente
   - HRV media ultimi 7 giorni
   - RHR media

3. **Profili Soglia Individuali**
   - FTP (per cycling) in Watt
   - Lactate Threshold Pace (per running) in min/km
   - Swim FTP in m/min
   - Max HR (frequenza cardiaca massima)
   - HR Reserve calcolato
   - Power/HR function se disponibile

4. **Obiettivi Specifici**
   - Distanza target gara
   - Data gara (settimane rimaste)
   - Performance goal (tempo, distanza, completamento)
   - Sport prioritari (per triathlon)
   - Vincoli (giorni disponibili, location, attrezzatura)

5. **Dati Storici**
   - Ultimi 12-24 mesi di training data
   - Injury history
   - Pattern di risposta al training (chi risponde meglio a volume vs intensità)
   - Performance precedenti (tempi gare storici)
   - Preferenze (mattino vs sera, indoor vs outdoor, sociali vs solitario)

6. **Fattori Ambientali**
   - Sonno medio (ore/notte)
   - Livello stress percepito (1-10)
   - Nutrizione qualità (soggettivo)
   - Impegni lavoro/famiglia
   - Malattie recenti

#### Elaborazione LLM

**Prompt Engineering Strutturato:**

```
{SYSTEM PROMPT}
Ti comporti come un coach di endurance esperto con PhD in sport science. 
La tua expertise combina:
- Scienza della fisiologia dell'esercizio
- Principi di periodizzazione e progressione
- Monitoraggio dei carichi con TTribute TSS/TRIMP
- Gestione del rischio infortuni
- Psicologia dello sport e motivazione

Basi le raccomandazioni SEMPRE su dati obiettivi (CTL, ACWR, HRV, TSB).
Non fornisci mai allenamenti che violino le soglie di sicurezza.
Adatti sempre il piano alle circostanze dell'atleta specifico.

{USER CONTEXT}
Athlete: [Nome]
Sport: [Running/Cycling/Swimming/Triathlon/Trail Running]
Level: [Beginner/Intermediate/Advanced]
Current CTL: [Numero]
Current ATL: [Numero]
Current TSB: [Numero]
Current ACWR: [Numero]
Weeks to Goal: [Numero]
Goal Distance: [Distanza/Tempo]
Available Sessions/Week: [Numero]
```

**Generazione Allenamento:**

L'LLM riceve il contesto e genera:

1. **Analisi Situazione Attuale**
   - Valutazione CTL/ATL balance
   - Sostenibilità del CTL attuale
   - Margine di crescita disponibile
   - Rischi identificati (ACWR alto, HRV basso, ecc.)

2. **Periodizzazione Raccomandata**
   - Numero settimane per fase
   - Incrementi specifici TSS/TRIMP
   - Settimane di scarico consigliate
   - Data taper e format

3. **Specifiche Settimana**
   Per ogni giorno propone:
   - Sport e durata
   - Intensità e zone HR/Power
   - TSS/TRIMP atteso
   - Note sulla forma (facile/moderato/difficile/recupero)
   - RPE suggerito
   - Dettagli specifici (se intervals: numero ripetute, durata, recovery)

4. **Metriche di Monitoring**
   - Range TSS settimanale atteso
   - Segnali di warning (ATL eccessivo, HRV basso)
   - Trigger per modifica piano
   - Checkpoints di valutazione (ogni settimana/mese)

5. **Adattamenti Dinamici**
   L'LLM fornisce anche logica per adattamenti:
   ```
   Se ATL settimanale > CTL + 50 punti:
     → Ridurre intensità della sessione successiva
     → Prolungare durata scarico se ACWR > 1.3
   
   Se HRV cala > 12%:
     → Schedulare scarico parziale
     → Saltare sessione intensa se ACWR > 1.4
   
   Se TSB rimane < -20 per 5 giorni:
     → Scarico full week programmato
   ```

#### Output: Generazione Strutturata

**Per il Ciclismo (Esempio):**

```
CICLO 8 SETTIMANE - OLYMPIC TRIATHLON PREP

ANALISI:
CTL attuale: 85 (appropriato per Olympic prep)
ATL: 65 (sostenibile)
TSB: +20 (forma buona, pronto per aumento)
ACWR: 0.76 (sotto-stimolato leggermente, margine di crescita)

FASI:
- Week 1-3: GROWTH PHASE (accumulo moderato)
- Week 4: SUSTAIN (consolidamento)
- Week 5-6: INTENSIFY (peak specifico)
- Week 7: TAPER
- Week 8: COMPETITION

---

WEEK 1 (Base=85 CTL, Target +8):
Target TSS Week: 350-380 (ciclismo 45% totale triathlon)
ACWR Target: 0.85-0.95

LUNEDI: Bike - Easy Steady
  Durata: 90 min
  Intensità: IF 0.65, Z2-Z3
  Power: 160-180W (adatta al FTP 250)
  TSS: 60
  Note: Recupero attivo, conversazione comoda
  
MARTEDI: Bike - Tempo Intervals
  Durata: 75 min
  Warm: 15 min Z2
  Main: 3×10' @ 215W (IF 0.86), 3 min rec @ 140W
  Cool: 10 min Z2
  TSS: 95
  RPE: 7/10
  Note: Criticale mantenere postura nelle ultime ripetute
  
MERCOLEDI: Riposo o Cross-Training (yoga 20 min, stretching)
  TSS: 0-5
  
GIOVEDI: Bike - Base Ride
  Durata: 60 min
  Intensità: IF 0.70, Z3
  Power: 175W steady
  TSS: 50
  Note: Continuità aerobica, focus cadenza 90-95 RPM
  
VENERDI: Riposo attivo
  TSS: 0-3
  
SABATO: Bike - Long Slow Distance + Brick
  Durata: 120 min bike + 30 min corsa
  Bike: IF 0.62, Z2, power 155W avg
  TSS Bike: 80
  Transition + Corsa 30 min easy: TRIMP ~25
  TSS Total: 105
  Note: Pratica real transizioni, sensibilità gambe post-bike
  
DOMENICA: Recovery or Skip
  TSS: 0-5
  
TOTAL WEEK: 405 TSS (Bike: 390, Cross: 15)
ACWR: 0.95 (within target)
Incremento CTL previsto: +8-10 punti
```

#### Validazione e Safety Checks LLM

L'LLM deve implementare validazioni automatiche prima di generare piano:

```python
# Pseudocodice per validazione LLM output
def validate_training_plan(plan, athlete):
    
    # Check 1: ACWR Safety
    if athlete.acwr > 1.5:
        return ERROR: "ACWR troppo alto, aumentare scarico prima del novo ciclo"
    
    # Check 2: CTL Growth Rate
    weekly_ctl_growth = plan.avg_tss_per_week / 7  # TSS/day
    if weekly_ctl_growth > 15:  # > 1.5% growth/day
        return WARNING: "CTL growth rate aggressive, recommend reduce 10%"
    
    # Check 3: ATL Peak Safety
    max_atl_planned = max(plan.weekly_atl)
    if max_atl_planned > athlete.ctx + 50:
        return WARNING: "Settimana picco ATL eccede CTL+50 soglia, risk infortuni"
    
    # Check 4: HRV Projection
    if athlete.hrv_recent_trend == "DOWN" and plan.intensity_high:
        return WARNING: "HRV in calo, considerare scarico preventivo Week 1"
    
    # Check 5: Intensity Distribution
    high_intensity_pct = plan.high_intensity_sessions / plan.total_sessions
    if high_intensity_pct > 0.35:  # > 35% sessions high intensity
        return WARNING: "80/20 rule violated, suggest reduce quality sessions"
    
    # Check 6: Sport-Specific Risk (Trail Running)
    if sport == "TRAIL_RUNNING":
        descent_km_week = sum(plan.descent_efforts)
        if descent_km_week > athlete.ctxl * 0.15:
            return WARNING: "Discese eccessive, aumentare focus tecnica"
    
    # If all checks pass:
    return VALIDATED: plan_object
```

### Integrazione con Dati Esterni

L'LLM deve interfacciarsi con:

1. **Wearable APIs** (Garmin, Strava, Coros, Apple Watch)
   - Retrieve TSS/TRIMP dati real-time
   - HRV, RHR, Sleep duration
   - Auto-update CTL, ATL, TSB
   - Alerts se metriche breach soglie

2. **Modelli Predittivi**
   - Performance Prediction: Data storica → predicted finish time
   - Injury Risk Model: ACWR + HRV + volume trends → injury probability
   - Recovery Duration: TSS + age + sleep → recovery hours needed

3. **Feedback Loop**
   - Atleta inputs: RPE, come si sente, modifiche esterne
   - LLM adapts plan next week based on feedback
   - Learning: Se atleta sempre fatica con certain format → adjust structure

---

## Considerazioni per l'Applicazione

### User Interface per LLM App

L'app deve presentare chiaramente:

#### Dashboard Principale
- **PMC Chart**: CTL (blu), ATL (rosso), TSB (giallo) ultimi 30-90 giorni
- **ACWR Visual**: Barra che indica range ottimale 0.8-1.3, highlight se fuori
- **HRV Trend**: Grafico ultimi 7-14 giorni con baseline personale
- **Top Risks**: Badge rossi se ACWR > 1.4, HRV < baseline-15%, ecc.

#### Schermata Workout Day
```
TODAY: Tuesday 12 Nov 2025
Status: READY TO TRAIN (TSB +8, HRV normal, sleep 7.5h)

PLANNED WORKOUT:
Bike - Tempo Intervals
Duration: 75 min
Intensity: IF 0.86 (Zone 3-4)
Effort: HARD
Expected TSS: 95

INSTRUCTIONS:
1. Warm 15 min easy (Zone 2)
2. Main Set: 3 ripetute di 10 min @ 215W (spia power meter)
   Recovery: 3 min @ 140W tra ripetute
3. Cool 10 min easy

PRE-WORKOUT MARKERS:
- Current HR: 52 bpm (normal)
- HRV: 42ms (normal range)
- Sleep last night: 7h 45min
- Stress level: 4/10
- → ALL GREEN: Proceed with planned intensity

POST-WORKOUT:
[Will show TSS, avg power, HR data, RPE slider, notes field]
```

#### Adattamenti in Real-Time
Se durante workout:
- Power/pace sostenuta risulta superiore del 10%+ to planned: "Session seems easier, consider target intensità o più volume Week prossima"
- Power/pace inferiore: "Sessione seems harder, verificare sleep/stress, considerare scarico"
- HR elevation eccessiva: "HR seems elevated vs power, considerare riposo aggiuntivo domani"

### Data Privacy e Sicurezza

- Tutti i dati di allenamento GDPR-compliant
- Opzione sync con Garmin/Strava encrypted
- Backup data locale sul device
- User può esportare dati in qualsiasi momento (CSV/JSON)

### Progettazione del Modello LLM

#### Fine-Tuning Consigliato
Per una app pubblica, considerare fine-tuning LLM su:
- Dataset pubblico TrainingPeaks anonymizzato (se disponibile)
- Caso studio pubblicati in literature (endurance training journals)
- Validation set: 100+ athlete plans with outcome data (injury/performance)

#### Architettura Consigliata
- **Base Model**: GPT-4-turbo o Claude-3-opus (per complex reasoning)
- **Context Length**: Minimo 8k tokens (4k dedicati a athlete historical data)
- **Temperature**: 0.3-0.5 (ridotta variabilità, focus determinismo)
- **Retrieval-Augmented Generation (RAG)**:
  - Vector DB con scientific literature su endurance training
  - Sport-specific training guidelines
  - Historical athlete data per recommendations

#### Prompt Template per Generazione Ciclo

```
{SYSTEM_ROLE}
Ti comporti da expert coach. I tuoi input sono:
- Metriche fisiologiche (CTL, ACWR, HRV)
- Letteratura scientifica (vincoli biologici reali)
- Dati atleta specifico (preferenze, rischi individuali)
- Periodizzazione proven (macrocicli testati)

Output SEMPRE con:
- Justification scientifica
- Numeri specifici (TSS, sessions, durations)
- Safety thresholds e red flags
- Trigger di modifica del piano

NON produrre mai piani che:
- Incrementino CTL > 10% settimanale
- Mantengano ACWR > 1.4 per 2+ settimane
- Ignorino warning fisiologici (HRV calo, TSB eccessivamente negativo)

{ATHLETE_DATA}
[JSON strutturato con tutti i dati]

{REQUEST}
Genera piano di [N settimane] per [sport] con obiettivo [gara/distanza].
Priorità: [costruzione/intensità/tapering].
Constraints: [giorni disponibili, equipaggiamento, infortuni passati].

Fornisci:
1. Analisi situazione attuale
2. Fasi periodizzazione con durate
3. Tabella settimana per settimana (giorni, sport, durata, intensità, TSS)
4. Checkpoints e trigger di modifica
5. Rischi identificati e mitigation strategies
```

### Testing e Validazione

Prima di deployment pubblico, l'app LLM deve essere testata:

1. **Validation vs Known Coaching Practices**
   - Comparare piani generati vs piani reali di coach pubblicati
   - Verificare allineamento con guidelines ACSM, ISSN, ecc.

2. **Edge Case Testing**
   - Atleta principiante con CTL molto bassa
   - Atleta avanzato con CTL massima
   - Transitioning tra sport
   - Injury recovery scenarios

3. **Beta Testing con Atleti**
   - 50-100 atleti volontari per 12 settimane
   - Misurare: compliance, infortuni, performance improvement
   - Feedback qualitativo

4. **Safety Audit**
   - Verifica che zero piani generate violino soglie di sicurezza
   - ACWR mai > 1.5, TSB mai < -30, ecc.
   - Escalation protocol se warning

---

## Conclusioni

La gestione dei carichi di allenamento negli sport di endurance è una scienza, non arte. Un'applicazione LLM efficace deve:

1. **Quantificare obiettivamente** lo stress con metriche consolidate (TSS, TRIMP, CTL, ATL, ACWR)
2. **Integrare feedback corporeo** (HRV, RPE, RHR) per completare il quadro
3. **Rispettare vincoli biologici** (80/20 distribution, incrementi graduali, scarichi programmati)
4. **Personalizzare aggressivamente** per sport, livello, caratteristiche individuali
5. **Adattarsi dinamicamente** ai dati incoming, modificando piani senza aspettare settimana successiva
6. **Prioritizzare sicurezza** su performance: prevenire infortuni è più importante che marginale gain

Un LLM che implementi questi principi può generare piani di allenamento veramente personalizzati, safer di coach medio, e in grado di scalare a migliaia di atleti simultaneamente.

---

## Appendice: Formule Chiave

### TSS (Training Stress Score)
```
TSS = ((Secondi × NP × IF) / (FTP × 3600)) × 100
```

### TRIMP (Training Impulse - Lucia Method)
```
TRIMP = Durata (min) × % della FC di Soglia
```

### Intensity Factor
```
IF = NP / FTP  (per power)
IF = Pace / FTP Pace  (per running)
IF = Swim Pace / Swim FTP  (per nuoto)
```

### ACWR
```
ACWR = ATL (7 giorni) / CTL (42 giorni)
```

### CTL (Chronic Training Load)
```
CTL = Media pesata TSS ultimi 42 giorni (pesi decrescenti verso passato)
```

### ATL (Acute Training Load)
```
ATL = Media pesata TSS ultimi 7 giorni (pesi decrescenti verso passato)
```

### TSB (Training Stress Balance)
```
TSB = CTL - ATL
```

### Trail Running: Carico Equivalente Pianura
```
Carico Equiv = Km × 1.5-2.0 + (Dislivello m / 100) × 10
```

### Swim TSS
```
Swim TSS = (IF^3) × (Ore) × 100
```

---

**Documento generato per applicazione LLM di allenamenti personalizzati - v1.0**
**Target: Running, Cycling, Swimming, Trail Running, Triathlon (Sprint, Olympic, Half-Ironman, Full Ironman)**
**Ultimo aggiornamento: Novembre 2025**