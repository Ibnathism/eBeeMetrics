# Setting Up the Client (Triton Client Container)

This guide describes how to set up the client-side scripts inside the `triton-client` Docker container.

---

## 1) Confirm the `triton-client` container is running

On the host machine, run:

```bash
docker ps
```
Verify you see a container named triton-client in the list.
If it is not running, start it (example):
```bash
docker start triton-clien
```

## 2) Copy client scripts into the container
### 2.1 Go to the client scripts directory (host)

From the repository root:
```bash
cd client/triton
```
You should see these four files:
1. `run-client.sh`
2. `setup-client.sh`
3. `triton-http.py`
4. `triton-grpc.py`

### 2.2 Copy the files into the container

Copy all four files into the container at:
`/workspace/client/src/python/examples/eBeeMetrics/`

Run:
```bash
docker cp run-client.sh triton-client:/workspace/client/src/python/examples/eBeeMetrics/
docker cp setup-client.sh triton-client:/workspace/client/src/python/examples/eBeeMetrics/
docker cp triton-http.py triton-client:/workspace/client/src/python/examples/eBeeMetrics/
docker cp triton-grpc.py triton-client:/workspace/client/src/python/examples/eBeeMetrics/
```
(Optional) Verify inside the container:
```bash 
docker exec -it triton-client /bin/bash
cd /workspace/client/src/python/examples/eBeeMetrics
ls -lah
```
## 3) Create required output directories (inside the container)

Inside the container (same directory as above), create:
1. `client_latencies/`
2. `data/`
3. `logs/`

Commands:
```bash
mkdir -p client_latencies data logs
```

(Optional) Verify:
```bash
ls -lah
```
Next Step

After client setup is complete, follow: [Latency-and-throughput-plots.md](./Latency-and-throughput-plots.md) to run the experiments and generate plots.