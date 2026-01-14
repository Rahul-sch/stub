#!/usr/bin/env python3
"""
Training Script for Combined Anomaly Detection Models.
Trains both Isolation Forest and LSTM Autoencoder models.

Usage:
    python train_combined_detector.py [--if-only] [--lstm-only] [--force]
    
Options:
    --if-only   Train only Isolation Forest
    --lstm-only Train only LSTM Autoencoder
    --force     Force retraining even if models exist
"""

import sys
import argparse
import logging
import warnings
import psycopg2

import config

# Suppress sklearn version warnings
warnings.filterwarnings('ignore', category=UserWarning, module='sklearn')
warnings.filterwarnings('ignore', message='.*InconsistentVersionWarning.*')
warnings.filterwarnings('ignore', message='.*FutureWarning.*')

# Setup logging - simpler format
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    datefmt=''
)
logger = logging.getLogger(__name__)


def get_reading_count():
    """Get the current number of sensor readings in the database."""
    try:
        conn = psycopg2.connect(**config.DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sensor_readings")
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return count
    except Exception as e:
        logger.error(f"Failed to get reading count: {e}")
        return 0


def train_isolation_forest(force=False):
    """Train the Isolation Forest model.
    
    Args:
        force: Force retraining even if model exists
        
    Returns:
        bool: True if training successful
    """
    print("\n" + "=" * 60)
    print("Training Isolation Forest")
    print("=" * 60)
    
    try:
        from ml_detector import get_detector
        
        detector = get_detector()
        
        if detector.is_trained and not force:
            print("\n✓ Isolation Forest model already trained")
            print(f"  Use --force to retrain\n")
            return True
        
        # Check data requirements
        count = get_reading_count()
        if count < config.MIN_TRAINING_SAMPLES:
            logger.warning(f"Not enough data for training")
            logger.warning(f"  Required: {config.MIN_TRAINING_SAMPLES} readings")
            logger.warning(f"  Available: {count} readings")
            return False
        
        print(f"\nTraining on {count} readings...")
        success = detector.train()
        
        if success:
            print("\n✓ Isolation Forest trained successfully!")
            print(f"  Contamination: {detector.contamination}")
            print(f"  Estimators: {detector.n_estimators}\n")
            return True
        else:
            print("\n✗ Isolation Forest training failed\n")
            return False
            
    except ImportError as e:
        logger.error(f"Failed to import ml_detector: {e}")
        return False
    except Exception as e:
        logger.error(f"Isolation Forest training error: {e}")
        import traceback
        traceback.print_exc()
        return False


def train_lstm(force=False):
    """Train the LSTM Autoencoder model.
    
    Args:
        force: Force retraining even if model exists
        
    Returns:
        bool: True if training successful
    """
    print("\n" + "=" * 60)
    print("Training LSTM Autoencoder")
    print("=" * 60)
    
    # Check if LSTM is enabled
    if not config.LSTM_ENABLED:
        logger.info("LSTM is disabled in config (LSTM_ENABLED=False)")
        logger.info("  Set LSTM_ENABLED=True in config.py to enable")
        return False
    
    try:
        from lstm_detector import get_lstm_detector, is_lstm_available
        
        if not is_lstm_available():
            logger.error("LSTM not available - TensorFlow not installed")
            logger.error("  Install with: pip install tensorflow==2.15.0")
            return False
        
        detector = get_lstm_detector()
        if not detector:
            logger.error("Failed to create LSTM detector")
            return False
        
        if detector.is_trained and not force:
            print("\n✓ LSTM model already trained")
            print(f"  Threshold: {detector.threshold:.6f}")
            print(f"  Use --force to retrain\n")
            return True
        
        # Check data requirements
        count = get_reading_count()
        min_required = detector.sequence_length * 5  # 100 for sequence_length=20
        recommended = 500
        
        if count < min_required:
            logger.warning(f"Not enough data for LSTM training")
            logger.warning(f"  Minimum required: {min_required} readings")
            logger.warning(f"  Recommended: {recommended}+ readings")
            logger.warning(f"  Available: {count} readings")
            return False
        
        if count < recommended:
            logger.warning(f"Data below recommended ({count} < {recommended})")
            logger.warning(f"  Training anyway, but results may be suboptimal")
        
        print(f"\nTraining LSTM on {count} readings...")
        print(f"  Sequence length: {detector.sequence_length}")
        print(f"  Encoding dimension: {detector.encoding_dim}")
        print(f"  This may take several minutes...\n")
        
        success = detector.train(epochs=50, batch_size=32)
        
        if success:
            print("\n✓ LSTM Autoencoder trained successfully!")
            print(f"  Threshold: {detector.threshold:.6f}")
            print(f"  Sequence length: {detector.sequence_length}")
            print(f"  Features: {detector.n_features}\n")
            return True
        else:
            print("\n✗ LSTM training failed\n")
            return False
            
    except ImportError as e:
        logger.error(f"Failed to import lstm_detector: {e}")
        logger.error("  Install TensorFlow: pip install tensorflow==2.15.0")
        return False
    except Exception as e:
        logger.error(f"LSTM training error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main training function."""
    parser = argparse.ArgumentParser(
        description='Train anomaly detection models (Isolation Forest + LSTM)'
    )
    parser.add_argument('--if-only', action='store_true',
                        help='Train only Isolation Forest')
    parser.add_argument('--lstm-only', action='store_true',
                        help='Train only LSTM Autoencoder')
    parser.add_argument('--force', action='store_true',
                        help='Force retraining even if models exist')
    
    args = parser.parse_args()
    
    print("\n" + "=" * 60)
    print("Combined Anomaly Detection Model Training")
    print("=" * 60)
    
    # Check database connection
    count = get_reading_count()
    print(f"\nDatabase contains {count} sensor readings\n")
    
    if count == 0:
        logger.error("No data in database. Run producer and consumer first.")
        return 1
    
    results = {'if': None, 'lstm': None}
    
    # Train Isolation Forest
    if not args.lstm_only:
        results['if'] = train_isolation_forest(force=args.force)
    
    # Train LSTM
    if not args.if_only:
        results['lstm'] = train_lstm(force=args.force)
    
    # Summary
    print("\n" + "=" * 60)
    print("Training Summary")
    print("=" * 60)
    
    if results['if'] is not None:
        status = "✓ Success" if results['if'] else "✗ Failed"
        print(f"\nIsolation Forest: {status}")
    
    if results['lstm'] is not None:
        status = "✓ Success" if results['lstm'] else "✗ Failed/Skipped"
        print(f"LSTM Autoencoder: {status}")
    
    print(f"\nDetection strategy: {config.HYBRID_DETECTION_STRATEGY}")
    
    # Recommend strategy based on results
    if results['if'] and results['lstm']:
        print("Both models trained - hybrid detection available")
    elif results['if'] and not results['lstm']:
        print("Only IF trained - using isolation_forest strategy")
        if config.LSTM_ENABLED:
            print("  Train LSTM when you have 500+ readings")
    elif results['lstm'] and not results['if']:
        print("Only LSTM trained - consider training IF first")
    
    print("=" * 60 + "\n")
    
    # Return exit code
    if args.if_only:
        return 0 if results['if'] else 1
    elif args.lstm_only:
        return 0 if results['lstm'] else 1
    else:
        # Both requested - success if at least IF worked
        return 0 if results['if'] else 1


if __name__ == '__main__':
    sys.exit(main())

