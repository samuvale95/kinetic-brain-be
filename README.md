# Kinetic Brain Backend

A comprehensive Python backend API for the Kinetic Brain sports training management application, built with FastAPI and integrated with ChatGPT APIs.

## Features

- **User Management**: Registration, authentication, and profile management
- **Workout Planning**: Create and manage personalized workout plans
- **Performance Tracking**: Track workouts, sessions, and performance metrics
- **Calendar Integration**: Schedule and manage training events
- **AI Integration**: ChatGPT-powered workout plan generation and analysis
- **Zone Calculations**: Automatic calculation of training zones (HR, pace, power)
- **Dashboard**: Comprehensive statistics and progress tracking

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Authentication**: JWT with refresh tokens
- **AI Integration**: OpenAI GPT-4
- **Validation**: Pydantic v2
- **Migrations**: Alembic
- **Testing**: pytest
- **Containerization**: Docker & Docker Compose

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Docker & Docker Compose (optional)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd kinetic-brain-backend
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

4. **Set up the database**
   ```bash
   # Create database
   createdb kinetic_brain
   
   # Run migrations
   alembic upgrade head
   ```

5. **Run the application**
   ```bash
   uvicorn app.main:app --reload
   ```

### Using Docker

1. **Start all services**
   ```bash
   docker-compose up -d
   ```

2. **Run migrations**
   ```bash
   docker-compose exec api alembic upgrade head
   ```

## API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:password@localhost/kinetic_brain` |
| `SECRET_KEY` | JWT secret key | `your-secret-key-change-in-production` |
| `OPENAI_API_KEY` | OpenAI API key for ChatGPT integration | Required |
| `CORS_ORIGINS` | Allowed CORS origins | `["http://localhost:3000"]` |
| `DEBUG` | Debug mode | `false` |

## API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login user
- `POST /auth/refresh` - Refresh access token
- `GET /auth/me` - Get current user info
- `POST /auth/logout` - Logout user

### Profile Management
- `GET /profile` - Get user profile
- `POST /profile` - Create user profile
- `PUT /profile` - Update user profile
- `GET /profile/performance` - Get performance metrics
- `POST /profile/performance` - Create performance metrics
- `POST /profile/calculate-zones` - Calculate training zones

### Workout Management
- `GET /workouts/plans` - Get workout plans
- `POST /workouts/plans` - Create workout plan
- `GET /workouts/plans/{id}` - Get specific plan
- `PUT /workouts/plans/{id}` - Update plan
- `DELETE /workouts/plans/{id}` - Delete plan
- `POST /workouts/plans/generate-ai` - Generate AI workout plan

### Workouts
- `GET /workouts` - Get workouts
- `POST /workouts` - Create workout
- `GET /workouts/{id}` - Get specific workout
- `PUT /workouts/{id}` - Update workout
- `DELETE /workouts/{id}` - Delete workout
- `POST /workouts/{id}/complete` - Complete workout

### Calendar
- `GET /calendar` - Get calendar events
- `GET /calendar/{year}/{month}` - Get monthly events
- `POST /calendar/events` - Create calendar event
- `PUT /calendar/events/{id}` - Update event
- `DELETE /calendar/events/{id}` - Delete event
- `POST /calendar/drag-drop` - Handle drag & drop

### AI Integration
- `POST /ai/generate` - Generate AI response
- `POST /ai/generate-plan` - Generate workout plan
- `POST /ai/analyze-workout` - Analyze workout performance
- `POST /ai/suggest` - Get AI suggestions

### Dashboard
- `GET /dashboard/stats` - Get dashboard statistics
- `GET /dashboard/upcoming` - Get upcoming workouts
- `GET /dashboard/progress` - Get progress data
- `GET /dashboard/calendar-events` - Get calendar events

## AI Integration

The backend integrates with OpenAI's GPT-4 API to provide:

- **Workout Plan Generation**: Personalized training plans based on user goals and profile
- **Workout Analysis**: Performance analysis and recommendations
- **Smart Suggestions**: Context-aware training advice

### Example AI Workout Plan Request

```json
{
  "sport_type": "running",
  "level": "intermediate",
  "goal": "Complete a half marathon",
  "duration_weeks": 12,
  "weekly_hours": 6.0,
  "user_profile": {
    "age": 30,
    "experience_years": 2,
    "weekly_hours": 6.0
  }
}
```

## Training Zone Calculations

The system automatically calculates training zones for:

- **Heart Rate Zones**: Based on threshold HR using Joe Friel's 5-zone system
- **Pace Zones**: Running pace zones based on threshold pace
- **Power Zones**: Cycling power zones based on FTP (Functional Threshold Power)

## Database Schema

### Core Tables
- `users` - User accounts and authentication
- `user_profiles` - User profile information
- `performance_metrics` - Performance data and training zones
- `workout_plans` - Multi-week training plans
- `workouts` - Individual workout sessions
- `workout_sessions` - Completed workout data
- `calendar_events` - Calendar scheduling

## Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_auth.py
```

## Development

### Code Quality

```bash
# Format code
black app/ tests/

# Sort imports
isort app/ tests/

# Lint code
flake8 app/ tests/

# Type checking
mypy app/
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

## Deployment

### Production Docker

```bash
# Build production image
docker build -t kinetic-brain-api .

# Run with production settings
docker run -p 8000:8000 --env-file .env kinetic-brain-api
```

### Environment Setup

1. Set production environment variables
2. Configure PostgreSQL database
3. Set up Redis (optional)
4. Configure Nginx reverse proxy
5. Set up SSL certificates
6. Configure monitoring and logging

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in the repository
- Contact the development team
- Check the API documentation at `/docs`
