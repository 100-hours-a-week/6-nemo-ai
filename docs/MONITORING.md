# 📊 vLLM FastAPI Monitoring Guide

A comprehensive monitoring solution for vLLM FastAPI applications using Prometheus and Grafana.

## 🚀 Quick Start

```bash
# 1. Start monitoring stack (from project root)
./start-monitoring.sh

# OR from monitoring directory
cd monitoring
./setup-monitoring.sh

# 2. Access services
open http://localhost:3000  # Grafana (admin/nemo_secure_2024)
open http://localhost:9090  # Prometheus
open http://localhost:8000/metrics  # Your app metrics
```

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │────│   Prometheus    │────│     Grafana     │
│  (Port 8000)    │    │  (Port 9090)    │    │  (Port 3000)    │
│   /metrics      │    │                 │    │   Dashboards    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                       ┌─────────────────┐    ┌─────────────────┐
                       │  Alertmanager   │    │  Node Exporter  │
                       │  (Port 9093)    │    │  (Port 9100)    │
                       │  Notifications  │    │ System Metrics  │
                       └─────────────────┘    └─────────────────┘
```

## 📊 Available Metrics

### vLLM Application Metrics
- `vllm_requests_total` - Total requests to vLLM endpoints
- `vllm_inference_duration_seconds` - Inference time distribution
- `vllm_active_connections` - Active WebSocket connections
- `vllm_queue_size` - Requests waiting in queue

### System Metrics
- `system_memory_usage_percent` - Memory usage percentage
- `system_cpu_usage_percent` - CPU usage percentage
- `system_disk_usage_percent` - Disk usage by device

### Health Metrics
- `health_check_requests_total` - Health check request counts
- `application_info` - Application version and environment info

## 📈 Dashboard Features

The included Grafana dashboard provides:
- **Real-time request rates** with method and endpoint breakdown
- **Response time percentiles** (50th, 95th, 99th)
- **System resource monitoring** (CPU, memory, disk)
- **Error rate tracking** with threshold alerting
- **WebSocket connection monitoring**
- **vLLM inference performance** over time

## 🚨 Alert Configuration

### Pre-configured Alerts
- **ServiceDown** - Service unavailable for 1+ minutes
- **HighErrorRate** - Error rate > 10% for 3+ minutes
- **VerySlowInference** - 95th percentile > 30s for 2+ minutes
- **HighMemoryUsage** - Memory > 85% for 5+ minutes
- **HighCPUUsage** - CPU > 80% for 5+ minutes

### Notification Channels
Alerts are sent via Discord webhooks by default. Configure additional channels in `monitoring/alertmanager.yml`.

## ⚙️ Setup Options

### Basic Setup
```bash
# From project root
./start-monitoring.sh

# OR from monitoring directory
cd monitoring && ./setup-monitoring.sh
```

### Production Setup
```bash
cd monitoring
./setup-monitoring.sh --production --alerting
```

### GPU Monitoring
```bash
cd monitoring
./setup-monitoring.sh --gpu
```

### Management Commands
```bash
cd monitoring
./setup-monitoring.sh --status    # Check service status
./setup-monitoring.sh --stop      # Stop all services
./setup-monitoring.sh --logs      # View service logs
```

## 🔧 Configuration Files

### Core Files
- `monitoring/prometheus.yml` - Metrics collection configuration
- `monitoring/docker-compose.monitoring.yml` - Service definitions
- `monitoring/prometheus-rules.yml` - Alert rules
- `monitoring/alertmanager.yml` - Notification routing
- `monitoring/grafana-provisioning/` - Dashboard auto-configuration

### Environment Variables (.env)
```bash
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=secure_password
PROMETHEUS_RETENTION_TIME=15d
ENABLE_METRICS=true
ALERT_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

## 🐛 Troubleshooting

### Common Issues

**Metrics Not Appearing:**
1. Check FastAPI health: `curl http://localhost:8000/health`
2. Verify metrics endpoint: `curl http://localhost:8000/metrics`
3. Check Prometheus targets: http://localhost:9090/targets

**Grafana Issues:**
1. Verify Prometheus data source connection
2. Re-import dashboard if panels are empty
3. Check query syntax in dashboard panels

**Alert Issues:**
1. Verify Alertmanager: http://localhost:9093
2. Test webhook URL manually
3. Check alert rules in Prometheus UI

### Service Logs
```bash
# View all service logs (from monitoring directory)
cd monitoring && ./setup-monitoring.sh --logs

# Individual service logs
docker logs nemo-prometheus
docker logs nemo-grafana
docker logs nemo-alertmanager
```

## 🔒 Production Deployment

### Security Hardening
1. **Enable production mode**: `cd monitoring && ./setup-monitoring.sh --production`
2. **Change default passwords**
3. **Set up HTTPS/TLS**
4. **Configure firewall rules**
5. **Enable authentication for Grafana**

### Backup Strategy
```bash
# Backup Prometheus data
tar -czf prometheus-backup-$(date +%Y%m%d).tar.gz monitoring/prometheus-data/

# Backup Grafana dashboards
tar -czf grafana-backup-$(date +%Y%m%d).tar.gz monitoring/grafana-data/
```

## 📚 Useful Queries

**Top Slowest Endpoints:**
```promql
topk(10, histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))) by (handler)
```

**Request Rate by Method:**
```promql
rate(http_requests_total[5m]) by (method)
```

**Memory Usage Trend:**
```promql
system_memory_usage_percent
```

**Active WebSocket Connections:**
```promql
vllm_active_connections
```

## 🎯 Performance Impact

The monitoring setup has minimal performance impact:
- **Metrics collection**: ~1-2ms per request
- **Memory overhead**: ~50MB for monitoring stack
- **Storage**: ~1GB per month for typical usage
- **CPU usage**: <1% additional load

## 📞 Support

For issues:
1. Check troubleshooting section above
2. Review logs: `cd monitoring && ./setup-monitoring.sh --logs`
3. Verify service status: `cd monitoring && ./setup-monitoring.sh --status`
4. Consult configuration files for customization

**Happy Monitoring! 📊🚀**
