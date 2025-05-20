# Prometheus Metrics Integration

Prometheus metrics are now available for monitoring the Presidio FastAPI service. This document provides information on how to use them.

## Available Metrics

The following metrics are available:

- **http_requests_total**: Total number of HTTP requests processed (labeled by method, endpoint, status_code)
- **http_request_duration_seconds**: Duration of HTTP requests in seconds (labeled by method, endpoint)
- **http_errors_total**: Total number of HTTP errors (labeled by method, endpoint, status_code)
- **http_active_requests**: Number of currently active HTTP requests (labeled by method, endpoint)
- **presidio_pii_entities_detected_total**: Total number of PII entities detected (labeled by entity_type, language)

## Accessing Metrics

The metrics are available at the standard Prometheus metrics endpoint:

```
http://your-server:port/api/v1/metrics
```

Example with default settings:
```
http://localhost:8000/api/v1/metrics
```

This is the endpoint you should configure in your Prometheus scrape configuration.

## Configuring Prometheus

To configure Prometheus to scrape these metrics, add the following to your `prometheus.yml` configuration:

```yaml
scrape_configs:
  - job_name: 'presidio-fastapi'
    metrics_path: '/api/v1/metrics'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:8000']
```

## Prometheus Configuration Example

Here's a complete example of a Prometheus configuration for the service:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'presidio-fastapi'
    scrape_interval: 5s
    metrics_path: '/api/v1/metrics'
    static_configs:
      - targets: ['localhost:8000']
    # For secure deployments, you might need to add:
    # scheme: https
    # basic_auth:
    #   username: your_username
    #   password: your_password
```

## Grafana Dashboard

You can create a Grafana dashboard using these metrics to monitor:
- Request rates and durations
- Error rates and types
- PII entity detection statistics by type and language

## Important Notes

1. The metrics endpoint returns data in the Prometheus text-based format, which is required for Prometheus to correctly scrape the metrics.

2. To maintain accurate metrics, always use the `analyze_with_metrics` function from `presidio_fastapi.app.services.analyzer` instead of directly calling the Presidio analyzer's `analyze` method.

4. By default, metrics are only collected for specific endpoints (`/analyze` and `/analyze/batch`). This can be configured by setting the `PROMETHEUS_MONITORED_PATHS` environment variable to a comma-separated list of path suffixes to monitor.

## Configuration

### Configuring Monitored Paths

You can configure which paths are monitored for metrics collection by setting the `PROMETHEUS_MONITORED_PATHS` environment variable. This is a comma-separated list of path suffixes.

Default value: `analyze,analyze/batch`

Example of monitoring only the analyze endpoint:

```bash
export PROMETHEUS_MONITORED_PATHS="analyze"
```

Example of monitoring additional endpoints:

```bash
export PROMETHEUS_MONITORED_PATHS="analyze,analyze/batch,health,status"
```

You can also set this in your configuration file or directly in the code.
