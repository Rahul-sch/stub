"""
ML-based Anomaly Detection using Isolation Forest.
Provides real-time outlier detection for sensor data.
"""

import os
import logging
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib
import psycopg2

import config


class AnomalyDetector:
    """Isolation Forest-based anomaly detector for sensor data."""

    # List of sensor columns to use for detection (all 50 parameters)
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

    def __init__(self, contamination=None, n_estimators=None):
        """Initialize the anomaly detector.
        
        Args:
            contamination: Expected proportion of anomalies (default from config)
            n_estimators: Number of trees in the forest (default from config)
        """
        self.contamination = contamination or config.ISOLATION_FOREST_CONTAMINATION
        self.n_estimators = n_estimators or config.ISOLATION_FOREST_N_ESTIMATORS
        
        self.model = IsolationForest(
            contamination=self.contamination,
            n_estimators=self.n_estimators,
            random_state=42,
            n_jobs=-1  # Use all CPU cores
        )
        self.scaler = StandardScaler()
        self.is_trained = False
        self.feature_means = None
        self.feature_stds = None
        
        self.logger = logging.getLogger(__name__)
        
        # Ensure models directory exists
        os.makedirs(config.MODELS_DIR, exist_ok=True)
        
        # Try to load existing model
        self._load_model()

    def _get_model_path(self):
        """Get the path to the saved model file."""
        return os.path.join(config.MODELS_DIR, 'isolation_forest.pkl')

    def _load_model(self):
        """Load a previously trained model if it exists."""
        model_path = self._get_model_path()
        if os.path.exists(model_path):
            try:
                saved_data = joblib.load(model_path)
                self.model = saved_data['model']
                self.scaler = saved_data['scaler']
                self.feature_means = saved_data.get('feature_means')
                self.feature_stds = saved_data.get('feature_stds')
                self.is_trained = True
                self.logger.info("Loaded existing Isolation Forest model")
            except Exception as e:
                self.logger.warning(f"Failed to load model: {e}")
                self.is_trained = False

    def _save_model(self):
        """Save the trained model to disk."""
        model_path = self._get_model_path()
        try:
            joblib.dump({
                'model': self.model,
                'scaler': self.scaler,
                'feature_means': self.feature_means,
                'feature_stds': self.feature_stds
            }, model_path)
            self.logger.info(f"Saved Isolation Forest model to {model_path}")
        except Exception as e:
            self.logger.error(f"Failed to save model: {e}")

    def _fetch_training_data(self, limit=1000):
        """Fetch historical sensor data from database for training.
        
        Args:
            limit: Maximum number of readings to fetch
            
        Returns:
            pandas DataFrame with sensor readings
        """
        conn = None
        try:
            conn = psycopg2.connect(**config.DB_CONFIG)
            cursor = conn.cursor()
            
            # Build column list for query
            columns = ', '.join(self.SENSOR_COLUMNS)
            query = f"""
                SELECT id, {columns}
                FROM sensor_readings
                ORDER BY created_at DESC
                LIMIT %s
            """
            
            cursor.execute(query, (limit,))
            rows = cursor.fetchall()
            cursor.close()
            
            if not rows:
                return None
            
            # Create DataFrame
            column_names = ['id'] + self.SENSOR_COLUMNS
            df = pd.DataFrame(rows, columns=column_names)
            
            return df
            
        except Exception as e:
            self.logger.error(f"Failed to fetch training data: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def train(self, data=None):
        """Train the Isolation Forest model.
        
        Args:
            data: Optional pandas DataFrame with sensor data.
                  If None, fetches from database.
                  
        Returns:
            bool: True if training successful
        """
        if data is None:
            data = self._fetch_training_data()
            
        if data is None or len(data) < config.MIN_TRAINING_SAMPLES:
            self.logger.warning(
                f"Not enough training data. Need at least {config.MIN_TRAINING_SAMPLES} samples, "
                f"got {len(data) if data is not None else 0}"
            )
            return False

        try:
            # Extract sensor columns only (exclude id)
            feature_data = data[self.SENSOR_COLUMNS].copy()
            
            # Handle missing values by filling with column means
            feature_data = feature_data.fillna(feature_data.mean())
            
            # Store feature statistics for contribution analysis
            self.feature_means = feature_data.mean().to_dict()
            self.feature_stds = feature_data.std().to_dict()
            
            # Scale the data
            scaled_data = self.scaler.fit_transform(feature_data)
            
            # Create a fresh model instance to avoid version compatibility issues
            self.model = IsolationForest(
                contamination=self.contamination,
                n_estimators=self.n_estimators,
                random_state=42,
                n_jobs=-1  # Use all CPU cores
            )
            
            # Train the model
            self.model.fit(scaled_data)
            self.is_trained = True
            
            # Save the model
            self._save_model()
            
            self.logger.info(f"Trained Isolation Forest on {len(data)} samples")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to train model: {e}")
            return False

    def _reading_to_features(self, reading):
        """Convert a sensor reading dict to a feature array.
        
        Args:
            reading: Dict with sensor values
            
        Returns:
            numpy array of feature values
        """
        features = []
        for col in self.SENSOR_COLUMNS:
            value = reading.get(col)
            if value is None:
                # Use stored mean if available, otherwise 0
                if self.feature_means and col in self.feature_means:
                    value = self.feature_means[col]
                else:
                    value = 0
            features.append(float(value))
        return np.array(features).reshape(1, -1)

    def _identify_contributing_sensors(self, reading, threshold_std=2.0):
        """Identify which sensors contributed most to an anomaly.
        
        Uses z-score analysis to find sensors that deviated significantly
        from their historical means.
        
        Args:
            reading: Dict with sensor values
            threshold_std: Number of standard deviations to consider significant
            
        Returns:
            List of sensor names that contributed to the anomaly
        """
        if not self.feature_means or not self.feature_stds:
            return []
            
        contributing = []
        for col in self.SENSOR_COLUMNS:
            value = reading.get(col)
            if value is None:
                continue
                
            mean = self.feature_means.get(col, 0)
            std = self.feature_stds.get(col, 1)
            
            if std > 0:
                z_score = abs((value - mean) / std)
                if z_score > threshold_std:
                    contributing.append(col)
                    
        return contributing

    def detect(self, reading):
        """Detect if a sensor reading is anomalous.
        
        Args:
            reading: Dict with sensor values (must include all SENSOR_COLUMNS)
            
        Returns:
            tuple: (is_anomaly: bool, anomaly_score: float, contributing_sensors: list)
                   - is_anomaly: True if the reading is an outlier
                   - anomaly_score: Lower (more negative) = more anomalous
                   - contributing_sensors: List of sensor names that contributed
        """
        if not self.is_trained:
            # Try to train on available data
            self.logger.info("Model not trained, attempting to train on historical data...")
            if not self.train():
                self.logger.warning("Cannot detect anomaly: model not trained")
                return False, 0.0, []
        
        try:
            # Convert reading to features
            features = self._reading_to_features(reading)
            
            # Convert to DataFrame with column names to match training data format
            features_df = pd.DataFrame(features, columns=self.SENSOR_COLUMNS)
            
            # Scale features
            scaled_features = self.scaler.transform(features_df)
            
            # Predict (-1 for anomaly, 1 for normal)
            prediction = self.model.predict(scaled_features)[0]
            
            # Get anomaly score (lower = more anomalous)
            anomaly_score = self.model.decision_function(scaled_features)[0]
            
            is_anomaly = prediction == -1
            
            # Identify contributing sensors if anomaly
            contributing_sensors = []
            if is_anomaly:
                contributing_sensors = self._identify_contributing_sensors(reading)
            
            return is_anomaly, float(anomaly_score), contributing_sensors
            
        except Exception as e:
            self.logger.error(f"Error during anomaly detection: {e}")
            return False, 0.0, []

    def retrain_if_needed(self, min_new_samples=100):
        """Retrain the model if enough new samples are available.
        
        Args:
            min_new_samples: Minimum new samples required to trigger retraining
            
        Returns:
            bool: True if retrained
        """
        # Check current sample count in database
        conn = None
        try:
            conn = psycopg2.connect(**config.DB_CONFIG)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM sensor_readings")
            count = cursor.fetchone()[0]
            cursor.close()
            
            # Retrain if we have significantly more data
            if count >= config.MIN_TRAINING_SAMPLES + min_new_samples:
                return self.train()
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to check sample count: {e}")
            return False
        finally:
            if conn:
                conn.close()


def record_anomaly_detection(reading_id, detection_method, anomaly_score, 
                             is_anomaly, detected_sensors=None):
    """Record an anomaly detection result in the database.
    
    Args:
        reading_id: ID of the sensor reading
        detection_method: 'isolation_forest', 'lstm_autoencoder', or 'hybrid'
        anomaly_score: The anomaly score from the model
        is_anomaly: Whether it was classified as an anomaly
        detected_sensors: List of sensor names that contributed
        
    Returns:
        int: ID of the inserted record, or None on failure
    """
    conn = None
    try:
        conn = psycopg2.connect(**config.DB_CONFIG)
        cursor = conn.cursor()
        
        # Convert numpy types to Python native types for psycopg2 compatibility
        cursor.execute("""
            INSERT INTO anomaly_detections 
                (reading_id, detection_method, anomaly_score, is_anomaly, detected_sensors)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (
            int(reading_id),
            detection_method,
            float(anomaly_score) if anomaly_score is not None else 0.0,
            bool(is_anomaly),
            detected_sensors or []
        ))
        
        detection_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        
        return detection_id
        
    except Exception as e:
        logging.error(f"Failed to record anomaly detection: {e}")
        if conn:
            conn.rollback()
        return None
    finally:
        if conn:
            conn.close()


# Global detector instance for reuse
_detector_instance = None


def get_detector():
    """Get or create the global AnomalyDetector instance."""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = AnomalyDetector()
    return _detector_instance

