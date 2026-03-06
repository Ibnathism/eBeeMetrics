import json
import numpy as np
import matplotlib.pyplot as plt

SERVER_FILE = "server_latencies_by_rps.json"
CLIENT_FILE = "client_latencies_by_rps.json"

BENCHMARK_DURATION = 30  # seconds

# (title, server_key, client_key)
BENCHMARKS = [
    ("triton-http", "eBee_triton-http", "client_triton-http"),
    ("triton-grpc", "eBee_triton-grpc", "client_triton-grpc"),
]


def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def compute_p95(latencies):
    return float(np.percentile(latencies, 95))


def normalize_keys(d):
    """
    Convert string keys like '1', '1.0' -> int 1
    """
    out = {}
    for k, v in d.items():
        try:
            out[int(float(k))] = v
        except Exception:
            # ignore weird keys
            pass
    return out


def r2_identity(x, y):
    """
    R^2 for the model y_hat = x (how close points are to the y=x line),
    using y as "true" and x as "pred".
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if len(y) < 2:
        return float("nan")
    ss_res = np.sum((y - x) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    if ss_tot == 0:
        return float("nan")
    return float(1.0 - (ss_res / ss_tot))


def get_common_rps(server_dict, client_dict):
    return sorted(set(server_dict.keys()) & set(client_dict.keys()))


def main():
    server_data = load_json(SERVER_FILE)
    client_data = load_json(CLIENT_FILE)

    # ========================
    # LATENCY FIGURE (2 subplots)
    # ========================
    fig_lat, axes_lat = plt.subplots(1, 2, figsize=(14, 5), sharey=False)

    for ax, (title, server_key, client_key) in zip(axes_lat, BENCHMARKS):
        if server_key not in server_data:
            ax.set_title(f"{title} (missing {server_key})")
            ax.axis("off")
            continue
        if client_key not in client_data:
            ax.set_title(f"{title} (missing {client_key})")
            ax.axis("off")
            continue

        server_dict = normalize_keys(server_data[server_key])
        client_dict = normalize_keys(client_data[client_key])
        common_rps = get_common_rps(server_dict, client_dict)

        if not common_rps:
            ax.set_title(f"{title} (no common RPS)")
            ax.axis("off")
            continue

        server_p95 = [compute_p95(server_dict[rps]) for rps in common_rps]
        client_p95 = [compute_p95(client_dict[rps]) for rps in common_rps]

        ax.plot(common_rps, client_p95, marker="o", label="Client-reported")
        ax.plot(common_rps, server_p95, marker="^", label="eBeeMetrics")

        ax.set_title(title)
        ax.set_xlabel("RPS")
        ax.set_ylabel("95th Percentile Latency (ms)")
        ax.grid(True, linestyle="--", alpha=0.5)
        ax.legend()

    fig_lat.suptitle("Latency (P95) Comparison", y=1.02, fontsize=14)
    fig_lat.tight_layout()
    fig_lat.savefig("latency_comparison_http_grpc.png", dpi=300)
    plt.close(fig_lat)

    # ========================
    # THROUGHPUT FIGURE (2 subplots)
    # ========================
    fig_tp, axes_tp = plt.subplots(1, 2, figsize=(14, 5), sharey=False)

    for ax, (title, server_key, client_key) in zip(axes_tp, BENCHMARKS):
        if server_key not in server_data:
            ax.set_title(f"{title} (missing {server_key})")
            ax.axis("off")
            continue
        if client_key not in client_data:
            ax.set_title(f"{title} (missing {client_key})")
            ax.axis("off")
            continue

        server_dict = normalize_keys(server_data[server_key])
        client_dict = normalize_keys(client_data[client_key])
        common_rps = get_common_rps(server_dict, client_dict)

        if not common_rps:
            ax.set_title(f"{title} (no common RPS)")
            ax.axis("off")
            continue

        client_tp = [len(client_dict[rps]) / BENCHMARK_DURATION for rps in common_rps]
        server_tp = [len(server_dict[rps]) / BENCHMARK_DURATION for rps in common_rps]

        r2 = r2_identity(client_tp, server_tp)

        ax.scatter(client_tp, server_tp, s=120, alpha=0.9)

        min_val = min(min(client_tp), min(server_tp))
        max_val = max(max(client_tp), max(server_tp))
        ax.plot([min_val, max_val], [min_val, max_val], linestyle="--", color="gray", linewidth=2)

        ax.text(
            0.05, 0.92,
            f"$R^2$ (y=x) = {r2:.4f}" if np.isfinite(r2) else "$R^2$ (y=x) = N/A",
            transform=ax.transAxes,
            fontsize=12,
            bbox=dict(facecolor="white", edgecolor="gray", boxstyle="round,pad=0.3")
        )

        ax.set_title(title)
        ax.set_xlabel("Client Throughput (RPS)")
        ax.set_ylabel("eBeeMetrics Throughput (RPS)")
        ax.grid(False)

    fig_tp.suptitle("Throughput Comparison", y=1.02, fontsize=14)
    fig_tp.tight_layout()
    fig_tp.savefig("throughput_comparison_http_grpc.png", dpi=300)
    plt.close(fig_tp)

    print("Saved latency_comparison_http_grpc.png")
    print("Saved throughput_comparison_http_grpc.png")


if __name__ == "__main__":
    main()