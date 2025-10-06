#!/bin/bash
set -euo pipefail

echo "--- Starting Automated Quality Gate ---"

# --- Configuration ---
# These values are passed from the GitHub Actions environment
GCP_PROJECT_ID="${GCP_PROJECT_ID:?GCP_PROJECT_ID is not set}"
GCP_REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-drawsguard-api-collector}"
OBSERVATION_WINDOW="180s" # 3 minutes

# --- Step 1: Identify Canary and Stable Revisions ---
echo "Fetching Cloud Run revision information..."

# Get the latest (Canary) revision which has 5% traffic
CANARY_REVISION=$(gcloud run services describe "$SERVICE_NAME" \
  --project="$GCP_PROJECT_ID" \
  --region="$GCP_REGION" \
  --format='json' | jq -r '.status.traffic[] | select(.percent == 5) | .revisionName')

# Get the stable revision which has 95% traffic
STABLE_REVISION=$(gcloud run services describe "$SERVICE_NAME" \
  --project="$GCP_PROJECT_ID" \
  --region="$GCP_REGION" \
  --format='json' | jq -r '.status.traffic[] | select(.percent == 95) | .revisionName')

if [[ -z "$CANARY_REVISION" || -z "$STABLE_REVISION" ]]; then
  echo "Error: Could not identify Canary or Stable revision. Halting."
  exit 1
fi

echo "Canary Revision: $CANARY_REVISION"
echo "Stable Revision: $STABLE_REVISION"

# --- Step 2: Query Metrics from Cloud Monitoring ---
echo "Waiting for observation window (${OBSERVATION_WINDOW}) to gather metrics..."
sleep "$OBSERVATION_WINDOW"

echo "Querying metrics from Cloud Monitoring..."

# Function to query a metric for a specific revision
query_metric() {
  local revision_name=$1
  local metric_type=$2
  local aggregator=$3
  
  gcloud monitoring query --project="$GCP_PROJECT_ID" --query="
    fetch cloud_run_revision
    | metric '$metric_type'
    | filter (resource.service_name == '$SERVICE_NAME' && resource.revision_name == '$revision_name')
    | group_by [], [$aggregator]
    | within $OBSERVATION_WINDOW
  " | jq -r '.timeSeriesData[0].pointData[0].values[0].doubleValue // 0'
}

# Query P95 Latency for both revisions
CANARY_LATENCY=$(query_metric "$CANARY_REVISION" "custom.googleapis.com/drawsguard/latency_ms" "aggregate(value.latency_ms, percentile(95))")
STABLE_LATENCY=$(query_metric "$STABLE_REVISION" "custom.googleapis.com/drawsguard/latency_ms" "aggregate(value.latency_ms, percentile(95))")

# Query Error Rate for Canary
CANARY_ERROR_COUNT=$(query_metric "$CANARY_REVISION" "custom.googleapis.com/drawsguard/errors_total" "aggregate(value.errors_total)")

echo "--- Metrics Report ---"
echo "Canary P95 Latency: ${CANARY_LATENCY} ms"
echo "Stable P95 Latency: ${STABLE_LATENCY} ms"
echo "Canary Error Count: ${CANARY_ERROR_COUNT}"
echo "----------------------"

# --- Step 3: Quality Gate Logic ---
echo "Evaluating quality gates..."

# Gate 1: Canary must have zero errors
if (( $(echo "$CANARY_ERROR_COUNT > 0" | bc -l) )); then
  echo "❌ FAILED: Canary version has reported errors ($CANARY_ERROR_COUNT)."
  exit 1
else
  echo "✅ PASSED: Canary has zero errors."
fi

# Gate 2: Canary latency should not exceed stable latency by more than 20%
# Adding a small number to stable latency to avoid division by zero
LATENCY_THRESHOLD=$(echo "($STABLE_LATENCY + 0.1) * 1.20" | bc -l)

if (( $(echo "$CANARY_LATENCY > $LATENCY_THRESHOLD" | bc -l) )); then
  echo "❌ FAILED: Canary P95 latency ($CANARY_LATENCY ms) exceeds threshold ($LATENCY_THRESHOLD ms)."
  exit 1
else
  echo "✅ PASSED: Canary latency is within acceptable limits."
fi

echo "--- Quality Gate Succeeded ---"
exit 0
