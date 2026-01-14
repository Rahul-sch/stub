"""
Sensor Data Producer
Generates stub sensor data and sends to Kafka topic every 30 seconds.
"""

import json
import logging
import random
import signal
import sys
import time
import requests
import os
from datetime import datetime, timedelta
from kafka import KafkaProducer
from kafka.errors import KafkaError
import psycopg2

import config

# Debug logging configuration
DEBUG_LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.cursor', 'debug.log')

def debug_log(location, message, data=None, hypothesis_id=None):
    """Write debug log entry in NDJSON format"""
    try:
        log_entry = {
            'sessionId': 'debug-session',
            'runId': 'run1',
            'hypothesisId': hypothesis_id,
            'location': location,
            'message': message,
            'data': data or {},
            'timestamp': int(time.time() * 1000)
        }
        with open(DEBUG_LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry) + '\n')
    except Exception:
        pass  # Silently fail if logging fails

# Dashboard API URL for injection settings
DASHBOARD_API_URL = 'http://localhost:5000'


class SensorDataProducer:
    """Generates stub sensor data and publishes to Kafka."""

    def __init__(self):
        """Initialize the producer with configuration."""
        self.setup_logging()
        self.producer = None
        self.message_count = 0
        self.total_messages = int((config.DURATION_HOURS * 3600) / config.INTERVAL_SECONDS)
        self.should_shutdown = False

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        # Windows-specific signal for process termination
        if sys.platform == 'win32':
            signal.signal(signal.SIGBREAK, self.signal_handler)

        self.logger.info(f"Producer initialized - Duration: {config.DURATION_HOURS} hours, "
                        f"Interval: {config.INTERVAL_SECONDS}s, "
                        f"Total messages: {self.total_messages}")
        
        # Anomaly injection state
        self.last_injection_check = None
        self.next_injection_time = None
        self.custom_thresholds = {}
        
        # Custom sensors state
        self.custom_sensors = {}  # {sensor_name: {min_range, max_range, unit, category, ...}}
        self.last_config_reload = None
        self.config_reload_interval = 60  # Reload custom sensors every 60 seconds

    def setup_logging(self):
        """Configure logging."""
        logging.basicConfig(
            level=config.LOG_LEVEL,
            format=config.LOG_FORMAT,
            datefmt=config.LOG_DATE_FORMAT
        )
        self.logger = logging.getLogger(__name__)

    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.should_shutdown = True

    def connect_to_kafka(self):
        """Connect to Kafka with retry logic and exponential backoff."""
        retry_delay = config.INITIAL_RETRY_DELAY

        for attempt in range(1, config.MAX_RETRIES + 1):
            if self.should_shutdown:
                return None

            try:
                self.logger.info(f"Attempting to connect to Kafka (attempt {attempt}/{config.MAX_RETRIES})...")
                producer = KafkaProducer(**config.KAFKA_PRODUCER_CONFIG)
                self.logger.info(f"Successfully connected to Kafka at {config.KAFKA_BOOTSTRAP_SERVERS}")
                return producer

            except KafkaError as e:
                self.logger.warning(f"Failed to connect to Kafka: {e}")

                if attempt < config.MAX_RETRIES:
                    self.logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay = min(retry_delay * config.BACKOFF_MULTIPLIER, config.MAX_RETRY_DELAY)
                else:
                    self.logger.error("Max retries reached. Could not connect to Kafka.")
                    raise

        return None

    def load_custom_sensors(self):
        """Load active custom sensors from database."""
        try:
            conn = psycopg2.connect(**config.DB_CONFIG)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT sensor_name, category, unit, min_range, max_range, 
                       low_threshold, high_threshold, updated_at
                FROM custom_sensors
                WHERE is_active = TRUE
                ORDER BY sensor_name
            """)
            
            custom_sensors = {}
            for row in cursor.fetchall():
                sensor_name, category, unit, min_range, max_range, low_threshold, high_threshold, updated_at = row
                custom_sensors[sensor_name] = {
                    'category': category or 'custom',
                    'unit': unit or '',
                    'min': float(min_range),
                    'max': float(max_range),
                    'low_threshold': float(low_threshold) if low_threshold else None,
                    'high_threshold': float(high_threshold) if high_threshold else None,
                    'updated_at': updated_at.isoformat() if updated_at else None
                }
            
            cursor.close()
            conn.close()
            
            if custom_sensors:
                self.logger.info(f"Loaded {len(custom_sensors)} custom sensors from database")
                # #region agent log
                debug_log('producer.py:load_custom_sensors', 'Custom sensors loaded', {
                    'count': len(custom_sensors),
                    'sensor_names': list(custom_sensors.keys())
                }, 'H1')
                # #endregion
            else:
                self.logger.debug("No custom sensors found in database")
                # #region agent log
                debug_log('producer.py:load_custom_sensors', 'No custom sensors found', {}, 'H1')
                # #endregion
            
            self.custom_sensors = custom_sensors
            self.last_config_reload = datetime.utcnow()
            return True
            
        except Exception as e:
            # Safe fallback: continue with built-in sensors only
            self.logger.warning(f"Failed to load custom sensors from database: {e}. Continuing with built-in sensors only.")
            self.custom_sensors = {}
            return False

    def should_reload_config(self):
        """Check if custom sensor config should be reloaded."""
        if self.last_config_reload is None:
            return True
        elapsed = (datetime.utcnow() - self.last_config_reload).total_seconds()
        return elapsed >= self.config_reload_interval

    def get_enabled_custom_sensors_for_machine(self, machine_id):
        """Get custom sensors enabled for a specific machine from machine_sensor_config."""
        if not self.custom_sensors:
            # #region agent log
            debug_log('producer.py:get_enabled_custom_sensors_for_machine', 'No custom sensors available', {
                'machine_id': machine_id
            }, 'H2')
            # #endregion
            return {}
        
        try:
            conn = psycopg2.connect(**config.DB_CONFIG)
            cursor = conn.cursor()
            
            # Get enabled state for each custom sensor for this machine
            # Default to enabled if not in machine_sensor_config
            enabled_sensors = {}
            for sensor_name in self.custom_sensors.keys():
                cursor.execute("""
                    SELECT enabled FROM machine_sensor_config
                    WHERE machine_id = %s AND sensor_name = %s
                """, (machine_id, sensor_name))
                row = cursor.fetchone()
                # Default to enabled (True) if not in config
                is_enabled = row[0] if row else True
                if is_enabled:
                    enabled_sensors[sensor_name] = self.custom_sensors[sensor_name]
            
            cursor.close()
            conn.close()
            
            # #region agent log
            debug_log('producer.py:get_enabled_custom_sensors_for_machine', 'Enabled custom sensors for machine', {
                'machine_id': machine_id,
                'enabled_count': len(enabled_sensors),
                'enabled_sensors': list(enabled_sensors.keys()),
                'total_custom_sensors': len(self.custom_sensors)
            }, 'H2')
            # #endregion
            
            return enabled_sensors
            
        except Exception as e:
            # Fallback: return all custom sensors if query fails
            self.logger.warning(f"Failed to load machine-specific custom sensor config: {e}. Using all custom sensors.")
            # #region agent log
            debug_log('producer.py:get_enabled_custom_sensors_for_machine', 'Error loading machine config, using all', {
                'machine_id': machine_id,
                'error': str(e),
                'fallback_count': len(self.custom_sensors)
            }, 'H2')
            # #endregion
            return self.custom_sensors

    def generate_custom_sensors(self, machine_id='A'):
        """Generate values for custom sensors enabled for the specified machine."""
        # Get only enabled custom sensors for this machine
        enabled_sensors = self.get_enabled_custom_sensors_for_machine(machine_id)
        custom_sensor_values = {}
        
        for sensor_name, sensor_config in enabled_sensors.items():
            min_val = sensor_config['min']
            max_val = sensor_config['max']
            
            # Generate random value within range
            value = random.uniform(min_val, max_val)
            
            # Round to 2 decimal places for consistency
            if abs(value) < 1:
                value = round(value, 3)
            elif abs(value) < 100:
                value = round(value, 2)
            else:
                value = round(value, 1)
            
            custom_sensor_values[sensor_name] = value
        
        # #region agent log
        debug_log('producer.py:generate_custom_sensors', 'Generated custom sensor values', {
            'machine_id': machine_id,
            'count': len(custom_sensor_values),
            'values': custom_sensor_values
        }, 'H3')
        # #endregion
        
        return custom_sensor_values

    def generate_sensor_reading(self):
        """Generate a correlated sensor reading with all 50 parameters."""
        # #region agent log
        debug_log('producer.py:generate_sensor_reading', 'Function entry', {
            'has_custom_sensors': len(self.custom_sensors) > 0,
            'custom_sensors_count': len(self.custom_sensors)
        }, 'H1')
        # #endregion
        
        # Start with RPM as the base - machinery speed drives other values
        rpm = round(random.uniform(
            config.SENSOR_RANGES['rpm']['min'],
            config.SENSOR_RANGES['rpm']['max']
        ), 2)

        # Normalize RPM to 0-1 range for correlations
        rpm_normalized = (rpm - config.SENSOR_RANGES['rpm']['min']) / (
            config.SENSOR_RANGES['rpm']['max'] - config.SENSOR_RANGES['rpm']['min']
        )

        # === ENVIRONMENTAL SENSORS ===
        # Higher RPM = Higher temperature (machinery heats up with speed)
        temp_min = config.SENSOR_RANGES['temperature']['min']
        temp_max = config.SENSOR_RANGES['temperature']['max']
        temperature = round(temp_min + (rpm_normalized * (temp_max - temp_min)) + random.uniform(-5, 5), 2)
        temperature = max(temp_min, min(temp_max, temperature))

        temp_normalized = (temperature - temp_min) / (temp_max - temp_min)

        # Higher temperature = Lower humidity (heat dries air)
        hum_min = config.SENSOR_RANGES['humidity']['min']
        hum_max = config.SENSOR_RANGES['humidity']['max']
        humidity = round(hum_max - (temp_normalized * (hum_max - hum_min)) + random.uniform(-5, 5), 2)
        humidity = max(hum_min, min(hum_max, humidity))

        # Pressure correlates with temperature (thermal expansion)
        press_min = config.SENSOR_RANGES['pressure']['min']
        press_max = config.SENSOR_RANGES['pressure']['max']
        pressure = round(press_min + (temp_normalized * 0.6 * (press_max - press_min)) + random.uniform(0, 3), 2)
        pressure = max(press_min, min(press_max, pressure))

        # Ambient temperature slightly lower than machinery temperature
        ambient_temp = round(temperature - random.uniform(5, 15), 2)
        ambient_temp = max(config.SENSOR_RANGES['ambient_temp']['min'],
                          min(config.SENSOR_RANGES['ambient_temp']['max'], ambient_temp))

        # Dew point correlates with humidity and ambient temperature
        dew_point = round(ambient_temp - ((100 - humidity) / 5), 2)
        dew_point = max(config.SENSOR_RANGES['dew_point']['min'],
                       min(config.SENSOR_RANGES['dew_point']['max'], dew_point))

        # Higher RPM = More particles and worse air quality
        air_quality_index = int(100 + (rpm_normalized * 200) + random.uniform(-50, 50))
        air_quality_index = max(config.SENSOR_RANGES['air_quality_index']['min'],
                               min(config.SENSOR_RANGES['air_quality_index']['max'], air_quality_index))

        co2_level = int(600 + (rpm_normalized * 800) + random.uniform(-100, 100))
        co2_level = max(config.SENSOR_RANGES['co2_level']['min'],
                       min(config.SENSOR_RANGES['co2_level']['max'], co2_level))

        particle_count = int(10000 + (rpm_normalized * 60000) + random.uniform(-5000, 5000))
        particle_count = max(config.SENSOR_RANGES['particle_count']['min'],
                            min(config.SENSOR_RANGES['particle_count']['max'], particle_count))

        # Higher RPM = Higher noise
        noise_level = int(60 + (rpm_normalized * 30) + random.uniform(-5, 5))
        noise_level = max(config.SENSOR_RANGES['noise_level']['min'],
                         min(config.SENSOR_RANGES['noise_level']['max'], noise_level))

        light_intensity = int(random.uniform(config.SENSOR_RANGES['light_intensity']['min'],
                                            config.SENSOR_RANGES['light_intensity']['max']))

        # === MECHANICAL SENSORS ===
        # Higher RPM = Higher vibration
        vib_min = config.SENSOR_RANGES['vibration']['min']
        vib_max = config.SENSOR_RANGES['vibration']['max']
        vibration = round(vib_min + (rpm_normalized * (vib_max - vib_min)) + random.uniform(-1, 1), 2)
        vibration = max(vib_min, min(vib_max, vibration))

        # Torque correlates with RPM (power output)
        torque = int(100 + (rpm_normalized * 300) + random.uniform(-30, 30))
        torque = max(config.SENSOR_RANGES['torque']['min'],
                    min(config.SENSOR_RANGES['torque']['max'], torque))

        # Shaft alignment varies slightly with vibration
        shaft_alignment = round(vibration * 0.05 * random.choice([-1, 1]) + random.uniform(-0.1, 0.1), 3)
        shaft_alignment = max(config.SENSOR_RANGES['shaft_alignment']['min'],
                             min(config.SENSOR_RANGES['shaft_alignment']['max'], shaft_alignment))

        # Bearing temperature correlates with RPM
        bearing_temp = int(80 + (rpm_normalized * 80) + random.uniform(-10, 10))
        bearing_temp = max(config.SENSOR_RANGES['bearing_temp']['min'],
                          min(config.SENSOR_RANGES['bearing_temp']['max'], bearing_temp))

        # Motor current correlates with torque and RPM
        motor_current = int(20 + (rpm_normalized * 60) + random.uniform(-5, 5))
        motor_current = max(config.SENSOR_RANGES['motor_current']['min'],
                           min(config.SENSOR_RANGES['motor_current']['max'], motor_current))

        belt_tension = int(40 + (rpm_normalized * 40) + random.uniform(-5, 5))
        belt_tension = max(config.SENSOR_RANGES['belt_tension']['min'],
                          min(config.SENSOR_RANGES['belt_tension']['max'], belt_tension))

        # Higher RPM = More gear wear
        gear_wear = int(20 + (rpm_normalized * 50) + random.uniform(-10, 10))
        gear_wear = max(config.SENSOR_RANGES['gear_wear']['min'],
                       min(config.SENSOR_RANGES['gear_wear']['max'], gear_wear))

        coupling_temp = int(70 + (rpm_normalized * 60) + random.uniform(-5, 5))
        coupling_temp = max(config.SENSOR_RANGES['coupling_temp']['min'],
                           min(config.SENSOR_RANGES['coupling_temp']['max'], coupling_temp))

        lubrication_pressure = int(25 + (rpm_normalized * 25) + random.uniform(-3, 3))
        lubrication_pressure = max(config.SENSOR_RANGES['lubrication_pressure']['min'],
                                  min(config.SENSOR_RANGES['lubrication_pressure']['max'], lubrication_pressure))

        # === THERMAL SENSORS ===
        # Coolant temperature correlates with machinery temperature
        coolant_temp = int(150 + (temp_normalized * 60) + random.uniform(-10, 10))
        coolant_temp = max(config.SENSOR_RANGES['coolant_temp']['min'],
                          min(config.SENSOR_RANGES['coolant_temp']['max'], coolant_temp))

        # Exhaust temperature correlates with RPM and machinery temp
        exhaust_temp = int(400 + (rpm_normalized * 400) + random.uniform(-50, 50))
        exhaust_temp = max(config.SENSOR_RANGES['exhaust_temp']['min'],
                          min(config.SENSOR_RANGES['exhaust_temp']['max'], exhaust_temp))

        oil_temp = int(160 + (rpm_normalized * 70) + random.uniform(-10, 10))
        oil_temp = max(config.SENSOR_RANGES['oil_temp']['min'],
                      min(config.SENSOR_RANGES['oil_temp']['max'], oil_temp))

        radiator_temp = int(160 + (temp_normalized * 60) + random.uniform(-10, 10))
        radiator_temp = max(config.SENSOR_RANGES['radiator_temp']['min'],
                           min(config.SENSOR_RANGES['radiator_temp']['max'], radiator_temp))

        # Higher RPM = Better thermal efficiency (optimal operating range)
        thermal_efficiency = int(70 + (rpm_normalized * 20) + random.uniform(-5, 5))
        thermal_efficiency = max(config.SENSOR_RANGES['thermal_efficiency']['min'],
                                min(config.SENSOR_RANGES['thermal_efficiency']['max'], thermal_efficiency))

        heat_dissipation = int(1000 + (rpm_normalized * 3000) + random.uniform(-200, 200))
        heat_dissipation = max(config.SENSOR_RANGES['heat_dissipation']['min'],
                              min(config.SENSOR_RANGES['heat_dissipation']['max'], heat_dissipation))

        inlet_temp = int(ambient_temp + random.uniform(0, 20))
        inlet_temp = max(config.SENSOR_RANGES['inlet_temp']['min'],
                        min(config.SENSOR_RANGES['inlet_temp']['max'], inlet_temp))

        outlet_temp = int(inlet_temp + 40 + (rpm_normalized * 50) + random.uniform(-10, 10))
        outlet_temp = max(config.SENSOR_RANGES['outlet_temp']['min'],
                         min(config.SENSOR_RANGES['outlet_temp']['max'], outlet_temp))

        core_temp = int(temperature + 50 + (rpm_normalized * 50) + random.uniform(-10, 10))
        core_temp = max(config.SENSOR_RANGES['core_temp']['min'],
                       min(config.SENSOR_RANGES['core_temp']['max'], core_temp))

        surface_temp = int(temperature + random.uniform(-10, 30))
        surface_temp = max(config.SENSOR_RANGES['surface_temp']['min'],
                          min(config.SENSOR_RANGES['surface_temp']['max'], surface_temp))

        # === ELECTRICAL SENSORS ===
        # Voltage stable with slight variation
        voltage = int(120 + random.uniform(-5, 5))
        voltage = max(config.SENSOR_RANGES['voltage']['min'],
                     min(config.SENSOR_RANGES['voltage']['max'], voltage))

        # Current correlates with motor load (RPM and torque)
        current = int(10 + (rpm_normalized * 30) + random.uniform(-3, 3))
        current = max(config.SENSOR_RANGES['current']['min'],
                     min(config.SENSOR_RANGES['current']['max'], current))

        # Power factor degrades slightly at higher loads
        power_factor = round(0.95 - (rpm_normalized * 0.15) + random.uniform(-0.05, 0.05), 3)
        power_factor = max(config.SENSOR_RANGES['power_factor']['min'],
                          min(config.SENSOR_RANGES['power_factor']['max'], power_factor))

        frequency = round(60.0 + random.uniform(-0.5, 0.5), 2)
        frequency = max(config.SENSOR_RANGES['frequency']['min'],
                       min(config.SENSOR_RANGES['frequency']['max'], frequency))

        resistance = round(10 + random.uniform(-5, 30), 2)
        resistance = max(config.SENSOR_RANGES['resistance']['min'],
                        min(config.SENSOR_RANGES['resistance']['max'], resistance))

        capacitance = int(100 + random.uniform(-50, 400))
        capacitance = max(config.SENSOR_RANGES['capacitance']['min'],
                         min(config.SENSOR_RANGES['capacitance']['max'], capacitance))

        inductance = round(2.0 + random.uniform(-1, 5), 2)
        inductance = max(config.SENSOR_RANGES['inductance']['min'],
                        min(config.SENSOR_RANGES['inductance']['max'], inductance))

        phase_angle = int(random.uniform(config.SENSOR_RANGES['phase_angle']['min'],
                                        config.SENSOR_RANGES['phase_angle']['max']))

        # Higher current = More harmonic distortion
        harmonic_distortion = int(2 + (current / 50 * 10) + random.uniform(-2, 2))
        harmonic_distortion = max(config.SENSOR_RANGES['harmonic_distortion']['min'],
                                 min(config.SENSOR_RANGES['harmonic_distortion']['max'], harmonic_distortion))

        ground_fault = int(random.uniform(config.SENSOR_RANGES['ground_fault']['min'],
                                         config.SENSOR_RANGES['ground_fault']['max']))

        # === FLUID DYNAMICS SENSORS ===
        # Flow rate correlates with pump speed (RPM)
        flow_rate = int(100 + (rpm_normalized * 350) + random.uniform(-30, 30))
        flow_rate = max(config.SENSOR_RANGES['flow_rate']['min'],
                       min(config.SENSOR_RANGES['flow_rate']['max'], flow_rate))

        # Fluid pressure correlates with flow rate
        flow_normalized = flow_rate / 500
        fluid_pressure = int(20 + (flow_normalized * 60) + random.uniform(-5, 5))
        fluid_pressure = max(config.SENSOR_RANGES['fluid_pressure']['min'],
                            min(config.SENSOR_RANGES['fluid_pressure']['max'], fluid_pressure))

        # Viscosity varies with temperature (hotter = less viscous)
        viscosity = int(50 - (temp_normalized * 30) + random.uniform(-5, 5))
        viscosity = max(config.SENSOR_RANGES['viscosity']['min'],
                       min(config.SENSOR_RANGES['viscosity']['max'], viscosity))

        density = round(1.0 + random.uniform(-0.3, 0.3), 2)
        density = max(config.SENSOR_RANGES['density']['min'],
                     min(config.SENSOR_RANGES['density']['max'], density))

        # Reynolds number correlates with flow rate
        reynolds_number = int(4000 + (flow_normalized * 5000) + random.uniform(-500, 500))
        reynolds_number = max(config.SENSOR_RANGES['reynolds_number']['min'],
                             min(config.SENSOR_RANGES['reynolds_number']['max'], reynolds_number))

        pipe_pressure_drop = int(5 + (flow_normalized * 35) + random.uniform(-3, 3))
        pipe_pressure_drop = max(config.SENSOR_RANGES['pipe_pressure_drop']['min'],
                                min(config.SENSOR_RANGES['pipe_pressure_drop']['max'], pipe_pressure_drop))

        # Pump efficiency optimal at mid-range RPM
        pump_efficiency = int(75 + ((0.5 - abs(rpm_normalized - 0.5)) * 30) + random.uniform(-5, 5))
        pump_efficiency = max(config.SENSOR_RANGES['pump_efficiency']['min'],
                             min(config.SENSOR_RANGES['pump_efficiency']['max'], pump_efficiency))

        cavitation_index = int(2 + random.uniform(-1, 5))
        cavitation_index = max(config.SENSOR_RANGES['cavitation_index']['min'],
                              min(config.SENSOR_RANGES['cavitation_index']['max'], cavitation_index))

        # Higher flow rate = More turbulence
        turbulence = int(20 + (flow_normalized * 60) + random.uniform(-10, 10))
        turbulence = max(config.SENSOR_RANGES['turbulence']['min'],
                        min(config.SENSOR_RANGES['turbulence']['max'], turbulence))

        valve_position = int(30 + (flow_normalized * 50) + random.uniform(-10, 10))
        valve_position = max(config.SENSOR_RANGES['valve_position']['min'],
                            min(config.SENSOR_RANGES['valve_position']['max'], valve_position))

        # Build complete reading with all 50 parameters
        reading = {
            'timestamp': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S'),
            # Environmental
            'temperature': temperature,
            'pressure': pressure,
            'humidity': humidity,
            'ambient_temp': ambient_temp,
            'dew_point': dew_point,
            'air_quality_index': air_quality_index,
            'co2_level': co2_level,
            'particle_count': particle_count,
            'noise_level': noise_level,
            'light_intensity': light_intensity,
            # Mechanical
            'vibration': vibration,
            'rpm': rpm,
            'torque': torque,
            'shaft_alignment': shaft_alignment,
            'bearing_temp': bearing_temp,
            'motor_current': motor_current,
            'belt_tension': belt_tension,
            'gear_wear': gear_wear,
            'coupling_temp': coupling_temp,
            'lubrication_pressure': lubrication_pressure,
            # Thermal
            'coolant_temp': coolant_temp,
            'exhaust_temp': exhaust_temp,
            'oil_temp': oil_temp,
            'radiator_temp': radiator_temp,
            'thermal_efficiency': thermal_efficiency,
            'heat_dissipation': heat_dissipation,
            'inlet_temp': inlet_temp,
            'outlet_temp': outlet_temp,
            'core_temp': core_temp,
            'surface_temp': surface_temp,
            # Electrical
            'voltage': voltage,
            'current': current,
            'power_factor': power_factor,
            'frequency': frequency,
            'resistance': resistance,
            'capacitance': capacitance,
            'inductance': inductance,
            'phase_angle': phase_angle,
            'harmonic_distortion': harmonic_distortion,
            'ground_fault': ground_fault,
            # Fluid Dynamics
            'flow_rate': flow_rate,
            'fluid_pressure': fluid_pressure,
            'viscosity': viscosity,
            'density': density,
            'reynolds_number': reynolds_number,
            'pipe_pressure_drop': pipe_pressure_drop,
            'pump_efficiency': pump_efficiency,
            'cavitation_index': cavitation_index,
            'turbulence': turbulence,
            'valve_position': valve_position
        }
        
        # Add custom sensors if any are configured
        # Note: For now, we generate for machine 'A' by default
        # In a multi-machine setup, this would be passed as a parameter
        # The consumer/dashboard will filter based on machine_sensor_config
        if self.custom_sensors:
            # Generate all custom sensors (consumer will filter per-machine)
            # This maintains backward compatibility
            custom_values = self.generate_custom_sensors('A')
            if custom_values:
                reading['custom_sensors'] = custom_values
                # #region agent log
                debug_log('producer.py:generate_sensor_reading', 'Added custom_sensors to reading', {
                    'custom_sensors_count': len(custom_values),
                    'custom_sensors': custom_values
                }, 'H3')
                # #endregion
            else:
                # #region agent log
                debug_log('producer.py:generate_sensor_reading', 'No custom sensor values generated', {
                    'has_custom_sensors_config': len(self.custom_sensors) > 0
                }, 'H3')
                # #endregion
        else:
            # #region agent log
            debug_log('producer.py:generate_sensor_reading', 'No custom sensors configured', {}, 'H1')
            # #endregion
        
        return reading

    def send_message(self, data):
        """Send message to Kafka topic."""
        try:
            # #region agent log
            custom_sensors_in_payload = data.get('custom_sensors', {})
            debug_log('producer.py:send_message', 'Sending message to Kafka', {
                'has_custom_sensors': 'custom_sensors' in data,
                'custom_sensors_count': len(custom_sensors_in_payload) if custom_sensors_in_payload else 0,
                'custom_sensors': custom_sensors_in_payload
            }, 'H4')
            # #endregion
            
            # Serialize to JSON
            message = json.dumps(data)

            # Send to Kafka
            future = self.producer.send(config.KAFKA_TOPIC, value=message)

            # Wait for acknowledgment
            record_metadata = future.get(timeout=10)

            self.message_count += 1

            # #region agent log
            debug_log('producer.py:send_message', 'Message sent successfully to Kafka', {
                'message_count': self.message_count,
                'partition': record_metadata.partition,
                'offset': record_metadata.offset
            }, 'H4')
            # #endregion

            # Log message sent with key parameters
            self.logger.info(f"Message {self.message_count}/{self.total_messages} sent: "
                           f"timestamp={data['timestamp']}, "
                           f"rpm={data['rpm']}, "
                           f"temp={data['temperature']}°F, "
                           f"vibration={data['vibration']}mm/s")

            # Log progress every N messages
            if self.message_count % config.LOG_PROGRESS_INTERVAL == 0:
                progress = (self.message_count / self.total_messages) * 100
                self.logger.info(f"Progress: {self.message_count}/{self.total_messages} "
                               f"({progress:.1f}%) messages sent")

            return True

        except Exception as e:
            # #region agent log
            debug_log('producer.py:send_message', 'ERROR sending message to Kafka', {
                'error_type': type(e).__name__,
                'error_message': str(e)
            }, 'H4')
            # #endregion
            self.logger.error(f"Failed to send message: {e}")
            return False

    def check_injection_settings(self):
        """Check dashboard API for injection settings."""
        try:
            response = requests.get(f'{DASHBOARD_API_URL}/api/injection-settings', timeout=2)
            if response.status_code == 200:
                data = response.json()
                self.custom_thresholds = data.get('thresholds', {})
                
                # Check for immediate injection trigger
                if data.get('inject_now'):
                    # Clear the inject_now flag via API
                    requests.post(f'{DASHBOARD_API_URL}/api/injection-settings', 
                                  json={'inject_now_ack': True}, timeout=2)
                    return True
                
                # Check scheduled injection
                if data.get('enabled') and data.get('next_injection_time'):
                    next_time = datetime.fromisoformat(data['next_injection_time'].replace('Z', '+00:00'))
                    if datetime.utcnow() >= next_time.replace(tzinfo=None):
                        # Time for scheduled injection - update next time
                        requests.post(f'{DASHBOARD_API_URL}/api/injection-settings',
                                      json={'enabled': True, 'interval_minutes': data.get('interval_minutes', 30)},
                                      timeout=2)
                        return True
                
                return False
        except Exception as e:
            # Silently fail - dashboard might not be running
            pass
        return False

    def generate_anomalous_reading(self):
        """Generate a sensor reading with intentional anomalies."""
        # Start with a normal reading
        reading = self.generate_sensor_reading()
        
        # Pick random sensors to make anomalous (using config values)
        all_sensors = list(config.SENSOR_RANGES.keys())
        min_sensors = getattr(config, 'INJECTION_MIN_SENSORS', 3)
        max_sensors = getattr(config, 'INJECTION_MAX_SENSORS', 7)
        num_anomalies = random.randint(min_sensors, max_sensors)
        anomaly_sensors = random.sample(all_sensors, num_anomalies)
        
        self.logger.warning(f"🚨 INJECTING ANOMALY - Affecting sensors: {', '.join(anomaly_sensors)}")
        
        for sensor in anomaly_sensors:
            sensor_config = config.SENSOR_RANGES[sensor]
            default_min = sensor_config['min']
            default_max = sensor_config['max']
            
            # Use custom threshold if set, otherwise use default
            threshold = self.custom_thresholds.get(sensor, {'min': default_min, 'max': default_max})
            threshold_min = threshold.get('min', default_min)
            threshold_max = threshold.get('max', default_max)
            
            # Get deviation range from config
            dev_min = getattr(config, 'INJECTION_DEVIATION_MIN', 0.1)
            dev_max = getattr(config, 'INJECTION_DEVIATION_MAX', 0.5)
            
            # Decide whether to go above max or below min
            if random.random() > 0.5:
                # Go above threshold max
                range_size = default_max - default_min
                anomaly_value = threshold_max + (range_size * random.uniform(dev_min, dev_max))
                # Clamp to sensor's physical max
                anomaly_value = min(anomaly_value, default_max * 1.5)
            else:
                # Go below threshold min
                range_size = default_max - default_min
                anomaly_value = threshold_min - (range_size * random.uniform(dev_min, dev_max))
                # Clamp to sensor's physical min
                anomaly_value = max(anomaly_value, default_min * 0.5)
            
            # Apply the anomalous value
            if isinstance(reading[sensor], int):
                reading[sensor] = int(anomaly_value)
            else:
                reading[sensor] = round(anomaly_value, 2)
        
        return reading

    def run(self):
        """Main producer loop."""
        try:
            # #region agent log
            debug_log('producer.py:run', 'Producer run() started', {
                'DURATION_HOURS': config.DURATION_HOURS,
                'INTERVAL_SECONDS': config.INTERVAL_SECONDS
            }, 'H1')
            # #endregion
            
            # Connect to Kafka
            self.producer = self.connect_to_kafka()
            if not self.producer:
                self.logger.error("Could not establish Kafka connection. Exiting.")
                # #region agent log
                debug_log('producer.py:run', 'Kafka connection FAILED, exiting', {}, 'H4')
                # #endregion
                return

            # #region agent log
            debug_log('producer.py:run', 'Kafka connected successfully', {}, 'H4')
            # #endregion

            # Load custom sensors at startup
            self.load_custom_sensors()

            # Calculate end time
            end_time = datetime.utcnow() + timedelta(hours=config.DURATION_HOURS)
            current_time = datetime.utcnow()
            # #region agent log
            debug_log('producer.py:run', 'Calculated loop end time', {
                'current_time': current_time.isoformat(),
                'end_time': end_time.isoformat(),
                'duration_seconds': (end_time - current_time).total_seconds()
            }, 'H1')
            # #endregion
            
            self.logger.info(f"Starting data generation. Will run until {end_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")

            # Main loop
            loop_iteration = 0
            while datetime.utcnow() < end_time and not self.should_shutdown:
                loop_iteration += 1
                # #region agent log
                if loop_iteration == 1:
                    debug_log('producer.py:run', 'Entered main loop (first iteration)', {
                        'loop_iteration': loop_iteration,
                        'should_shutdown': self.should_shutdown
                    }, 'H2')
                if loop_iteration % 10 == 0:  # Log every 10 iterations
                    debug_log('producer.py:run', 'Loop still running', {
                        'loop_iteration': loop_iteration,
                        'message_count': self.message_count,
                        'should_shutdown': self.should_shutdown,
                        'time_remaining': (end_time - datetime.utcnow()).total_seconds()
                    }, 'H2')
                # #endregion
                # Reload custom sensor config if needed
                if self.should_reload_config():
                    # #region agent log
                    debug_log('producer.py:run', 'Reloading custom sensor config', {
                        'last_reload': str(self.last_config_reload),
                        'elapsed_seconds': (datetime.utcnow() - self.last_config_reload).total_seconds() if self.last_config_reload else None
                    }, 'H1')
                    # #endregion
                    self.load_custom_sensors()
                # Check if we should inject an anomaly
                should_inject = self.check_injection_settings()
                
                # Generate sensor reading (normal or anomalous)
                if should_inject:
                    reading = self.generate_anomalous_reading()
                else:
                    reading = self.generate_sensor_reading()
                
                # #region agent log
                debug_log('producer.py:run', 'Generated reading, about to send', {
                    'has_custom_sensors': 'custom_sensors' in reading,
                    'reading_keys': list(reading.keys())[:5]  # First 5 keys
                }, 'H4')
                # #endregion

                # Send to Kafka
                send_success = self.send_message(reading)
                
                # #region agent log
                if not send_success:
                    debug_log('producer.py:run', 'Message send FAILED', {
                        'loop_iteration': loop_iteration,
                        'message_count': self.message_count
                    }, 'H4')
                # #endregion

                # Sleep until next interval
                time.sleep(config.INTERVAL_SECONDS)

            # #region agent log
            debug_log('producer.py:run', 'Loop exited - CHECKING WHY', {
                'loop_iteration_count': loop_iteration,
                'should_shutdown': self.should_shutdown,
                'current_time': datetime.utcnow().isoformat(),
                'end_time': end_time.isoformat(),
                'time_expired': datetime.utcnow() >= end_time,
                'time_check': datetime.utcnow() < end_time,
                'message_count': self.message_count,
                'reason': 'time_expired' if datetime.utcnow() >= end_time else ('shutdown' if self.should_shutdown else 'unknown')
            }, 'H2')
            # #endregion

            # Log completion
            if not self.should_shutdown:
                self.logger.info(f"Data generation complete! Total messages sent: {self.message_count}")
            else:
                self.logger.info(f"Shutdown requested. Messages sent: {self.message_count}/{self.total_messages}")

        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt received. Shutting down...")
            # #region agent log
            debug_log('producer.py:run', 'KeyboardInterrupt caught', {
                'message_count': self.message_count
            }, 'H2')
            # #endregion
        except Exception as e:
            self.logger.error(f"Unexpected error in producer: {e}", exc_info=True)
            # #region agent log
            import traceback
            debug_log('producer.py:run', 'EXCEPTION in producer loop', {
                'error': str(e),
                'error_type': type(e).__name__,
                'message_count': self.message_count,
                'traceback': traceback.format_exc()[:500]
            }, 'H2')
            # #endregion
        finally:
            # #region agent log
            debug_log('producer.py:run', 'Entering shutdown()', {
                'message_count': self.message_count
            }, 'H2')
            # #endregion
            self.shutdown()

    def shutdown(self):
        """Cleanup and shutdown."""
        if self.producer:
            self.logger.info("Flushing producer buffer...")
            self.producer.flush(timeout=30)
            self.logger.info("Closing Kafka producer...")
            self.producer.close()
        self.logger.info("Producer shutdown complete.")


def main():
    """Main entry point."""
    producer = SensorDataProducer()
    producer.run()


if __name__ == '__main__':
    main()
