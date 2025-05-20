# Deployment Instructions

Follow these steps to apply the Prometheus metrics changes:

## 1. Install Required Dependencies

The Prometheus client library needs to be installed:

```powershell
# Navigate to your project directory
cd c:\Users\csquire\Documents\ai\presidio-fastapi

# If using pip:
pip install prometheus-client>=0.17.1

# If using uv:
uv pip install prometheus-client>=0.17.1
```

## 2. Apply Code Changes

The following files have been updated or created:
- `presidio_fastapi/app/prometheus.py` (new)
- `presidio_fastapi/app/main.py` (updated)
- `presidio_fastapi/app/api/routes.py` (updated)
- `presidio_fastapi/app/services/analyzer.py` (updated)
- `pyproject.toml` (updated dependencies)
- `docs/prometheus-metrics.md` (new documentation)

## 3. Configure Metrics Collection (Optional)

By default, metrics are only collected for the `/analyze` and `/analyze/batch` endpoints. You can customize which endpoints are monitored by setting the `PROMETHEUS_MONITORED_PATHS` environment variable:

```powershell
# Example: Only monitor the analyze endpoint
$env:PROMETHEUS_MONITORED_PATHS = "analyze"

# Example: Monitor more endpoints
$env:PROMETHEUS_MONITORED_PATHS = "analyze,analyze/batch,health,status"
```

You can also set this permanently in your environment variables or deployment configuration.

## 4. Restart the Service

```powershell
# Kill any existing running service (if needed)
# If you're running it as a background process, you might need to find and kill it:
# Get-Process -Name python | Where-Object {$_.CommandLine -like "*uvicorn*"} | Stop-Process

# Start the service
cd c:\Users\csquire\Documents\ai\presidio-fastapi
uvicorn presidio_fastapi.app.main:app --reload --host 0.0.0.0 --port 8000
```

## 4. Verify the Changes

1. Verify the Prometheus metrics endpoint:
   - Navigate to `http://localhost:8000/api/v1/metrics` in your browser
   - You should see metrics in Prometheus format (plain text)

2. Test PII detection with metrics tracking:
   - Make a request to the analyze endpoint:
     ```powershell
     $headers = @{
         "Content-Type" = "application/json"
     }
     $body = @{
         text = "My name is John Doe and my email is john@example.com"
         language = "en"
     } | ConvertTo-Json
     
     Invoke-RestMethod -Uri "http://localhost:8000/api/v1/analyze" -Method Post -Headers $headers -Body $body
     ```

3. Check the updated metrics:
   - Refresh `http://localhost:8000/api/v1/metrics` to see the PII entity counts

## 5. Configure Prometheus (if applicable)

If you have Prometheus running, update its configuration to scrape the metrics. See `docs/prometheus-metrics.md` for detailed instructions.

## 6. Troubleshooting

If you experience any issues:

1. Check the server logs for errors
2. Ensure all dependencies are correctly installed
3. Verify that the `/api/v1/metrics` endpoint is accessible and returns content with the correct format
4. If using Prometheus, verify that it can scrape the endpoint correctly (check Prometheus logs)

For more details on the metrics available and Prometheus configuration, see `docs/prometheus-metrics.md`.
