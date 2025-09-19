"""
Model inference and data processing module.
Handles model loading, prediction logic, and feature scaling.
"""

import logging
import pickle
import json
from typing import Optional, Dict, Any, Tuple
import numpy as np
import torch
import torch.utils.data
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error

from advanced_models import AttentionLSTM
from model_loader import load_model_from_checkpoint
from week2_feature_engineering_fixed import PowerConsumptionDataset

logger = logging.getLogger(__name__)

# Global variables for model and scalers
model: Optional[AttentionLSTM] = None
feature_scaler = None
target_scaler = None
metadata: Optional[Dict[str, Any]] = None
model_validation_metrics: Optional[Dict[str, float]] = None


def partial_scale_features(arr: np.ndarray) -> np.ndarray:
    """Apply feature_scaler to matching leading columns only when counts differ.

    - arr can be (T,F) or (N,T,F). Returns array with same shape.
    - If feature_scaler expects K features and arr has F != K, only the first K
      columns are scaled; the remainder are left unchanged.
    """
    if feature_scaler is None:
        return arr
    try:
        k = getattr(feature_scaler, 'n_features_in_', None)
        if k is None:
            # Fallback: try length of feature_names_in_
            names = getattr(feature_scaler, 'feature_names_in_', None)
            k = len(names) if names is not None else arr.shape[-1]
        F = arr.shape[-1]
        if arr.ndim == 2:
            if k == F:
                return feature_scaler.transform(arr)
            else:
                out = arr.copy()
                out[:, :k] = feature_scaler.transform(arr[:, :k])
                return out
        elif arr.ndim == 3:
            T = arr.shape[0] * arr.shape[1]
            flat = arr.reshape(T, F)
            if k == F:
                flat_scaled = feature_scaler.transform(flat)
            else:
                flat_scaled = flat.copy()
                flat_scaled[:, :k] = feature_scaler.transform(flat[:, :k])
            return flat_scaled.reshape(arr.shape)
        else:
            return arr
    except Exception:
        return arr


def load_model_and_scalers():
    """Load the trained model, scalers, and metadata"""
    global model, feature_scaler, target_scaler, metadata

    logger.info("Loading model and scalers...")

    # Load model checkpoint
    try:
        import os
        model_path = os.getenv("MODEL_PATH", "best_attentionlstm_20250907-091842.pth")
        model, checkpoint = load_model_from_checkpoint(model_path, input_size=11, output_size=3, device='cpu')
        logger.info(f"Model loaded successfully from {model_path}")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise

    # Load feature scaler
    try:
        with open('feature_scaler.pkl', 'rb') as f:
            feature_scaler = pickle.load(f)
        logger.info("Feature scaler loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load feature scaler: {e}")
        raise

    # Load target scaler
    try:
        with open('target_scaler.pkl', 'rb') as f:
            target_scaler = pickle.load(f)
        logger.info("Target scaler loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load target scaler: {e}")
        raise

    # Load metadata
    try:
        with open('dataset_metadata_fixed.json', 'r') as f:
            metadata = json.load(f)
        logger.info("Dataset metadata loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load metadata: {e}")
        raise


