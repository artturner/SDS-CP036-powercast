"""
Visualization helpers for creating charts and plots.
"""

import logging
from typing import List, Dict, Any
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

def create_time_series_plot(data: List[List[float]], feature_names: List[str]) -> str:
    """Create a time series plot HTML for input data visualization.

    Args:
        data: Time series data as list of feature vectors
        feature_names: Names of the features

    Returns:
        HTML string containing the plot
    """
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots

        if not data or not feature_names:
            return "<div style='text-align: center; padding: 50px;'>No data to display</div>"

        # Convert to DataFrame for easier handling
        df = pd.DataFrame(data, columns=feature_names[:len(data[0])])

        # Create subplots for different feature groups
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Environmental', 'Occupancy & Efficiency', 'Temporal Features', 'Day Type'),
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}]]
        )

        # Environmental features (Temperature, Humidity, Wind Speed)
        env_features = ['Temperature', 'Humidity', 'Wind_Speed']
        for feature in env_features:
            if feature in df.columns:
                fig.add_trace(
                    go.Scatter(x=df.index, y=df[feature], name=feature, line_width=2),
                    row=1, col=1
                )

        # Occupancy and efficiency
        occ_features = ['Occupancy', 'HVAC_Efficiency', 'Lighting_Efficiency']
        for feature in occ_features:
            if feature in df.columns:
                fig.add_trace(
                    go.Scatter(x=df.index, y=df[feature], name=feature, line_width=2),
                    row=1, col=2
                )

        # Temporal features
        temp_features = ['Seasonal_Factor', 'Time_Factor_sin', 'Time_Factor_cos']
        for feature in temp_features:
            if feature in df.columns:
                fig.add_trace(
                    go.Scatter(x=df.index, y=df[feature], name=feature, line_width=2),
                    row=2, col=1
                )

        # Day type features
        day_features = ['Is_Weekend', 'Is_Weekday']
        for feature in day_features:
            if feature in df.columns:
                fig.add_trace(
                    go.Scatter(x=df.index, y=df[feature], name=feature,
                              line_width=2, mode='lines+markers'),
                    row=2, col=2
                )

        fig.update_layout(
            height=600,
            title_text="Input Time Series Features",
            showlegend=True,
            template="plotly_white"
        )

        return fig.to_html(include_plotlyjs='cdn', div_id="time-series-plot")

    except Exception as e:
        logger.error(f"Time series plot creation failed: {str(e)}")
        return f"<div style='text-align: center; padding: 50px; color: red;'>Error creating time series plot: {str(e)}</div>"


def create_feature_distribution_plot(data: List[List[float]], feature_names: List[str]) -> str:
    """Create feature distribution plots.

    Args:
        data: Time series data as list of feature vectors
        feature_names: Names of the features

    Returns:
        HTML string containing the distribution plots
    """
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots

        if not data or not feature_names:
            return "<div style='text-align: center; padding: 50px;'>No data to display</div>"

        df = pd.DataFrame(data, columns=feature_names[:len(data[0])])

        # Create histograms for each feature
        n_features = len(df.columns)
        cols = 3
        rows = (n_features + cols - 1) // cols

        fig = make_subplots(
            rows=rows, cols=cols,
            subplot_titles=df.columns,
            specs=[[{"type": "xy"}] * cols for _ in range(rows)]
        )

        for i, feature in enumerate(df.columns):
            row = i // cols + 1
            col = i % cols + 1

            fig.add_trace(
                go.Histogram(x=df[feature], name=feature, nbinsx=20, showlegend=False),
                row=row, col=col
            )

        fig.update_layout(
            height=200 * rows,
            title_text="Feature Distributions",
            template="plotly_white"
        )

        return fig.to_html(include_plotlyjs='cdn', div_id="feature-dist-plot")

    except Exception as e:
        logger.error(f"Feature distribution plot creation failed: {str(e)}")
        return f"<div style='text-align: center; padding: 50px; color: red;'>Error creating distribution plot: {str(e)}</div>"


def create_correlation_heatmap(data: List[List[float]], feature_names: List[str]) -> str:
    """Create correlation heatmap for features.

    Args:
        data: Time series data as list of feature vectors
        feature_names: Names of the features

    Returns:
        HTML string containing the correlation heatmap
    """
    try:
        import plotly.graph_objects as go

        if not data or not feature_names:
            return "<div style='text-align: center; padding: 50px;'>No data to display</div>"

        df = pd.DataFrame(data, columns=feature_names[:len(data[0])])

        # Calculate correlation matrix
        corr_matrix = df.corr()

        # Create heatmap
        fig = go.Figure(data=go.Heatmap(
            z=corr_matrix.values,
            x=corr_matrix.columns,
            y=corr_matrix.columns,
            colorscale='RdBu',
            zmid=0,
            text=corr_matrix.round(2).values,
            texttemplate="%{text}",
            textfont={"size": 10},
            hoverongaps=False
        ))

        fig.update_layout(
            title="Feature Correlation Matrix",
            width=600,
            height=600,
            template="plotly_white"
        )

        return fig.to_html(include_plotlyjs='cdn', div_id="correlation-plot")

    except Exception as e:
        logger.error(f"Correlation heatmap creation failed: {str(e)}")
        return f"<div style='text-align: center; padding: 50px; color: red;'>Error creating correlation heatmap: {str(e)}</div>"


def create_prediction_gauge_charts(predictions: Dict[str, float]) -> str:
    """Create gauge charts for zone predictions.

    Args:
        predictions: Dictionary of zone predictions

    Returns:
        HTML string containing gauge charts
    """
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots

        zones = list(predictions.keys())
        values = list(predictions.values())

        if len(zones) != 3:
            # Fallback for different number of zones
            cols = min(len(zones), 3)
            rows = 1
        else:
            cols = 3
            rows = 1

        fig = make_subplots(
            rows=rows, cols=cols,
            specs=[[{"type": "indicator"}] * cols],
            subplot_titles=zones
        )

        # Determine appropriate ranges based on prediction values
        max_val = max(values) if values else 100
        gauge_max = max(100, max_val * 1.2)

        for i, (zone, value) in enumerate(predictions.items()):
            col = i + 1

            fig.add_trace(
                go.Indicator(
                    mode="gauge+number+delta",
                    value=value,
                    domain={'x': [0, 1], 'y': [0, 1]},
                    title={'text': f"{zone} (kW)"},
                    delta={'reference': gauge_max * 0.7},
                    gauge={
                        'axis': {'range': [None, gauge_max]},
                        'bar': {'color': "darkblue"},
                        'steps': [
                            {'range': [0, gauge_max * 0.5], 'color': "lightgray"},
                            {'range': [gauge_max * 0.5, gauge_max * 0.8], 'color': "gray"}
                        ],
                        'threshold': {
                            'line': {'color': "red", 'width': 4},
                            'thickness': 0.75,
                            'value': gauge_max * 0.9
                        }
                    }
                ),
                row=1, col=col
            )

        fig.update_layout(
            height=400,
            template="plotly_white",
            title_text="Power Consumption Predictions"
        )

        return fig.to_html(include_plotlyjs='cdn', div_id="prediction-gauges")

    except Exception as e:
        logger.error(f"Gauge chart creation failed: {str(e)}")
        return f"<div style='text-align: center; padding: 50px; color: red;'>Error creating gauge charts: {str(e)}</div>"