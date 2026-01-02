"""
Simple Web Dashboard for Sensor Data Pipeline
Provides controls and monitoring for the Kafka pipeline
"""

from flask import Flask, render_template, jsonify, request, make_response
import psycopg2
import subprocess
import os
import sys
import signal
import json
import threading
import time
import csv
import io
from datetime import datetime
from kafka import KafkaAdminClient

# Import ML components
try:
    from report_generator import ReportGenerator, get_report, get_report_by_anomaly
    from analysis_engine import ContextAnalyzer, get_anomaly_details
    ML_REPORTS_AVAILABLE = True
except ImportError as e:
    ML_REPORTS_AVAILABLE = False
    print(f"ML report generation not available: {e}")

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

@app.route('/api/start/<component>', methods=['POST'])
def start_component(component):
    """Start producer or consumer"""
    if component not in ['producer', 'consumer']:
        return jsonify({'success': False, 'error': 'Invalid component'})

    try:
        # Determine Python executable path (cross-platform)
        script_path = os.path.join(os.path.dirname(__file__), f'{component}.py')
        
        # Check for venv first (Windows)
        if os.name == 'nt':
            venv_python = os.path.join(os.path.dirname(__file__), 'venv', 'Scripts', 'python.exe')
            if os.path.exists(venv_python):
                python_exe = venv_python
            else:
                python_exe = sys.executable  # Use current Python
        else:
            # macOS/Linux
            venv_python = os.path.join(os.path.dirname(__file__), 'venv', 'bin', 'python')
            if os.path.exists(venv_python):
                python_exe = venv_python
            else:
                python_exe = sys.executable  # Use current Python

        # Prepare subprocess arguments
        popen_args = [python_exe, script_path]
        popen_kwargs = {}
        
        # Only use Windows-specific creationflags on Windows
        if os.name == 'nt':
            popen_kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP

        proc = subprocess.Popen(popen_args, **popen_kwargs)
        processes[component] = proc  # Store the process object, not just PID

        return jsonify({'success': True, 'pid': proc.pid})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/stop/<component>', methods=['POST'])
