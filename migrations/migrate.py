#!/usr/bin/env python3
"""
Database migration runner for TalentScan.

Usage:
    python migrations/migrate.py up     # Apply all pending migrations
    python migrations/migrate.py down   # Rollback the last migration
    python migrations/migrate.py status # Show migration status
"""

import sqlite3
import os
import sys
import re
from pathlib import Path

# Add parent directory to path to import database module
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.database import DB_FILE

MIGRATIONS_DIR = Path(__file__).parent


def get_db_connection():
    """Get database connection."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_migrations_table():
    """Create migrations tracking table if it doesn't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            migration_name TEXT UNIQUE NOT NULL,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()


def get_applied_migrations():
    """Get list of already applied migrations."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT migration_name FROM migrations ORDER BY id')
    applied = [row['migration_name'] for row in cursor.fetchall()]
    conn.close()
    return applied


def get_migration_files():
    """Get all migration files sorted by name."""
    migration_files = sorted(MIGRATIONS_DIR.glob('*.sql'))
    return [f.stem for f in migration_files]


def parse_migration_file(filepath):
    """Parse migration file into up and down statements."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    up_statements = []
    down_statements = []
    
    # Extract up statements
    # Updated regex to handle files with or without trailing newlines
    up_matches = re.findall(r'-- up\s*\n(.*?)(?:\n(?=-- (?:up|down))|$)', content, re.DOTALL)
    for match in up_matches:
        statement = match.strip()
        if statement:
            up_statements.append(statement)
    
    # Extract down statements
    # Updated regex to handle files with or without trailing newlines
    down_matches = re.findall(r'-- down\s*\n(.*?)(?:\n(?=-- (?:up|down))|$)', content, re.DOTALL)
    for match in down_matches:
        statement = match.strip()
        if statement:
            down_statements.append(statement)
    
    return up_statements, down_statements


def migrate_up():
    """Apply all pending migrations."""
    init_migrations_table()
    applied = get_applied_migrations()
    all_migrations = get_migration_files()
    
    pending = [m for m in all_migrations if m not in applied]
    
    if not pending:
        print("✓ No pending migrations")
        return
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    for migration_name in pending:
        print(f"Applying migration: {migration_name}")
        
        migration_file = MIGRATIONS_DIR / f"{migration_name}.sql"
        up_statements, _ = parse_migration_file(migration_file)
        
        try:
            for statement in up_statements:
                cursor.execute(statement)
            
            cursor.execute(
                'INSERT INTO migrations (migration_name) VALUES (?)',
                (migration_name,)
            )
            conn.commit()
            print(f"  ✓ Applied: {migration_name}")
        
        except Exception as e:
            conn.rollback()
            print(f"  ✗ Failed: {migration_name}")
            print(f"  Error: {e}")
            conn.close()
            sys.exit(1)
    
    conn.close()
    print(f"\n✓ Applied {len(pending)} migration(s)")


def migrate_down():
    """Rollback the last migration."""
    init_migrations_table()
    applied = get_applied_migrations()
    
    if not applied:
        print("✓ No migrations to rollback")
        return
    
    last_migration = applied[-1]
    print(f"Rolling back migration: {last_migration}")
    
    migration_file = MIGRATIONS_DIR / f"{last_migration}.sql"
    _, down_statements = parse_migration_file(migration_file)
    
    if not down_statements:
        print(f"  ✗ No down migration found for: {last_migration}")
        sys.exit(1)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Execute down statements in reverse order
        for statement in reversed(down_statements):
            cursor.execute(statement)
        
        cursor.execute(
            'DELETE FROM migrations WHERE migration_name = ?',
            (last_migration,)
        )
        conn.commit()
        print(f"  ✓ Rolled back: {last_migration}")
    
    except Exception as e:
        conn.rollback()
        print(f"  ✗ Failed to rollback: {last_migration}")
        print(f"  Error: {e}")
        conn.close()
        sys.exit(1)
    
    conn.close()


def show_status():
    """Show migration status."""
    init_migrations_table()
    applied = get_applied_migrations()
    all_migrations = get_migration_files()
    
    pending = [m for m in all_migrations if m not in applied]
    
    print("Migration Status")
    print("=" * 60)
    
    if applied:
        print("\nApplied Migrations:")
        for migration in applied:
            print(f"  ✓ {migration}")
    else:
        print("\nApplied Migrations: None")
    
    if pending:
        print("\nPending Migrations:")
        for migration in pending:
            print(f"  ○ {migration}")
    else:
        print("\nPending Migrations: None")
    
    print()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == 'up':
        migrate_up()
    elif command == 'down':
        migrate_down()
    elif command == 'status':
        show_status()
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == '__main__':
    main()
