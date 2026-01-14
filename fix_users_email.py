"""Fix users table email column."""
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
    SELECT column_name, is_nullable, data_type, column_default
    FROM information_schema.columns 
    WHERE table_name = 'users' 
    ORDER BY ordinal_position
""")
cols = cur.fetchall()
print('Current columns in users table:')
for c in cols:
    nullable = 'NULL' if c[1] == 'YES' else 'NOT NULL'
    default = f' DEFAULT {c[3]}' if c[3] else ''
    print(f'  {c[0]}: {c[2]} {nullable}{default}')

# Check if email exists and is NOT NULL
email_col = next((c for c in cols if c[0] == 'email'), None)

if email_col:
    if email_col[1] == 'NO':  # NOT NULL
        print('\n[FIXING] Making email column nullable...')
        cur.execute("ALTER TABLE users ALTER COLUMN email DROP NOT NULL")
        conn.commit()
        print('[SUCCESS] email column is now nullable!')
    else:
        print('\n[OK] email column is already nullable')
else:
    print('\n[INFO] email column does not exist (this is fine)')

cur.close()
conn.close()
