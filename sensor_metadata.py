"""
Sensor Metadata Service
Provides metadata lookup for sensors (location, equipment, criticality, etc.)
"""

import psycopg2
import logging
from functools import lru_cache

# Cache metadata lookup to avoid repeated DB queries
_metadata_cache = None
_cache_lock = None

def _init_cache_lock():
    """Initialize cache lock if needed"""
    global _cache_lock
    if _cache_lock is None:
        import threading
        _cache_lock = threading.Lock()

def get_db_connection():
    """Get PostgreSQL connection"""
    try:
        import config
        conn = psycopg2.connect(**config.DB_CONFIG)
        return conn
    except Exception as e:
        logging.error(f"Failed to connect to database: {e}")
        return None

def load_sensor_metadata():
    """
    Load all sensor metadata from database into a lookup dictionary.
    Returns dict keyed by sensor_name with metadata fields.
    Falls back gracefully if table doesn't exist or query fails.
    """
    global _metadata_cache
    
    # Return cached data if available
    if _metadata_cache is not None:
        return _metadata_cache
    
    _init_cache_lock()
    
    with _cache_lock:
        # Double-check after acquiring lock
        if _metadata_cache is not None:
            return _metadata_cache
        
        conn = get_db_connection()
        if not conn:
            logging.warning("Database connection failed, metadata unavailable")
            _metadata_cache = {}
            return _metadata_cache
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT sensor_name, machine_type, category, location, 
                       equipment_section, criticality, unit
                FROM sensor_metadata
            """)
            
            metadata = {}
            for row in cursor.fetchall():
                sensor_name, machine_type, category, location, equipment_section, criticality, unit = row
                metadata[sensor_name] = {
                    'machine_type': machine_type or 'industrial',
                    'category': category or '',
                    'location': location or '',
                    'equipment_section': equipment_section or '',
                    'criticality': criticality or 'medium',
                    'unit': unit or ''
                }
            
            cursor.close()
            conn.close()
            
            _metadata_cache = metadata
            logging.info(f"Loaded {len(metadata)} sensor metadata records")
            return metadata
            
        except psycopg2.errors.UndefinedTable:
            # Table doesn't exist yet - return empty dict (graceful fallback)
            logging.warning("sensor_metadata table does not exist - run migration first")
            _metadata_cache = {}
            return _metadata_cache
        except Exception as e:
            logging.error(f"Error loading sensor metadata: {e}")
            _metadata_cache = {}
            return _metadata_cache

def get_sensor_metadata(sensor_name):
    """
    Get metadata for a specific sensor.
    Returns dict with location, equipment_section, criticality, unit.
    Returns empty dict if sensor not found (safe fallback).
    """
    metadata = load_sensor_metadata()
    return metadata.get(sensor_name, {})

def enrich_sensor_data(sensor_name, sensor_data):
    """
    Enrich sensor data dict with metadata.
    Adds 'metadata' key with location, equipment_section, criticality, unit.
    Preserves all existing fields in sensor_data.
    """
    metadata = get_sensor_metadata(sensor_name)
    
    # Add metadata if available, otherwise add empty dict
    sensor_data['metadata'] = {
        'location': metadata.get('location', ''),
        'equipment_section': metadata.get('equipment_section', ''),
        'criticality': metadata.get('criticality', 'medium'),
        'unit': metadata.get('unit', '')
    }
    
    return sensor_data

def clear_cache():
    """Clear metadata cache (useful for testing or after updates)"""
    global _metadata_cache
    _metadata_cache = None

