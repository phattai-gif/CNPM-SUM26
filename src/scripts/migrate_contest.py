"""
Migration script: Add missing columns to database tables.
- rounds.updated_at
- contests.rules
"""
import sys
import os

# When run from project root, the script is at src/scripts/migrate_contest.py
# We need src on the path
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, src_path)

from sqlalchemy import text
from infrastructure.databases.factory_database import FactoryDatabase as db_factory

def run_migration():
    session = db_factory.get_database('POSTGREE').session

    migrations = [
        {
            'description': 'Add updated_at to rounds table',
            'check': "SELECT column_name FROM information_schema.columns WHERE table_name='rounds' AND column_name='updated_at'",
            'sql': "ALTER TABLE rounds ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()"
        },
        {
            'description': 'Add rules to contests table',
            'check': "SELECT column_name FROM information_schema.columns WHERE table_name='contests' AND column_name='rules'",
            'sql': "ALTER TABLE contests ADD COLUMN rules TEXT"
        },
    ]

    for m in migrations:
        try:
            result = session.execute(text(m['check'])).fetchone()
            if result:
                print(f"  [SKIP] {m['description']} - column already exists")
            else:
                session.execute(text(m['sql']))
                session.commit()
                print(f"  [OK]   {m['description']} - column added successfully")
        except Exception as e:
            session.rollback()
            print(f"  [ERR]  {m['description']} - {e}")

    session.close()
    print("\nMigration complete.")


if __name__ == '__main__':
    run_migration()
