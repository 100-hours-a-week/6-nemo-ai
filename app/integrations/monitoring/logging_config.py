import logging
import sys
from pathlib import Path
from datetime import datetime

def setup_monitoring_logging():
    """Configure logging for monitoring components"""
    
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configure formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler for monitoring logs
    file_handler = logging.FileHandler(
        log_dir / f"monitoring_{datetime.now().strftime('%Y%m%d')}.log"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    
    # Configure monitoring logger
    monitoring_logger = logging.getLogger("monitoring")
    monitoring_logger.setLevel(logging.INFO)
    monitoring_logger.addHandler(file_handler)
    monitoring_logger.addHandler(console_handler)
    
    # Configure prometheus logger
    prometheus_logger = logging.getLogger("prometheus_client")
    prometheus_logger.setLevel(logging.WARNING)
    
    return monitoring_logger

def log_metric_collection(metric_name: str, value: float, labels: dict = None):
    """Log metric collection for debugging"""
    logger = logging.getLogger("monitoring")
    labels_str = f" with labels {labels}" if labels else ""
    logger.debug(f"Collected metric {metric_name}: {value}{labels_str}")

def log_monitoring_error(error: Exception, context: str = ""):
    """Log monitoring-related errors"""
    logger = logging.getLogger("monitoring")
    context_str = f" in {context}" if context else ""
    logger.error(f"Monitoring error{context_str}: {str(error)}", exc_info=True)
