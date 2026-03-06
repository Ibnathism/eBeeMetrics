from bcc import BPF  # type: ignore
import argparse
import ctypes
import numpy as np  # type: ignore
import time
import os
import threading
import json
from collections import defaultdict
import socket

CTRL_PORT = int(os.environ.get("CTRL_PORT", "9999"))
latency_json = defaultdict(lambda: defaultdict(list))
CURRENT_RPS = int(os.environ.get("CURRENT_RPS", 0))

MAX_LATENCIES = 100000
BUFFER_READ_INTERVAL = 1.0


def get_pid(container_name):
    cmd = f"docker inspect --format '{{{{.State.Pid}}}}' {container_name}"
    return int(os.popen(cmd).read().strip())

def parse_udp_packet(data: bytes):
    if len(data) < 5:
        return None

    identifier = data[:5].decode(errors="ignore")
    payload = data[5:].decode(errors="ignore").strip()

    # START / END markers (5-byte identifiers)
    if identifier == "START":
        return {"identifier": "START", "payload": payload}

    if identifier == "END__":   # client sends END__ to keep 5 bytes
        return {"identifier": "END", "payload": payload}

    # Expected format: "STTTR<slack>,<latency>"
    if identifier == "STTTR":
        parts = payload.split(',')
        if len(parts) != 2:
            print("Malformed STTTR packet:", payload)
            return None

        try:
            slack_val = parts[0]
            latency_val = parts[1]
        except Exception:
            print("Non-integer STTTR packet:", payload)
            return None

        return {"identifier": identifier, "slack": slack_val, "latency": latency_val}

    return None


class LatencyEvent(ctypes.Structure):
    _fields_ = [
        ("pid", ctypes.c_uint),
        ("fd", ctypes.c_int),
        ("accept_ts", ctypes.c_ulonglong),
        ("latency_ns", ctypes.c_ulonglong),
        ("comm", ctypes.c_char * 16),
    ]


class LatencyMetricsThread(threading.Thread):
    def __init__(self, bpf, name, start_evt, end_evt, show_metrics=False):
        super().__init__()
        self.bpf = bpf
        self.benchmark_name = name
        self.latencies = []
        self.rps_count = 0
        self.show_metrics = show_metrics
        self.lock = threading.Lock()
        self.start_evt = start_evt
        self.end_evt = end_evt

    def handle_event(self, cpu, data, size):
        # only record between START and END
        if (not self.start_evt.is_set()) or self.end_evt.is_set():
            return

        event = ctypes.cast(data, ctypes.POINTER(LatencyEvent)).contents
        latency = event.latency_ns / 1e6

        with self.lock:
            self.latencies.append(latency)
            if len(self.latencies) > MAX_LATENCIES:
                self.latencies.pop(0)

            self.rps_count += 1
            latency_json[f"eBee_{self.benchmark_name}"][CURRENT_RPS].append(latency)

    def run(self):
        self.bpf["events"].open_ring_buffer(self.handle_event)

        last_print_time = time.time()

        # Poll until END arrives
        while not self.end_evt.is_set():
            self.bpf.ring_buffer_poll(timeout=100)

            if self.show_metrics and self.start_evt.is_set() and (time.time() - last_print_time >= BUFFER_READ_INTERVAL):
                with self.lock:
                    avg = round(sum(self.latencies) / len(self.latencies), 3) if self.latencies else None
                    p99 = round(np.percentile(self.latencies, 99), 3) if self.latencies else None
                    rps = self.rps_count
                    self.rps_count = 0

                print(f"\n[{self.benchmark_name}] --- Metrics ---")
                print(f"Average latency: {avg} ms")
                print(f"99th percentile latency: {p99} ms")
                print(f"Current RPS: {rps}")
                last_print_time = time.time()

