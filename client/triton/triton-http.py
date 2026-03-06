import requests
import time
import sys
import threading
from datetime import datetime
import json
import os
import socket
from collections import defaultdict

client_latency_json = defaultdict(lambda: defaultdict(list))

latencies_lock = threading.Lock()
latencies = []

CTRL_PORT = int(os.environ.get("CTRL_PORT", "9999"))  # UDP control port on server


def send_udp_marker(server_ip: str, marker5: bytes, payload: str = ""):
    # marker5 must be exactly 5 bytes (e.g., b"START" or b"END__")
    try:
        msg = marker5 + payload.encode(errors="ignore")
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.sendto(msg, (server_ip, CTRL_PORT))
    except Exception:
        pass


def send_request(target_url):
    data = {
        "inputs": [
            {
                "name": "data_0",
                "data": [0.0] * 224 * 224 * 3,
                "datatype": "FP32",
                "shape": [3, 224, 224]
            }
        ]
    }

    try:
        start_time = time.time()
        response = requests.post(target_url, json=data)

        if response.status_code == 200:
            response_time = time.time()
            latency = (response_time - start_time) * 1000

            with latencies_lock:
                latencies.append(latency)

    except Exception:
        pass


def send_requests_for_duration(target_url, duration, rps):
    end_time = time.time() + duration
    interval = 1 / rps

    threads = []
    while time.time() < end_time:
        t = threading.Thread(target=send_request, args=(target_url,))
        t.start()
        threads.append(t)
        time.sleep(interval)

    # Wait for all in-flight requests to complete before END marker
    for t in threads:
        t.join()


def write_client_json(rps):
    os.makedirs("client_latencies", exist_ok=True)
    output_path = "client_latencies/client_latencies_by_rps.json"

    if os.path.exists(output_path):
        with open(output_path, "r") as f:
            existing_data = json.load(f)
    else:
        existing_data = {}

    bench_name = "client_triton-http"

    if bench_name not in existing_data:
        existing_data[bench_name] = {}

    rps_str = str(rps)
    if rps_str not in existing_data[bench_name]:
        existing_data[bench_name][rps_str] = []

    existing_data[bench_name][rps_str].extend(latencies)

    with open(output_path, "w") as f:
        json.dump(existing_data, f, indent=4)

    print(f"📦 Client latencies saved for RPS={rps}")


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python3 triton-http.py <IP> <Port> <Duration> <RPS>")
        sys.exit(1)

    ip = sys.argv[1]
    port = sys.argv[2]
    duration = int(sys.argv[3])
    rps = float(sys.argv[4])

    target_url = f"http://{ip}:{port}/v2/models/densenet_onnx/infer"
    run_id = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    print(f"Running client for {duration}s at RPS={rps} (CTRL_PORT={CTRL_PORT}, run_id={run_id})")

    # 5-byte UDP START marker
    send_udp_marker(ip, b"START", f"{run_id}\n")

    send_requests_for_duration(target_url, duration, rps)

    # 5-byte UDP END marker (END__ to keep 5 bytes)
    send_udp_marker(ip, b"END__", f"{run_id}\n")

    write_client_json(rps)