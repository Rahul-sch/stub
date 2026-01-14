"""Test if consumer can insert a message."""
import json
import sys
import os
from dotenv import load_dotenv
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from consumer import SensorDataConsumer

# Create consumer instance
consumer = SensorDataConsumer()

# Connect to database
consumer.db_conn, consumer.db_cursor = consumer.connect_to_database()
if not consumer.db_conn or not consumer.db_cursor:
    print("ERROR: Could not connect to database")
    sys.exit(1)

print("Connected to database successfully")

# Create a test message
test_data = {
    'timestamp': '2026-01-08T14:20:00.000000',
    'temperature': 75.5,
    'pressure': 5.2,
    'humidity': 50.0,
    'vibration': 2.5,
    'rpm': 2000,
    'custom_sensors': {}
}

print(f"\nAttempting to insert test reading...")
print(f"Data: {json.dumps(test_data, indent=2)}")

reading_id = consumer.insert_reading(test_data)

if reading_id:
    print(f"\n[SUCCESS] Inserted reading with ID: {reading_id}")
else:
    print(f"\n[FAILED] insert_reading returned None")

consumer.db_cursor.close()
consumer.db_conn.close()
