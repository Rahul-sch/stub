"""Add updated_at column to users table."""
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

# Check if updated_at exists
cur.execute("""
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name = 'users' AND column_name = 'updated_at'
""")
exists = cur.fetchone()

if not exists:
    print('[FIXING] Adding updated_at column...')
    cur.execute("""
        ALTER TABLE users 
        ADD COLUMN updated_at TIMESTAMPTZ DEFAULT NOW()
    """)
    conn.commit()
    print('[SUCCESS] updated_at column added!')
else:
    print('[OK] updated_at column already exists')

cur.close()
conn.close()
