"""
LSTM Future Anomaly Predictor
Predicts future anomalies based on reconstruction error trends and sequence patterns.
"""

import logging
import numpy as np
import psycopg2
from datetime import datetime, timedelta
import config

try:
    from lstm_detector import get_lstm_detector, is_lstm_available
    LSTM_AVAILABLE = is_lstm_available()
except ImportError:
    LSTM_AVAILABLE = False

logger = logging.getLogger(__name__)


class LSTMPredictor:
    """Predicts future anomalies using LSTM sequence analysis."""
    
    def __init__(self):
        """Initialize the LSTM predictor."""
        self.lstm_detector = get_lstm_detector() if LSTM_AVAILABLE else None
        self.sequence_length = config.LSTM_SEQUENCE_LENGTH
        self.logger = logging.getLogger(__name__)
        
    def predict_future_anomaly(self, reading_id=None, lookahead=10):
        """Predict if an anomaly is likely in the next N readings.
        
        Args:
            reading_id: ID of the reading to predict from (None = latest)
            lookahead: Number of future readings to consider
            
        Returns:
            dict: {
                'risk_score': float (0-100),
                'predicted_window': str,
                'confidence': float (0-1),
                'contributing_sensors': list,
                'trend': str ('increasing', 'stable', 'decreasing'),
                'current_error': float,
                'threshold': float
            }
        """
        if not LSTM_AVAILABLE or not self.lstm_detector or not self.lstm_detector.is_trained:
            return {
                'risk_score': 0,
                'predicted_window': 'N/A',
                'confidence': 0,
                'contributing_sensors': [],
                'trend': 'unknown',
                'current_error': 0,
                'threshold': 0,
                'error': 'LSTM not available or not trained'
            }
        
        try:
            # Get recent sequence
            conn = psycopg2.connect(**config.DB_CONFIG)
            cursor = conn.cursor()
            
            if reading_id is None:
                cursor.execute('SELECT MAX(id) FROM sensor_readings')
                reading_id = cursor.fetchone()[0]
            
            # Fetch last sequence_length + 5 readings for trend analysis
            # Note: get_recent_sequence returns exactly sequence_length readings
            # We'll fetch multiple sequences for trend analysis
            sequence_data = self.lstm_detector.get_recent_sequence(reading_id)
            
            if sequence_data is None or len(sequence_data) < self.sequence_length:
                cursor.close()
                conn.close()
                return {
                    'risk_score': 0,
                    'predicted_window': 'Insufficient data',
                    'confidence': 0,
                    'contributing_sensors': [],
                    'trend': 'unknown',
                    'current_error': 0,
                    'threshold': self.lstm_detector.threshold,
                    'error': 'Not enough historical data'
                }
            
            # Calculate reconstruction errors for trend analysis
            # We'll analyze multiple overlapping sequences to see trend
            errors = []
            
            # Get multiple sequences by fetching readings at different points
            for offset in range(5, 0, -1):
                try:
                    seq_id = reading_id - offset
                    if seq_id > 0:
                        seq = self.lstm_detector.get_recent_sequence(seq_id)
                        if seq is not None and len(seq) >= self.sequence_length:
                            _, error, _ = self.lstm_detector.detect(seq)
                            errors.append(error)
                except:
                    pass
            
            # Add current sequence
            _, error, _ = self.lstm_detector.detect(sequence_data)
            errors.append(error)
            
            # Current error (most recent)
            current_error = errors[-1]
            threshold = self.lstm_detector.threshold
            
            # Analyze trend
            trend = self._analyze_trend(errors)
            
            # Calculate risk score
            risk_score = self._calculate_risk_score(
                current_error, 
                threshold, 
                trend, 
                errors
            )
            
            # Predict window based on trend and current error
            predicted_window = self._predict_window(
                current_error, 
                threshold, 
                trend, 
                lookahead
            )
            
            # Calculate confidence
            confidence = self._calculate_confidence(errors, trend)
            
            # Get detailed sensor trend analysis
            sensor_analyses = self.analyze_sensor_trends(reading_id)
            
            # Extract top problematic sensors
            contributing_sensors = []
            sensor_details = {}
            
            for analysis in sensor_analyses[:10]:  # Top 10 most problematic
                if analysis['severity'] in ['critical', 'high', 'medium']:
                    contributing_sensors.append(analysis['sensor'])
                    sensor_details[analysis['sensor']] = {
                        'reason': analysis['reason'],
                        'severity': analysis['severity'],
                        'trend': analysis['trend'],
                        'trend_rate': analysis['trend_rate'],
                        'predicted_failure_reading': analysis['predicted_failure_reading'],
                        'current_value': analysis['current_value'],
                        'error_percentile': analysis['error_percentile']
                    }
            
            cursor.close()
            conn.close()
            
            result = {
                'risk_score': float(risk_score),
                'predicted_window': predicted_window,
                'confidence': float(confidence),
                'contributing_sensors': contributing_sensors[:5],  # Top 5 for backward compatibility
                'trend': trend,
                'current_error': float(current_error),
                'threshold': float(threshold),
                'reading_id': reading_id,
                'sensor_analyses': sensor_analyses[:10],  # Top 10 detailed analyses
                'sensor_details': sensor_details  # Key sensors with reasons
            }
            
            self.logger.info(f"Prediction for reading {reading_id}: risk={risk_score:.1f}%, trend={trend}, {len(contributing_sensors)} problematic sensors")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error predicting future anomaly: {e}")
            return {
                'risk_score': 0,
                'predicted_window': 'Error',
                'confidence': 0,
                'contributing_sensors': [],
                'trend': 'unknown',
                'current_error': 0,
                'threshold': 0,
                'error': str(e)
            }
    
    def _analyze_trend(self, errors):
        """Analyze the trend in reconstruction errors.
        
        Args:
            errors: List of reconstruction errors
            
        Returns:
            str: 'increasing', 'stable', or 'decreasing'
        """
        if len(errors) < 3:
            return 'stable'
        
        # Calculate linear regression slope
        x = np.arange(len(errors))
        y = np.array(errors)
        
        # Fit line
        slope = np.polyfit(x, y, 1)[0]
        
        # Determine trend based on slope
        if slope > 0.01:  # Increasing
            return 'increasing'
        elif slope < -0.01:  # Decreasing
            return 'decreasing'
        else:
            return 'stable'
    
    def _calculate_risk_score(self, current_error, threshold, trend, errors):
        """Calculate risk score (0-100).
        
        Args:
            current_error: Current reconstruction error
            threshold: Anomaly threshold
            trend: Trend direction
            errors: List of recent errors
            
        Returns:
            float: Risk score (0-100)
        """
        # Base risk: how close to threshold
        proximity_ratio = current_error / threshold
        base_risk = min(proximity_ratio * 60, 90)  # Max 90 from proximity
        
        # Trend bonus
        trend_bonus = 0
        if trend == 'increasing':
            # Calculate rate of increase
            if len(errors) >= 3:
                recent_increase = (errors[-1] - errors[-3]) / errors[-3]
                trend_bonus = min(recent_increase * 50, 30)  # Max 30 from trend
        elif trend == 'decreasing':
            trend_bonus = -10  # Reduce risk if decreasing
        
        # Total risk
        risk_score = max(0, min(100, base_risk + trend_bonus))
        
        return risk_score
    
    def _predict_window(self, current_error, threshold, trend, lookahead):
        """Predict time window for potential anomaly.
        
        Args:
            current_error: Current reconstruction error
            threshold: Anomaly threshold
            trend: Trend direction
            lookahead: Number of readings to look ahead
            
        Returns:
            str: Predicted time window
        """
        if current_error >= threshold:
            return "Anomaly detected now"
        
        proximity_ratio = current_error / threshold
        
        if trend == 'increasing':
            if proximity_ratio > 0.9:
                return f"Very likely in next 1-3 readings"
            elif proximity_ratio > 0.7:
                return f"Likely in next 3-5 readings"
            elif proximity_ratio > 0.5:
                return f"Possible in next 5-10 readings"
            else:
                return f"Low risk in next {lookahead} readings"
        elif trend == 'stable':
            if proximity_ratio > 0.8:
                return f"Possible in next 5-10 readings"
            else:
                return f"Low risk in next {lookahead} readings"
        else:  # decreasing
            return f"Decreasing risk - unlikely in next {lookahead} readings"
    
    def _calculate_confidence(self, errors, trend):
        """Calculate prediction confidence (0-1).
        
        Args:
            errors: List of recent errors
            trend: Trend direction
            
        Returns:
            float: Confidence (0-1)
        """
        if len(errors) < 3:
            return 0.3  # Low confidence with little data
        
        # Calculate consistency (inverse of variance)
        variance = np.var(errors)
        consistency = 1 / (1 + variance)
        
        # Trend strength
        if trend == 'increasing' or trend == 'decreasing':
            trend_strength = 0.8
        else:
            trend_strength = 0.5
        
        # Combined confidence
        confidence = (consistency * 0.6 + trend_strength * 0.4)
        
        return min(1.0, max(0.1, confidence))
    
    def analyze_sensor_trends(self, reading_id=None):
        """Analyze which sensors are trending toward problems and why.
        
        Args:
            reading_id: ID of the reading to analyze from (None = latest)
            
        Returns:
            list: List of dicts with sensor analysis:
                {
                    'sensor': str,
                    'reconstruction_error': float,
                    'trend': str ('increasing', 'decreasing', 'stable'),
                    'trend_rate': float (change per reading),
                    'current_value': float,
                    'predicted_failure_reading': int (when it might fail),
                    'reason': str (why it's problematic),
                    'severity': str ('critical', 'high', 'medium', 'low')
                }
        """
        if not LSTM_AVAILABLE or not self.lstm_detector or not self.lstm_detector.is_trained:
            return []
        
        try:
            conn = psycopg2.connect(**config.DB_CONFIG)
            cursor = conn.cursor()
            
            if reading_id is None:
                cursor.execute('SELECT MAX(id) FROM sensor_readings')
                reading_id = cursor.fetchone()[0]
            
            # Get sequence for analysis
            sequence_data = self.lstm_detector.get_recent_sequence(reading_id)
            if sequence_data is None or len(sequence_data) < self.sequence_length:
                cursor.close()
                conn.close()
                return []
            
            # Get latest reading values
            cursor.execute(f'''
                SELECT {', '.join(self.lstm_detector.SENSOR_COLUMNS)}
                FROM sensor_readings
                WHERE id = %s
            ''', (reading_id,))
            latest_values = cursor.fetchone()
            
            # Calculate per-sensor reconstruction errors
            features = sequence_data[self.lstm_detector.SENSOR_COLUMNS].copy()
            features = features.fillna(0)
            scaled = self.lstm_detector.scaler.transform(features)
            sequence = scaled.reshape(1, self.sequence_length, self.lstm_detector.n_features)
            reconstruction = self.lstm_detector.model.predict(sequence, verbose=0)
            
            # Per-sensor errors
            sensor_errors = np.mean(np.power(sequence - reconstruction, 2), axis=1)[0]
            
            # Analyze trends for each sensor
            sensor_analyses = []
            
            for i, sensor in enumerate(self.lstm_detector.SENSOR_COLUMNS):
                error = float(sensor_errors[i])
                current_value = float(latest_values[i]) if latest_values[i] is not None else 0
                
                # Get historical values for trend analysis
                sensor_values = sequence_data[sensor].values
                
                # Calculate trend
                if len(sensor_values) >= 3:
                    # Linear regression to find trend
                    x = np.arange(len(sensor_values))
                    slope = np.polyfit(x, sensor_values, 1)[0]
                    
                    # Determine trend direction
                    if abs(slope) < 0.01:
                        trend = 'stable'
                        trend_rate = 0
                    elif slope > 0:
                        trend = 'increasing'
                        trend_rate = float(slope)
                    else:
                        trend = 'decreasing'
                        trend_rate = float(slope)
                else:
                    trend = 'unknown'
                    trend_rate = 0
                
                # Calculate severity based on error and trend
                error_percentile = (error / np.max(sensor_errors)) * 100 if np.max(sensor_errors) > 0 else 0
                
                if error_percentile > 80 and trend == 'increasing':
                    severity = 'critical'
                elif error_percentile > 60 and (trend == 'increasing' or trend == 'stable'):
                    severity = 'high'
                elif error_percentile > 40:
                    severity = 'medium'
                else:
                    severity = 'low'
                
                # Predict when it might fail (if trend continues)
                predicted_failure_reading = None
                reason = ""
                
                if trend == 'increasing' and trend_rate > 0:
                    # Get sensor normal range from config
                    sensor_range = config.SENSOR_RANGES.get(sensor, {})
                    max_normal = sensor_range.get('max', current_value * 2)
                    
                    # Estimate readings until failure
                    if trend_rate > 0:
                        readings_to_failure = (max_normal - current_value) / trend_rate
                        if readings_to_failure > 0 and readings_to_failure < 100:
                            predicted_failure_reading = int(reading_id + readings_to_failure)
                            reason = f"{sensor} is increasing at {abs(trend_rate):.2f} per reading. At this rate, it will exceed normal range ({max_normal:.1f}) in approximately {int(readings_to_failure)} readings."
                        else:
                            reason = f"{sensor} is increasing at {abs(trend_rate):.2f} per reading, but rate is too slow to predict failure window."
                    else:
                        reason = f"{sensor} shows high reconstruction error ({error:.4f}) but trend is unclear."
                elif error_percentile > 60:
                    reason = f"{sensor} has high reconstruction error ({error:.4f}), indicating it's deviating from learned normal patterns. The LSTM model cannot accurately predict its behavior."
                elif trend == 'decreasing':
                    reason = f"{sensor} is decreasing, which may indicate recovery or shutdown. Monitor for stabilization."
                else:
                    reason = f"{sensor} shows moderate deviation from normal patterns."
                
                sensor_analyses.append({
                    'sensor': sensor,
                    'reconstruction_error': error,
                    'error_percentile': error_percentile,
                    'trend': trend,
                    'trend_rate': trend_rate,
                    'current_value': current_value,
                    'predicted_failure_reading': predicted_failure_reading,
                    'reason': reason,
                    'severity': severity
                })
            
            cursor.close()
            conn.close()
            
            # Sort by severity and error
            severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
            sensor_analyses.sort(key=lambda x: (severity_order.get(x['severity'], 4), -x['error_percentile']))
            
            return sensor_analyses
            
        except Exception as e:
            self.logger.error(f"Error analyzing sensor trends: {e}")
            return []
    
    def get_recent_predictions(self, limit=10):
        """Get recent prediction history.
        
        Args:
            limit: Number of predictions to return
            
        Returns:
            list: List of recent predictions with timestamps
        """
        try:
            conn = psycopg2.connect(**config.DB_CONFIG)
            cursor = conn.cursor()
            
            # Get recent readings
            cursor.execute(f'''
                SELECT id, timestamp 
                FROM sensor_readings 
                ORDER BY id DESC 
                LIMIT {limit}
            ''')
            
            readings = cursor.fetchall()
            predictions = []
            
            for reading_id, timestamp in readings:
                prediction = self.predict_future_anomaly(reading_id)
                prediction['timestamp'] = timestamp.isoformat() if timestamp else None
                predictions.append(prediction)
            
            cursor.close()
            conn.close()
            
            return predictions
            
        except Exception as e:
            self.logger.error(f"Error getting recent predictions: {e}")
            return []


# Singleton instance
_predictor_instance = None


def get_predictor():
    """Get the singleton LSTM predictor instance."""
    global _predictor_instance
    if _predictor_instance is None:
        _predictor_instance = LSTMPredictor()
    return _predictor_instance


def predict_next_anomaly(reading_id=None, lookahead=10):
    """Convenience function to predict future anomaly.
    
    Args:
        reading_id: ID of reading to predict from (None = latest)
        lookahead: Number of readings to look ahead
        
    Returns:
        dict: Prediction results
    """
    predictor = get_predictor()
    return predictor.predict_future_anomaly(reading_id, lookahead)

