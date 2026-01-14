"""Check and fix users table."""
import psycopg2
from urllib.parse import urlparse
import os
from dotenv import load_dotenv

load_dotenv()
url = urlparse(os.getenv('DATABASE_URL'))
conn = psycopg2.connect(
    host=url.hostname,
    port=url.port,
    user=url.username,
    password=url.password,
    database=url.path[1:],
    sslmode='require'
)
cur = conn.cursor()

# Check current columns
cur.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'users' 
    ORDER BY ordinal_position
""")
cols = cur.fetchall()
print('Current columns in users table:')
for c in cols:
    print(f'  {c[0]}: {c[1]}')

# Check if password_hash exists
has_password_hash = any(c[0] == 'password_hash' for c in cols)

if not has_password_hash:
    print('\n[FIXING] Adding password_hash column...')
    cur.execute("""
        ALTER TABLE users 
        ADD COLUMN password_hash VARCHAR(255) NOT NULL DEFAULT '';
    """)
    conn.commit()
    print('[SUCCESS] password_hash column added!')
else:
    print('\n[OK] password_hash column already exists')

cur.close()
conn.close()
