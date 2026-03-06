#!/bin/bash
set -euo pipefail

# Usage:
#   ./run-server.sh triton-http
#   ./run-server.sh triton-http "1 2 4 6 8 10 12"
#
# Arg1: benchmark name (required)
# Arg2: optional space-separated RPS list

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <benchmark_name> [\"rps_values...\"]"
  echo "Example: $0 triton-http"
  echo "Example: $0 triton-http \"1 2 4 6 8 10 12\""
  exit 1
fi

BENCHMARK="$1"

if [[ $# -ge 2 ]]; then
  # split the second arg by spaces into an array
  read -r -a RPS_VALUES <<< "$2"
else
  RPS_VALUES=(1 2 4 6 8 10 12 14)
fi

OUTPUT_JSON="latencies/server_latencies_by_rps.json"

for RPS in "${RPS_VALUES[@]}"; do
  echo "======================================"
  echo "Tracing benchmark '$BENCHMARK' at RPS = $RPS"
  echo "======================================"

  CURRENT_RPS="$RPS" python3 lib_for_latency.py \
    -b "$BENCHMARK" \
    --buffer_read

  echo "Finished RPS = $RPS"
  echo
  sleep 5
done

echo "All tracing experiments completed."