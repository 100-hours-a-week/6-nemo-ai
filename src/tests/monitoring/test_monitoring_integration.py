import pytest
import requests
import time
from src.monitoring.prometheus_config import PrometheusConfig

def test_metrics_endpoint():
    """Test that metrics endpoint is accessible"""
    response = requests.get("http://localhost:8000/metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text

def test_prometheus_integration():
    """Test Prometheus integration"""
    # Make a request to generate metrics
    response = requests.get("http://localhost:8000/health")
    assert response.status_code == 200
    
    # Check metrics endpoint
    metrics_response = requests.get("http://localhost:8000/metrics")
    assert "health_check_requests_total" in metrics_response.text

def test_custom_metrics():
    """Test custom vLLM metrics are present"""
    response = requests.get("http://localhost:8000/metrics")
    metrics_text = response.text
    
    # Check for custom metrics
    assert "vllm_requests_total" in metrics_text
    assert "system_memory_usage_percent" in metrics_text
    assert "system_cpu_usage_percent" in metrics_text

@pytest.mark.integration
def test_monitoring_stack():
    """Test full monitoring stack integration"""
    # Check Prometheus
    try:
        prom_response = requests.get("http://localhost:9090/api/v1/query?query=up")
        assert prom_response.status_code == 200
    except requests.ConnectionError:
        pytest.skip("Prometheus not running")
    
    # Check Grafana
    try:
        grafana_response = requests.get("http://localhost:3000/api/health")
        assert grafana_response.status_code == 200
    except requests.ConnectionError:
        pytest.skip("Grafana not running")
