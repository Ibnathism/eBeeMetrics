#include <uapi/linux/ptrace.h>
#include <linux/sched.h>

struct latency_event_t {
    u32 pid;
    int fd;
    u64 accept_ts;
    u64 latency_ns;
    char comm[TASK_COMM_LEN];
};


BPF_HASH(start_ts_map, int, u64);
BPF_HASH(fd_temp, u32, int);  // pid -> fd map
BPF_RINGBUF_OUTPUT(events, 8);

int trace_accept4_exit(struct pt_regs *ctx) {
    u32 pid = bpf_get_current_pid_tgid() >> 32;
    if (pid != PID) return 0;

    int new_fd = PT_REGS_RC(ctx);
    if (new_fd < 0) return 0;

    u64 ts = bpf_ktime_get_ns();
    start_ts_map.update(&new_fd, &ts);
    return 0;
}

int syscall__close(struct pt_regs *ctx, int fd) {
    u32 pid = bpf_get_current_pid_tgid() >> 32;
    if (pid != PID) return 0;

    fd_temp.update(&pid, &fd);
    return 0;
}

int trace_close_exit(struct pt_regs *ctx) {
    u32 pid = bpf_get_current_pid_tgid() >> 32;
    if (pid != PID) return 0;

    int ret = PT_REGS_RC(ctx);
    if (ret < 0) return 0;

    int *fdp = fd_temp.lookup(&pid);
    if (!fdp) return 0;
    int fd = *fdp;

    u64 *start_ts = start_ts_map.lookup(&fd);
    if (!start_ts) {
        fd_temp.delete(&pid);
        return 0;
    }

    u64 end_ts = bpf_ktime_get_ns();
    u64 latency = end_ts - *start_ts;

    // Full latency event to ringbuf (for logging)
    struct latency_event_t *event = events.ringbuf_reserve(sizeof(struct latency_event_t));
    if (event) {
        event->pid = pid;
        event->fd = fd;
        event->accept_ts = *start_ts;
        event->latency_ns = latency;
        bpf_get_current_comm(&event->comm, sizeof(event->comm));
        events.ringbuf_submit(event, 0);
    }

    // Cleanup
    start_ts_map.delete(&fd);
    fd_temp.delete(&pid);
    return 0;
}
