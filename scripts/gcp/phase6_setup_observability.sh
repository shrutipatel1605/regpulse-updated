#!/usr/bin/env bash
# RegPulse GCP Phase 6 — Setup Observability
set -uo pipefail

echo "==> Creating Log-based Metrics for Scraper"
gcloud logging metrics create regpulse_scraper_documents \
  --description="Documents processed by scraper" \
  --log-filter='resource.type="cloud_run_job" AND resource.labels.job_name="regpulse-scraper" AND jsonPayload.event="process_document_started"' || true

gcloud logging metrics create regpulse_scraper_errors \
  --description="Scraper execution errors" \
  --log-filter='resource.type="cloud_run_job" AND resource.labels.job_name="regpulse-scraper" AND severity>=ERROR' || true

gcloud logging metrics create regpulse_scraper_success \
  --description="Scraper job completed successfully" \
  --log-filter='resource.type="cloud_run_job" AND resource.labels.job_name="regpulse-scraper" AND jsonPayload.event="daily_scrape_completed"' || true

echo "==> Creating Dashboard Configuration"
cat << 'EOF' > /tmp/scraper_dashboard.json
{
  "displayName": "RegPulse Scraper Observability",
  "mosaicLayout": {
    "columns": 12,
    "tiles": [
      {
        "widget": {
          "title": "Scraper Errors",
          "xyChart": {
            "chartOptions": {"mode": "COLOR"},
            "dataSets": [{
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "metric.type=\"logging.googleapis.com/user/regpulse_scraper_errors\"",
                  "aggregation": {
                    "perSeriesAligner": "ALIGN_RATE",
                    "crossSeriesReducer": "REDUCE_SUM",
                    "alignmentPeriod": "60s"
                  }
                }
              }
            }]
          }
        },
        "yPos": 0, "xPos": 0, "width": 6, "height": 4
      },
      {
        "widget": {
          "title": "Documents Processed",
          "xyChart": {
            "chartOptions": {"mode": "COLOR"},
            "dataSets": [{
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "metric.type=\"logging.googleapis.com/user/regpulse_scraper_documents\"",
                  "aggregation": {
                    "perSeriesAligner": "ALIGN_RATE",
                    "crossSeriesReducer": "REDUCE_SUM",
                    "alignmentPeriod": "60s"
                  }
                }
              }
            }]
          }
        },
        "yPos": 0, "xPos": 6, "width": 6, "height": 4
      }
    ]
  }
}
EOF

echo "==> Deploying Dashboard"
gcloud monitoring dashboards create --config-from-file=/tmp/scraper_dashboard.json

echo "==> Observability setup complete!"
