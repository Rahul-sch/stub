"""
Simple Web Dashboard for Sensor Data Pipeline
Provides controls and monitoring for the Kafka pipeline
"""

from flask import Flask, render_template, jsonify, request, make_response
import psycopg2
import subprocess
import os
import signal
import json
import threading
import time
import csv
import io
from datetime import datetime
from kafka import KafkaAdminClient

app = Flask(__name__)

# Store process IDs
processes = {
    'producer': None,
    'consumer': None
}

kafka_health = {
    'status': 'unknown',
    'checked_at': None,
    'latency_ms': None,
    'error': None
}
kafka_health_lock = threading.Lock()
HEARTBEAT_INTERVAL_SECONDS = 10
last_kafka_status = None
heartbeat_thread_started = False
heartbeat_lock = threading.Lock()

def get_db_connection():
    """Get PostgreSQL connection"""
    try:
        import config
        conn = psycopg2.connect(**config.DB_CONFIG)
        return conn
    except:
        return None

def record_alert(alert_type, message, severity='INFO', source='dashboard'):
    """Persist alert messages for dashboard display."""
    conn = None
    cursor = None
    try:
        import config
        conn = psycopg2.connect(**config.DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO alerts (alert_type, source, severity, message)
            VALUES (%s, %s, %s, %s)
            """,
            (alert_type, source, severity, message)
        )
        conn.commit()
    except Exception:
        if conn:
            conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def get_alerts(limit=20):
    """Fetch recent alerts."""
    conn = get_db_connection()
    if not conn:
        return []

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT alert_type, source, severity, message, created_at
            FROM alerts
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (limit,)
        )
        records = cursor.fetchall()
        cursor.close()
        conn.close()
        return [
            {
                'alert_type': row[0],
                'source': row[1],
                'severity': row[2],
                'message': row[3],
                'created_at': str(row[4])
            } for row in records
        ]
    except Exception:
        return []

def check_kafka_health():
    """Ping Kafka broker and update global status."""
    global last_kafka_status
    start_time = time.time()
    try:
        import config
        admin = KafkaAdminClient(
            bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS,
            client_id='dashboard-heartbeat',
            request_timeout_ms=5000
        )
        admin.list_topics()
        admin.close()

        latency_ms = round((time.time() - start_time) * 1000, 2)
        with kafka_health_lock:
            kafka_health.update({
                'status': 'healthy',
                'checked_at': datetime.utcnow().isoformat(),
                'latency_ms': latency_ms,
                'error': None
            })

        if last_kafka_status != 'healthy':
            last_kafka_status = 'healthy'
    except Exception as e:
        error_message = str(e)
        with kafka_health_lock:
            kafka_health.update({
                'status': 'unhealthy',
                'checked_at': datetime.utcnow().isoformat(),
                'latency_ms': None,
                'error': error_message
            })

        if last_kafka_status != 'unhealthy':
            record_alert('KAFKA_HEARTBEAT', f"Kafka heartbeat failed: {error_message}", severity='CRITICAL')
            last_kafka_status = 'unhealthy'

def heartbeat_worker():
    """Background thread that keeps Kafka heartbeat fresh."""
    while True:
        check_kafka_health()
        time.sleep(HEARTBEAT_INTERVAL_SECONDS)

def start_kafka_monitor():
    """Launch heartbeat worker exactly once."""
    global heartbeat_thread_started
    with heartbeat_lock:
        if heartbeat_thread_started:
            return
        thread = threading.Thread(target=heartbeat_worker, daemon=True)
        thread.start()
        heartbeat_thread_started = True

def get_stats():
    """Get current statistics from database with all 50 parameters organized by category"""
    conn = get_db_connection()
    if not conn:
        return {'error': 'Database not connected'}

    try:
        import config
        cursor = conn.cursor()

        # Total count
        cursor.execute("SELECT COUNT(*) FROM sensor_readings;")
        total_count = cursor.fetchone()[0]

        # Recent readings (last 10 with key parameters for top stats)
        cursor.execute("""
            SELECT timestamp, rpm, temperature, vibration, pressure, humidity, created_at
            FROM sensor_readings
            ORDER BY created_at DESC
            LIMIT 10;
        """)
        recent_readings = cursor.fetchall()

        # Recent readings with ALL 50 parameters for history display
        cursor.execute("""
            SELECT
                timestamp, created_at,
                temperature, pressure, humidity, ambient_temp, dew_point,
                air_quality_index, co2_level, particle_count, noise_level, light_intensity,
                vibration, rpm, torque, shaft_alignment, bearing_temp,
                motor_current, belt_tension, gear_wear, coupling_temp, lubrication_pressure,
                coolant_temp, exhaust_temp, oil_temp, radiator_temp, thermal_efficiency,
                heat_dissipation, inlet_temp, outlet_temp, core_temp, surface_temp,
                voltage, current, power_factor, frequency, resistance,
                capacitance, inductance, phase_angle, harmonic_distortion, ground_fault,
                flow_rate, fluid_pressure, viscosity, density, reynolds_number,
                pipe_pressure_drop, pump_efficiency, cavitation_index, turbulence, valve_position
            FROM sensor_readings
            ORDER BY created_at DESC
            LIMIT 10;
        """)
        full_readings = cursor.fetchall()

        # Calculate averages for all 50 parameters organized by category
        stats_by_category = {}
        for category_key, category_name in config.SENSOR_CATEGORIES.items():
            # Get sensors in this category
            sensors = [name for name, spec in config.SENSOR_RANGES.items()
                      if spec.get('category') == category_key]

            if sensors:
                # Build dynamic query for averages
                avg_fields = ', '.join([f"AVG({sensor})::NUMERIC(10,2) as avg_{sensor}" for sensor in sensors])
                query = f"SELECT {avg_fields} FROM sensor_readings;"
                cursor.execute(query)
                averages = cursor.fetchone()

                # Build category stats
                category_stats = {}
                for i, sensor in enumerate(sensors):
                    value = averages[i] if averages and averages[i] is not None else None
                    category_stats[sensor] = {
                        'value': float(value) if value is not None else None,
                        'unit': config.SENSOR_RANGES[sensor].get('unit', '')
                    }

                stats_by_category[category_key] = {
                    'name': category_name,
                    'sensors': category_stats
                }

        cursor.close()
        conn.close()

        # Build full readings with all 50 parameters
        full_readings_list = []
        if full_readings:
            for reading in full_readings:
                full_readings_list.append({
                    'timestamp': str(reading[0]),
                    'created_at': str(reading[1]),
                    'temperature': reading[2], 'pressure': reading[3], 'humidity': reading[4],
                    'ambient_temp': reading[5], 'dew_point': reading[6],
                    'air_quality_index': reading[7], 'co2_level': reading[8],
                    'particle_count': reading[9], 'noise_level': reading[10], 'light_intensity': reading[11],
                    'vibration': reading[12], 'rpm': reading[13], 'torque': reading[14],
                    'shaft_alignment': reading[15], 'bearing_temp': reading[16],
                    'motor_current': reading[17], 'belt_tension': reading[18], 'gear_wear': reading[19],
                    'coupling_temp': reading[20], 'lubrication_pressure': reading[21],
                    'coolant_temp': reading[22], 'exhaust_temp': reading[23], 'oil_temp': reading[24],
                    'radiator_temp': reading[25], 'thermal_efficiency': reading[26],
                    'heat_dissipation': reading[27], 'inlet_temp': reading[28], 'outlet_temp': reading[29],
                    'core_temp': reading[30], 'surface_temp': reading[31],
                    'voltage': reading[32], 'current': reading[33], 'power_factor': reading[34],
                    'frequency': reading[35], 'resistance': reading[36],
                    'capacitance': reading[37], 'inductance': reading[38], 'phase_angle': reading[39],
                    'harmonic_distortion': reading[40], 'ground_fault': reading[41],
                    'flow_rate': reading[42], 'fluid_pressure': reading[43], 'viscosity': reading[44],
                    'density': reading[45], 'reynolds_number': reading[46],
                    'pipe_pressure_drop': reading[47], 'pump_efficiency': reading[48],
                    'cavitation_index': reading[49], 'turbulence': reading[50], 'valve_position': reading[51]
                })

        return {
            'total_count': total_count,
            'recent_readings': [
                {
                    'timestamp': str(reading[0]),
                    'rpm': reading[1],
                    'temperature': reading[2],
                    'vibration': reading[3],
                    'pressure': reading[4],
                    'humidity': reading[5],
                    'created_at': str(reading[6])
                } for reading in recent_readings
            ] if recent_readings else [],
            'recent_readings_full': full_readings_list,
            'stats_by_category': stats_by_category
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
            'interval_seconds': config.INTERVAL_SECONDS,
            'limits': config.CONFIG_LIMITS,
            'defaults': get_default_config_values()
        }
    except Exception as e:
        return {'error': str(e)}

def get_default_config_values():
    """Expose defaults from config module."""
    try:
        import config
        total_hours = config.DEFAULT_DURATION_HOURS
        hours = int(total_hours)
        minutes = int(round((total_hours - hours) * 60))
        return {
            'duration_hours': hours,
            'duration_minutes': minutes,
            'interval_seconds': config.DEFAULT_INTERVAL_SECONDS
        }
    except Exception:
        return {
            'duration_hours': 0,
            'duration_minutes': 1,
            'interval_seconds': 5
        }

def validate_config_values(duration_hours, duration_minutes, interval_seconds):
    """Validate duration and interval input from dashboard."""
    try:
        import config
        if duration_hours < 0 or duration_minutes < 0:
            return False, "Duration cannot be negative."

        total_hours = duration_hours + (duration_minutes / 60.0)
        limits = config.CONFIG_LIMITS['duration_hours']
        if total_hours < limits['min'] or total_hours > limits['max']:
            return False, f"Duration must be between {limits['min']} and {limits['max']} hours."

        interval_limits = config.CONFIG_LIMITS['interval_seconds']
        if interval_seconds < interval_limits['min'] or interval_seconds > interval_limits['max']:
            return False, f"Interval must be between {interval_limits['min']} and {interval_limits['max']} seconds."

        return True, ""
    except Exception as e:
        return False, str(e)

def update_config(duration_hours, duration_minutes, interval_seconds):
    """Update config.py file"""
    try:
        is_valid, message = validate_config_values(duration_hours, duration_minutes, interval_seconds)
        if not is_valid:
            return False, message

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

        return True, "Configuration updated."
    except Exception as e:
        return False, str(e)

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html')

def init_background_threads():
    """Ensure background monitors are running."""
    start_kafka_monitor()
init_background_threads()

@app.route('/api/stats')
def api_stats():
    """Get current stats"""
    return jsonify(get_stats())

@app.route('/api/alerts')
def api_alerts():
    """Get recent alerts"""
    limit = request.args.get('limit', default=20, type=int)
    return jsonify({'alerts': get_alerts(limit)})

@app.route('/api/config', methods=['GET', 'POST'])
def api_config():
    """Get or update configuration"""
    if request.method == 'POST':
        data = request.json or {}
        duration_hours = int(data.get('duration_hours', 0))
        duration_minutes = int(data.get('duration_minutes', 0))
        interval = int(data.get('interval_seconds', 30))

        success, message = update_config(duration_hours, duration_minutes, interval)
        if success:
            return jsonify({'success': True, 'config': get_config()})
        else:
            return jsonify({'success': False, 'error': message})
    else:
        return jsonify(get_config())

@app.route('/api/config/reset', methods=['POST'])
def reset_config():
    """Reset config.py to default values."""
    defaults = get_default_config_values()
    success, message = update_config(
        defaults['duration_hours'],
        defaults['duration_minutes'],
        defaults['interval_seconds']
    )
    if success:
        return jsonify({'success': True, 'config': get_config()})
    else:
        return jsonify({'success': False, 'error': message})

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
            pid = proc.pid
            # Use taskkill to force terminate the process tree on Windows
            if os.name == 'nt':
                # /F = force, /T = terminate child processes, /PID = process ID
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(pid)],
                             capture_output=True, timeout=5)
            else:
                proc.kill()

            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                pass

            processes[component] = None
            return jsonify({'success': True, 'pid': pid})
        else:
            return jsonify({'success': False, 'error': 'Not running'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/status')
def api_status():
    """Get status of components"""
    with kafka_health_lock:
        kafka_snapshot = kafka_health.copy()

    # Check if processes are actually running
    for component in ['producer', 'consumer']:
        proc = processes.get(component)
        if proc and proc.poll() is not None:
            # Process has terminated, clean it up
            processes[component] = None

    return jsonify({
        'producer_running': processes['producer'] is not None and processes['producer'].poll() is None,
        'consumer_running': processes['consumer'] is not None and processes['consumer'].poll() is None,
        'kafka': kafka_snapshot
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

@app.route('/api/export')
def export_data():
    """Export recent readings as CSV with all 50 parameters."""
    limit = request.args.get('limit', default=500, type=int)
    if limit is None:
        limit = 500
    limit = max(1, min(limit, 5000))
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database not connected'}), 500

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                timestamp, created_at,
                temperature, pressure, humidity, ambient_temp, dew_point,
                air_quality_index, co2_level, particle_count, noise_level, light_intensity,
                vibration, rpm, torque, shaft_alignment, bearing_temp,
                motor_current, belt_tension, gear_wear, coupling_temp, lubrication_pressure,
                coolant_temp, exhaust_temp, oil_temp, radiator_temp, thermal_efficiency,
                heat_dissipation, inlet_temp, outlet_temp, core_temp, surface_temp,
                voltage, current, power_factor, frequency, resistance,
                capacitance, inductance, phase_angle, harmonic_distortion, ground_fault,
                flow_rate, fluid_pressure, viscosity, density, reynolds_number,
                pipe_pressure_drop, pump_efficiency, cavitation_index, turbulence, valve_position
            FROM sensor_readings
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (limit,)
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        output = io.StringIO()
        writer = csv.writer(output)
        # Write CSV header with all 50 parameters
        writer.writerow([
            'timestamp', 'created_at',
            'temperature', 'pressure', 'humidity', 'ambient_temp', 'dew_point',
            'air_quality_index', 'co2_level', 'particle_count', 'noise_level', 'light_intensity',
            'vibration', 'rpm', 'torque', 'shaft_alignment', 'bearing_temp',
            'motor_current', 'belt_tension', 'gear_wear', 'coupling_temp', 'lubrication_pressure',
            'coolant_temp', 'exhaust_temp', 'oil_temp', 'radiator_temp', 'thermal_efficiency',
            'heat_dissipation', 'inlet_temp', 'outlet_temp', 'core_temp', 'surface_temp',
            'voltage', 'current', 'power_factor', 'frequency', 'resistance',
            'capacitance', 'inductance', 'phase_angle', 'harmonic_distortion', 'ground_fault',
            'flow_rate', 'fluid_pressure', 'viscosity', 'density', 'reynolds_number',
            'pipe_pressure_drop', 'pump_efficiency', 'cavitation_index', 'turbulence', 'valve_position'
        ])
        for row in rows:
            writer.writerow(row)

        response = make_response(output.getvalue())
        filename = f"sensor_readings_50params_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        response.headers['Content-Type'] = 'text/csv'
        return response
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
