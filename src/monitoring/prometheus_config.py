"""
Prometheus Configuration for vLLM FastAPI Monitoring

This module sets up comprehensive Prometheus monitoring with:
- Custom vLLM-specific metrics
- System resource monitoring  
- WebSocket connection tracking
- Health check monitoring
- GPU metrics (optional)

Usage:
    from src.monitoring.prometheus_config import PrometheusConfig
    
    prometheus_config = PrometheusConfig()
    prometheus_config.setup_instrumentator(app)
    prometheus_config.expose_metrics(app)
"""

import logging
import time
from typing import Optional

import psutil
from fastapi import FastAPI, Request
from prometheus_client import Counter, Histogram, Gauge, REGISTRY
from prometheus_fastapi_instrumentator import Instrumentator

# Optional GPU monitoring
try:
    import GPUtil
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False

# ============================================================================
# CUSTOM METRICS DEFINITIONS
# ============================================================================

# vLLM-specific metrics
vllm_requests_total = Counter(
    name='vllm_requests_total',
    documentation='Total number of requests to vLLM endpoints',
    labelnames=['endpoint', 'method', 'status', 'model']
)

vllm_inference_duration = Histogram(
    name='vllm_inference_duration_seconds',
    documentation='Time spent on vLLM inference operations',
    labelnames=['model', 'endpoint', 'status'],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 25.0, 50.0, 100.0, float('inf'))
)

vllm_active_connections = Gauge(
    name='vllm_active_connections',
    documentation='Number of active WebSocket connections'
)

vllm_queue_size = Gauge(
    name='vllm_queue_size',
    documentation='Number of requests waiting in the vLLM queue'
)

# System resource metrics
system_memory_usage = Gauge(
    name='system_memory_usage_percent',
    documentation='System memory usage percentage'
)

system_cpu_usage = Gauge(
    name='system_cpu_usage_percent',
    documentation='System CPU usage percentage'
)

system_disk_usage = Gauge(
    name='system_disk_usage_percent',
    documentation='System disk usage percentage',
    labelnames=['device', 'mountpoint']
)

# GPU metrics (if available)
if GPU_AVAILABLE:
    gpu_memory_usage = Gauge(
        name='gpu_memory_usage_mb',
        documentation='GPU memory usage in MB',
        labelnames=['gpu_id', 'gpu_name', 'gpu_uuid']
    )
    
    gpu_utilization = Gauge(
        name='gpu_utilization_percent',
        documentation='GPU utilization percentage',
        labelnames=['gpu_id', 'gpu_name', 'gpu_uuid']
    )
    
    gpu_temperature = Gauge(
        name='gpu_temperature_celsius',
        documentation='GPU temperature in Celsius',
        labelnames=['gpu_id', 'gpu_name', 'gpu_uuid']
    )

# Application health metrics
health_check_counter = Counter(
    name='health_check_requests_total',
    documentation='Total health check requests',
    labelnames=['status', 'endpoint']
)

application_info = Gauge(
    name='application_info',
    documentation='Application information',
    labelnames=['version', 'environment', 'service_name']
)

# ============================================================================
# PROMETHEUS CONFIGURATION CLASS
# ============================================================================