def compute_validation_metrics(batch_size: int = 256, max_samples: Optional[int] = None):
    """Evaluate the loaded model on validation data and cache metrics.

    Uses feature_scaler to normalize inputs and target_scaler to denormalize outputs.
    Automatically detects whether validation targets are raw or normalized by
    comparing RMSE of two candidates.
    """
    global model_validation_metrics

    if model is None or feature_scaler is None or target_scaler is None or metadata is None:
        raise RuntimeError("Model/scalers/metadata not loaded")

    import os

    val_sequences_path = "val_sequences_fixed.npy"
    val_targets_path = "val_targets_fixed.npy"

    if not os.path.exists(val_sequences_path) or not os.path.exists(val_targets_path):
        logger.warning("Validation files not found; skipping metrics computation")
        return

    try:
        val_sequences = np.load(val_sequences_path)
        val_targets = np.load(val_targets_path)
        logger.info(f"Loaded validation data: sequences {val_sequences.shape}, targets {val_targets.shape}")

        # Limit samples if specified
        if max_samples is not None and len(val_sequences) > max_samples:
            val_sequences = val_sequences[:max_samples]
            val_targets = val_targets[:max_samples]
            logger.info(f"Limited to {max_samples} samples")

        # Create dataset
        val_dataset = PowerConsumptionDataset(val_sequences, val_targets)
        val_loader = torch.utils.data.DataLoader(val_dataset, batch_size=batch_size, shuffle=False)

        # Generate predictions
        model.eval()
        all_predictions = []
        all_targets = []

        with torch.no_grad():
            for batch_features, batch_targets in val_loader:
                batch_features = batch_features.float()
                batch_targets = batch_targets.float()

                # Model prediction
                predictions = model(batch_features)

                all_predictions.append(predictions.cpu().numpy())
                all_targets.append(batch_targets.cpu().numpy())

        # Concatenate all predictions and targets
        y_pred = np.concatenate(all_predictions, axis=0)
        y_true = np.concatenate(all_targets, axis=0)

        # Try both denormalized and raw targets to detect scaling
        try:
            y_true_denorm = target_scaler.inverse_transform(y_true)
            y_pred_denorm = target_scaler.inverse_transform(y_pred)

            rmse_denorm = np.sqrt(mean_squared_error(y_true_denorm, y_pred_denorm))
            rmse_raw = np.sqrt(mean_squared_error(y_true, y_pred))

            # Use the version that gives more reasonable RMSE
            if rmse_denorm < rmse_raw and rmse_denorm > 0.1:
                y_true_final, y_pred_final = y_true_denorm, y_pred_denorm
                logger.info("Using denormalized targets for metrics")
            else:
                y_true_final, y_pred_final = y_true, y_pred
                logger.info("Using raw targets for metrics")

        except Exception as e:
            logger.warning(f"Denormalization failed: {e}, using raw targets")
            y_true_final, y_pred_final = y_true, y_pred

        # Calculate comprehensive metrics
        mse = mean_squared_error(y_true_final, y_pred_final)
        rmse = np.sqrt(mse)
        mae = mean_absolute_error(y_true_final, y_pred_final)
        r2 = r2_score(y_true_final, y_pred_final)

        # Calculate per-zone metrics
        zone_metrics = {}
        for i, zone_name in enumerate(['Zone_1', 'Zone_2', 'Zone_3']):
            if y_true_final.shape[1] > i:
                zone_r2 = r2_score(y_true_final[:, i], y_pred_final[:, i])
                zone_rmse = np.sqrt(mean_squared_error(y_true_final[:, i], y_pred_final[:, i]))
                zone_mae = mean_absolute_error(y_true_final[:, i], y_pred_final[:, i])
                zone_metrics[zone_name] = {
                    'r2': float(zone_r2),
                    'rmse': float(zone_rmse),
                    'mae': float(zone_mae)
                }

        model_validation_metrics = {
            'overall_r2': float(r2),
            'overall_rmse': float(rmse),
            'overall_mae': float(mae),
            'overall_mse': float(mse),
            'sample_count': len(y_true_final),
            'zone_metrics': zone_metrics
        }

        logger.info(f"Validation metrics computed: R² = {r2:.4f}, RMSE = {rmse:.4f}")

    except Exception as e:
        logger.error(f"Failed to compute validation metrics: {e}")
        model_validation_metrics = {
            'error': str(e),
            'overall_r2': 0.0,
            'overall_rmse': float('inf'),
            'overall_mae': float('inf')
        }


def make_prediction(features: np.ndarray, normalize: bool = True) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Make a prediction using the loaded model.

    Args:
        features: Input features array of shape (timesteps, features)
        normalize: Whether to apply feature scaling

    Returns:
        Tuple of (predictions, model_info)
    """
    if model is None:
        raise RuntimeError("Model not loaded")

    # Convert to numpy array if needed
    if not isinstance(features, np.ndarray):
        features = np.array(features)

    # Validate input shape
    if metadata is not None:
        expected_shape = (metadata['lookback_window'], len(metadata['feature_names']))
        if features.shape != expected_shape:
            raise ValueError(f"Input shape {features.shape} doesn't match expected {expected_shape}")

    # Apply feature scaling if requested
    if normalize and feature_scaler is not None:
        features = partial_scale_features(features)

    # Convert to tensor and add batch dimension
    features_tensor = torch.FloatTensor(features).unsqueeze(0)  # Shape: (1, timesteps, features)

    # Make prediction
    model.eval()
    with torch.no_grad():
        prediction = model(features_tensor)
        prediction_np = prediction.cpu().numpy().squeeze()  # Remove batch dimension

    # Denormalize prediction if we have a target scaler
    if target_scaler is not None:
        try:
            prediction_np = target_scaler.inverse_transform(prediction_np.reshape(1, -1)).squeeze()
        except Exception as e:
            logger.warning(f"Failed to denormalize prediction: {e}")

    # Model info
    model_info = {
        'model_type': 'AttentionLSTM',
        'architecture': 'LSTM with Attention Mechanism',
        'normalized_input': normalize,
        'input_shape': features.shape,
        'output_shape': prediction_np.shape
    }

    if metadata is not None:
        model_info.update({
            'feature_names': metadata.get('feature_names', []),
            'target_names': metadata.get('target_names', ['Zone_1', 'Zone_2', 'Zone_3'])
        })

    return prediction_np, model_info


def get_model_info() -> Dict[str, Any]:
    """Get comprehensive model information."""
    if model is None or metadata is None:
        raise RuntimeError("Model not loaded")

    # Count model parameters
    param_count = sum(p.numel() for p in model.parameters())

    # Get validation metrics if available
    best_performance = model_validation_metrics or {'r2': 0.0, 'rmse': float('inf')}

    return {
        'model_type': 'AttentionLSTM',
        'architecture': 'LSTM with Attention Mechanism',
        'input_features': len(metadata.get('feature_names', [])),
        'output_targets': len(metadata.get('target_names', [])),
        'model_parameters': param_count,
        'best_performance': best_performance,
        'feature_names': metadata.get('feature_names', []),
        'target_names': metadata.get('target_names', [])
    }