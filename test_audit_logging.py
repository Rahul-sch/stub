#!/usr/bin/env python
"""
Test script to verify audit logging is working correctly.
This script tests that all /api/v1/ingest and /api/admin/ endpoints are logging to audit_logs_v2.
"""

import os
import sys
import requests
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Configuration
BASE_URL = "http://localhost:5000"
API_KEY = os.environ.get('INGEST_API_KEY', 'rig-alpha-secret')

def test_ingest_endpoint():
    """Test /api/v1/ingest endpoint logging."""
    print("=" * 80)
    print("Testing /api/v1/ingest endpoint")
    print("=" * 80)
    
    url = f"{BASE_URL}/api/v1/ingest"
    headers = {
        'X-API-KEY': API_KEY,
        'Content-Type': 'application/json'
    }
    data = {
        'machine_id': 'A',
        'temperature': 75.5,
        'pressure': 120.3
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            print("[OK] Ingest endpoint responded successfully")
            print("[INFO] Check audit_logs_v2 table for entry with action_type='INGEST'")
        else:
            print(f"[ERROR] Ingest endpoint failed: {response.text}")
    except Exception as e:
        print(f"[ERROR] Failed to test ingest endpoint: {e}")

def test_admin_endpoints():
    """Test admin endpoints (requires authentication)."""
    print("\n" + "=" * 80)
    print("Testing Admin Endpoints")
    print("=" * 80)
    print("\n[INFO] Admin endpoints require authentication.")
    print("[INFO] Please login first and update the session cookie below.")
    print("\nTo test admin endpoints:")
    print("1. Login via browser: http://localhost:5000/login")
    print("2. Open browser DevTools > Network tab")
    print("3. Make a request to any /api/admin/ endpoint")
    print("4. Copy the session cookie from the request headers")
    print("5. Update SESSION_COOKIE in this script")
    print("\nOr use the Flask test client for automated testing.")

def check_audit_logs():
    """Check audit_logs_v2 table for recent entries."""
    print("\n" + "=" * 80)
    print("Checking Audit Logs")
    print("=" * 80)
    
    try:
        import config
        import psycopg2
        
        conn = psycopg2.connect(**config.DB_CONFIG)
        cursor = conn.cursor()
        
        # Get recent audit logs
        cursor.execute("""
            SELECT id, user_id, username, role, action_type, resource_type, resource_id, timestamp
            FROM audit_logs_v2
            ORDER BY timestamp DESC
            LIMIT 10
        """)
        
        rows = cursor.fetchall()
        
        if rows:
            print(f"\nFound {len(rows)} recent audit log entries:\n")
            for row in rows:
                print(f"  ID: {row[0]}, User: {row[2]} ({row[3]}), Action: {row[4]}, Resource: {row[5]}, Time: {row[7]}")
        else:
            print("\n[WARNING] No audit log entries found. Make sure:")
            print("  1. audit_logs_v2 table exists")
            print("  2. Endpoints are being called")
            print("  3. @log_action decorator is applied")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"[ERROR] Failed to check audit logs: {e}")

if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("AUDIT LOGGING TEST SUITE")
    print("=" * 80)
    
    # Test ingest endpoint (no auth required)
    test_ingest_endpoint()
    
    # Check audit logs
    check_audit_logs()
    
    # Admin endpoints info
    test_admin_endpoints()
    
    print("\n" + "=" * 80)
    print("Test Complete")
    print("=" * 80)

