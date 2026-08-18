#!/usr/bin/env python3
"""Fix missing columns in Supabase schema to match ORM models."""

from pathlib import Path
import psycopg2

# Load .env
env = {}
env_file = Path('.env')
for line in env_file.read_text(encoding='utf-8').splitlines():
    line = line.strip()
    if not line or line.startswith('#') or '=' not in line:
        continue
    k, v = line.split('=', 1)
    env[k.strip()] = v.strip()

# Connect to Supabase
conn = psycopg2.connect(env['POSTGREE_DATABASE_URL'])
cur = conn.cursor()

print("=== CURRENT SCHEMA ===")
cur.execute("""
    SELECT table_name, column_name 
    FROM information_schema.columns 
    WHERE table_schema='app' AND table_name IN ('roles','permissions','users') 
    ORDER BY table_name, ordinal_position
""")
for row in cur.fetchall():
    print(f"  {row[0]}.{row[1]}")

print("\n=== APPLYING MIGRATIONS ===")
migrations = [
    ("roles", "created_at", "TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP"),
    ("permissions", "created_at", "TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP"),
    ("users", "created_at", "TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP"),
    ("users", "updated_at", "TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP"),
]

for table, column, col_type in migrations:
    try:
        cur.execute(
            f"""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_schema='app' AND table_name=%s AND column_name=%s
            )
            """,
            (table, column)
        )
        exists = cur.fetchone()[0]
        if not exists:
            print(f"  Adding {table}.{column} ...")
            cur.execute(f"ALTER TABLE app.{table} ADD COLUMN {column} {col_type}")
            print(f"    ✓ Added {table}.{column}")
        else:
            print(f"  Skipping {table}.{column} (already exists)")
    except Exception as e:
        print(f"  ✗ Error on {table}.{column}: {e}")

conn.commit()

print("\n=== FINAL SCHEMA ===")
cur.execute("""
    SELECT table_name, column_name 
    FROM information_schema.columns 
    WHERE table_schema='app' AND table_name IN ('roles','permissions','users') 
    ORDER BY table_name, ordinal_position
""")
for row in cur.fetchall():
    print(f"  {row[0]}.{row[1]}")

conn.close()
print("\n✓ Database schema sync complete!")
