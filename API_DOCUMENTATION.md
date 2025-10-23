# Kinetic Brain API - Documentazione Completa

## Indice
- [Autenticazione](#autenticazione)
- [Profilo Utente](#profilo-utente)
- [Piani di Allenamento](#piani-di-allenamento)
- [Allenamenti](#allenamenti)
- [Calendario](#calendario)
- [AI Integration](#ai-integration)
- [Dashboard](#dashboard)

---

## Autenticazione

### POST /auth/register
Registra un nuovo utente.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "password123",
  "name": "Mario Rossi"
}
```

**Response (201):**
```json
{
  "id": 1,
  "email": "user@example.com",
  "name": "Mario Rossi",
  "is_active": true,
  "is_verified": false,
  "created_at": "2024-01-15T10:30:00Z",
  "last_login": null
}
```

**Errori:**
- `400`: Email già esistente
- `422`: Dati di validazione non corretti

---

### POST /auth/login
Effettua il login dell'utente.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Errori:**
- `401`: Credenziali non valide
- `400`: Utente inattivo

---

### POST /auth/refresh
Rinnova il token di accesso.

**Request:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

---

### GET /auth/me
Ottiene le informazioni dell'utente corrente.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200):**
```json
{
  "id": 1,
  "email": "user@example.com",
  "name": "Mario Rossi",
  "is_active": true,
  "is_verified": false,
  "created_at": "2024-01-15T10:30:00Z",
  "last_login": "2024-01-15T12:00:00Z"
}
```

---

### POST /auth/logout
Effettua il logout dell'utente.

**Response (200):**
```json
{
  "message": "Successfully logged out"
}
```

---

## Profilo Utente

### GET /profile
Ottiene il profilo dell'utente.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200):**
```json
{
  "id": 1,
  "user_id": 1,
  "age": 30,
  "gender": "male",
  "weight": 70.0,
  "height": 175.0,
  "sports": ["running", "cycling"],
  "experience_years": 5,
  "weekly_hours": 8.0,
  "main_goal": "Improve endurance",
  "physical_notes": "No injuries",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

**Errori:**
- `404`: Profilo non trovato

---

### POST /profile
Crea il profilo dell'utente.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
  "age": 30,
  "gender": "male",
  "weight": 70.0,
  "height": 175.0,
  "sports": ["running", "cycling"],
  "experience_years": 5,
  "weekly_hours": 8.0,
  "main_goal": "Improve endurance",
  "physical_notes": "No injuries"
}
```

**Response (201):**
```json
{
  "id": 1,
  "user_id": 1,
  "age": 30,
  "gender": "male",
  "weight": 70.0,
  "height": 175.0,
  "sports": ["running", "cycling"],
  "experience_years": 5,
  "weekly_hours": 8.0,
  "main_goal": "Improve endurance",
  "physical_notes": "No injuries",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": null
}
```

---

### PUT /profile
Aggiorna il profilo dell'utente.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
  "age": 31,
  "weight": 69.0,
  "weekly_hours": 10.0
}
```

**Response (200):**
```json
{
  "id": 1,
  "user_id": 1,
  "age": 31,
  "gender": "male",
  "weight": 69.0,
  "height": 175.0,
  "sports": ["running", "cycling"],
  "experience_years": 5,
  "weekly_hours": 10.0,
  "main_goal": "Improve endurance",
  "physical_notes": "No injuries",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T12:00:00Z"
}
```

---

### GET /profile/performance
Ottiene le metriche di performance dell'utente.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200):**
```json
[
  {
    "id": 1,
    "user_id": 1,
    "metric_type": "hr",
    "threshold_value": 180.0,
    "max_value": 200.0,
    "rest_value": 50.0,
    "zones_json": {
      "Z1": {
        "min": 50.0,
        "max": 147.5,
        "description": "Recovery"
      },
      "Z2": {
        "min": 147.5,
        "max": 177.5,
        "description": "Aerobic Base"
      },
      "Z3": {
        "min": 177.5,
        "max": 192.5,
        "description": "Aerobic Threshold"
      },
      "Z4": {
        "min": 192.5,
        "max": 180.0,
        "description": "Lactate Threshold"
      },
      "Z5": {
        "min": 180.0,
        "max": 200.0,
        "description": "VO2 Max"
      }
    },
    "test_date": "2024-01-15T10:30:00Z",
    "created_at": "2024-01-15T10:30:00Z"
  }
]
```

---

### POST /profile/performance
Crea nuove metriche di performance.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
  "metric_type": "hr",
  "threshold_value": 180.0,
  "max_value": 200.0,
  "rest_value": 50.0,
  "test_date": "2024-01-15"
}
```

**Response (201):**
```json
{
  "id": 1,
  "user_id": 1,
  "metric_type": "hr",
  "threshold_value": 180.0,
  "max_value": 200.0,
  "rest_value": 50.0,
  "zones_json": {
    "Z1": {
      "min": 50.0,
      "max": 147.5,
      "description": "Recovery"
    },
    "Z2": {
      "min": 147.5,
      "max": 177.5,
      "description": "Aerobic Base"
    },
    "Z3": {
      "min": 177.5,
      "max": 192.5,
      "description": "Aerobic Threshold"
    },
    "Z4": {
      "min": 192.5,
      "max": 180.0,
      "description": "Lactate Threshold"
    },
    "Z5": {
      "min": 180.0,
      "max": 200.0,
      "description": "VO2 Max"
    }
  },
  "test_date": "2024-01-15T10:30:00Z",
  "created_at": "2024-01-15T10:30:00Z"
}
```

---

### POST /profile/calculate-zones
Calcola le zone di allenamento.

**Request:**
```json
{
  "metric_type": "hr",
  "threshold_value": 180.0,
  "max_value": 200.0,
  "rest_value": 50.0
}
```

**Response (200):**
```json
{
  "zones": {
    "Z1": {
      "min": 50.0,
      "max": 147.5,
      "description": "Recovery"
    },
    "Z2": {
      "min": 147.5,
      "max": 177.5,
      "description": "Aerobic Base"
    },
    "Z3": {
      "min": 177.5,
      "max": 192.5,
      "description": "Aerobic Threshold"
    },
    "Z4": {
      "min": 192.5,
      "max": 180.0,
      "description": "Lactate Threshold"
    },
    "Z5": {
      "min": 180.0,
      "max": 200.0,
      "description": "VO2 Max"
    }
  },
  "calculated_at": "2024-01-15T10:30:00Z"
}
```

---

## Piani di Allenamento

### GET /workouts/plans
Ottiene i piani di allenamento dell'utente.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `skip` (int, optional): Numero di record da saltare (default: 0)
- `limit` (int, optional): Numero massimo di record (default: 100)

**Response (200):**
```json
[
  {
    "id": 1,
    "user_id": 1,
    "title": "Maratona 2024",
    "description": "Piano di allenamento per la maratona di primavera",
    "start_date": "2024-01-15",
    "end_date": "2024-04-15",
    "total_weeks": 12,
    "goal": "Completare la maratona in 3:30",
    "sport_type": "running",
    "level": "intermediate",
    "status": "active",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
]
```

---

### POST /workouts/plans
Crea un nuovo piano di allenamento.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
  "title": "Maratona 2024",
  "description": "Piano di allenamento per la maratona di primavera",
  "start_date": "2024-01-15",
  "end_date": "2024-04-15",
  "goal": "Completare la maratona in 3:30",
  "sport_type": "running",
  "level": "intermediate"
}
```

**Response (201):**
```json
{
  "id": 1,
  "user_id": 1,
  "title": "Maratona 2024",
  "description": "Piano di allenamento per la maratona di primavera",
  "start_date": "2024-01-15",
  "end_date": "2024-04-15",
  "total_weeks": 12,
  "goal": "Completare la maratona in 3:30",
  "sport_type": "running",
  "level": "intermediate",
  "status": "active",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": null
}
```

---

### GET /workouts/plans/{plan_id}
Ottiene un piano di allenamento specifico.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200):**
```json
{
  "id": 1,
  "user_id": 1,
  "title": "Maratona 2024",
  "description": "Piano di allenamento per la maratona di primavera",
  "start_date": "2024-01-15",
  "end_date": "2024-04-15",
  "total_weeks": 12,
  "goal": "Completare la maratona in 3:30",
  "sport_type": "running",
  "level": "intermediate",
  "status": "active",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

**Errori:**
- `404`: Piano di allenamento non trovato

---

### PUT /workouts/plans/{plan_id}
Aggiorna un piano di allenamento.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
  "title": "Maratona 2024 - Aggiornato",
  "status": "paused"
}
```

**Response (200):**
```json
{
  "id": 1,
  "user_id": 1,
  "title": "Maratona 2024 - Aggiornato",
  "description": "Piano di allenamento per la maratona di primavera",
  "start_date": "2024-01-15",
  "end_date": "2024-04-15",
  "total_weeks": 12,
  "goal": "Completare la maratona in 3:30",
  "sport_type": "running",
  "level": "intermediate",
  "status": "paused",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T12:00:00Z"
}
```

---

### DELETE /workouts/plans/{plan_id}
Elimina un piano di allenamento.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200):**
```json
{
  "message": "Workout plan deleted successfully"
}
```

---

### POST /workouts/plans/generate-ai
Genera un piano di allenamento usando l'AI.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
  "sport_type": "running",
  "level": "intermediate",
  "goal": "Completare una mezza maratona",
  "duration_weeks": 12,
  "weekly_hours": 6.0,
  "user_profile": {
    "age": 30,
    "experience_years": 2,
    "weekly_hours": 6.0
  }
}
```

**Response (200):**
```json
{
  "plan": {
    "title": "Mezza Maratona - Piano Intermedio",
    "description": "Piano di allenamento personalizzato per completare la mezza maratona",
    "sport_type": "running",
    "level": "intermediate",
    "goal": "Completare una mezza maratona",
    "duration_weeks": 12,
    "weekly_hours": 6.0,
    "weeks": [
      {
        "week": 1,
        "focus": "Base building",
        "workouts": [
          {
            "day": "Monday",
            "type": "Endurance",
            "duration_minutes": 45,
            "intensity": "Z2",
            "description": "Corsa facile per costruire la base aerobica"
          },
          {
            "day": "Wednesday",
            "type": "Tempo",
            "duration_minutes": 30,
            "intensity": "Z3",
            "description": "Corsa a ritmo sostenuto"
          },
          {
            "day": "Saturday",
            "type": "Long Run",
            "duration_minutes": 60,
            "intensity": "Z2",
            "description": "Lunga corsa per resistenza"
          }
        ]
      }
    ]
  }
}
```

---

## Allenamenti

### GET /workouts
Ottiene gli allenamenti dell'utente.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `skip` (int, optional): Numero di record da saltare (default: 0)
- `limit` (int, optional): Numero massimo di record (default: 100)
- `plan_id` (int, optional): Filtra per piano di allenamento

**Response (200):**
```json
[
  {
    "id": 1,
    "plan_id": 1,
    "user_id": 1,
    "title": "Corsa facile",
    "type": "endurance",
    "day_number": 1,
    "scheduled_date": "2024-01-15",
    "duration_minutes": 45,
    "intensity": "easy",
    "zone": "Z2",
    "structure_json": {
      "warmup": {
        "duration_minutes": 10,
        "description": "Riscaldamento graduale"
      },
      "main": {
        "duration_minutes": 30,
        "description": "Corsa a ritmo facile"
      },
      "cooldown": {
        "duration_minutes": 5,
        "description": "Defaticamento"
      }
    },
    "status": "scheduled",
    "notes": "Primo allenamento del piano",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
]
```

---

### POST /workouts
Crea un nuovo allenamento.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
  "plan_id": 1,
  "title": "Corsa facile",
  "type": "endurance",
  "day_number": 1,
  "scheduled_date": "2024-01-15",
  "duration_minutes": 45,
  "intensity": "easy",
  "zone": "Z2",
  "structure_json": {
    "warmup": {
      "duration_minutes": 10,
      "description": "Riscaldamento graduale"
    },
    "main": {
      "duration_minutes": 30,
      "description": "Corsa a ritmo facile"
    },
    "cooldown": {
      "duration_minutes": 5,
      "description": "Defaticamento"
    }
  },
  "notes": "Primo allenamento del piano"
}
```

**Response (201):**
```json
{
  "id": 1,
  "plan_id": 1,
  "user_id": 1,
  "title": "Corsa facile",
  "type": "endurance",
  "day_number": 1,
  "scheduled_date": "2024-01-15",
  "duration_minutes": 45,
  "intensity": "easy",
  "zone": "Z2",
  "structure_json": {
    "warmup": {
      "duration_minutes": 10,
      "description": "Riscaldamento graduale"
    },
    "main": {
      "duration_minutes": 30,
      "description": "Corsa a ritmo facile"
    },
    "cooldown": {
      "duration_minutes": 5,
      "description": "Defaticamento"
    }
  },
  "status": "scheduled",
  "notes": "Primo allenamento del piano",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": null
}
```

---

### GET /workouts/{workout_id}
Ottiene un allenamento specifico.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200):**
```json
{
  "id": 1,
  "plan_id": 1,
  "user_id": 1,
  "title": "Corsa facile",
  "type": "endurance",
  "day_number": 1,
  "scheduled_date": "2024-01-15",
  "duration_minutes": 45,
  "intensity": "easy",
  "zone": "Z2",
  "structure_json": {
    "warmup": {
      "duration_minutes": 10,
      "description": "Riscaldamento graduale"
    },
    "main": {
      "duration_minutes": 30,
      "description": "Corsa a ritmo facile"
    },
    "cooldown": {
      "duration_minutes": 5,
      "description": "Defaticamento"
    }
  },
  "status": "scheduled",
  "notes": "Primo allenamento del piano",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

---

### PUT /workouts/{workout_id}
Aggiorna un allenamento.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
  "title": "Corsa facile - Aggiornata",
  "duration_minutes": 50,
  "notes": "Aggiunto 5 minuti"
}
```

**Response (200):**
```json
{
  "id": 1,
  "plan_id": 1,
  "user_id": 1,
  "title": "Corsa facile - Aggiornata",
  "type": "endurance",
  "day_number": 1,
  "scheduled_date": "2024-01-15",
  "duration_minutes": 50,
  "intensity": "easy",
  "zone": "Z2",
  "structure_json": {
    "warmup": {
      "duration_minutes": 10,
      "description": "Riscaldamento graduale"
    },
    "main": {
      "duration_minutes": 30,
      "description": "Corsa a ritmo facile"
    },
    "cooldown": {
      "duration_minutes": 5,
      "description": "Defaticamento"
    }
  },
  "status": "scheduled",
  "notes": "Aggiunto 5 minuti",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T12:00:00Z"
}
```

---

### DELETE /workouts/{workout_id}
Elimina un allenamento.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200):**
```json
{
  "message": "Workout deleted successfully"
}
```

---

### POST /workouts/{workout_id}/complete
Completa un allenamento creando una sessione.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
  "workout_id": 1,
  "actual_date": "2024-01-15T10:30:00Z",
  "duration_minutes": 45,
  "avg_hr": 150.0,
  "max_hr": 165.0,
  "avg_pace": 5.5,
  "avg_power": null,
  "perceived_exertion": 6,
  "notes": "Allenamento completato con successo"
}
```

**Response (201):**
```json
{
  "id": 1,
  "workout_id": 1,
  "user_id": 1,
  "actual_date": "2024-01-15T10:30:00Z",
  "duration_minutes": 45,
  "avg_hr": 150.0,
  "max_hr": 165.0,
  "avg_pace": 5.5,
  "avg_power": null,
  "perceived_exertion": 6,
  "notes": "Allenamento completato con successo",
  "created_at": "2024-01-15T10:30:00Z"
}
```

---

### GET /workouts/sessions
Ottiene le sessioni di allenamento.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `skip` (int, optional): Numero di record da saltare (default: 0)
- `limit` (int, optional): Numero massimo di record (default: 100)
- `workout_id` (int, optional): Filtra per allenamento specifico

**Response (200):**
```json
[
  {
    "id": 1,
    "workout_id": 1,
    "user_id": 1,
    "actual_date": "2024-01-15T10:30:00Z",
    "duration_minutes": 45,
    "avg_hr": 150.0,
    "max_hr": 165.0,
    "avg_pace": 5.5,
    "avg_power": null,
    "perceived_exertion": 6,
    "notes": "Allenamento completato con successo",
    "created_at": "2024-01-15T10:30:00Z"
  }
]
```

---

## Calendario

### GET /calendar
Ottiene gli eventi del calendario.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `start_date` (date, optional): Data di inizio (default: inizio mese corrente)
- `end_date` (date, optional): Data di fine (default: fine mese corrente)

**Response (200):**
```json
[
  {
    "id": 1,
    "user_id": 1,
    "workout_id": 1,
    "title": "Corsa facile",
    "event_type": "workout",
    "scheduled_date": "2024-01-15",
    "duration_minutes": 45,
    "is_recurring": false,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
]
```

---

### GET /calendar/{year}/{month}
Ottiene gli eventi del calendario per un mese specifico.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200):**
```json
[
  {
    "id": 1,
    "user_id": 1,
    "workout_id": 1,
    "title": "Corsa facile",
    "event_type": "workout",
    "scheduled_date": "2024-01-15",
    "duration_minutes": 45,
    "is_recurring": false,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
]
```

---

### POST /calendar/events
Crea un nuovo evento del calendario.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
  "workout_id": 1,
  "title": "Corsa facile",
  "event_type": "workout",
  "scheduled_date": "2024-01-15",
  "duration_minutes": 45,
  "is_recurring": false
}
```

**Response (201):**
```json
{
  "id": 1,
  "user_id": 1,
  "workout_id": 1,
  "title": "Corsa facile",
  "event_type": "workout",
  "scheduled_date": "2024-01-15",
  "duration_minutes": 45,
  "is_recurring": false,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": null
}
```

---

### PUT /calendar/events/{event_id}
Aggiorna un evento del calendario.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
  "title": "Corsa facile - Aggiornata",
  "duration_minutes": 50
}
```

**Response (200):**
```json
{
  "id": 1,
  "user_id": 1,
  "workout_id": 1,
  "title": "Corsa facile - Aggiornata",
  "event_type": "workout",
  "scheduled_date": "2024-01-15",
  "duration_minutes": 50,
  "is_recurring": false,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T12:00:00Z"
}
```

---

### DELETE /calendar/events/{event_id}
Elimina un evento del calendario.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200):**
```json
{
  "message": "Calendar event deleted successfully"
}
```

---

### POST /calendar/drag-drop
Gestisce il drag & drop degli eventi del calendario.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
  "event_id": 1,
  "new_date": "2024-01-16",
  "new_duration_minutes": 50
}
```

**Response (200):**
```json
{
  "message": "Event updated successfully",
  "event": {
    "id": 1,
    "user_id": 1,
    "workout_id": 1,
    "title": "Corsa facile",
    "event_type": "workout",
    "scheduled_date": "2024-01-16",
    "duration_minutes": 50,
    "is_recurring": false,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T12:00:00Z"
  }
}
```

---

## AI Integration

### POST /ai/generate
Genera una risposta AI per query generali.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
  "prompt": "Come posso migliorare la mia resistenza nella corsa?",
  "context": {
    "sport": "running",
    "level": "intermediate"
  },
  "max_tokens": 1000,
  "temperature": 0.7
}
```

**Response (200):**
```json
{
  "response": "Per migliorare la tua resistenza nella corsa, ti consiglio di:\n\n1. **Aumentare gradualmente il volume**: Aggiungi 10% di chilometri ogni settimana\n2. **Includere corse lunghe**: Una volta a settimana fai una corsa lunga a ritmo facile\n3. **Variare l'intensità**: Alterna corse facili, medie e intense\n4. **Mantenere la costanza**: È meglio correre 3-4 volte a settimana regolarmente\n5. **Ascoltare il corpo**: Rispetta i giorni di riposo per evitare infortuni",
  "usage": {
    "prompt_tokens": 25,
    "completion_tokens": 150,
    "total_tokens": 175
  },
  "model": "gpt-4",
  "created_at": "2024-01-15T10:30:00Z"
}
```

---

### POST /ai/generate-plan
Genera un piano di allenamento personalizzato usando l'AI.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
  "sport_type": "running",
  "level": "intermediate",
  "goal": "Completare una mezza maratona",
  "duration_weeks": 12,
  "weekly_hours": 6.0,
  "user_profile": {
    "age": 30,
    "experience_years": 2,
    "weekly_hours": 6.0
  }
}
```

**Response (200):**
```json
{
  "plan": {
    "title": "Mezza Maratona - Piano Intermedio",
    "description": "Piano di allenamento personalizzato per completare la mezza maratona",
    "sport_type": "running",
    "level": "intermediate",
    "goal": "Completare una mezza maratona",
    "duration_weeks": 12,
    "weekly_hours": 6.0,
    "weeks": [
      {
        "week": 1,
        "focus": "Base building",
        "workouts": [
          {
            "day": "Monday",
            "type": "Endurance",
            "duration_minutes": 45,
            "intensity": "Z2",
            "description": "Corsa facile per costruire la base aerobica"
          },
          {
            "day": "Wednesday",
            "type": "Tempo",
            "duration_minutes": 30,
            "intensity": "Z3",
            "description": "Corsa a ritmo sostenuto"
          },
          {
            "day": "Saturday",
            "type": "Long Run",
            "duration_minutes": 60,
            "intensity": "Z2",
            "description": "Lunga corsa per resistenza"
          }
        ]
      }
    ]
  }
}
```

---

### POST /ai/analyze-workout
Analizza le performance di un allenamento usando l'AI.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
  "workout_data": {
    "duration_minutes": 45,
    "avg_hr": 150.0,
    "max_hr": 165.0,
    "avg_pace": 5.5,
    "perceived_exertion": 6
  },
  "performance_metrics": {
    "threshold_hr": 180.0,
    "zones": {
      "Z2": {"min": 147.5, "max": 177.5}
    }
  },
  "analysis_type": "performance"
}
```

**Response (200):**
```json
{
  "analysis": "Ottimo allenamento! Hai mantenuto una frequenza cardiaca media di 150 bpm, che corrisponde perfettamente alla zona Z2. Il ritmo di 5:30 min/km è appropriato per un allenamento di resistenza. La percezione dello sforzo di 6/10 indica che hai lavorato nella zona giusta.",
  "recommendations": [
    "Continua con questo tipo di allenamento per costruire la base aerobica",
    "Prova ad aumentare gradualmente la durata delle corse lunghe",
    "Mantieni la costanza negli allenamenti"
  ],
  "score": 8.5,
  "areas_for_improvement": [
    "Potresti lavorare sulla variabilità dell'intensità",
    "Considera di aggiungere esercizi di forza"
  ],
  "next_steps": [
    "Programma una corsa lunga per la prossima settimana",
    "Includi 1-2 allenamenti di velocità",
    "Mantieni 2-3 corse facili a settimana"
  ]
}
```

---

### POST /ai/suggest
Ottiene suggerimenti AI basati sul contesto.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
  "context": "Sono un runner intermedio che si allena 4 volte a settimana. Voglio migliorare il mio tempo sui 10K.",
  "suggestion_type": "workout",
  "user_profile": {
    "age": 30,
    "sport": "running",
    "level": "intermediate",
    "weekly_hours": 6.0
  }
}
```

