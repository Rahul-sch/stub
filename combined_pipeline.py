"""
Combined Anomaly Detection Pipeline.
Combines Isolation Forest and LSTM Autoencoder for hybrid anomaly detection.
"""

import logging

import config

# Import Isolation Forest detector
try:
    from ml_detector import get_detector, record_anomaly_detection
    IF_AVAILABLE = True
except ImportError as e:
    IF_AVAILABLE = False
    logging.warning(f"Isolation Forest not available: {e}")

# Import LSTM detector (optional, requires TensorFlow)
LSTM_AVAILABLE = False
if config.LSTM_ENABLED:
    try:
        from lstm_detector import get_lstm_detector, is_lstm_available
        LSTM_AVAILABLE = is_lstm_available()
        if LSTM_AVAILABLE:
            logging.info("LSTM Autoencoder is available")
        else:
            logging.info("LSTM requested but TensorFlow not installed")
    except ImportError as e:
        logging.warning(f"LSTM detector import failed: {e}")


class CombinedDetector:
    """Combined anomaly detector using Isolation Forest and LSTM Autoencoder.
    
    Supports multiple detection strategies:
    - isolation_forest: Only use Isolation Forest
    - lstm: Only use LSTM Autoencoder
    - hybrid_or: Flag if EITHER method detects anomaly
    - hybrid_and: Flag only if BOTH methods agree
    - hybrid_smart: IF primary, LSTM catches what IF misses
    """

    def __init__(self):
        """Initialize the combined detector."""
        self.logger = logging.getLogger(__name__)
        self.strategy = config.HYBRID_DETECTION_STRATEGY
        
        # Initialize Isolation Forest
        self.if_detector = None
        if IF_AVAILABLE:
            self.if_detector = get_detector()
            self.logger.info("Isolation Forest detector initialized")
        
        # Initialize LSTM (if available)
        self.lstm_detector = None
        if LSTM_AVAILABLE:
            self.lstm_detector = get_lstm_detector()
            if self.lstm_detector:
                self.logger.info(f"LSTM detector initialized (trained: {self.lstm_detector.is_trained})")
        
        self.logger.info(f"Combined detector initialized with strategy: {self.strategy}")

    def detect(self, reading, reading_id):
        """Run anomaly detection using the configured strategy.
        
        Args:
            reading: Dict with sensor values
            reading_id: ID of the reading in the database
            
        Returns:
            tuple: (is_anomaly, score, contributing_sensors, detection_method)
        """
        # Strategy: isolation_forest only
        if self.strategy == 'isolation_forest':
            return self._detect_if_only(reading)
        
        # Strategy: lstm only
        if self.strategy == 'lstm':
            return self._detect_lstm_only(reading_id)
        
        # Hybrid strategies
        if self.strategy in ['hybrid_or', 'hybrid_and', 'hybrid_smart']:
            return self._detect_hybrid(reading, reading_id)
        
        # Default: isolation_forest only
        self.logger.warning(f"Unknown strategy '{self.strategy}', using isolation_forest")
        return self._detect_if_only(reading)

    def _detect_if_only(self, reading):
        """Run Isolation Forest detection only.
        
        Args:
            reading: Dict with sensor values
            
        Returns:
            tuple: (is_anomaly, score, sensors, method)
        """
        if not self.if_detector:
            self.logger.warning("Isolation Forest not available")
            return False, 0.0, [], 'none'
        
        try:
            is_anomaly, score, sensors = self.if_detector.detect(reading)
            return is_anomaly, score, sensors, 'isolation_forest'
        except Exception as e:
            self.logger.error(f"Isolation Forest detection error: {e}")
            return False, 0.0, [], 'error'

    def _detect_lstm_only(self, reading_id):
        """Run LSTM detection only.
        
        Args:
            reading_id: ID of the reading in the database
            
        Returns:
            tuple: (is_anomaly, score, sensors, method)
        """
        if not self.lstm_detector:
            self.logger.warning("LSTM not available")
            return False, 0.0, [], 'none'
        
        if not self.lstm_detector.is_trained:
            self.logger.warning("LSTM model not trained")
            return False, 0.0, [], 'none'
        
        if reading_id < config.LSTM_MIN_READINGS:
            self.logger.debug(f"Not enough readings for LSTM (need {config.LSTM_MIN_READINGS})")
            return False, 0.0, [], 'none'
        
        try:
            # Get sequence of recent readings
            sequence = self.lstm_detector.get_recent_sequence(reading_id)
            if sequence is None or len(sequence) < self.lstm_detector.sequence_length:
                self.logger.debug("Insufficient sequence data for LSTM")
                return False, 0.0, [], 'none'
            
            is_anomaly, error, sensors = self.lstm_detector.detect(sequence)
            return is_anomaly, error, sensors, 'lstm_autoencoder'
        except Exception as e:
            self.logger.error(f"LSTM detection error: {e}")
            return False, 0.0, [], 'error'

    def _detect_hybrid(self, reading, reading_id):
        """Run hybrid detection using both methods.
        
        Args:
            reading: Dict with sensor values
            reading_id: ID of the reading in the database
            
        Returns:
            tuple: (is_anomaly, score, sensors, method)
        """
        # Run Isolation Forest
        if_anomaly = False
        if_score = 0.0
        if_sensors = []
        
        if self.if_detector:
            try:
                if_anomaly, if_score, if_sensors = self.if_detector.detect(reading)
            except Exception as e:
                self.logger.error(f"IF detection error in hybrid: {e}")
        
        # Run LSTM (if available and conditions met)
        lstm_anomaly = False
        lstm_error = 0.0
        lstm_sensors = []
        lstm_ran = False
        
        if (self.lstm_detector and 
            self.lstm_detector.is_trained and 
            reading_id >= config.LSTM_MIN_READINGS):
            try:
                sequence = self.lstm_detector.get_recent_sequence(reading_id)
                if sequence is not None and len(sequence) >= self.lstm_detector.sequence_length:
                    lstm_anomaly, lstm_error, lstm_sensors = self.lstm_detector.detect(sequence)
                    lstm_ran = True
            except Exception as e:
                self.logger.debug(f"LSTM detection skipped in hybrid: {e}")
        
        # Combine results based on strategy
        return self._combine_results(
            if_anomaly, if_score, if_sensors,
            lstm_anomaly, lstm_error, lstm_sensors,
            lstm_ran
        )

    def _combine_results(self, if_anomaly, if_score, if_sensors,
                         lstm_anomaly, lstm_error, lstm_sensors, lstm_ran):
        """Combine detection results based on strategy.
        
        Args:
            if_anomaly: Isolation Forest anomaly result
            if_score: Isolation Forest score
            if_sensors: Isolation Forest contributing sensors
            lstm_anomaly: LSTM anomaly result
            lstm_error: LSTM reconstruction error
            lstm_sensors: LSTM contributing sensors
            lstm_ran: Whether LSTM actually ran
            
        Returns:
            tuple: (is_anomaly, score, sensors, method)
        """
        strategy = self.strategy
        
        # If LSTM didn't run, fall back to IF only
        if not lstm_ran:
            return if_anomaly, if_score, if_sensors, 'isolation_forest'
        
        if strategy == 'hybrid_or':
            # Flag if EITHER method detects
            final_anomaly = if_anomaly or lstm_anomaly
            
            if if_anomaly and lstm_anomaly:
                # Both detected - combine info
                final_sensors = list(set(if_sensors + lstm_sensors))
                final_score = (if_score + lstm_error) / 2
                method = 'hybrid'
            elif lstm_anomaly:
                # Only LSTM detected
                final_sensors = lstm_sensors
                final_score = lstm_error
                method = 'lstm_autoencoder'
            else:
                # Only IF detected (or neither)
                final_sensors = if_sensors
                final_score = if_score
                method = 'isolation_forest'
            
            return final_anomaly, final_score, final_sensors, method
        
        elif strategy == 'hybrid_and':
            # Flag only if BOTH agree
            final_anomaly = if_anomaly and lstm_anomaly
            
            if final_anomaly:
                final_sensors = list(set(if_sensors + lstm_sensors))
                final_score = (if_score + lstm_error) / 2
                method = 'hybrid'
            else:
                # No consensus - report IF result but not as anomaly
                final_sensors = if_sensors
                final_score = if_score
                method = 'isolation_forest'
            
            return final_anomaly, final_score, final_sensors, method
        
        elif strategy == 'hybrid_smart':
            # IF primary, LSTM catches what IF misses
            if if_anomaly:
                # IF detected - flag immediately
                if lstm_anomaly:
                    # Both detected - combine for richer info
                    final_sensors = list(set(if_sensors + lstm_sensors))
                    final_score = (if_score + lstm_error) / 2
                    method = 'hybrid'
                else:
                    # Only IF detected
                    final_sensors = if_sensors
                    final_score = if_score
                    method = 'isolation_forest'
                return True, final_score, final_sensors, method
            
            elif lstm_anomaly:
                # IF missed but LSTM caught (gradual trend)
                return True, lstm_error, lstm_sensors, 'lstm_autoencoder'
            
            else:
                # Neither detected
                return False, if_score, if_sensors, 'isolation_forest'
        
        # Fallback
        return if_anomaly, if_score, if_sensors, 'isolation_forest'

    def record_detection(self, reading_id, is_anomaly, score, sensors, method):
        """Record the detection result in the database.
        
        Args:
            reading_id: ID of the reading
            is_anomaly: Whether anomaly was detected
            score: Anomaly score
            sensors: Contributing sensors
            method: Detection method used
            
        Returns:
            int: Detection ID, or None on failure
        """
        try:
            return record_anomaly_detection(
                reading_id=reading_id,
                detection_method=method,
                anomaly_score=score,
                is_anomaly=is_anomaly,
                detected_sensors=sensors
            )
        except Exception as e:
            self.logger.error(f"Failed to record detection: {e}")
            return None


# Global instance
_combined_detector = None


def get_combined_detector():
    """Get or create the global CombinedDetector instance."""
    global _combined_detector
    if _combined_detector is None:
        _combined_detector = CombinedDetector()
    return _combined_detector

