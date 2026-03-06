#!/bin/bash
set -euo pipefail

OUTPUT_JSON_CLIENT="client_latencies/client_latencies_by_rps.json"
if [[ -f "$OUTPUT_JSON_CLIENT" ]]; then
    rm -f "$OUTPUT_JSON_CLIENT"
    echo "Deleted existing $OUTPUT_JSON_CLIENT"
fi
