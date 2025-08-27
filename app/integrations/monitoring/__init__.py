"""
vLLM FastAPI Monitoring Integration

This module provides comprehensive monitoring capabilities for vLLM FastAPI applications
including Prometheus metrics, logging configuration, and Docker-based monitoring stack.

Main Components:
- PrometheusConfig: Prometheus metrics configuration and setup
- WebSocketMetricsMiddleware: WebSocket connection monitoring
- Logging configuration for monitoring components
- Docker-based monitoring stack (Prometheus, Grafana, Alertmanager)

Example Usage:
    from app.integrations.monitoring import PrometheusConfig, setup_monitoring_logging
    
    # Setup logging
    logger = setup_monitoring_logging()
    
    # Configure Prometheus
    prometheus_config = PrometheusConfig(
        service_name="nemo-ai",
        version="2.0.0",
        environment="production"
    )
    
    # Initialize with FastAPI app
    prometheus_config.setup_instrumentator(app).expose_metrics(app)
"""

# Import main components
from .prometheus_config import (
    PrometheusConfig,
    WebSocketMetricsMiddleware,
    websocket_metrics,
    get_prometheus_config,
    track_health_check,
    update_queue_size,
    record_inference_time,
    validate_metrics
)

from .logging_config import (
    setup_monitoring_logging,
    log_metric_collection,
    log_monitoring_error
)

# Version information
__version__ = "2.0.0"
__author__ = "NEMO AI Team"

# Module metadata
__all__ = [
    # Prometheus components
    "PrometheusConfig",
    "WebSocketMetricsMiddleware", 
    "websocket_metrics",
    "get_prometheus_config",
    "track_health_check",
    "update_queue_size", 
    "record_inference_time",
    "validate_metrics",
    
    # Logging components
    "setup_monitoring_logging",
    "log_metric_collection",
    "log_monitoring_error",
    
    # Module info
    "__version__",
    "__author__"
]

# Initialize module logging
import logging
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

def get_monitoring_info():
    """
    Get information about the monitoring module configuration.
    
    Returns:
        dict: Module information including version, available components, etc.
    """
    return {
        "version": __version__,
        "author": __author__,
        "components": {
            "prometheus": "Metrics collection and exposition",
            "logging": "Monitoring-specific logging configuration", 
            "websocket": "WebSocket connection metrics",
            "docker": "Docker-based monitoring stack"
        },
        "services": {
            "prometheus": "http://localhost:9090",
            "grafana": "http://localhost:3000",
            "alertmanager": "http://localhost:9093",
            "metrics_endpoint": "http://localhost:8000/metrics"
        },
        "config_files": [
            "config/prometheus.yml",
            "config/prometheus-rules.yml", 
            "config/alertmanager.yml"
        ],
        "docker_files": [
            "docker/docker-compose.monitoring.yml",
            "docker/docker-compose.monitoring.prod.yml"
        ],
        "scripts": [
            "scripts/setup-monitoring.sh",
            "scripts/setup-monitoring.ps1",
            "run-monitoring.ps1"
        ]
    }

# Log module initialization
logger.info(f"NEMO AI Monitoring module v{__version__} initialized")