class UdpControlThread(threading.Thread):
    def __init__(self, start_evt: threading.Event, end_evt: threading.Event):
        super().__init__(daemon=True)
        self.start_evt = start_evt
        self.end_evt = end_evt

    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("0.0.0.0", CTRL_PORT))
        sock.settimeout(1.0)

        while not self.end_evt.is_set():
            try:
                data, addr = sock.recvfrom(512)
            except socket.timeout:
                continue
            except Exception:
                continue

            pkt = parse_udp_packet(data)
            if not pkt:
                continue

            if pkt["identifier"] == "START":
                print(f"[udp] START from {addr} payload={pkt.get('payload','')}")
                self.start_evt.set()

            elif pkt["identifier"] == "END":
                print(f"[udp] END from {addr} payload={pkt.get('payload','')}")
                self.end_evt.set()

        sock.close()

def attach_kprobe_accept_close(bpf):
    bpf.attach_kretprobe(event="__x64_sys_accept4", fn_name="trace_accept4_exit")
    bpf.attach_kprobe(event="__x64_sys_close", fn_name="syscall__close")
    bpf.attach_kretprobe(event="__x64_sys_close", fn_name="trace_close_exit")

def attach_uprobe_grpc_core(bpf):
    triton_binary = "/var/lib/docker/overlay2/972bbec5a2a89e332901e1564aa2f3d59b80f0ec7d77ed547cbcccdaab7694e6/diff/opt/tritonserver/bin/tritonserver"
    constructor_symbol = "_ZN18grpc_chttp2_streamC1EP21grpc_chttp2_transportP20grpc_stream_refcountPKvPN9grpc_core5ArenaE"
    metadata_symbol = "_Z49grpc_chttp2_maybe_complete_recv_trailing_metadataP21grpc_chttp2_transportP18grpc_chttp2_stream"
    bpf.attach_uprobe(name=triton_binary, sym=constructor_symbol, fn_name="trace_constructor")
    bpf.attach_uprobe(name=triton_binary, sym=metadata_symbol, fn_name="trace_metadata_func")

benchmark_config = {
    "triton-http": {
        "bpf_file": "bpf/kprobe_accept_close.c",
        "attach_func": "attach_kprobe_accept_close",
        "container": "triton-server",
    },
    "triton-grpc": {
        "bpf_file": "bpf/uprobe_grpc_core.c", 
        "attach_func": "attach_uprobe_grpc_core", 
        "container": "triton-server"
    },
}


def init_benchmark(benchmark_name):
    config = benchmark_config[benchmark_name]
    pid = get_pid(config["container"])

    print(f"Initializing {benchmark_name} (PID {pid})")

    with open(config["bpf_file"]) as f:
        bpf_text = f.read().replace("PID", str(pid))

    b = BPF(text=bpf_text)
    globals()[config["attach_func"]](b)
    return b


def write_latency_file():
    os.makedirs("latencies", exist_ok=True)
    output_path = "latencies/server_latencies_by_rps.json"

    if os.path.exists(output_path):
        with open(output_path, "r") as f:
            existing_data = json.load(f)
    else:
        existing_data = {}

    for bench, rps_dict in latency_json.items():
        if bench not in existing_data:
            existing_data[bench] = {}

        for rps, lat_list in rps_dict.items():
            rps_str = str(rps)
            if rps_str not in existing_data[bench]:
                existing_data[bench][rps_str] = []
            existing_data[bench][rps_str].extend(lat_list)

    with open(output_path, "w") as f:
        json.dump(existing_data, f, indent=4)

    print(f"\n📦 Latency data saved to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-b", "--benchmark", default="triton-http")
    parser.add_argument("--buffer_read", action="store_true")
    args = parser.parse_args()

    bpf = init_benchmark(args.benchmark)

    start_evt = threading.Event()
    end_evt = threading.Event()

    udp_thread = UdpControlThread(start_evt, end_evt)
    udp_thread.start()

    print(f"[server] Listening for UDP markers on port {CTRL_PORT} (START/END__)")

    metrics_thread = LatencyMetricsThread(
        bpf=bpf,
        name=args.benchmark,
        start_evt=start_evt,
        end_evt=end_evt,
        show_metrics=args.buffer_read,
    )
    metrics_thread.start()

    metrics_thread.join()
    write_latency_file()