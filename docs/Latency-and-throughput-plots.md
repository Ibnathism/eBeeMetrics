# Running Latency and Throughput Comparison

Benchmark names:
1. triton-http
2. triton-grpc

This experiment 
- Collects **Client-reported latency** and **eBeeMetrics-reported latency** for each benchmark
- Plots the latency comparison plot
- Plots the throughput comparison plot with  R^2 value

The experiment sweeps RPS values for each benchmark:
`1, 2, 4, 6, 8, 10, 12, 14`

Each run lasts **30 seconds** per RPS.

---
## Step 1 - Setup library and client
```bash
# Navigate to the library folder
cd /home/test/eBeeMetrics/lib

# Setup the library
./setup-lib.sh
```
## Step 2 — Start eBeeMetrics and generate client-side load

```bash
# Navigate to the library folder
cd /home/test/eBeeMetrics/lib

# Run the server-side tracer
# <benchmark-name> will be either "triton-http" or "triton-grpc" for this experiment
sudo ./run-ebee.sh <benchmark-name>
```
Open another terminal:
```bash
# Enter the Triton client container:
docker exec -it triton-client /bin/bash

# Navigate to /workspace/client/src/python/examples/eBeeMetrics
cd /workspace/client/src/python/examples/eBeeMetrics

# Run the client load generator:
./run_client.sh <benchmark-name>
```
This will:
- Attach eBPF probes to the Triton container
- Sweep RPS values
- Store eBeeMetrics results in: `latencies/latencies_by_rps.json`
- Generate HTTP or gRPC load at different RPS values
- Store client-side latencies inside the container at: `client_latencies/client_latencies_by_rps.json`

## Step 3 - Running for both the benchmarks
Repeat step 2 for the other benchmark as well

## Step 4 — Copy Client Latency JSON to Host
After both server and client runs complete for each of the benchmark
```bash
# From a terminal outside the container, navigate to /home/test/eBeeMetrics/latencies
cd /home/test/eBeeMetrics/lib/latencies

# Copy the client latency file from the container:
docker cp triton-client:/workspace/client/src/python/examples/eBeeMetrics/client_latencies/client_latencies_by_rps.json .
```

## Step 5 — Generate Latency and Throughput Comparison Plots

```bash
# Go to the folder
cd /home/test/eBeeMetrics/lib/latencies

# Activate the virtual environment
source venv/bin/activate

# Generate the plot
python3 plot_latency_and_throughput.py
```
This will generate `latency_comparison_http_grpc.png`(Figure 7) and `throughput_comparison_http_grpc.png`(Figure 8) similar to the evaluation figures in the eBeeMetrics paper.