def stop_component(component):
    """Stop producer or consumer"""
    if component not in ['producer', 'consumer']:
        return jsonify({'success': False, 'error': 'Invalid component'})

    try:
        proc = processes.get(component)
        killed_pids = []

        # First try to kill tracked process
        if proc:
            pid = proc.pid
            if os.name == 'nt':
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(pid)],
                             capture_output=True, timeout=5)
            else:
                # macOS/Linux: Try graceful shutdown first (SIGTERM), then force kill (SIGKILL)
                try:
                    proc.terminate()  # Send SIGTERM
                    try:
                        proc.wait(timeout=2)  # Wait up to 2 seconds
                    except subprocess.TimeoutExpired:
                        # Process didn't respond, force kill
                        proc.kill()  # Send SIGKILL
                        proc.wait(timeout=1)
                except ProcessLookupError:
                    pass  # Process already dead

            try:
                proc.wait(timeout=1)
            except (subprocess.TimeoutExpired, ProcessLookupError):
                pass

            killed_pids.append(pid)
            processes[component] = None

        # Also search for any running processes with the component script name
        # This catches processes started outside the dashboard
        script_name = f'{component}.py'
        
        if os.name == 'nt':
            # Windows: Use WMIC
            try:
                result = subprocess.run(
                    ['wmic', 'process', 'where', f"CommandLine like '%{script_name}%'", 'get', 'CommandLine,ProcessId'],
                    capture_output=True, text=True, timeout=2
                )

                # Parse output and filter for actual Python processes (not wmic itself)
                lines = result.stdout.strip().split('\n')
                for line in lines[1:]:  # Skip header
                    try:
                        # Extract PID from the end of the line
                        parts = line.strip().split()
                        if parts and parts[-1].isdigit():
                            # Check if this is an actual python process (not wmic)
                            if script_name in line and 'wmic' not in line.lower() and 'python' in line.lower():
                                pid = parts[-1]
                                subprocess.run(['taskkill', '/F', '/T', '/PID', pid],
                                             capture_output=True, timeout=2)
                                killed_pids.append(int(pid))
                    except:
                        pass
            except:
                pass
        else:
            # macOS/Linux: Use ps to find and kill processes
            # Note: 'ps aux' works on macOS and most Linux distributions
            try:
                result = subprocess.run(
                    ['ps', 'aux'],
                    capture_output=True, text=True, timeout=2
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        if script_name in line and 'python' in line.lower() and 'grep' not in line:
                            try:
                                # Extract PID (second column in ps aux output)
                                parts = line.split()
                                if len(parts) >= 2 and parts[1].isdigit():
                                    pid = int(parts[1])
                                    # Only kill if not already killed
                                    if pid not in killed_pids:
                                        try:
                                            os.kill(pid, signal.SIGTERM)
                                            # Wait a bit, then force kill if still running
                                            time.sleep(0.5)
                                            try:
                                                os.kill(pid, 0)  # Check if process exists
                                                os.kill(pid, signal.SIGKILL)  # Force kill
                                            except ProcessLookupError:
                                                pass  # Process already dead
                                            killed_pids.append(pid)
                                        except ProcessLookupError:
                                            pass  # Process doesn't exist
                            except (ValueError, IndexError):
                                pass
            except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
                # ps command not available or failed - continue without error
                pass

        if killed_pids:
            return jsonify({'success': True, 'pids': killed_pids})
        else:
            return jsonify({'success': False, 'error': 'No running process found'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

def is_component_running(component):
    """Check if a component (producer or consumer) is running, even if not tracked by dashboard"""
    # First check tracked process
    proc = processes.get(component)
    if proc:
        # Check if process is still alive
        poll_result = proc.poll()
        if poll_result is None:
            # Process is still running
            return True
        else:
            # Process has terminated, clean it up
            processes[component] = None

    # Search for any running process with the component script name
    script_name = f'{component}.py'
    
    if os.name == 'nt':
        # Windows: Use WMIC
        try:
            result = subprocess.run(
                ['wmic', 'process', 'where', f"CommandLine like '%{script_name}%'", 'get', 'CommandLine,ProcessId'],
                capture_output=True, text=True, timeout=2
            )

            # Filter out lines that are from wmic itself and check for actual script execution
            lines = result.stdout.strip().split('\n')
            for line in lines[1:]:  # Skip header
                line = line.strip()
                # Check if this is an actual python process running the script (not wmic)
                if script_name in line and 'wmic' not in line.lower() and 'python' in line.lower():
                    return True
        except Exception:
            # If WMIC fails, return False (assume not running)
            pass
    else:
        # macOS/Linux: Use ps to find processes
        # Note: 'ps aux' works on macOS and most Linux distributions
        # For systems where 'ps aux' doesn't work, we fall back gracefully
        try:
            result = subprocess.run(
                ['ps', 'aux'],
                capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if script_name in line and 'python' in line.lower() and 'grep' not in line:
                        return True
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            # ps command not available or failed - assume process not running
            pass

    return False

@app.route('/api/status')
def api_status():
    """Get status of components"""
    with kafka_health_lock:
        kafka_snapshot = kafka_health.copy()

    # Check if processes are actually running (including those not tracked by dashboard)
    producer_running = is_component_running('producer')
    consumer_running = is_component_running('consumer')

    return jsonify({
        'producer_running': producer_running,
        'consumer_running': consumer_running,
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

@app.route('/api/anomalies')
def api_anomalies():
    """Get ML-detected anomalies."""
    limit = request.args.get('limit', default=50, type=int)
    only_anomalies = request.args.get('only_anomalies', default='true', type=str).lower() == 'true'
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database not connected'}), 500
    
    try:
        cursor = conn.cursor()
        
        query = """
            SELECT 
                ad.id, ad.reading_id, ad.detection_method, ad.anomaly_score,
                ad.is_anomaly, ad.detected_sensors, ad.created_at,
                sr.timestamp, sr.temperature, sr.pressure, sr.rpm, sr.vibration,
                ar.id as report_id, ar.status as report_status
            FROM anomaly_detections ad
            JOIN sensor_readings sr ON ad.reading_id = sr.id
            LEFT JOIN analysis_reports ar ON ad.id = ar.anomaly_id
        """
        
        if only_anomalies:
            query += " WHERE ad.is_anomaly = TRUE"
        
        query += " ORDER BY ad.created_at DESC LIMIT %s"
        
        cursor.execute(query, (limit,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        anomalies = []
        for row in rows:
            anomalies.append({
                'id': row[0],
                'reading_id': row[1],
                'detection_method': row[2],
                'anomaly_score': row[3],
                'is_anomaly': row[4],
                'detected_sensors': row[5] or [],
                'created_at': str(row[6]),
                'reading_timestamp': str(row[7]),
                'temperature': row[8],
                'pressure': row[9],
                'rpm': row[10],
                'vibration': row[11],
                'report_id': row[12],
                'report_status': row[13]
            })
        
        return jsonify({'anomalies': anomalies})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/anomalies/<int:anomaly_id>')
def api_anomaly_detail(anomaly_id):
    """Get details of a specific anomaly."""
    if not ML_REPORTS_AVAILABLE:
        return jsonify({'error': 'ML components not available'}), 500
    
    anomaly = get_anomaly_details(anomaly_id)
    if not anomaly:
        return jsonify({'error': 'Anomaly not found'}), 404
    
    return jsonify(anomaly)


@app.route('/api/generate-report/<int:anomaly_id>', methods=['POST'])
def api_generate_report(anomaly_id):
    """Generate an analysis report for an anomaly."""
    if not ML_REPORTS_AVAILABLE:
        return jsonify({'error': 'ML components not available'}), 500
    
    try:
        generator = ReportGenerator()
        report_id, report_data = generator.generate_and_save_report(anomaly_id)
        
        if report_id:
            return jsonify({
                'success': True,
                'report_id': report_id,
                'message': 'Report generated successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to generate report'
            }), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/reports/<int:report_id>')
def api_get_report(report_id):
    """Get a generated report."""
    if not ML_REPORTS_AVAILABLE:
        return jsonify({'error': 'ML components not available'}), 500
    
    report = get_report(report_id)
    if not report:
        return jsonify({'error': 'Report not found'}), 404
    
    return jsonify(report)


@app.route('/api/reports/by-anomaly/<int:anomaly_id>')
def api_get_report_by_anomaly(anomaly_id):
    """Get report for a specific anomaly."""
    if not ML_REPORTS_AVAILABLE:
        return jsonify({'error': 'ML components not available'}), 500
    
    report = get_report_by_anomaly(anomaly_id)
    if not report:
        return jsonify({'error': 'Report not found'}), 404
    
    return jsonify(report)


@app.route('/api/generate-full-report', methods=['POST'])
def api_generate_full_session_report():
    """Generate a comprehensive report for the entire monitoring session."""
    if not ML_REPORTS_AVAILABLE:
        return jsonify({'error': 'ML components not available'}), 500
    
    try:
        from report_generator import generate_full_session_report
        result = generate_full_session_report()
        return jsonify(result)
    except Exception as e:
        logging.error(f"Full session report generation failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/ml-stats')
def api_ml_stats():
    """Get ML detection statistics."""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database not connected'}), 500
    
    try:
        cursor = conn.cursor()
        
        # Total detections and anomalies
        cursor.execute("""
            SELECT 
                COUNT(*) as total_detections,
                COUNT(*) FILTER (WHERE is_anomaly = TRUE) as total_anomalies,
                AVG(anomaly_score) as avg_score,
                MIN(anomaly_score) as min_score,
                MAX(anomaly_score) as max_score
            FROM anomaly_detections
        """)
        stats = cursor.fetchone()
        
        # Recent anomaly rate (last 100 readings)
        cursor.execute("""
            SELECT 
                COUNT(*) FILTER (WHERE is_anomaly = TRUE)::FLOAT / 
                NULLIF(COUNT(*), 0) * 100 as recent_anomaly_rate
            FROM (
                SELECT is_anomaly FROM anomaly_detections 
                ORDER BY created_at DESC LIMIT 100
            ) recent
        """)
        recent_rate = cursor.fetchone()[0] or 0
        
        # Reports generated
        cursor.execute("""
            SELECT 
                COUNT(*) as total_reports,
                COUNT(*) FILTER (WHERE status = 'completed') as completed_reports
            FROM analysis_reports
        """)
        report_stats = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'total_detections': stats[0] or 0,
            'total_anomalies': stats[1] or 0,
            'avg_score': round(stats[2], 4) if stats[2] else 0,
            'min_score': round(stats[3], 4) if stats[3] else 0,
            'max_score': round(stats[4], 4) if stats[4] else 0,
            'recent_anomaly_rate': round(recent_rate, 2),
            'total_reports': report_stats[0] or 0,
            'completed_reports': report_stats[1] or 0,
            'ml_available': ML_REPORTS_AVAILABLE
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# THRESHOLD AND ANOMALY INJECTION APIs
# ============================================================================

# Store custom thresholds in memory (session-based)
custom_thresholds = {}

# Anomaly injection settings
injection_settings = {
    'enabled': False,
    'interval_minutes': 30,
    'next_injection_time': None,
    'inject_now': False
}


@app.route('/api/thresholds', methods=['GET'])
def api_get_thresholds():
    """Get all custom thresholds and default safe operating limits."""
    import config
    
    # Build defaults from SENSOR_THRESHOLDS (safe operating limits)
    # Fall back to SENSOR_RANGES if threshold not defined
    defaults = {}
    for name, info in config.SENSOR_RANGES.items():
        threshold = config.SENSOR_THRESHOLDS.get(name, {})
        defaults[name] = {
            'low': threshold.get('low', info['min']),
            'high': threshold.get('high', info['max']),
            'unit': info.get('unit', ''),
            # Also include ranges for reference
            'range_min': info['min'],
            'range_max': info['max']
        }
    
    return jsonify({
        'thresholds': custom_thresholds,
        'defaults': defaults
    })


@app.route('/api/thresholds', methods=['POST'])
def api_set_threshold():
    """Set custom threshold for a sensor."""
    data = request.get_json()
    if not data or 'sensor' not in data:
        return jsonify({'error': 'Missing sensor name'}), 400
    
    sensor = data['sensor']
    
    # Validate sensor exists
    if sensor not in config.SENSOR_RANGES:
        return jsonify({'error': f'Unknown sensor: {sensor}'}), 400
    
    # Handle reset
    if data.get('reset'):
        if sensor in custom_thresholds:
            del custom_thresholds[sensor]
        return jsonify({'success': True, 'message': f'Threshold for {sensor} reset to default'})
    
    # Set custom threshold
    min_val = data.get('min')
    max_val = data.get('max')
    
    if min_val is None or max_val is None:
        return jsonify({'error': 'Missing min or max value'}), 400
    
    try:
        min_val = float(min_val)
        max_val = float(max_val)
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid min or max value'}), 400
    
    if min_val >= max_val:
        return jsonify({'error': 'Min must be less than max'}), 400
    
    custom_thresholds[sensor] = {'min': min_val, 'max': max_val}
    
    return jsonify({
        'success': True,
        'sensor': sensor,
        'min': min_val,
        'max': max_val
    })


@app.route('/api/injection-settings', methods=['GET'])
def api_get_injection_settings():
    """Get anomaly injection settings for producer."""
    # Return inject_now flag and clear it immediately (one-time trigger)
    inject_now = injection_settings.get('inject_now', False)
    if inject_now:
        injection_settings['inject_now'] = False
    
    return jsonify({
        'enabled': injection_settings['enabled'],
        'interval_minutes': injection_settings['interval_minutes'],
        'next_injection_time': injection_settings['next_injection_time'],
        'inject_now': inject_now,
        'thresholds': custom_thresholds
    })


@app.route('/api/injection-settings', methods=['POST'])
def api_set_injection_settings():
    """Update anomaly injection settings."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Missing data'}), 400
    
    if 'enabled' in data:
        injection_settings['enabled'] = bool(data['enabled'])
    
    if 'interval_minutes' in data:
        try:
            interval = int(data['interval_minutes'])
            if interval < 1:
                return jsonify({'error': 'Interval must be at least 1 minute'}), 400
            injection_settings['interval_minutes'] = interval
        except (TypeError, ValueError):
            return jsonify({'error': 'Invalid interval'}), 400
    
    # Calculate next injection time
    if injection_settings['enabled']:
        from datetime import datetime, timedelta
        injection_settings['next_injection_time'] = (
            datetime.utcnow() + timedelta(minutes=injection_settings['interval_minutes'])
        ).isoformat()
    else:
        injection_settings['next_injection_time'] = None
    
    return jsonify({
        'success': True,
        'settings': injection_settings
    })


@app.route('/api/inject-anomaly', methods=['POST'])
def api_inject_anomaly_now():
    """Trigger immediate anomaly injection."""
    injection_settings['inject_now'] = True
    return jsonify({
        'success': True,
        'message': 'Anomaly injection triggered for next reading'
    })


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
    app.run(debug=True, host='0.0.0.0', port=5001)
