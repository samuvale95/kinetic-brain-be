# Database Scripts

This directory contains SQL scripts for database setup and migrations.

## Available Scripts

### Core Setup
- **create_tables.sql** - Creates all necessary database tables
- **create_strava_tables.sql** - Creates additional tables for Strava integration

### Migrations
- **add_city_to_user_profiles.sql** - Adds city field to user profiles table
- **add_location_fields_to_user_profiles.sql** - Adds location-related fields to user profiles

## Usage

### Automated Setup
```bash
# Run the automated setup script from the project root
./setup_database.sh
```

### Manual Execution
```bash
# Execute individual SQL scripts
psql "$DATABASE_URL" -f database/create_tables.sql
psql "$DATABASE_URL" -f database/create_strava_tables.sql
```

## Documentation

For detailed database setup instructions, see [docs/DATABASE_SETUP.md](../docs/DATABASE_SETUP.md).
