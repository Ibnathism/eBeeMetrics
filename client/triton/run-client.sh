#!/bin/bash
set -euo pipefail

# Usage:
#   ./run_client.sh triton-http
#   ./run_client.sh triton-grpc "1 2 4 6 8 10 12"
#
# Arg1: benchmark name (required)  -> expects corresponding python file: <benchmark>.py
# Arg2: optional space-separated RPS list

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <benchmark_name> [\"rps_values...\"]"
  echo "Example: $0 triton-http"
  echo "Example: $0 triton-grpc \"1 2 4 6 8 10 12\""
  exit 1
fi

BENCHMARK_NAME="$1"
BENCHMARK_PY="${BENCHMARK_NAME}.py"

if [[ $# -ge 2 ]]; then
  read -r -a RPS_VALUES <<< "$2"
else
  RPS_VALUES=(1 2 4 6 8 10 12 14)
fi

DURATION=30
HOST=localhost

# Port selection based on benchmark
if [[ "$BENCHMARK_NAME" == "triton-http" ]]; then
  PORT=8000
elif [[ "$BENCHMARK_NAME" == "triton-grpc" ]] || [[ "$BENCHMARK_NAME" == *grpc* ]]; then
  PORT=8001
else
  echo "[ERROR] Unknown benchmark '$BENCHMARK_NAME' for port selection."
  echo "Expected: triton-http or triton-grpc"
  exit 1
fi

OUTPUT_JSON="client_latencies/client_latencies_by_rps.json"

for RPS in "${RPS_VALUES[@]}"; do
  echo "======================================"
  echo "Running client '$BENCHMARK_NAME' at RPS = $RPS for $DURATION seconds (PORT=$PORT)"
  echo "======================================"

  python3 "$BENCHMARK_PY" "$HOST" "$PORT" "$DURATION" "$RPS"

  echo "Finished RPS = $RPS"
  echo
  sleep 50
done

echo "All client runs completed."