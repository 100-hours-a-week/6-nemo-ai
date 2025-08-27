import logging
import sys
from pathlib import Path
from datetime import datetime
from app.core.ai_logger import AIFormatter, get_ai_logger

def setup_monitoring_logging():
    """Configure logging for monitoring components using AI logger format"""
    
    # Create logs directory
    log_dir = Path("app/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Use AI formatter for consistency
    formatter = AIFormatter()
    
    # File handler for monitoring logs
    file_handler = logging.FileHandler(
        log_dir / f"monitoring_{datetime.now().strftime('%Y%m%d')}.log"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    
    # Console handler with AI format
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    
    # Configure monitoring logger to use AI format
    monitoring_logger = logging.getLogger("monitoring")
    monitoring_logger.handlers.clear()  # Clear any existing handlers
    monitoring_logger.setLevel(logging.INFO)
    monitoring_logger.addHandler(file_handler)
    monitoring_logger.addHandler(console_handler)
    monitoring_logger.propagate = False
    
    # Configure prometheus logger
    prometheus_logger = logging.getLogger("prometheus_client")
    prometheus_logger.setLevel(logging.WARNING)
    
    return monitoring_logger

def log_metric_collection(metric_name: str, value: float, labels: dict = None):
    """Log metric collection for debugging using AI format"""
    ai_logger = get_ai_logger()
    labels_str = f" with labels {labels}" if labels else ""
    ai_logger.debug(f"Collected metric {metric_name}: {value}{labels_str}")

def log_monitoring_error(error: Exception, context: str = ""):
    """Log monitoring-related errors using AI format"""
    ai_logger = get_ai_logger()
    context_str = f" in {context}" if context else ""
    ai_logger.error(f"Monitoring error{context_str}: {str(error)}", exc_info=True)