**Response (200):**
```json
{
  "response": "Per migliorare il tuo tempo sui 10K, ti suggerisco questo approccio:\n\n**Struttura settimanale:**\n- **Lunedì**: Corsa facile (Z2) - 45-60 min\n- **Mercoledì**: Intervalli (Z4-Z5) - 8x400m con recupero 90s\n- **Venerdì**: Tempo run (Z3) - 20-30 min\n- **Domenica**: Corsa lunga (Z2) - 60-90 min\n\n**Focus specifici:**\n1. **Velocità**: Includi 1-2 sessioni di intervalli a settimana\n2. **Resistenza**: Mantieni la corsa lunga settimanale\n3. **Ritmo gara**: Fai prove di ritmo sui 10K ogni 2-3 settimane\n4. **Recupero**: Non sottovalutare l'importanza del riposo",
  "usage": {
    "prompt_tokens": 45,
    "completion_tokens": 200,
    "total_tokens": 245
  },
  "model": "gpt-4",
  "created_at": "2024-01-15T10:30:00Z"
}
```

---

## Dashboard

### GET /dashboard/stats
Ottiene le statistiche della dashboard.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200):**
```json
{
  "total_workouts": 45,
  "workouts_this_week": 3,
  "total_training_time_minutes": 1800,
  "total_training_time_hours": 30.0,
  "active_plans": 2,
  "upcoming_workouts": 5
}
```

