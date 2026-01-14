#!/usr/bin/env python3
"""
Run database migrations
Usage: python run_migration.py <migration_file.sql>
"""

import sys
import os
import psycopg2
from psycopg2 import sql

def get_db_connection():
    """Get database connection using the same config as the main application."""
    try:
        # Try to use config.py (same as dashboard.py)
        try:
            import config
            conn = psycopg2.connect(**config.DB_CONFIG)
            return conn
        except ImportError:
            # Fallback to environment variables or defaults
            conn = psycopg2.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                port=int(os.getenv('DB_PORT', '5432')),
                database=os.getenv('DB_NAME', 'sensordb'),
                user=os.getenv('DB_USER', 'sensoruser'),
                password=os.getenv('DB_PASSWORD', 'sensorpass')
            )
            return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        print(f"\nTrying to connect with:")
        print(f"  Host: {os.getenv('DB_HOST', 'localhost')}")
        print(f"  Port: {os.getenv('DB_PORT', '5432')}")
        print(f"  Database: {os.getenv('DB_NAME', 'sensordb')}")
        print(f"  User: {os.getenv('DB_USER', 'sensoruser')}")
        print(f"\nIf using Docker, the default credentials are:")
        print(f"  User: sensoruser")
        print(f"  Password: sensorpass")
        print(f"  Database: sensordb")
        return None

def run_migration(migration_file):
    """Run a SQL migration file."""
    if not os.path.exists(migration_file):
        print(f"Migration file not found: {migration_file}")
        return False
    
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Read migration file
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        # Execute migration
        cursor.execute(migration_sql)
        conn.commit()
        
        print(f"[SUCCESS] Migration {migration_file} executed successfully")
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        if conn:
            conn.rollback()
            cursor.close()
            conn.close()
        print(f"[ERROR] Migration failed: {e}")
        return False

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python run_migration.py <migration_file.sql>")
        sys.exit(1)
    
    migration_file = sys.argv[1]
    success = run_migration(migration_file)
    sys.exit(0 if success else 1)

