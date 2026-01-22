# Funzionalità mancanti – Kinetic Brain

**Documento**: elenco completo delle funzioni non ancora implementate, divise in **prioritarie** e **future**.  
**Ultimo aggiornamento**: 2025.

---

## Indice

1. [Prioritarie](#prioritarie)
2. [Future](#future)
3. [Riepilogo per area](#riepilogo-per-area)

---

## Prioritarie

Funzionalità essenziali per sicurezza, parity con i competitor principali e uso quotidiano dell’app.

### Sicurezza e infrastruttura

| # | Funzionalità | Descrizione | Riferimento |
|---|--------------|-------------|-------------|
| P1 | **Rate limiting** | Limite richieste per IP e per utente (es. 1000/h generale, 100/h AI, 10/h login). Middleware + Redis. | BACKEND_ANALYSIS |
| P2 | **Health check completo** | `/health` che verifica DB, Redis, OpenAI, Strava; status `healthy` / `degraded`. | BACKEND_ANALYSIS |
| P3 | **Error handling strutturato** | Exception custom, error code, logging con `request_id` / `user_id`. Distinguere validation, auth, business, server. | BACKEND_ANALYSIS |
| P4 | **Backup database** | Script backup automatico (pg_dump), retention, opzionale upload S3. Test di restore. | BACKEND_ANALYSIS |

### Export workout e dispositivi

| # | Funzionalità | Descrizione | Riferimento |
|---|--------------|-------------|-------------|
| P5 | **Export FIT** | Generare file .FIT per workout strutturati (warmup/main/cooldown, zone) per Garmin, rulli, Zwift. | Competitor (TP, Runna) |
| P6 | **Export TCX** | Generare .TCX per compatibilità con altri dispositivi e app. | Competitor |
| P7 | **Sync Garmin** | Invio workout pianificati al calendario Garmin Connect (o link Garmin) per riceverli su watch. | Competitor |
| P8 | **Export ZWO (opzionale)** | Per library workout / import in TrainingPeaks e indoor. | Competitor |

### Calendario e integrazioni esterne

| # | Funzionalità | Descrizione | Riferimento |
|---|--------------|-------------|-------------|
| P9 | **Export iCal / subscribe** | Feed iCal o export per Google Calendar / Outlook: workout programmati visibili in calendario esterno. | Competitor |
| P10 | **Sync Google Calendar (opzionale)** | Scrittura diretta su Google Calendar dell’utente (OAuth Calendar API). | Competitor |

### Workout e piano

| # | Funzionalità | Descrizione | Riferimento |
|---|--------------|-------------|-------------|
| P11 | **Daily suggested workout** | Suggerimento “workout del giorno” in base a readiness, CTL/ATL, recovery, sonno (HealthKit): es. oggi base / quality / recovery / skip. | Garmin, Whoop, SYSTM |
| P12 | **Instant workout (TrainNow)** | Generare un singolo workout on‑demand (es. “recovery 30’”, “intervalli 45’”) senza piano. Endpoint dedicato. | TrainerRoad, Runna |
| P13 | **Skip workout** | Azione esplicita “salta workout” con storico; eventuale impatto su adattamento prossima settimana. | Runna |
| P14 | **Riordino piano (drag‑drop)** | Spostare workout tra giorni e aggiornare il piano nel backend (non solo `calendar_events`). | Runna |
| P15 | **Restart piano** | Possibilità di riavviare un piano (o blocco) con logica chiara e storico. | Runna |

### Metriche e proiezioni

| # | Funzionalità | Descrizione | Riferimento |
|---|--------------|-------------|-------------|
| P16 | **Proiezione CTL/ATL “futuro”** | Grafico “se segui il piano” che mostra l’andamento atteso di CTL/ATL/TSB nelle prossime settimane. | Intervals.icu, TP |
| P17 | **Readiness → suggerimento** | Usare readiness/diary (e sonno se disponibile) per influenzare daily suggestion e tipo di sessione consigliata. | Whoop, Garmin |

### Caching e performance

| # | Funzionalità | Descrizione | Riferimento |
|---|--------------|-------------|-------------|
| P18 | **Caching Redis** | Cache per profile, performance metrics, statistiche, piani (TTL configurabile). Decorator o layer dedicato. | BACKEND_ANALYSIS |
| P19 | **Endpoint /metrics Prometheus** | Endpoint `/metrics` in formato Prometheus per request rate, error rate, latency, metriche business. | BACKEND_ANALYSIS |

### Validator e struttura workout

| # | Funzionalità | Descrizione | Riferimento |
|---|--------------|-------------|-------------|
| P20 | **Eccezione validator per strength/stretching** | I workout “solo main” (strength, stretching) non devono fallire il check warmup/cooldown; validator deve escluderli esplicitamente. | Analisi codebase |
| P21 | **Ripristino modelli WorkoutStructure** | Reintrodurre modelli Pydantic per `WorkoutStructure` / segmenti / steps (senza recursion) per validazione e API chiare. | workout.py schema |

### Import dati

| # | Funzionalità | Descrizione | Riferimento |
|---|--------------|-------------|-------------|
| P22 | **Import attività da FIT/TCX/GPX** | Caricamento file .FIT / .TCX / .GPX come attività completate, oltre a Strava/HealthKit. | Competitor |

---

## Future

Funzionalità utili per differenziazione e scaling, da pianificare dopo le prioritarie.

### Nuovi sport e formati

| # | Funzionalità | Descrizione | Riferimento |
|---|--------------|-------------|-------------|
| F1 | **Sport “gym” come principale** | Palestra come disciplina primaria: `sport_type: "gym"`, config in `WORKOUT_PARAMETERS`, piani solo gym, `normalize_sport_type`. | Analisi gym |
| F2 | **Sport “Hyrox”** | Tipo `hyrox` / `hyrox_race`, struttura 8×(1 km run + 1 station), esercizi per le 8 station, guide LLM e eventuale `HyroxWorkoutService`. | Analisi Hyrox |
| F3 | **Metriche per gym** | Volume (sets×reps×carico), RPE, eventuale adattamento metriche per forza. | Analisi gym |
| F4 | **Metriche per Hyrox** | Tempo per run, per station, tempo totale; eventuale TSS adattato. | Analisi Hyrox |

### Adaptive training e AI

| # | Funzionalità | Descrizione | Riferimento |
|---|--------------|-------------|-------------|
| F5 | **Adattamento per singolo workout** | Modificare i prossimi 1–3 workout in base a completamento/skip/RPE degli ultimi, non solo “adapt next week”. | TrainerRoad |
| F6 | **Stima automatica FTP/soglie** | Stima FTP o soglie da dati Strava/HealthKit senza test formale (tipo TrainerRoad AI FTP). | TrainerRoad |
| F7 | **Integrazione AI con metriche** | Usare CTL/ATL/TSB e metriche in prompt LLM per piani progressivi e AI; context “fitness attuale” strutturato. | IMPLEMENTATION_STATUS |
| F8 | **RAG su storico** | RAG su metriche e feedback (es. pgvector) per arricchire i prompt con contesto storico. | LLM_COACHING_ROADMAP |

### Workout builder e UX piano

| # | Funzionalità | Descrizione | Riferimento |
|---|--------------|-------------|-------------|
| F9 | **Workout builder visuale** | UI drag‑and‑drop per costruire workout (blocchi warmup/main/cooldown, repeat); TSS/IF calcolati in tempo reale. | TrainingPeaks |
| F10 | **Workout Library** | Libreria di workout predefiniti (named); import/export da file (ZWO, etc.). | TrainingPeaks |
| F11 | **Import piani da file** | Import di piani da .FIT, .TCX, .ZWO, .MRC. | TrainingPeaks |

### Coach e social

| # | Funzionalità | Descrizione | Riferimento |
|---|--------------|-------------|-------------|
| F12 | **Marketplace / Find a coach** | Directory coach, matching atleta–coach, abbonamenti. | TrainingPeaks |
| F13 | **Ruolo coach** | Account “coach” che vede piani/allenamenti degli atleti e può modificarli o commentare. | TrainingPeaks |
| F14 | **Segmenti e leaderboard** | Segmenti Strada-style, classifiche (globali o per club). Richiede routing e geo. | Strava |
| F15 | **Route e heatmap** | Creazione route, heatmap, suggested routes. | Strava |

### Contenuti e gamification

| # | Funzionalità | Descrizione | Riferimento |
|---|--------------|-------------|-------------|
| F16 | **Video / audio guidati** | Warm‑up, drills, strength, stretching guidati (video o audio). | Wahoo SYSTM, Garmin Coach |
| F17 | **Badge e streak** | Badge per workout completati, streak di allenamenti, livelli. | Wahoo SYSTM, Whoop |
| F18 | **Challenge** | Challenge settimanali/mensili (km, workout, ecc.) individuali o per club. | Strava |

### Backend e DevOps

| # | Funzionalità | Descrizione | Riferimento |
|---|--------------|-------------|-------------|
| F19 | **Logging strutturato JSON** | Log in JSON per aggregazione (ELK, CloudWatch); correlation ID. | BACKEND_ANALYSIS |
| F20 | **Validazione input avanzata** | Rate limit su size input, sanitizzazione stringhe, validazione upload file più rigorosa. | BACKEND_ANALYSIS |
| F21 | **Async DB per endpoint critici** | Utilizzo consistente di async DB per endpoint ad alto traffico. | BACKEND_ANALYSIS |
| F22 | **Test integrazione ed E2E** | Test di flussi completi (crea piano → workout → completa, sync Strava, metriche). | BACKEND_ANALYSIS |
| F23 | **Test di sicurezza** | Test per SQL injection, XSS, auth bypass. | BACKEND_ANALYSIS |
| F24 | **Export statistiche CSV/PDF** | Export report o statistiche in CSV/PDF per utente. | DEPLOYMENT_NOTES |

### Wearable e dispositivi

| # | Funzionalità | Descrizione | Riferimento |
|---|--------------|-------------|-------------|
| F25 | **Supporto RPE su Apple Watch** | Gestione workout con target RPE su Watch (oggi limitato). | TrainingPeaks + Watch |
| F26 | **Sync con COROS / Suunto / Fitbit** | Supporto aggiuntivo oltre a Garmin e Apple Watch. | Runna |

### Notifiche e engagement

| # | Funzionalità | Descrizione | Riferimento |
|---|--------------|-------------|-------------|
| F27 | **Notifiche contestuali** | Notifiche legate a recovery (“oggi meglio recovery”), streak, obiettivi settimanali. | Whoop, Garmin |
| F28 | **Pianificazione adattiva** | Suggerimenti post‑sessione e aggiornamenti ciclici del piano basati su metriche in quasi real‑time. | LLM_COACHING_ROADMAP |

### Governance e compliance

| # | Funzionalità | Descrizione | Riferimento |
|---|--------------|-------------|-------------|
| F29 | **Pipeline governance LLM** | Moderazione output, controlli privacy/GDPR, versionamento piani e revisioni, audit log. | LLM_COACHING_ROADMAP |
| F30 | **Feedback atleta strutturato** | RPE, adesione, injury notes; KPI (compliance, miglioramento, infortuni). | LLM_COACHING_ROADMAP |

---

## Riepilogo per area

### Prioritarie (22)

| Area | Count | Id |
|------|-------|-----|
| Sicurezza e infrastruttura | 4 | P1–P4 |
| Export workout e dispositivi | 4 | P5–P8 |
| Calendario e integrazioni | 2 | P9–P10 |
| Workout e piano | 5 | P11–P15 |
| Metriche e proiezioni | 2 | P16–P17 |
| Caching e performance | 2 | P18–P19 |
| Validator e struttura | 2 | P20–P21 |
| Import dati | 1 | P22 |

### Future (30)

| Area | Count | Id |
|------|-------|-----|
| Nuovi sport (gym, Hyrox) | 4 | F1–F4 |
| Adaptive training e AI | 4 | F5–F8 |
| Workout builder e UX | 3 | F9–F11 |
| Coach e social | 4 | F12–F15 |
| Contenuti e gamification | 3 | F16–F18 |
| Backend e DevOps | 6 | F19–F24 |
| Wearable | 2 | F25–F26 |
| Notifiche e engagement | 2 | F27–F28 |
| Governance e compliance | 2 | F29–F30 |

---

## Note

- **Prioritarie**: da implementare per allineamento competitor, sicurezza e stabilità. Ordine suggerito: prima P1–P4, poi P5–P10 (export/calendario), quindi P11–P17 (workout e metriche).
- **Future**: da schedulare in roadmap successive; priorità da rivedere in base a feedback utenti e obiettivi di prodotto.
- **Riferimenti**:  
  - `BACKEND_ANALYSIS` = `docs/BACKEND_ANALYSIS_AND_IMPROVEMENTS.md`  
  - `IMPLEMENTATION_STATUS` = `docs/roadmap/IMPLEMENTATION_STATUS.md`  
  - `LLM_COACHING_ROADMAP` = `docs/roadmap/LLM_COACHING_ROADMAP.md`  
  - `DEPLOYMENT_NOTES` = `docs/setup/DEPLOYMENT_NOTES.md`  
  - “Competitor” = analisi vs TrainingPeaks, Strava, Garmin, TrainerRoad, Wahoo SYSTM, Whoop, Intervals.icu, Runna.
