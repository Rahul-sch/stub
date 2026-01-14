"""Quick script to check database reading count."""
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
cur.execute('SELECT COUNT(*) FROM sensor_readings')
count = cur.fetchone()[0]
print(f'Readings in database: {count}')

if count > 0:
    cur.execute('SELECT id, timestamp, temperature, rpm FROM sensor_readings ORDER BY id DESC LIMIT 5')
    rows = cur.fetchall()
    print(f'\nLatest 5 readings:')
    for r in rows:
        print(f'  ID {r[0]}: {r[1]} | Temp: {r[2]}F | RPM: {r[3]}')

cur.close()
conn.close()
