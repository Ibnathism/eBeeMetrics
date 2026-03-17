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

## 2) Create required output directories (inside the container)
First, create a directory for the eBeeMetrics client:
```bash
docker exec -it triton-client /bin/bash
cd /workspace/client/src/python/examples/
mkdir eBeeMetrics
cd eBeeMetrics
```

Now in this directory, create the following folders:
1. `client_latencies/`
2. `data/`
3. `logs/`
4. `data/8000`
5. `logs/8000`
6. `data/8001`
7. `logs/8001`

Command:
```bash
mkdir -p client_latencies data logs data/8000 logs/8000 data/8001 logs/8001
```

(Optional) Verify:
```bash
ls -lah
```

## 3) Copy client scripts into the container
### 3.1 Go to the client scripts directory (host)

From the repository root in a new terminal:
```bash
cd client/triton
```
You should see these four files:
1. `run-client.sh`
2. `setup-client.sh`
3. `triton-http.py`
4. `triton-grpc.py`

### 3.2 Copy the files into the container

Copy all four files into the container at:
`/workspace/client/src/python/examples/eBeeMetrics/`

Run:
```bash
docker cp run-client.sh triton-client:/workspace/client/src/python/examples/eBeeMetrics/
docker cp setup-client.sh triton-client:/workspace/client/src/python/examples/eBeeMetrics/
docker cp triton-http.py triton-client:/workspace/client/src/python/examples/eBeeMetrics/
docker cp triton-grpc.py triton-client:/workspace/client/src/python/examples/eBeeMetrics/
```
After copying the client codes, make the client scripts executable. In a new terminal:
```bash
docker exec -it triton-client /bin/bash
cd /workspace/client/src/python/examples/eBeeMetrics
chmod +x *.sh
chmod +x *.py
```

(Optional) Verify inside the container:
```bash 
docker exec -it triton-client /bin/bash
cd /workspace/client/src/python/examples/eBeeMetrics
ls -lah
```

**Next Step**
After client setup is complete, follow: [Latency-and-throughput-plots.md](./Latency-and-throughput-plots.md) to run the experiments and generate plots.