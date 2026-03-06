#!/bin/bash
set -euo pipefail

OUTPUT_JSON="latencies/server_latencies_by_rps.json"
# Delete old JSON if it exists
if [[ -f "$OUTPUT_JSON" ]]; then
    rm -f "$OUTPUT_JSON"
    echo "Deleted existing $OUTPUT_JSON"
fi

OUTPUT_JSON_CLIENT="latencies/client_latencies_by_rps.json"
if [[ -f "$OUTPUT_JSON_CLIENT" ]]; then
    rm -f "$OUTPUT_JSON_CLIENT"
    echo "Deleted existing $OUTPUT_JSON_CLIENT"
fi

LATENCY_PLOT="latencies/latency_comparison.png"
if [[ -f "$LATENCY_PLOT" ]]; then
    rm -f "$LATENCY_PLOT"
    echo "Deleted existing $LATENCY_PLOT"
fi

THROUGHPUT_PLOT="latencies/throughput_comparison.png"
if [[ -f "$THROUGHPUT_PLOT" ]]; then
    rm -f "$THROUGHPUT_PLOT"
    echo "Deleted existing $THROUGHPUT_PLOT"
fi

CONTAINER="triton-client"
WORKDIR="/workspace/client/src/python/examples/eBeeMetrics"
SCRIPT="./setup-client.sh"

docker exec -it "$CONTAINER" /bin/bash -lc "
  set -euo pipefail
  cd '$WORKDIR'
  $SCRIPT
"
