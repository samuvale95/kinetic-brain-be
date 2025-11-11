## Visione Generale
- Obiettivo: orchestrare LLM e componenti deterministici per generare piani di allenamento endurance (run, trail, triathlon, nuoto, bici) scalabili e sicuri.
- Stato attuale: un singolo modello riceve metriche atleta via prompt; non ci sono validator o revisori automatici, né gestione strutturata di meso/macro cicli.

## Strategia LLM Consigliata
- **GPT-4.1 (ChatGPT)** come motore principale: genera il piano integrando metriche, richieste utente, function calling verso servizi esterni.
- **Claude 3.5 Sonnet** come revisore: verifica il piano (progressioni, sicurezza, coerenza) e produce spiegazioni/changelog.
- **Gemini 1.5 Pro** per casi speciali: ingestion di contesto lunghissimo (log mesi, manuali) o materiale multimodale (video tecnica).
- Workflow: GPT-4.1 → validator deterministico → Claude 3.5 (se necessario) → approvazione/ritorno all’utente; Gemini usato on-demand.

## Funzionalità Mancanti e Roadmap

### Obbligatorie Subito (anche con 0 utenti)
- Logging completo richieste LLM (`prompt`, `response`, modello, esito parsing).
- Validator deterministico dei piani (incremento carico <10%, giorni rest minimi, limiti intensità per livello, continuità settimane).
- Limite duration piano (max 24 settimane) e rigenerazione modulare per blocchi più lunghi.
- Versionamento output + metadati (`phases`, `macrocycles`) con storage persistente e audit trail.

### Sviluppi Futuri ma Necessari per Scalare
- Orchestrazione multi-modello (es. LangChain, Semantic Kernel o orchestratore custom) con routing GPT-4.1 → Claude 3.5 → consegna.
- RAG strutturato su metriche/feedback storici: indicizzazione (Pinecone/Weaviate/pgvector) + retrieval mirato per arricchire il prompt.
- Sistema feedback atleta (RPE, adesione, injury notes) e calcolo KPI di prodotto (compliance, miglioramento, riduzione infortuni).
- Pipeline governance: moderazione output, controlli privacy/GDPR, versionamento piani e revisioni, audit log per assistenza coach.

### Sviluppi Futuri per Migliorare il Servizio
- Supporto multimodale (Gemini) per analizzare video, foto tecnica, log estesi con pre-estrazione feature.
- Fine-tuning/LoRA su modello open-weight (`Llama 3.1 70B`, `Mixtral 8x22B`) per ridurre costi e aumentare coerenza; fallback a modello frontier per casi complessi.
- Pianificazione adattiva automatizzata (notifiche, reminder, aggiornamenti ciclici) e suggerimenti post-sessione basati su metriche in tempo quasi reale.
- Integrazione wearables/Strava avanzata (analisi real-time, suggerimenti correttivi post workout).

## Gestione Mesocicli/Macro-cicli
- Il backend attuale delega al modello la definizione di `phases` e `macrocycles`; non esiste logica deterministica o validazione.
- Next step: introdurre generazione/validazione hard-coded di blocchi (es. Base → Build → Peak → Taper) o fornirli al modello come vincoli.

## Piano Costi Indicativo

| Fase | Componenti | Stima mensile |
| --- | --- | --- |
| Test interni | Singolo modello (GPT-4.1/Claude), 50–100 prompt/giorno | 50–150 $ |
| Step 1 | +Claude revisore su 20% piani | +40–80 $ |
| Step 2 | Validator deterministico + logging | costo sviluppo (1–2 sett.) |
| Step 3 | RAG light (Pinecone/pgvector + embedding) | 80 $ (DB 24–60 $, embedding 15–20 $) |
| Step 4 | Fine-tuning/LoRA + hosting open-weight | Setup 1–2k $, inferenza 0,9–1,2 $/M token o GPU 2,5–3,5k $/mese se self-host |
| Step 5 | Gemini multimodale on-demand | <50 $/mese (uso spot) |

- Budget target prossimo step (200–300 piani/mese): GPT-4.1 150 $ + Claude 60 $ + RAG 80 $ ≈ 290 $/mese.
- Fase attuale: ≤150 $/mese rimanendo su un solo modello e prompt curati.

## Linee Guida Operative
- Limita i piani a blocchi ≤6 mesi; aggiorna mensilmente con nuovi dati.
- Implementa cicli di revisione: piano → validator → eventuale rigenerazione → consegna.
- Usa feedback atleta per rigenerare blocchi successivi e alimentare KPI.
- Versiona template prompt (`ai/prompt_templates`) e automatizza test su output JSON.


