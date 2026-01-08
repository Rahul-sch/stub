"""
Predictive Health Engine - Remaining Useful Life (RUL) Prediction
Uses degradation patterns to estimate time until failure.
Simplified implementation using Linear Regression and Exponential Decay.
"""

import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class PTTFPredictor:
    """
    Predicted Time To Failure (PTTF) Predictor
    
    Uses degradation patterns from critical sensors (vibration, temperature)
    to estimate Remaining Useful Life (RUL) in hours.
    
    Simplified implementation for systems without 1000+ failure cycles.
    Uses Linear Regression and Exponential Decay trend analysis.
    """
    
    def __init__(self):
        """Initialize the predictor with default thresholds."""
        # Critical sensors for degradation analysis
        self.critical_sensors = ['vibration', 'temperature', 'bearing_temp', 'rpm']
        
        # Failure thresholds (based on config.py SENSOR_THRESHOLDS)
        self.failure_thresholds = {
            'vibration': 7.1,  # mm/s (ISO 10816 Unsatisfactory)
            'temperature': 85.0,  # °F (Industrial safe limit)
            'bearing_temp': 180.0,  # °F (Critical alarm)
            'rpm': 4500.0  # RPM (Excessive speed)
        }
        
        # Normal operating ranges (for trend calculation)
        self.normal_ranges = {
            'vibration': (0.0, 2.8),  # Good range
            'temperature': (65.0, 75.0),  # Comfort range
            'bearing_temp': (100.0, 150.0),  # Normal range
            'rpm': (1800.0, 3600.0)  # Typical range
        }
    
    def predict_rul(self, sensor_sequence: List[Dict], machine_id: str = 'A') -> Dict:
        """
        Predict Remaining Useful Life (RUL) based on sensor degradation trends.
        
        Args:
            sensor_sequence: List of sensor readings (most recent last)
            machine_id: Machine identifier
        
        Returns:
            {
                'rul_hours': float,  # Estimated hours until failure
                'confidence': float,  # Confidence score (0.0-1.0)
                'degradation_trend': str,  # 'stable', 'accelerating', 'decelerating'
                'critical_sensors': List[str],  # Sensors showing degradation
                'estimated_failure_time': str,  # ISO timestamp
                'machine_id': str
            }
        """
        if not sensor_sequence or len(sensor_sequence) < 10:
            # Not enough data for prediction
            return {
                'rul_hours': None,
                'confidence': 0.0,
                'degradation_trend': 'insufficient_data',
                'critical_sensors': [],
                'estimated_failure_time': None,
                'machine_id': machine_id,
                'message': 'Insufficient data for prediction (need at least 10 readings)'
            }
        
        # Extract time series for critical sensors
        sensor_data = {}
        timestamps = []
        
        for reading in sensor_sequence:
            if 'timestamp' in reading:
                try:
                    ts = datetime.fromisoformat(reading['timestamp'].replace('Z', '+00:00'))
                    timestamps.append(ts)
                except:
                    continue
            
            for sensor in self.critical_sensors:
                if sensor in reading:
                    if sensor not in sensor_data:
                        sensor_data[sensor] = []
                    sensor_data[sensor].append(reading[sensor])
        
        if not timestamps or len(timestamps) < 10:
            return {
                'rul_hours': None,
                'confidence': 0.0,
                'degradation_trend': 'insufficient_data',
                'critical_sensors': [],
                'estimated_failure_time': None,
                'machine_id': machine_id,
                'message': 'Insufficient timestamp data'
            }
        
        # Calculate degradation trends using Linear Regression
        rul_predictions = []
        critical_sensors = []
        degradation_scores = {}
        
        for sensor in self.critical_sensors:
            if sensor not in sensor_data or len(sensor_data[sensor]) < 10:
                continue
            
            values = np.array(sensor_data[sensor][-50:])  # Last 50 readings
            time_indices = np.arange(len(values))
            
            # Linear regression: value = slope * time + intercept
            slope, intercept = np.polyfit(time_indices, values, 1)
            
            # Check if trending toward failure threshold
            threshold = self.failure_thresholds.get(sensor)
            normal_min, normal_max = self.normal_ranges.get(sensor, (0, 100))
            
            if threshold:
                current_value = values[-1]
                distance_to_threshold = threshold - current_value
                
                # Calculate hours until threshold (assuming readings every 30 seconds)
                # Convert slope (per reading) to slope (per hour)
                readings_per_hour = 120  # 30-second intervals
                slope_per_hour = slope * readings_per_hour
                
                if abs(slope_per_hour) > 0.001:  # Significant trend
                    if slope_per_hour > 0 and current_value < threshold:
                        # Increasing toward threshold
                        hours_to_threshold = distance_to_threshold / slope_per_hour
                        if hours_to_threshold > 0 and hours_to_threshold < 10000:  # Reasonable range
                            rul_predictions.append(hours_to_threshold)
                            critical_sensors.append(sensor)
                            degradation_scores[sensor] = {
                                'current': current_value,
                                'threshold': threshold,
                                'slope_per_hour': slope_per_hour,
                                'hours_to_threshold': hours_to_threshold
                            }
        
        # Calculate aggregate RUL
        if rul_predictions:
            # Use minimum RUL (most critical sensor)
            rul_hours = min(rul_predictions)
            
            # Confidence based on data quality and trend consistency
            confidence = min(0.9, 0.3 + (len(rul_predictions) * 0.1) + (len(sensor_sequence) / 1000))
            
            # Determine degradation trend
            if len(rul_predictions) > 1:
                trend_variance = np.var(rul_predictions)
                if trend_variance < 100:
                    degradation_trend = 'stable'
                elif np.mean([s['slope_per_hour'] for s in degradation_scores.values()]) > 0.1:
                    degradation_trend = 'accelerating'
                else:
                    degradation_trend = 'decelerating'
            else:
                degradation_trend = 'accelerating' if rul_predictions[0] < 100 else 'stable'
            
            # Estimate failure time
            estimated_failure = datetime.utcnow() + timedelta(hours=rul_hours)
            
            return {
                'rul_hours': round(rul_hours, 2),
                'confidence': round(confidence, 2),
                'degradation_trend': degradation_trend,
                'critical_sensors': critical_sensors,
                'estimated_failure_time': estimated_failure.isoformat(),
                'machine_id': machine_id,
                'degradation_details': degradation_scores
            }
        else:
            # No critical degradation detected
            return {
                'rul_hours': None,
                'confidence': 0.8,
                'degradation_trend': 'stable',
                'critical_sensors': [],
                'estimated_failure_time': None,
                'machine_id': machine_id,
                'message': 'No degradation trends detected - system operating normally'
            }


# Global predictor instance
_predictor_instance = None

def get_predictor() -> PTTFPredictor:
    """Get or create the global predictor instance."""
    global _predictor_instance
    if _predictor_instance is None:
        _predictor_instance = PTTFPredictor()
    return _predictor_instance

