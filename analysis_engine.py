"""
Context and Correlation Analysis Engine.
Analyzes sensor readings around anomalies to identify patterns and correlations.
"""

import logging
import numpy as np
import pandas as pd
from scipy import stats
import psycopg2
import json

import config


class ContextAnalyzer:
    """Analyzes context around detected anomalies."""

    # Sensor columns for analysis
    SENSOR_COLUMNS = [
        # Environmental
        'temperature', 'pressure', 'humidity', 'ambient_temp', 'dew_point',
        'air_quality_index', 'co2_level', 'particle_count', 'noise_level', 'light_intensity',
        # Mechanical
        'vibration', 'rpm', 'torque', 'shaft_alignment', 'bearing_temp',
        'motor_current', 'belt_tension', 'gear_wear', 'coupling_temp', 'lubrication_pressure',
        # Thermal
        'coolant_temp', 'exhaust_temp', 'oil_temp', 'radiator_temp', 'thermal_efficiency',
        'heat_dissipation', 'inlet_temp', 'outlet_temp', 'core_temp', 'surface_temp',
        # Electrical
        'voltage', 'current', 'power_factor', 'frequency', 'resistance',
        'capacitance', 'inductance', 'phase_angle', 'harmonic_distortion', 'ground_fault',
        # Fluid Dynamics
        'flow_rate', 'fluid_pressure', 'viscosity', 'density', 'reynolds_number',
        'pipe_pressure_drop', 'pump_efficiency', 'cavitation_index', 'turbulence', 'valve_position'
    ]

    # Sensor category mapping
    SENSOR_CATEGORIES = {
        'environmental': ['temperature', 'pressure', 'humidity', 'ambient_temp', 'dew_point',
                         'air_quality_index', 'co2_level', 'particle_count', 'noise_level', 'light_intensity'],
        'mechanical': ['vibration', 'rpm', 'torque', 'shaft_alignment', 'bearing_temp',
                      'motor_current', 'belt_tension', 'gear_wear', 'coupling_temp', 'lubrication_pressure'],
        'thermal': ['coolant_temp', 'exhaust_temp', 'oil_temp', 'radiator_temp', 'thermal_efficiency',
                   'heat_dissipation', 'inlet_temp', 'outlet_temp', 'core_temp', 'surface_temp'],
        'electrical': ['voltage', 'current', 'power_factor', 'frequency', 'resistance',
                      'capacitance', 'inductance', 'phase_angle', 'harmonic_distortion', 'ground_fault'],
        'fluid': ['flow_rate', 'fluid_pressure', 'viscosity', 'density', 'reynolds_number',
                 'pipe_pressure_drop', 'pump_efficiency', 'cavitation_index', 'turbulence', 'valve_position']
    }

    def __init__(self, window_size=None):
        """Initialize the context analyzer.
        
        Args:
            window_size: Number of readings before/after to analyze (default from config)
        """
        self.window_size = window_size or config.CONTEXT_WINDOW_SIZE
        self.logger = logging.getLogger(__name__)

    def get_context_window(self, reading_id):
        """Fetch readings before and after an anomaly for context.
        
        Args:
            reading_id: ID of the anomalous reading
            
        Returns:
            dict with 'before', 'anomaly', and 'after' DataFrames
        """
        conn = None
        try:
            conn = psycopg2.connect(**config.DB_CONFIG)
            cursor = conn.cursor()
            
            columns = ', '.join(['id', 'timestamp', 'created_at'] + self.SENSOR_COLUMNS)
            
            # Get the anomaly reading
            cursor.execute(f"""
                SELECT {columns}
                FROM sensor_readings
                WHERE id = %s
            """, (reading_id,))
            anomaly_row = cursor.fetchone()
            
            if not anomaly_row:
                self.logger.warning(f"Reading {reading_id} not found")
                return None
            
            column_names = ['id', 'timestamp', 'created_at'] + self.SENSOR_COLUMNS
            anomaly_df = pd.DataFrame([anomaly_row], columns=column_names)
            
            # Get readings before the anomaly
            cursor.execute(f"""
                SELECT {columns}
                FROM sensor_readings
                WHERE id < %s
                ORDER BY id DESC
                LIMIT %s
            """, (reading_id, self.window_size))
            before_rows = cursor.fetchall()
            before_df = pd.DataFrame(before_rows[::-1], columns=column_names) if before_rows else pd.DataFrame(columns=column_names)
            
            # Get readings after the anomaly
            cursor.execute(f"""
                SELECT {columns}
                FROM sensor_readings
                WHERE id > %s
                ORDER BY id ASC
                LIMIT %s
            """, (reading_id, self.window_size))
            after_rows = cursor.fetchall()
            after_df = pd.DataFrame(after_rows, columns=column_names) if after_rows else pd.DataFrame(columns=column_names)
            
            cursor.close()
            
            return {
                'before': before_df,
                'anomaly': anomaly_df,
                'after': after_df
            }
            
        except Exception as e:
            self.logger.error(f"Failed to fetch context window: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def compute_correlations(self, context_data, significance_threshold=0.05):
        """Compute correlations between sensor parameters.
        
        Args:
            context_data: Dict from get_context_window()
            significance_threshold: P-value threshold for significance
            
        Returns:
            dict with correlation matrix and significant correlations
        """
        if not context_data:
            return None
            
        # Combine all readings for correlation analysis
        all_readings = pd.concat([
            context_data['before'],
            context_data['anomaly'],
            context_data['after']
        ], ignore_index=True)
        
        if len(all_readings) < 3:
            self.logger.warning("Not enough readings for correlation analysis")
            return None
        
        # Extract sensor columns only
        sensor_data = all_readings[self.SENSOR_COLUMNS].copy()
        sensor_data = sensor_data.fillna(sensor_data.mean())
        
        try:
            # Compute correlation matrix
            corr_matrix = sensor_data.corr()
            
            # Find significant correlations
            significant_correlations = []
            n = len(sensor_data)
            
            for i, col1 in enumerate(self.SENSOR_COLUMNS):
                for j, col2 in enumerate(self.SENSOR_COLUMNS):
                    if i >= j:  # Skip diagonal and duplicates
                        continue
                    
                    corr = corr_matrix.loc[col1, col2]
                    if pd.isna(corr):
                        continue
                    
                    # Calculate p-value for correlation
                    if n > 2:
                        t_stat = corr * np.sqrt((n - 2) / (1 - corr**2 + 1e-10))
                        p_value = 2 * (1 - stats.t.cdf(abs(t_stat), n - 2))
                    else:
                        p_value = 1.0
                    
                    # Only include strong correlations (|r| > 0.5) that are significant
                    if abs(corr) > 0.5 and p_value < significance_threshold:
                        significant_correlations.append({
                            'sensor1': col1,
                            'sensor2': col2,
                            'correlation': round(corr, 4),
                            'p_value': round(p_value, 6),
                            'strength': 'strong' if abs(corr) > 0.7 else 'moderate'
                        })
            
            # Sort by absolute correlation strength
            significant_correlations.sort(key=lambda x: abs(x['correlation']), reverse=True)
            
            return {
                'matrix': corr_matrix.to_dict(),
                'significant_correlations': significant_correlations[:20],  # Top 20
                'sample_size': n
            }
            
        except Exception as e:
            self.logger.error(f"Failed to compute correlations: {e}")
            return None

    def identify_anomalous_patterns(self, context_data, detected_sensors=None):
        """Identify which parameters deviated most from normal.
        
        Args:
            context_data: Dict from get_context_window()
            detected_sensors: List of sensors that triggered the anomaly
            
        Returns:
            dict with pattern analysis results
        """
        if not context_data:
            return None
            
        anomaly_reading = context_data['anomaly']
        before_readings = context_data['before']
        
        if len(before_readings) == 0:
            self.logger.warning("No baseline readings available for pattern analysis")
            return None
        
        patterns = []
        
        for sensor in self.SENSOR_COLUMNS:
            try:
                anomaly_value = anomaly_reading[sensor].iloc[0]
                baseline_values = before_readings[sensor].dropna()
                
                if len(baseline_values) == 0 or pd.isna(anomaly_value):
                    continue
                
                baseline_mean = baseline_values.mean()
                baseline_std = baseline_values.std()
                
                if baseline_std > 0:
                    z_score = (anomaly_value - baseline_mean) / baseline_std
                else:
                    z_score = 0
                
                # Calculate percent change from baseline
                if baseline_mean != 0:
                    percent_change = ((anomaly_value - baseline_mean) / abs(baseline_mean)) * 100
                else:
                    percent_change = 0
                
                # Determine trend direction
                if len(baseline_values) >= 3:
                    recent_trend = baseline_values.iloc[-3:].mean()
                    trend_direction = 'increasing' if anomaly_value > recent_trend else 'decreasing'
                else:
                    trend_direction = 'unknown'
                
                # Get sensor category
                category = None
                for cat, sensors in self.SENSOR_CATEGORIES.items():
                    if sensor in sensors:
                        category = cat
                        break
                
                # Get sensor unit from config
                unit = config.SENSOR_RANGES.get(sensor, {}).get('unit', '')
                
                patterns.append({
                    'sensor': sensor,
                    'category': category,
                    'anomaly_value': round(float(anomaly_value), 2),
                    'baseline_mean': round(float(baseline_mean), 2),
                    'baseline_std': round(float(baseline_std), 2),
                    'z_score': round(float(z_score), 2),
                    'percent_change': round(float(percent_change), 2),
                    'trend_direction': trend_direction,
                    'unit': unit,
                    'is_detected': sensor in (detected_sensors or [])
                })
                
            except Exception as e:
                self.logger.debug(f"Error analyzing {sensor}: {e}")
                continue
        
        # Sort by z-score magnitude (most deviated first)
        patterns.sort(key=lambda x: abs(x['z_score']), reverse=True)
        
        # Group by category
        by_category = {}
        for pattern in patterns:
            cat = pattern['category'] or 'unknown'
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(pattern)
        
        return {
            'all_patterns': patterns,
            'by_category': by_category,
            'top_deviations': patterns[:10],  # Top 10 most deviated
            'detected_sensors': detected_sensors or []
        }

    def generate_analysis_summary(self, reading_id, detected_sensors=None):
        """Generate a complete analysis summary for an anomaly.
        
        Args:
            reading_id: ID of the anomalous reading
            detected_sensors: List of sensors that triggered the anomaly
            
        Returns:
            dict with complete analysis data ready for ChatGPT
        """
        context = self.get_context_window(reading_id)
        if not context:
            return None
        
        correlations = self.compute_correlations(context)
        patterns = self.identify_anomalous_patterns(context, detected_sensors)
        
        # Convert DataFrames to serializable format
        context_serializable = {
            'before': context['before'].to_dict('records') if len(context['before']) > 0 else [],
            'anomaly': context['anomaly'].to_dict('records')[0] if len(context['anomaly']) > 0 else {},
            'after': context['after'].to_dict('records') if len(context['after']) > 0 else []
        }
        
        # Clean up timestamps for JSON serialization
        for key in ['before', 'after']:
            for record in context_serializable[key]:
                for field in ['timestamp', 'created_at']:
                    if field in record and record[field] is not None:
                        record[field] = str(record[field])
        
        if 'timestamp' in context_serializable['anomaly']:
            context_serializable['anomaly']['timestamp'] = str(context_serializable['anomaly'].get('timestamp', ''))
        if 'created_at' in context_serializable['anomaly']:
            context_serializable['anomaly']['created_at'] = str(context_serializable['anomaly'].get('created_at', ''))
        
        return {
            'reading_id': reading_id,
            'context': context_serializable,
            'correlations': {
                'significant': correlations['significant_correlations'] if correlations else [],
                'sample_size': correlations['sample_size'] if correlations else 0
            },
            'patterns': patterns,
            'detected_sensors': detected_sensors or []
        }


def get_anomaly_details(anomaly_id):
    """Fetch anomaly detection details from the database.
    
    Args:
        anomaly_id: ID from anomaly_detections table
        
    Returns:
        dict with anomaly details or None
    """
    conn = None
    try:
        conn = psycopg2.connect(**config.DB_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, reading_id, detection_method, anomaly_score, 
                   is_anomaly, detected_sensors, created_at
            FROM anomaly_detections
            WHERE id = %s
        """, (anomaly_id,))
        
        row = cursor.fetchone()
        cursor.close()
        
        if not row:
            return None
        
        return {
            'id': row[0],
            'reading_id': row[1],
            'detection_method': row[2],
            'anomaly_score': row[3],
            'is_anomaly': row[4],
            'detected_sensors': row[5] or [],
            'created_at': str(row[6])
        }
        
    except Exception as e:
        logging.error(f"Failed to fetch anomaly details: {e}")
        return None
    finally:
        if conn:
            conn.close()