---

### GET /dashboard/upcoming
Ottiene i prossimi allenamenti (7 giorni).

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200):**
```json
[
  {
    "id": 1,
    "plan_id": 1,
    "user_id": 1,
    "title": "Corsa facile",
    "type": "endurance",
    "day_number": 1,
    "scheduled_date": "2024-01-16",
    "duration_minutes": 45,
    "intensity": "easy",
    "zone": "Z2",
    "structure_json": {
      "warmup": {
        "duration_minutes": 10,
        "description": "Riscaldamento graduale"
      },
      "main": {
        "duration_minutes": 30,
        "description": "Corsa a ritmo facile"
      },
      "cooldown": {
        "duration_minutes": 5,
        "description": "Defaticamento"
      }
    },
    "status": "scheduled",
    "notes": "Prossimo allenamento",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
]
```

---

### GET /dashboard/progress
Ottiene i dati di progresso per i grafici.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200):**
```json
{
  "weekly_data": [
    {
      "week": "2024-01-08",
      "workouts": 3,
      "duration_minutes": 180,
      "duration_hours": 3.0
    },
    {
      "week": "2024-01-15",
      "workouts": 4,
      "duration_minutes": 240,
      "duration_hours": 4.0
    }
  ],
  "recent_performance": [
    {
      "date": "2024-01-15T10:30:00Z",
      "duration_minutes": 45,
      "avg_hr": 150.0,
      "max_hr": 165.0,
      "avg_pace": 5.5,
      "avg_power": null,
      "perceived_exertion": 6
    }
  ]
}
```