class PrometheusConfig:
    """
    Main configuration class for Prometheus monitoring setup.
    
    This class handles:
    - FastAPI instrumentator setup
    - Custom metrics registration
    - System resource monitoring
    - GPU monitoring (if available)
    - Health check tracking
    """
    
    def __init__(self, service_name: str = "nemo-ai", version: str = "2.0.0", environment: str = "production"):
        """
        Initialize Prometheus configuration.
        
        Args:
            service_name: Name of the service being monitored
            version: Version of the application
            environment: Deployment environment (dev, staging, prod)
        """
        self.service_name = service_name
        self.version = version
        self.environment = environment
        self.instrumentator: Optional[Instrumentator] = None
        self.logger = logging.getLogger(__name__)
        
        # Set application info metric
        application_info.labels(
            version=self.version,
            environment=self.environment,
            service_name=self.service_name
        ).set(1)
        
        self.logger.info(f"Prometheus config initialized for {service_name} v{version} ({environment})")
    
    def setup_instrumentator(self, app: FastAPI) -> 'PrometheusConfig':
        """
        Set up the Prometheus instrumentator with custom configurations.
        
        Args:
            app: FastAPI application instance
            
        Returns:
            Self for method chaining
        """
        try:
            self.instrumentator = Instrumentator(
                should_group_status_codes=False,
                should_ignore_untemplated=True,
                should_respect_env_var=True,
                should_instrument_requests_inprogress=True,
                excluded_handlers=[
                    "/docs", "/redoc", "/openapi.json", 
                    "/favicon.ico", "/robots.txt", "/.well-known/"
                ],
                env_var_name="ENABLE_METRICS",
                inprogress_name="http_requests_inprogress",
                inprogress_labels=True,
            )
            
            # Instrument the FastAPI app
            self.instrumentator.instrument(app)
            
            # Add custom metric collectors
            self.instrumentator.add(self._track_vllm_requests())
            self.instrumentator.add(self._track_system_metrics())
            
            if GPU_AVAILABLE:
                self.instrumentator.add(self._track_gpu_metrics())
                self.logger.info("GPU monitoring enabled")
            else:
                self.logger.info("GPU monitoring disabled (GPUtil not available)")
            
            self.logger.info("FastAPI instrumentator configured successfully")
            return self
            
        except Exception as e:
            self.logger.error(f"Failed to setup instrumentator: {e}")
            raise
    
    def expose_metrics(self, app: FastAPI, endpoint: str = "/metrics") -> None:
        """
        Expose the metrics endpoint.
        
        Args:
            app: FastAPI application instance
            endpoint: URL path for metrics endpoint
        """
        try:
            if not self.instrumentator:
                raise ValueError("Instrumentator not initialized. Call setup_instrumentator() first.")
            
            self.instrumentator.expose(app, endpoint=endpoint)
            self.logger.info(f"Prometheus metrics exposed at {endpoint}")
            
        except Exception as e:
            self.logger.error(f"Failed to expose metrics endpoint: {e}")
            raise
    
    def _track_vllm_requests(self):
        """Custom metric collector for vLLM-specific requests."""
        def instrumentation(info):
            try:
                request_path = info.request.url.path
                
                # Track vLLM/AI-specific endpoints
                if any(pattern in request_path for pattern in ['/ai/', '/chatbot', '/vector_db', '/generate']):
                    # Extract model name from request if available
                    model_name = getattr(info.request.state, 'model_name', 'unknown')
                    
                    vllm_requests_total.labels(
                        endpoint=request_path,
                        method=info.request.method,
                        status=str(info.response.status_code),
                        model=model_name
                    ).inc()
                    
                    # Track inference duration for specific endpoints
                    if any(endpoint in request_path for endpoint in ['/chatbot', '/generate']):
                        duration = info.modified_duration
                        vllm_inference_duration.labels(
                            model=model_name,
                            endpoint=request_path,
                            status=str(info.response.status_code)
                        ).observe(duration)
                
            except Exception as e:
                self.logger.error(f"Error in vLLM request tracking: {e}")
        
        return instrumentation
    
    def _track_system_metrics(self):
        """Custom metric collector for system resource usage."""
        def instrumentation(info):
            try:
                # Update system metrics periodically (not on every request)
                current_time = time.time()
                if not hasattr(self, '_last_system_update'):
                    self._last_system_update = 0
                
                # Update system metrics every 5 seconds
                if current_time - self._last_system_update > 5:
                    # Memory usage
                    memory = psutil.virtual_memory()
                    system_memory_usage.set(memory.percent)
                    
                    # CPU usage (non-blocking)
                    cpu_percent = psutil.cpu_percent(interval=None)
                    system_cpu_usage.set(cpu_percent)
                    
                    # Disk usage for main partitions
                    try:
                        disk_partitions = psutil.disk_partitions()
                        for partition in disk_partitions[:3]:  # Limit to first 3 partitions
                            try:
                                disk_usage = psutil.disk_usage(partition.mountpoint)
                                system_disk_usage.labels(
                                    device=partition.device,
                                    mountpoint=partition.mountpoint
                                ).set(disk_usage.percent)
                            except (PermissionError, OSError):
                                continue
                    except Exception:
                        pass  # Skip disk monitoring if it fails
                    
                    self._last_system_update = current_time
                    
            except Exception as e:
                self.logger.error(f"Error in system metrics tracking: {e}")
        
        return instrumentation
    
    def _track_gpu_metrics(self):
        """Custom metric collector for GPU metrics (if available)."""
        def instrumentation(info):
            try:
                current_time = time.time()
                if not hasattr(self, '_last_gpu_update'):
                    self._last_gpu_update = 0
                
                # Update GPU metrics every 10 seconds
                if current_time - self._last_gpu_update > 10:
                    gpus = GPUtil.getGPUs()
                    for gpu in gpus:
                        labels = {
                            'gpu_id': str(gpu.id),
                            'gpu_name': gpu.name,
                            'gpu_uuid': gpu.uuid
                        }
                        
                        gpu_memory_usage.labels(**labels).set(gpu.memoryUsed)
                        gpu_utilization.labels(**labels).set(gpu.load * 100)
                        gpu_temperature.labels(**labels).set(gpu.temperature)
                    
                    self._last_gpu_update = current_time
                    
            except Exception as e:
                self.logger.error(f"Error in GPU metrics tracking: {e}")
        
        return instrumentation


