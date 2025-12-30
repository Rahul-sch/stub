"""
Simple Web Dashboard for Sensor Data Pipeline
Provides controls and monitoring for the Kafka pipeline
"""

from flask import Flask, render_template, jsonify, request
import psycopg2
import subprocess
import os
import signal
import json
from datetime import datetime

app = Flask(__name__)

# Store process IDs
processes = {
    'producer': None,
    'consumer': None
}

def get_db_connection():
    """Get PostgreSQL connection"""
    try:
        import config
        conn = psycopg2.connect(**config.DB_CONFIG)
        return conn
    except:
        return None

def get_stats():
    """Get current statistics from database"""
    conn = get_db_connection()
    if not conn:
        return {'error': 'Database not connected'}

    try:
        cursor = conn.cursor()

        # Total count
        cursor.execute("SELECT COUNT(*) FROM sensor_readings;")
        total_count = cursor.fetchone()[0]

        # Recent readings (last 20)
        cursor.execute("""
            SELECT timestamp, temperature, pressure, vibration, humidity, rpm, created_at
            FROM sensor_readings
            ORDER BY created_at DESC
            LIMIT 20;
        """)
        recent_readings = cursor.fetchall()

        # Average values
        cursor.execute("""
            SELECT
                AVG(temperature) as avg_temp,
                AVG(pressure) as avg_pressure,
                AVG(vibration) as avg_vibration,
                AVG(humidity) as avg_humidity,
                AVG(rpm) as avg_rpm
            FROM sensor_readings;
        """)
        averages = cursor.fetchone()

        cursor.close()
        conn.close()

        return {
            'total_count': total_count,
            'recent_readings': [
                {
                    'timestamp': str(reading[0]),
                    'temperature': reading[1],
                    'pressure': reading[2],
                    'vibration': reading[3],
                    'humidity': reading[4],
                    'rpm': reading[5],
                    'created_at': str(reading[6])
                } for reading in recent_readings
            ] if recent_readings else [],
            'averages': {
                'temperature': round(averages[0], 2) if averages[0] else 0,
                'pressure': round(averages[1], 2) if averages[1] else 0,
                'vibration': round(averages[2], 2) if averages[2] else 0,
                'humidity': round(averages[3], 2) if averages[3] else 0,
                'rpm': round(averages[4], 2) if averages[4] else 0
            } if averages else None
        }
    except Exception as e:
        return {'error': str(e)}

def get_config():
    """Get current configuration"""
    try:
        import config
        total_hours = config.DURATION_HOURS
        hours = int(total_hours)
        minutes = int((total_hours - hours) * 60)
        return {
            'duration_hours': hours,
            'duration_minutes': minutes,
            'interval_seconds': config.INTERVAL_SECONDS
        }
    except Exception as e:
        return {'error': str(e)}

def update_config(duration_hours, duration_minutes, interval_seconds):
    """Update config.py file"""
    try:
        # Convert hours + minutes to decimal hours
        total_hours = duration_hours + (duration_minutes / 60.0)

        config_path = os.path.join(os.path.dirname(__file__), 'config.py')
        with open(config_path, 'r') as f:
            content = f.read()

        # Update values
        import re
        content = re.sub(
            r'DURATION_HOURS\s*=\s*[\d.]+',
            f'DURATION_HOURS = {total_hours}',
            content
        )
        content = re.sub(
            r'INTERVAL_SECONDS\s*=\s*\d+',
            f'INTERVAL_SECONDS = {interval_seconds}',
            content
        )

        with open(config_path, 'w') as f:
            f.write(content)

        return True
    except Exception as e:
        return False

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/stats')
def api_stats():
    """Get current stats"""
    return jsonify(get_stats())

@app.route('/api/config', methods=['GET', 'POST'])
def api_config():
    """Get or update configuration"""
    if request.method == 'POST':
        data = request.json
        duration_hours = int(data.get('duration_hours', 0))
        duration_minutes = int(data.get('duration_minutes', 0))
        interval = int(data.get('interval_seconds', 30))

        if update_config(duration_hours, duration_minutes, interval):
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to update config'})
    else:
        return jsonify(get_config())

@app.route('/api/start/<component>')
def start_component(component):
    """Start producer or consumer"""
    if component not in ['producer', 'consumer']:
        return jsonify({'success': False, 'error': 'Invalid component'})

    try:
        venv_python = os.path.join(os.path.dirname(__file__), 'venv', 'Scripts', 'python.exe')
        script_path = os.path.join(os.path.dirname(__file__), f'{component}.py')

        proc = subprocess.Popen(
            [venv_python, script_path],
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        )
        processes[component] = proc  # Store the process object, not just PID

        return jsonify({'success': True, 'pid': proc.pid})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/stop/<component>')
def stop_component(component):
    """Stop producer or consumer"""
    if component not in ['producer', 'consumer']:
        return jsonify({'success': False, 'error': 'Invalid component'})

    try:
        proc = processes.get(component)
        if proc:
            proc.terminate()  # Use terminate() instead of os.kill()
            proc.wait(timeout=5)  # Wait for process to finish
            processes[component] = None
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Not running'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/status')
def api_status():
    """Get status of components"""
    return jsonify({
        'producer_running': processes['producer'] is not None,
        'consumer_running': processes['consumer'] is not None
    })

@app.route('/api/clear_data')
def clear_data():
    """Clear all data from database"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'error': 'Database not connected'})

    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sensor_readings;")
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
