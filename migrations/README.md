# Database Migrations

This directory contains database migration files for the TalentScan application.

## Migration Files

- **001_initial_schema.sql** - Creates the initial database schema with `candidates` and `work_experience` tables

## Usage

### Apply All Pending Migrations
```bash
make migrate-up
```

### Rollback Last Migration
```bash
make migrate-down
```

### Check Migration Status
```bash
make migrate-status
```

## Migration File Format

Migration files are SQL files with a specific format:

```sql
-- Migration: <number>_<name>
-- Description: <description>
-- Created: <date>

-- ============================================
-- UP MIGRATION
-- ============================================

-- up
<SQL statement 1>

-- up
<SQL statement 2>

-- ============================================
-- DOWN MIGRATION
-- ============================================

-- down
<SQL statement 1>

-- down
<SQL statement 2>
```

## Creating New Migrations

1. Create a new `.sql` file in this directory with a sequential number prefix (e.g., `002_add_index.sql`)
2. Follow the migration file format above
3. Each statement should be prefixed with `-- up` or `-- down`
4. Down migrations should reverse the up migrations in reverse order
5. Run `make migrate-up` to apply the new migration

## Migration Tracking

Applied migrations are tracked in the `migrations` table in the database. This ensures migrations are only applied once.
