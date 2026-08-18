#!/usr/bin/env python3
"""
Script to initialize DB schema by creating all tables.
Usage: python3 scripts/create_tables.py

This script imports the app factory which will initialize the database
engine via the project's FactoryDatabase and then calls SQLAlchemy
metadata.create_all() as a safety-net.
"""

from pathlib import Path
import sys

# ensure project root on path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'src'))

try:
    from create_app import create_app
    from infrastructure.databases.base import Base
    from infrastructure.databases.factory_database import FactoryDatabase
except Exception as e:
    print('Import error:', e)
    raise


def main():
    app = create_app()
    # create_app() already calls init_db which triggers Base.metadata.create_all,
    # but we also call it explicitly here to be safe when running standalone.
    with app.app_context():
        try:
            db = FactoryDatabase.get_database('POSTGREE')
            Base.metadata.create_all(bind=db.engine)
            print('Database tables created successfully.')
        except Exception as exc:
            print('Failed to create tables:', exc)
            raise


if __name__ == '__main__':
    main()
