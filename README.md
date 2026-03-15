# eBeeMetrics
An eBPF-based library framework to accurately observe application-level metrics derived from only eBPF-observable events, such as system calls.

This repository contains eBeeMetrics experiments and plotting scripts for comparing **client-reported** latency/throughput vs **eBeeMetrics-reported** latency/throughput for **Triton HTTP** and **Triton gRPC**.

---
## Repository Layout
- `client/triton/`: Client runners for Triton HTTP and Triton gRPC. These are already set in the existing `triton-client` docker container in the Chameleon instance.
- `lib/`: eBeeMetrics tracing library
   - `lib/bpf/`: kernel programs used by the library
   - `lib/latencies/`: storage for latency data and plots 
- `docs/`: Step-by-step documentation for setup and experiment execution.

## Quickstart (Artifact Evaluation on Chameleon)

Everything needed for the artifact evaluation is **already installed and configured** on the provided Chameleon Cloud instance.

1. **Log into Chameleon**
   - Directions provided in the Artifact Appendix section of the paper

2. **Run the experiments + generate plots**
   - Follow: [docs/Latency-and-throughput-plots.md](docs/Latency-and-throughput-plots.md)

That’s it.

---

## Running Everything From Scratch (Your Own Machine)

If you want to reproduce the full setup on your own machine (instead of using the pre-configured Chameleon instance), follow these steps.

### 1) Build / install dependencies
From the repository root:

```bash
make all
```

### 2) Set up the workload

Follow the workload setup guide: [docs/Setting-up-the-workload.md](docs/Setting-up-the-workload.md)

### 3) (gRPC only) Set the binary path for uprobes

For the Triton gRPC experiment, the uprobe script requires the correct Triton server binary path.

Follow: [docs/Binary-for-uprobes.md](docs/Binary-for-uprobes.md)

### 4) Set up the client
For setting up the client for `triton-http` and `triton-grpc` clients, the client codes are inside the `client/triton` directory. Go through [docs/Setting-up-client.md](docs/Setting-up-client.md).

### 5) Run the experiments + generate plots

Finally, follow: [docs/Latency-and-throughput-plots.md](docs/Latency-and-throughput-plots.md)

Notes
- All measured latencies are stored as JSON under `lib/latencies/`
- The plotting script produces side-by-side HTTP vs gRPC comparison figures.

## Citation

If you use eBeeMetrics in your research, please cite our paper:
```bash
@inproceedings{ibnath2026ebeemetrics,
  title     = {eBeeMetrics: An eBPF-based Library Framework for Feedback-free Observability of QoS Metrics},
  author    = {Ibnath, Muntaka and Rezvani, Mohammadreza and Wong, Daniel},
  booktitle = {Proceedings of the IEEE International Symposium on Performance Analysis of Systems and Software (ISPASS)},
  year      = {2026}
}
```
