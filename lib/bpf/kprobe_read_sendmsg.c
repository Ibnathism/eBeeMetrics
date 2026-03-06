#include <uapi/linux/ptrace.h>
#include <linux/sched.h>

struct latency_event_t {
    u32 pid;
    int fd;
    u64 read_ts;
    u64 latency_ns;
    char comm[TASK_COMM_LEN];
};

BPF_HASH(read_ts_map, int, u64);     // fd -> read timestamp
BPF_HASH(fd_temp, u32, int);         // pid -> fd for sendmsg
BPF_HASH(accepted_fds, int, u8);     // fd -> 1 if accepted
BPF_RINGBUF_OUTPUT(events, 8);

// Track newly accepted sockets
int trace_accept4_exit(struct pt_regs *ctx) {
    u32 pid = bpf_get_current_pid_tgid() >> 32;
    if (pid != PID) return 0;

    int fd = PT_REGS_RC(ctx);
    if (fd < 0) return 0;

    u8 one = 1;
    accepted_fds.update(&fd, &one);
    return 0;
}

// Save timestamp on read if fd was accepted
int syscall__read(struct pt_regs *ctx, int fd, void *buf, u64 count) {
    u32 pid = bpf_get_current_pid_tgid() >> 32;
    if (pid != PID) return 0;

    u8 *found = accepted_fds.lookup(&fd);
    if (!found) return 0;

    u64 ts = bpf_ktime_get_ns();
    read_ts_map.update(&fd, &ts);
    return 0;
}

// Save fd temporarily on sendmsg entry
int syscall__sendmsg(struct pt_regs *ctx, int fd, void *msg, int flags) {
    u32 pid = bpf_get_current_pid_tgid() >> 32;
    if (pid != PID) return 0;

    u8 *found = accepted_fds.lookup(&fd);
    if (!found) return 0;

    fd_temp.update(&pid, &fd);
    return 0;
}

// Compute latency and emit event
int trace_sendmsg_exit(struct pt_regs *ctx) {
    u32 pid = bpf_get_current_pid_tgid() >> 32;
    if (pid != PID) return 0;

    int ret = PT_REGS_RC(ctx);
    if (ret < 0) return 0;

    int *fdp = fd_temp.lookup(&pid);
    if (!fdp) return 0;
    int fd = *fdp;

    u64 *read_ts = read_ts_map.lookup(&fd);
    if (!read_ts) {
        fd_temp.delete(&pid);
        return 0;
    }

    u64 now = bpf_ktime_get_ns();
    u64 latency = now - *read_ts;

    struct latency_event_t *event = events.ringbuf_reserve(sizeof(struct latency_event_t));
    if (!event) return 0;

    event->pid = pid;
    event->fd = fd;
    event->read_ts = *read_ts;
    event->latency_ns = latency;
    bpf_get_current_comm(&event->comm, sizeof(event->comm));
    events.ringbuf_submit(event, 0);

    read_ts_map.delete(&fd);
    fd_temp.delete(&pid);
    return 0;
}
