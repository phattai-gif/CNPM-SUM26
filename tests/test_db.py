#!/usr/bin/env python
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent / ".env")

sys.path.insert(0, "src")

from infrastructure.databases.factory_database import FactoryDatabase

print("Testing database connection...")
print("=" * 80)

try:
    db = FactoryDatabase.get_database('POSTGREE')
    print(f"✓ Database connection successful")
    print(f"  Database URI: {db.database_uri[:50]}..." if db.database_uri else "  Database URI: Not configured")
    
    # Try a simple query
    session = db.session
    from infrastructure.models.app import UserModel
    user_count = session.query(UserModel).count()
    print(f"  Total users in database: {user_count}")
    
    session.close()
    print("✓ Database query successful")
    
except Exception as e:
    print(f"✗ Database connection failed: {type(e).__name__}")
    print(f"  Error: {str(e)[:100]}")

print("=" * 80)
