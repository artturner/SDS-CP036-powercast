"""
Test inference and scaling functionality.
"""

import pytest
import numpy as np
from unittest.mock import patch, MagicMock


def test_partial_scale_features():
    """Test the partial feature scaling function"""
    from app_core.inference import partial_scale_features

    # Test with no scaler
    with patch('app_core.inference.feature_scaler', None):
        arr = np.random.rand(10, 5)
        result = partial_scale_features(arr)
        np.testing.assert_array_equal(arr, result)


def test_make_prediction_validation():
    """Test prediction input validation"""
    from app_core.inference import make_prediction

    # Mock dependencies
    with patch('app_core.inference.model') as mock_model, \
         patch('app_core.inference.metadata') as mock_metadata, \
         patch('app_core.inference.feature_scaler') as mock_scaler, \
         patch('app_core.inference.target_scaler') as mock_target_scaler:

        # Setup mocks
        mock_model.eval.return_value = None
        mock_model.return_value = MagicMock()
        mock_model.return_value.cpu.return_value.numpy.return_value.squeeze.return_value = np.array([1.0, 2.0, 3.0])

        mock_metadata.get.side_effect = lambda key, default=None: {
            'lookback_window': 3,
            'feature_names': ['temp', 'humidity', 'wind'],
            'target_names': ['Zone_1', 'Zone_2', 'Zone_3']
        }.get(key, default)

        mock_scaler.transform.return_value = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
        mock_target_scaler.inverse_transform.return_value = np.array([10.0, 20.0, 30.0])

        # Test valid input
        features = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
        predictions, model_info = make_prediction(features, normalize=True)

        assert predictions is not None
        assert 'model_type' in model_info
        assert model_info['model_type'] == 'AttentionLSTM'


def test_get_model_info():
    """Test model info retrieval"""
    from app_core.inference import get_model_info

    # Mock dependencies
    with patch('app_core.inference.model') as mock_model, \
         patch('app_core.inference.metadata') as mock_metadata, \
         patch('app_core.inference.model_validation_metrics') as mock_metrics:

        # Setup mocks
        mock_model.parameters.return_value = [
            MagicMock(numel=lambda: 100),
            MagicMock(numel=lambda: 200)
        ]

        mock_metadata.get.side_effect = lambda key, default=None: {
            'feature_names': ['temp', 'humidity'],
            'target_names': ['Zone_1', 'Zone_2']
        }.get(key, default)

        mock_metrics.__bool__ = lambda x: True
        mock_metrics.__getitem__ = lambda x, key: {'r2': 0.95, 'rmse': 1.5}.get(key, 0)

        # Test model info retrieval
        info = get_model_info()

        assert info['model_type'] == 'AttentionLSTM'
        assert info['model_parameters'] == 300
        assert info['input_features'] == 2
        assert info['output_targets'] == 2


def test_load_model_error_handling():
    """Test error handling during model loading"""
    from app_core.inference import load_model_and_scalers

    # Test with missing model file
    with patch('app_core.inference.load_model_from_checkpoint') as mock_load:
        mock_load.side_effect = FileNotFoundError("Model file not found")

        with pytest.raises(FileNotFoundError):
            load_model_and_scalers()


def test_compute_validation_metrics_missing_files():
    """Test validation metrics computation with missing files"""
    from app_core.inference import compute_validation_metrics

    # Mock dependencies
    with patch('app_core.inference.model', MagicMock()), \
         patch('app_core.inference.feature_scaler', MagicMock()), \
         patch('app_core.inference.target_scaler', MagicMock()), \
         patch('app_core.inference.metadata', {}), \
         patch('os.path.exists', return_value=False):

        # Should not raise error when files are missing
        compute_validation_metrics()