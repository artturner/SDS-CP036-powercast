from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict


class PredictionRequest(BaseModel):
    """Request model for predictions"""
    features: List[List[float]] = Field(
        ...,
        description="Time series features as a 2D array (timesteps x features)",
        example=[[25.5, 60.2, 3.1, 0.8, 0.6, 0.5, 0.87, -0.71, 0.71, 0.0, 1.0]] * 36,
    )
    normalize: bool = Field(
        True,
        description="Whether to normalize input features (should be True for production)",
    )
    echo_input: bool = Field(
        False,
        description="Whether to include input data in response (security: default False)",
    )


class PredictionResponse(BaseModel):
    """Response model for predictions"""
    model_config = ConfigDict(protected_namespaces=())

    predictions: List[float] = Field(..., description="Predicted power consumption for 3 zones")
    zone_predictions: Dict[str, float] = Field(..., description="Named zone predictions")
    model_info: Dict[str, Any] = Field(..., description="Model metadata")
    timestamp: str = Field(..., description="Prediction timestamp")
    input_data: Optional[List[List[float]]] = Field(
        None, description="Input features used for prediction"
    )
    input_summary: Optional[Dict[str, Any]] = Field(
        None, description="Summary statistics of input data"
    )


class ModelInfo(BaseModel):
    """Model information response"""
    model_config = ConfigDict(protected_namespaces=())

    model_type: str
    architecture: str
    input_features: int
    output_targets: int
    model_parameters: int
    best_performance: Dict[str, float]
    feature_names: List[str]
    target_names: List[str]


class HealthResponse(BaseModel):
    """Health check response"""
    model_config = ConfigDict(protected_namespaces=())

    status: str
    model_loaded: bool
    timestamp: str


class InputVisualization(BaseModel):
    """Input data visualization response"""
    input_data: List[List[float]] = Field(
        ..., description="The input time series data"
    )
    feature_names: List[str] = Field(..., description="Names of the features")
    time_series_plot: str = Field(..., description="HTML time series plot")
    feature_distribution_plot: str = Field(
        ..., description="HTML feature distribution plot"
    )
    correlation_plot: str = Field(..., description="HTML correlation heatmap plot")

