import sys
import time
import threading
from datetime import datetime
import json
import logging
import csv
import os
import socket
from collections import defaultdict

import tritonclient.grpc as grpcclient
from tritonclient.utils import InferenceServerException
import numpy as np

CTRL_PORT = int(os.environ.get("CTRL_PORT", "9999"))  # UDP control port on server

latencies_lock = threading.Lock()
latencies = []


def send_udp_marker(server_ip: str, marker5: bytes, payload: str = ""):
    # marker5 must be exactly 5 bytes (e.g., b"START" or b"END__")
    try:
        msg = marker5 + payload.encode(errors="ignore")
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.sendto(msg, (server_ip, CTRL_PORT))
    except Exception:
        pass


# --- Logging / CSV setup (same as your code) ---
open(f'logs/{sys.argv[2]}/request_response_log_{int(sys.argv[3])}d{sys.argv[4]}rps.log', 'w').close()

logging.basicConfig(
    filename=f'logs/{sys.argv[2]}/request_response_log_{int(sys.argv[3])}d{sys.argv[4]}rps.log',
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

with open(f'data/{sys.argv[2]}/request_response_log_{int(sys.argv[3])}d{sys.argv[4]}rps.csv', mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(['Request Start Time', 'Response Receive Time', 'Latency (ms)', 'Request Payload Size (bytes)', 'Response Payload Size (bytes)'])


def send_request(grpc_client, model_name, rps):
    inputs = grpcclient.InferInput("data_0", [3, 224, 224], "FP32")
    input_data = np.zeros([3, 224, 224], dtype=np.float32)
    inputs.set_data_from_numpy(input_data)

    outputs = grpcclient.InferRequestedOutput("fc6_1")

    try:
        start_time = time.time()
        formatted_start_time = datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')

        response = grpc_client.infer(model_name, inputs=[inputs], outputs=[outputs])

        response_time = time.time()
        formatted_response_time = datetime.fromtimestamp(response_time).strftime('%Y-%m-%d %H:%M:%S')

        latency = round((response_time - start_time) * 1000, 5)
        print(latency)

        # Save latency for JSON (like HTTP client)
        with latencies_lock:
            latencies.append(latency)

        logging.info(f"Latency: {latency}")
        logging.info(f"Request sent at {formatted_start_time}")
        logging.info(f"Response: {response.as_numpy('fc6_1')}")

        with open(f'data/{sys.argv[2]}/request_response_log_{int(sys.argv[3])}d{sys.argv[4]}rps.csv', mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([formatted_start_time, formatted_response_time, latency, "N/A", "N/A"])

    except InferenceServerException as e:
        logging.error(f"Failed to send request: {str(e)}", exc_info=True)
    except Exception as e:
        logging.error(f"Unexpected failure: {str(e)}", exc_info=True)


def send_requests_for_duration(grpc_client, model_name, duration, rps):
    end_time = time.time() + duration
    interval = 1 / rps
    t_count = 0

    threads = []
    while time.time() < end_time:
        t_count += 1
        t = threading.Thread(target=send_request, args=(grpc_client, model_name, rps))
        t.start()
        threads.append(t)
        time.sleep(interval)

    # Wait for all in-flight requests to finish (important before END marker)
    for t in threads:
        t.join()

    print(f"Total threads: {t_count}")


def write_client_json(rps):
    os.makedirs("client_latencies", exist_ok=True)
    output_path = "client_latencies/client_latencies_by_rps.json"

    if os.path.exists(output_path):
        with open(output_path, "r") as f:
            existing_data = json.load(f)
    else:
        existing_data = {}

    bench_name = "client_triton-grpc"

    if bench_name not in existing_data:
        existing_data[bench_name] = {}

    rps_str = str(rps)
    if rps_str not in existing_data[bench_name]:
        existing_data[bench_name][rps_str] = []

    with latencies_lock:
        existing_data[bench_name][rps_str].extend(latencies)

    with open(output_path, "w") as f:
        json.dump(existing_data, f, indent=4)

    print(f"📦 Client latencies saved for RPS={rps} -> {output_path}")


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python triton-grpc.py <IP> <Port> <Duration_in_seconds> <Requests_per_second>")
        sys.exit(1)

    ip = sys.argv[1]
    port = sys.argv[2]
    duration = int(sys.argv[3])
    rps = float(sys.argv[4])
    model_name = "densenet_onnx"

    # Create a gRPC client
    try:
        grpc_client = grpcclient.InferenceServerClient(url=f"{ip}:{port}")
    except Exception as e:
        print(f"Failed to create gRPC client: {str(e)}")
        sys.exit(1)

    run_id = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    print(f"Running gRPC client for {duration}s at RPS={rps} (CTRL_PORT={CTRL_PORT}, run_id={run_id})")

    # 5-byte UDP START marker
    send_udp_marker(ip, b"START", f"{run_id}\n")

    # Send requests for the specified duration
    send_requests_for_duration(grpc_client, model_name, duration, rps)

    # 5-byte UDP END marker (END__ to keep 5 bytes)
    send_udp_marker(ip, b"END__", f"{run_id}\n")

    # Write JSON latencies (same style as HTTP client)
    write_client_json(rps)
