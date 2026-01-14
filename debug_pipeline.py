#!/usr/bin/env python3
"""
Debug script to check data flow through the pipeline:
1. Producer → Kafka (check if messages are being sent)
2. Kafka → Consumer (check if messages are in Kafka)
3. Consumer → Database (check if consumer is saving to DB)
4. Database → Dashboard (check if data is in DB)
"""

import json
import os
import sys
from datetime import datetime
from urllib.parse import urlparse
from dotenv import load_dotenv
import psycopg2
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError

# Load environment
load_dotenv()

def check_kafka_messages():
    """Check if there are messages in Kafka topic."""
    print("\n" + "="*60)
    print("STEP 1: Checking Kafka Topic (sensor-data)")
    print("="*60)
    
    try:
        consumer = KafkaConsumer(
            'sensor-data',
            bootstrap_servers='localhost:9092',
            auto_offset_reset='latest',  # Only new messages
            consumer_timeout_ms=2000,  # Wait 2 seconds for messages
            value_deserializer=lambda v: v.decode('utf-8')
        )
        
        print("[OK] Connected to Kafka")
        
        # Try to get a few messages
        messages = []
        for message in consumer:
            messages.append({
                'offset': message.offset,
                'timestamp': datetime.fromtimestamp(message.timestamp / 1000).isoformat(),
                'value': json.loads(message.value) if message.value else None
            })
            if len(messages) >= 3:
                break
        
        if messages:
            print(f"[OK] Found {len(messages)} recent messages in Kafka")
            print(f"  Latest message offset: {messages[0]['offset']}")
            print(f"  Latest timestamp: {messages[0]['timestamp']}")
            return True
        else:
            print("[WARN] No NEW messages in Kafka (checking old messages...)")
            
            # Check old messages
            consumer_old = KafkaConsumer(
                'sensor-data',
                bootstrap_servers='localhost:9092',
                auto_offset_reset='earliest',
                consumer_timeout_ms=2000,
                value_deserializer=lambda v: v.decode('utf-8')
            )
            
            old_messages = []
            for message in consumer_old:
                old_messages.append(message.offset)
                if len(old_messages) >= 5:
                    break
            
            if old_messages:
                print(f"  Found {len(old_messages)} old messages (offsets: {old_messages})")
                print("  [WARN] Producer might not be running or not sending NEW messages")
            else:
                print("  [ERROR] No messages found in Kafka at all")
            
            return False
            
    except KafkaError as e:
        print(f"[ERROR] Failed to connect to Kafka: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        return False

def check_database():
    """Check if data is in the database."""
    print("\n" + "="*60)
    print("STEP 2: Checking Database (sensor_readings table)")
    print("="*60)
    
    try:
        url = urlparse(os.getenv('DATABASE_URL'))
        conn = psycopg2.connect(
            host=url.hostname,
            port=url.port,
            user=url.username,
            password=url.password,
            database=url.path[1:],
            sslmode='require'
        )
        
        print("[OK] Connected to database")
        
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'sensor_readings'
            )
        """)
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            print("[ERROR] Table 'sensor_readings' does NOT exist!")
            print("  Run: python run_migration.py setup_db_neon.sql")
            cursor.close()
            conn.close()
            return False
        
        print("[OK] Table 'sensor_readings' exists")
        
        # Count records
        cursor.execute("SELECT COUNT(*) FROM sensor_readings")
        count = cursor.fetchone()[0]
        print(f"[OK] Total readings in database: {count}")
        
        if count > 0:
            # Get latest reading
            cursor.execute("""
                SELECT id, timestamp, temperature, pressure, rpm, vibration, created_at
                FROM sensor_readings
                ORDER BY created_at DESC
                LIMIT 1
            """)
            latest = cursor.fetchone()
            print(f"[OK] Latest reading:")
            print(f"    ID: {latest[0]}")
            print(f"    Timestamp: {latest[1]}")
            print(f"    Temperature: {latest[2]}")
            print(f"    Created at: {latest[6]}")
            return True
        else:
            print("[WARN] Database table is EMPTY")
            print("  This means Consumer is not saving messages to database")
            return False
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"[ERROR] Database error: {e}")
        return False

def check_producer_running():
    """Check if producer process is running."""
    print("\n" + "="*60)
    print("STEP 3: Checking if Producer is Running")
    print("="*60)
    
    import subprocess
    try:
        # Check for producer.py in process list
        result = subprocess.run(
            ['tasklist', '/FI', 'IMAGENAME eq python.exe', '/FO', 'CSV'],
            capture_output=True,
            text=True
        )
        
        if 'producer.py' in result.stdout or 'producer' in result.stdout.lower():
            print("[OK] Producer process appears to be running")
            return True
        else:
            print("[WARN] Producer process NOT found")
            print("  Start it with: python producer.py")
            return False
    except:
        print("[WARN] Could not check process list")
        return None

def check_consumer_running():
    """Check if consumer process is running."""
    print("\n" + "="*60)
    print("STEP 4: Checking if Consumer is Running")
    print("="*60)
    
    import subprocess
    try:
        result = subprocess.run(
            ['tasklist', '/FI', 'IMAGENAME eq python.exe', '/FO', 'CSV'],
            capture_output=True,
            text=True
        )
        
        if 'consumer.py' in result.stdout or 'consumer' in result.stdout.lower():
            print("[OK] Consumer process appears to be running")
            return True
        else:
            print("[WARN] Consumer process NOT found")
            print("  Start it with: python consumer.py")
            return False
    except:
        print("[WARN] Could not check process list")
        return None

def main():
    """Run all debug checks."""
    print("\n" + "="*60)
    print("PIPELINE DEBUG TOOL")
    print("="*60)
    print("\nData Flow: Producer -> Kafka -> Consumer -> Database -> Dashboard")
    
    kafka_ok = check_kafka_messages()
    db_ok = check_database()
    producer_ok = check_producer_running()
    consumer_ok = check_consumer_running()
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Kafka has messages:     {'[OK]' if kafka_ok else '[ERROR]'}")
    print(f"Database has data:       {'[OK]' if db_ok else '[ERROR]'}")
    print(f"Producer running:        {'[OK]' if producer_ok else '[ERROR]'}")
    print(f"Consumer running:        {'[OK]' if consumer_ok else '[ERROR]'}")
    
    print("\n" + "="*60)
    print("DIAGNOSIS")
    print("="*60)
    
    if not producer_ok:
        print("[ISSUE] Producer is not running")
        print("   Fix: Start producer with 'python producer.py'")
    elif not kafka_ok:
        print("[ISSUE] Producer is running but not sending messages to Kafka")
        print("   Fix: Check producer logs for errors")
    elif not consumer_ok:
        print("[ISSUE] Consumer is not running")
        print("   Fix: Start consumer with 'python consumer.py'")
    elif not db_ok:
        print("[ISSUE] Consumer is running but not saving to database")
        print("   Fix: Check consumer logs for database connection errors")
    else:
        print("[SUCCESS] All systems operational! Data should be flowing.")
        print("   If dashboard still shows no data, check dashboard API endpoints")

if __name__ == '__main__':
    main()
