#!/usr/bin/env python
"""
Quick script to check PostgreSQL version and database connection info.
Run this to verify your current database configuration.
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

try:
    import config
    import psycopg2
    from urllib.parse import urlparse
    
    print("=" * 80)
    print("DATABASE CONFIGURATION CHECK")
    print("=" * 80)
    print()
    
    # Check environment variable
    database_url = os.environ.get('DATABASE_URL', '')
    print(f"1. DATABASE_URL environment variable:")
    if database_url:
        # Mask password for security
        parsed = urlparse(database_url)
        masked_url = f"{parsed.scheme}://{parsed.username}:***@{parsed.hostname}:{parsed.port}{parsed.path}"
        print(f"   [OK] Found: {masked_url}")
        print(f"   -> Host: {parsed.hostname}")
        print(f"   -> Port: {parsed.port or 5432}")
        print(f"   -> Database: {parsed.path.lstrip('/')}")
        print(f"   -> User: {parsed.username}")
    else:
        print("   [NOT SET] Using local defaults")
    print()
    
    # Check config.py values
    print(f"2. Current config.py values:")
    print(f"   -> Host: {config.DB_HOST}")
    print(f"   -> Port: {config.DB_PORT}")
    print(f"   -> Database: {config.DB_NAME}")
    print(f"   -> User: {config.DB_USER}")
    print(f"   -> Password: {'***' if config.DB_PASSWORD else '(empty)'}")
    print()
    
    # Check connection
    print(f"3. Testing connection...")
    try:
        conn = psycopg2.connect(**config.DB_CONFIG)
        cursor = conn.cursor()
        
        # Get PostgreSQL version
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"   [OK] Connected successfully!")
        print(f"   -> PostgreSQL Version: {version}")
        print()
        
        # Get database info
        cursor.execute("SELECT current_database(), current_user, inet_server_addr(), inet_server_port();")
        db_info = cursor.fetchone()
        print(f"4. Database Information:")
        print(f"   -> Current Database: {db_info[0]}")
        print(f"   -> Current User: {db_info[1]}")
        print(f"   -> Server Address: {db_info[2] or 'localhost'}")
        print(f"   -> Server Port: {db_info[3] or config.DB_PORT}")
        print()
        
        # Check if it's a remote host
        if config.DB_HOST not in ['localhost', '127.0.0.1']:
            print(f"   -> [REMOTE] Database detected: {config.DB_HOST}")
        else:
            print(f"   -> [LOCAL] Database (Docker container)")
        
        cursor.close()
        conn.close()
        
    except psycopg2.Error as e:
        print(f"   [ERROR] Connection failed: {e}")
        print()
        print("   Troubleshooting:")
        print("   - Is PostgreSQL running?")
        print("   - Check DATABASE_URL in .env file")
        print("   - Verify credentials are correct")
        sys.exit(1)
    
    print("=" * 80)
    
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure you're running from the stub directory with venv activated")
    sys.exit(1)

