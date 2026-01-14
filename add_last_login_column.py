"""Add last_login column to users table."""
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

# Check if last_login exists
cur.execute("""
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name = 'users' AND column_name = 'last_login'
""")
exists = cur.fetchone()

if not exists:
    print('[FIXING] Adding last_login column...')
    cur.execute("""
        ALTER TABLE users 
        ADD COLUMN last_login TIMESTAMPTZ
    """)
    conn.commit()
    print('[SUCCESS] last_login column added!')
else:
    print('[OK] last_login column already exists')

cur.close()
conn.close()
