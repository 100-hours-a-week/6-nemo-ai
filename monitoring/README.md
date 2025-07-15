# 📊 Monitoring Directory

This directory contains all monitoring-related files for the vLLM FastAPI application.

## 📁 File Structure

```
📦 monitoring/
├── 🚀 setup-monitoring.sh              # Main setup script
├── 🐳 docker-compose.monitoring.yml    # Docker services (development)
├── 🔒 docker-compose.monitoring.prod.yml # Docker services (production)
├── 📊 prometheus.yml                   # Prometheus configuration
├── 🚨 prometheus-rules.yml             # Alert rules
├── 📬 alertmanager.yml                 # Notification configuration
├── 🔐 grafana-security.env             # Security settings
├── 📈 grafana-provisioning/            # Auto-configuration
│   ├── 🔌 datasources/
│   │   └── prometheus.yml              # Prometheus datasource
│   └── 📊 dashboards/
│       ├── dashboards.yml              # Dashboard provisioning
│       └── vllm-dashboard.json         # Main monitoring dashboard
├── 📁 Data Directories (created automatically):
│   ├── prometheus-data/                # Prometheus time-series data
│   ├── grafana-data/                   # Grafana settings & dashboards
│   ├── alertmanager-data/              # Alertmanager data
│   └── backups/                        # Automated backups
└── 📚 README.md                        # This file
```

## 🚀 Quick Start

```bash
# Basic setup
./setup-monitoring.sh

# Production setup with alerts
./setup-monitoring.sh --production --alerting

# GPU monitoring (if you have NVIDIA GPUs)
./setup-monitoring.sh --gpu

# Check status
./setup-monitoring.sh --status

# View logs
./setup-monitoring.sh --logs

# Stop all services
./setup-monitoring.sh --stop
```

## 🌐 Service URLs

After setup, access these services:
- **Grafana**: http://localhost:3000 (admin/nemo_secure_2024)
- **Prometheus**: http://localhost:9090
- **Alertmanager**: http://localhost:9093
- **FastAPI Metrics**: http://localhost:8000/metrics

## 📚 Documentation

For detailed documentation, see: `../docs/MONITORING.md`

## 🔧 Configuration

All configuration files are in this directory:
- Modify `prometheus.yml` for scrape configurations
- Edit `prometheus-rules.yml` for custom alerts
- Update `alertmanager.yml` for notification channels
- Customize `grafana-provisioning/` for dashboard auto-import

## 🔒 Security

For production deployments:
1. Use `--production` flag for enhanced security
2. Change default passwords in `.env` file
3. Set up HTTPS with reverse proxy
4. Review `security-checklist.md` for complete hardening

## 📞 Support

If you encounter issues:
1. Run `./setup-monitoring.sh --status` to check service health
2. Run `./setup-monitoring.sh --logs` to view detailed logs
3. Check the troubleshooting section in `../docs/MONITORING.md`
