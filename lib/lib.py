from bcc import BPF
import argparse
import ctypes
import numpy as np
import time
import os
import threading

MAX_LATENCIES = 10000
BUFFER_READ_INTERVAL = 1.0

def get_pid(container_name):
    cmd = f"docker inspect --format '{{{{.State.Pid}}}}' {container_name}"
    return int(os.popen(cmd).read().strip())

class LatencyEvent(ctypes.Structure):
    _fields_ = [
        ("pid", ctypes.c_uint),
        ("fd", ctypes.c_int),
        ("accept_ts", ctypes.c_ulonglong),
        ("latency_ns", ctypes.c_ulonglong),
        ("comm", ctypes.c_char * 16),
    ]

class LatencyMetricsThread(threading.Thread):
    def __init__(self, bpf, name, show_metrics=False):
        super().__init__()
        self.bpf = bpf
        self.benchmark_name = name
        self.latencies = []
        self.rps_count = 0
        self.show_metrics = show_metrics
        self.running = True
        self.lock = threading.Lock()

    def handle_event(self, cpu, data, size):
        event = ctypes.cast(data, ctypes.POINTER(LatencyEvent)).contents
        latency = event.latency_ns / 1e6
        with self.lock:
            self.latencies.append(latency)
            if len(self.latencies) > MAX_LATENCIES:
                self.latencies.pop(0)
            self.rps_count += 1

    def get_latest_latency(self):
        with self.lock:
            return round(self.latencies[-1], 3) if self.latencies else None

    def get_average_latency(self):
        with self.lock:
            return round(sum(self.latencies) / len(self.latencies), 3) if self.latencies else None

    def get_latency_percentile(self, p=99):
        with self.lock:
            return round(np.percentile(self.latencies, p), 3) if self.latencies else None

    def get_RPS(self):
        with self.lock:
            return self.rps_count

    def run(self):
        self.bpf["events"].open_ring_buffer(self.handle_event)
        last_print_time = time.time()
        while self.running:
            self.bpf.ring_buffer_poll(timeout=100)
            now = time.time()
            if self.show_metrics and (now - last_print_time >= BUFFER_READ_INTERVAL):
                print(f"\n[{self.benchmark_name}] --- Metrics ---")
                print(f"Latest latency: {self.get_latest_latency()} ms")
                print(f"Average latency: {self.get_average_latency()} ms")
                print(f"99th percentile latency: {self.get_latency_percentile()} ms")
                print(f"Current RPS: {self.get_RPS()}")
                with self.lock:
                    self.rps_count = 0
                last_print_time = now

    def stop(self):
        self.running = False

def attach_kprobe_accept_close(bpf):
    bpf.attach_kretprobe(event="__x64_sys_accept4", fn_name="trace_accept4_exit")
    bpf.attach_kprobe(event="__x64_sys_close", fn_name="syscall__close")
    bpf.attach_kretprobe(event="__x64_sys_close", fn_name="trace_close_exit")

def attach_kprobe_read_sendmsg(bpf):
    bpf.attach_kprobe(event="__x64_sys_read", fn_name="syscall__read")
    bpf.attach_kprobe(event="__x64_sys_sendmsg", fn_name="syscall__sendmsg")
    bpf.attach_kretprobe(event="__x64_sys_accept4", fn_name="trace_accept4_exit")
    bpf.attach_kretprobe(event="__x64_sys_sendmsg", fn_name="trace_sendmsg_exit")

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
        "container": "triton-server"
    },
    "vswarm-hotel-app-profile": { "bpf_file": "bpf/kprobe_accept_close.c", "attach_func": "attach_kprobe_accept_close", "container": "docker-compose-relay-1" },
    "vswarm-hotel-app-rate": { "bpf_file": "bpf/kprobe_accept_close.c", "attach_func": "attach_kprobe_accept_close", "container": "docker-compose-relay-1" },
    "vswarm-hotel-app-reservation": { "bpf_file": "bpf/kprobe_accept_close.c", "attach_func": "attach_kprobe_accept_close", "container": "docker-compose-relay-1" },
    "vswarm-hotel-app-search": { "bpf_file": "bpf/kprobe_accept_close.c", "attach_func": "attach_kprobe_accept_close", "container": "docker-compose-relay-1" },
    "vswarm-online-shop-adservice": { "bpf_file": "bpf/kprobe_accept_close.c", "attach_func": "attach_kprobe_accept_close", "container": "docker-compose-relay-1" },
    "vswarm-online-shop-cartservice": { "bpf_file": "bpf/kprobe_accept_close.c", "attach_func": "attach_kprobe_accept_close", "container": "docker-compose-relay-1" },
    "vswarm-online-shop-recommendation": { "bpf_file": "bpf/kprobe_accept_close.c", "attach_func": "attach_kprobe_accept_close", "container": "docker-compose-relay-1" },
    "cloudsuite-data-caching": { "bpf_file": "bpf/kprobe_read_sendmsg.c", "attach_func": "attach_kprobe_read_sendmsg", "container": "dc-server" },
    "triton-grpc": {
        "bpf_file": "bpf/uprobe_grpc_core.c", 
        "attach_func": "attach_uprobe_grpc_core", 
        "container": "triton-server"
    },
}

def init_benchmark(benchmark_name):
    if benchmark_name not in benchmark_config:
        raise ValueError(f"Unknown benchmark: {benchmark_name}")
    config = benchmark_config[benchmark_name]
    pid = get_pid(config["container"])
    print(f"Initializing {benchmark_name} for container '{config['container']}' (PID {pid})")
    with open(config["bpf_file"]) as f:
        bpf_text = f.read().replace("PID", str(pid))
    b = BPF(text=bpf_text)
    globals()[config["attach_func"]](b)
    return b

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Trace benchmark latencies")
    parser.add_argument("-b", "--benchmark", nargs="*", help="List of benchmark names")
    parser.add_argument("--buffer_read", action="store_true", help="Print metrics every second")
    args = parser.parse_args()

    benchmarks = args.benchmark or list(benchmark_config.keys())

    threads = []
    for bench in benchmarks:
        try:
            bpf = init_benchmark(bench)
            thread = LatencyMetricsThread(bpf, name=bench, show_metrics=args.buffer_read)
            thread.start()
            threads.append(thread)
        except Exception as e:
            print(f"[ERROR] Skipping '{bench}': {e}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping all tracing threads...")
        for t in threads:
            t.stop()
            t.join()
