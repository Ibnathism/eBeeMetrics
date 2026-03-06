#include <uapi/linux/ptrace.h>
#include <linux/sched.h>

struct latency_event_t {
    u32 pid;
    u64 start_ts;
    u64 latency_ns;
    void *stream;
    char comm[TASK_COMM_LEN];
};

BPF_HASH(start_ts_map, void *, u64);       // stream_ptr -> start_ts
BPF_HASH(occurrence_count, void *, u32);   // stream_ptr -> count
BPF_RINGBUF_OUTPUT(events, 8);

// Uprobe: grpc_chttp2_stream constructor
int trace_constructor(struct pt_regs *ctx) {
    u32 pid = bpf_get_current_pid_tgid() >> 32;
    if (pid != PID) return 0;

    void *stream_ptr = (void *)PT_REGS_PARM1(ctx);
    u64 ts = bpf_ktime_get_ns();
    start_ts_map.update(&stream_ptr, &ts);
    return 0;
}

// Uprobe: grpc_chttp2_maybe_complete_recv_trailing_metadata
int trace_metadata_func(struct pt_regs *ctx) {
    u32 pid = bpf_get_current_pid_tgid() >> 32;
    if (pid != PID) return 0;

    void *stream_ptr = (void *)PT_REGS_PARM2(ctx);
    if (!stream_ptr)
        return 0;

    u32 *cnt = occurrence_count.lookup(&stream_ptr);
    u32 count = cnt ? *cnt : 0;
    count += 1;

    if (count < 3) {
        occurrence_count.update(&stream_ptr, &count);
        return 0;
    }

    // Third occurrence: compute latency
    u64 *start_ts = start_ts_map.lookup(&stream_ptr);
    if (!start_ts) {
        occurrence_count.delete(&stream_ptr);
        return 0;
    }

    u64 now = bpf_ktime_get_ns();
    u64 latency = now - *start_ts;

    struct latency_event_t *event = events.ringbuf_reserve(sizeof(struct latency_event_t));
    if (!event) return 0;

    event->pid = pid;
    event->start_ts = *start_ts;
    event->latency_ns = latency;
    event->stream = stream_ptr;
    bpf_get_current_comm(&event->comm, sizeof(event->comm));
    events.ringbuf_submit(event, 0);

    start_ts_map.delete(&stream_ptr);
    occurrence_count.delete(&stream_ptr);
    return 0;
}
