from pathlib import Path
import psycopg2

env = {}
for line in Path('.env').read_text(encoding='utf-8').splitlines():
    line = line.strip()
    if not line or line.startswith('#') or '=' not in line:
        continue
    k, v = line.split('=', 1)
    env[k.strip()] = v.strip()

conn = psycopg2.connect(env['POSTGREE_DATABASE_URL'])
cur = conn.cursor()
cur.execute("SELECT table_name, column_name FROM information_schema.columns WHERE table_schema='app' AND table_name IN ('roles','permissions','users') ORDER BY table_name, column_name")
print('CURRENT_COLUMNS:')
for row in cur.fetchall():
    print(row)

for table, column in [('roles','created_at'), ('permissions','created_at'), ('users','created_at'), ('users','updated_at')]:
    cur.execute(f"SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='app' AND table_name=%s AND column_name=%s)", (table, column))
    exists = cur.fetchone()[0]
    if not exists:
        print(f'ADDING {table}.{column}')
        cur.execute(f"ALTER TABLE app.{table} ADD COLUMN IF NOT EXISTS {column} TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP")

conn.commit()
cur.execute("SELECT table_name, column_name FROM information_schema.columns WHERE table_schema='app' AND table_name IN ('roles','permissions','users') ORDER BY table_name, column_name")
print('FINAL_COLUMNS:')
for row in cur.fetchall():
    print(row)
conn.close()
print('DB schema sync complete')