---

### GET /dashboard/calendar-events
Ottiene gli eventi del calendario per la dashboard.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200):**
```json
[
  {
    "id": 1,
    "user_id": 1,
    "workout_id": 1,
    "title": "Corsa facile",
    "event_type": "workout",
    "scheduled_date": "2024-01-16",
    "duration_minutes": 45,
    "is_recurring": false,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
]
```

---

## Codici di Errore

### Errori di Autenticazione
- `401 Unauthorized`: Token non valido o scaduto
- `403 Forbidden`: Accesso negato

### Errori di Validazione
- `400 Bad Request`: Dati di richiesta non validi
- `422 Unprocessable Entity`: Errori di validazione Pydantic

### Errori di Risorsa
- `404 Not Found`: Risorsa non trovata
- `409 Conflict`: Conflitto (es. email già esistente)

### Errori del Server
- `500 Internal Server Error`: Errore interno del server
- `503 Service Unavailable`: Servizio temporaneamente non disponibile

---

## Autenticazione

Tutti gli endpoint (eccetto `/auth/register` e `/auth/login`) richiedono un token di accesso JWT nell'header:

```
Authorization: Bearer <access_token>
```

Il token ha una durata di 30 minuti. Per rinnovarlo, usa l'endpoint `/auth/refresh` con il refresh token.

---

## Rate Limiting

L'API implementa rate limiting per prevenire abusi:
- **Generale**: 1000 richieste per ora per IP
- **AI Endpoints**: 100 richieste per ora per utente
- **Autenticazione**: 10 tentativi per ora per IP

---

## Supporto

Per supporto tecnico o domande:
- **Documentazione API**: `/docs` (Swagger UI)
- **Documentazione Alternativa**: `/redoc`
- **Health Check**: `/health`
