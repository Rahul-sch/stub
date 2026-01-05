"""
LSTM Autoencoder for Sequence-Based Anomaly Detection.
Detects anomalies by learning normal temporal patterns and flagging high reconstruction errors.

NOTE: This is an optional component that requires TensorFlow.
Uncomment 'tensorflow==2.15.0' in requirements.txt to use this.
"""

import os
import logging
import numpy as np
import pandas as pd
import psycopg2

import config

# Try to import TensorFlow
try:
    import tensorflow as tf
    from tensorflow.keras.models import Model, load_model
    from tensorflow.keras.layers import Input, LSTM, Dense, RepeatVector, TimeDistributed
    from tensorflow.keras.callbacks import EarlyStopping
    from sklearn.preprocessing import StandardScaler
    import joblib
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False


class LSTMAutoencoder:
    """LSTM Autoencoder for sequence-based anomaly detection.
    
    This model learns the normal temporal patterns in sensor data and
    detects anomalies based on reconstruction error. High reconstruction
    error indicates the pattern is unusual/anomalous.
    """

    # Sensor columns to use (same as Isolation Forest)
    SENSOR_COLUMNS = [
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
    ]

    def __init__(self, sequence_length=20, encoding_dim=32, threshold_percentile=95):
        """Initialize the LSTM Autoencoder.
        
        Args:
            sequence_length: Number of time steps in each sequence
            encoding_dim: Dimension of the encoded representation
            threshold_percentile: Percentile of training errors to use as threshold
        """
        if not TENSORFLOW_AVAILABLE:
            raise ImportError(
                "TensorFlow is required for LSTM Autoencoder. "
                "Install with: pip install tensorflow==2.15.0"
            )
        
        self.sequence_length = sequence_length
        self.encoding_dim = encoding_dim
        self.threshold_percentile = threshold_percentile
        self.n_features = len(self.SENSOR_COLUMNS)
        
        self.model = None
        self.scaler = StandardScaler()
        self.threshold = None
        self.is_trained = False
        
        self.logger = logging.getLogger(__name__)
        
        # Ensure models directory exists
        os.makedirs(config.MODELS_DIR, exist_ok=True)
        
        # Try to load existing model
        self._load_model()

    def _get_model_path(self):
        """Get paths for model files."""
        base_path = os.path.join(config.MODELS_DIR, 'lstm_autoencoder')
        return {
            'model': base_path + '.keras',
            'scaler': base_path + '_scaler.pkl',
            'threshold': base_path + '_threshold.pkl'
        }

    def _build_model(self):
        """Build the LSTM Autoencoder architecture."""
        # Encoder
        inputs = Input(shape=(self.sequence_length, self.n_features))
        
        # Encoder LSTM layers
        encoded = LSTM(128, activation='relu', return_sequences=True)(inputs)
        encoded = LSTM(64, activation='relu', return_sequences=False)(encoded)
        encoded = Dense(self.encoding_dim, activation='relu')(encoded)
        
        # Decoder
        decoded = RepeatVector(self.sequence_length)(encoded)
        decoded = LSTM(64, activation='relu', return_sequences=True)(decoded)
        decoded = LSTM(128, activation='relu', return_sequences=True)(decoded)
        outputs = TimeDistributed(Dense(self.n_features))(decoded)
        
        # Build model
        self.model = Model(inputs, outputs)
        self.model.compile(optimizer='adam', loss='mse')
        
        self.logger.info(f"Built LSTM Autoencoder: sequence_length={self.sequence_length}, "
                        f"features={self.n_features}, encoding_dim={self.encoding_dim}")

    def _load_model(self):
        """Load a previously trained model if it exists."""
        paths = self._get_model_path()
        
        if os.path.exists(paths['model']):
            try:
                self.model = load_model(paths['model'])
                self.scaler = joblib.load(paths['scaler'])
                self.threshold = joblib.load(paths['threshold'])
                self.is_trained = True
                self.logger.info("Loaded existing LSTM Autoencoder model")
            except Exception as e:
                self.logger.warning(f"Failed to load LSTM model: {e}")
                self.is_trained = False

    def _save_model(self):
        """Save the trained model to disk."""
        paths = self._get_model_path()
        
        try:
            self.model.save(paths['model'])
            joblib.dump(self.scaler, paths['scaler'])
            joblib.dump(self.threshold, paths['threshold'])
            self.logger.info(f"Saved LSTM Autoencoder model")
        except Exception as e:
            self.logger.error(f"Failed to save LSTM model: {e}")

    def _fetch_training_data(self, limit=2000):
        """Fetch historical sensor data from database.
        
        Args:
            limit: Maximum number of readings to fetch
            
        Returns:
            pandas DataFrame with sensor readings ordered by time
        """
        conn = None
        try:
            conn = psycopg2.connect(**config.DB_CONFIG)
            cursor = conn.cursor()
            
            columns = ', '.join(self.SENSOR_COLUMNS)
            query = f"""
                SELECT {columns}
                FROM sensor_readings
                ORDER BY created_at ASC
                LIMIT %s
            """
            
            cursor.execute(query, (limit,))
            rows = cursor.fetchall()
            cursor.close()
            
            if not rows:
                return None
            
            df = pd.DataFrame(rows, columns=self.SENSOR_COLUMNS)
            return df
            
        except Exception as e:
            self.logger.error(f"Failed to fetch training data: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def _create_sequences(self, data):
        """Create sequences from time series data.
        
        Args:
            data: 2D numpy array of shape (n_samples, n_features)
            
        Returns:
            3D numpy array of shape (n_sequences, sequence_length, n_features)
        """
        sequences = []
        for i in range(len(data) - self.sequence_length + 1):
            sequences.append(data[i:i + self.sequence_length])
        return np.array(sequences)

    def train(self, data=None, epochs=50, batch_size=32, validation_split=0.1):
        """Train the LSTM Autoencoder.
        
        Args:
            data: Optional pandas DataFrame with sensor data.
                  If None, fetches from database.
            epochs: Number of training epochs
            batch_size: Training batch size
            validation_split: Fraction of data for validation
            
        Returns:
            bool: True if training successful
        """
        if data is None:
            data = self._fetch_training_data()
        
        min_samples = self.sequence_length * 5  # Need enough for sequences
        if data is None or len(data) < min_samples:
            self.logger.warning(
                f"Not enough training data. Need at least {min_samples} samples, "
                f"got {len(data) if data is not None else 0}"
            )
            return False

        try:
            # Extract sensor columns
            feature_data = data[self.SENSOR_COLUMNS].copy()
            feature_data = feature_data.fillna(feature_data.mean())
            
            # Scale data
            scaled_data = self.scaler.fit_transform(feature_data)
            
            # Create sequences
            sequences = self._create_sequences(scaled_data)
            
            if len(sequences) < 10:
                self.logger.warning("Not enough sequences for training")
                return False
            
            # Build model if not exists
            if self.model is None:
                self._build_model()
            
            # Train with early stopping
            early_stopping = EarlyStopping(
                monitor='val_loss',
                patience=5,
                restore_best_weights=True
            )
            
            self.logger.info(f"Training LSTM Autoencoder on {len(sequences)} sequences...")
            
            history = self.model.fit(
                sequences, sequences,
                epochs=epochs,
                batch_size=batch_size,
                validation_split=validation_split,
                callbacks=[early_stopping],
                verbose=1
            )
            
            # Calculate reconstruction errors on training data to set threshold
            reconstructions = self.model.predict(sequences, verbose=0)
            mse = np.mean(np.power(sequences - reconstructions, 2), axis=(1, 2))
            self.threshold = np.percentile(mse, self.threshold_percentile)
            
            self.is_trained = True
            self._save_model()
            
            self.logger.info(f"LSTM training complete. Threshold: {self.threshold:.6f}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to train LSTM model: {e}")
            return False

    def detect(self, sequence_data):
        """Detect if a sequence is anomalous.
        
        Args:
            sequence_data: List of dicts or DataFrame with sensor readings.
                          Must have at least sequence_length readings.
                          
        Returns:
            tuple: (is_anomaly: bool, reconstruction_error: float, 
                    contributing_sensors: list)
        """
        if not self.is_trained:
            self.logger.warning("LSTM model not trained")
            return False, 0.0, []
        
        try:
            # Convert to DataFrame if needed
            if isinstance(sequence_data, list):
                df = pd.DataFrame(sequence_data)
            else:
                df = sequence_data
            
            # Need at least sequence_length readings
            if len(df) < self.sequence_length:
                return False, 0.0, []
            
            # Take the last sequence_length readings
            df = df.tail(self.sequence_length)
            
            # Extract features
            features = df[self.SENSOR_COLUMNS].copy()
            features = features.fillna(0)
            
            # Scale
            scaled = self.scaler.transform(features)
            
            # Reshape for LSTM
            sequence = scaled.reshape(1, self.sequence_length, self.n_features)
            
            # Predict (reconstruct)
            reconstruction = self.model.predict(sequence, verbose=0)
            
            # Calculate reconstruction error
            mse = np.mean(np.power(sequence - reconstruction, 2))
            
            # Check if anomalous
            is_anomaly = mse > self.threshold
            
            # Identify contributing sensors
            contributing_sensors = []
            if is_anomaly:
                # Calculate per-sensor reconstruction error
                sensor_errors = np.mean(np.power(sequence - reconstruction, 2), axis=1)[0]
                
                # Find sensors with high reconstruction error
                for i, sensor in enumerate(self.SENSOR_COLUMNS):
                    if sensor_errors[i] > np.percentile(sensor_errors, 80):
                        contributing_sensors.append(sensor)
            
            return is_anomaly, float(mse), contributing_sensors
            
        except Exception as e:
            self.logger.error(f"LSTM detection error: {e}")
            return False, 0.0, []

    def get_recent_sequence(self, reading_id):
        """Fetch recent readings to form a sequence ending at reading_id.
        
        Args:
            reading_id: ID of the reading to end the sequence at
            
        Returns:
            DataFrame with sequence_length readings, or None
        """
        conn = None
        try:
            conn = psycopg2.connect(**config.DB_CONFIG)
            cursor = conn.cursor()
            
            columns = ', '.join(self.SENSOR_COLUMNS)
            query = f"""
                SELECT {columns}
                FROM sensor_readings
                WHERE id <= %s
                ORDER BY id DESC
                LIMIT %s
            """
            
            cursor.execute(query, (reading_id, self.sequence_length))
            rows = cursor.fetchall()
            cursor.close()
            
            if len(rows) < self.sequence_length:
                return None
            
            # Reverse to chronological order
            rows = rows[::-1]
            df = pd.DataFrame(rows, columns=self.SENSOR_COLUMNS)
            return df
            
        except Exception as e:
            self.logger.error(f"Failed to fetch sequence: {e}")
            return None
        finally:
            if conn:
                conn.close()


# Global instance
_lstm_instance = None


def get_lstm_detector():
    """Get or create the global LSTM Autoencoder instance."""
    global _lstm_instance
    
    if not TENSORFLOW_AVAILABLE:
        return None
    
    if _lstm_instance is None:
        try:
            _lstm_instance = LSTMAutoencoder()
        except Exception as e:
            logging.error(f"Failed to create LSTM detector: {e}")
            return None
    
    return _lstm_instance


def is_lstm_available():
    """Check if LSTM detector is available."""
    return TENSORFLOW_AVAILABLE