# ============================================================================
# WEBSOCKET METRICS MIDDLEWARE
# ============================================================================

class WebSocketMetricsMiddleware:
    """
    Middleware for tracking WebSocket connection metrics.
    
    Usage:
        websocket_metrics = WebSocketMetricsMiddleware()
        
        @app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            websocket_metrics.connect()
            try:
                # ... websocket logic
            finally:
                websocket_metrics.disconnect()
    """
    
    def __init__(self):
        self.active_connections = 0
        self.total_connections = 0
        self.logger = logging.getLogger(f"{__name__}.websocket")
    
    def connect(self):
        """Record a new WebSocket connection."""
        self.active_connections += 1
        self.total_connections += 1
        vllm_active_connections.set(self.active_connections)
        self.logger.debug(f"WebSocket connected. Active: {self.active_connections}")
    
    def disconnect(self):
        """Record a WebSocket disconnection."""
        self.active_connections = max(0, self.active_connections - 1)
        vllm_active_connections.set(self.active_connections)
        self.logger.debug(f"WebSocket disconnected. Active: {self.active_connections}")
    
    def get_stats(self) -> dict:
        """Get current WebSocket statistics."""
        return {
            'active_connections': self.active_connections,
            'total_connections': self.total_connections
        }


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def track_health_check(status: str, endpoint: str = "/health") -> None:
    """
    Track health check requests.
    
    Args:
        status: Status of the health check ('success' or 'failure')
        endpoint: Health check endpoint path
    """
    health_check_counter.labels(status=status, endpoint=endpoint).inc()


def update_queue_size(size: int) -> None:
    """
    Update the vLLM queue size metric.
    
    Args:
        size: Current number of requests in queue
    """
    vllm_queue_size.set(size)


def record_inference_time(duration: float, model: str, endpoint: str, status: str = "200") -> None:
    """
    Manually record an inference duration.
    
    Args:
        duration: Duration in seconds
        model: Model name used for inference
        endpoint: API endpoint
        status: HTTP status code
    """
    vllm_inference_duration.labels(
        model=model,
        endpoint=endpoint,
        status=status
    ).observe(duration)


# Global instance for easy import
websocket_metrics = WebSocketMetricsMiddleware()

# ============================================================================
# MODULE INITIALIZATION
# ============================================================================

def get_prometheus_config(**kwargs) -> PrometheusConfig:
    """
    Factory function to create a PrometheusConfig instance.
    
    Args:
        **kwargs: Arguments to pass to PrometheusConfig constructor
        
    Returns:
        Configured PrometheusConfig instance
    """
    return PrometheusConfig(**kwargs)


# Validate that all metrics are properly registered
def validate_metrics():
    """Validate that all custom metrics are properly registered."""
    try:
        # Try to collect all metrics to ensure they're valid
        from prometheus_client import generate_latest
        generate_latest(REGISTRY)
        return True
    except Exception as e:
        logging.getLogger(__name__).error(f"Metrics validation failed: {e}")
        return False


# Initialize logging for this module
logging.getLogger(__name__).addHandler(logging.NullHandler())
