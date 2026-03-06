# Find and set the appropriate binary and function symbol for userspace probing

## Locate the Triton binary inside Docker’s overlay2

For hooking user space probes we need to find the triton binary file. The binary files of the docker containers are generally located inside the `overlay2` directory. To locate the `overlay2` directory run the following command:
```bash
docker info | grep "Docker Root Dir"
# Example: /var/lib/docker/
```

Using the following command, find the specific binary file for the `tritonserver`:
```bash
sudo find /var/lib/docker/overlay2/ -type f -name "tritonserver"
```
    
```bash
# Example result:
/var/lib/docker/overlay2/6f3e90...dd0f/diff/opt/tritonserver/bin/tritonserver
```

## Look for the function symbol in the target binary

This shows all the symbols for a specific function.
```bash
# Function name example from grpc core library: "grpc_chttp2_maybe_complete_recv_trailing_metadata"
sudo objdump -t <tritonserver-binary-path> | grep <function-name>​
```

This command demangles the function symbol to match it with the actual function signature:
```bash
echo <symbol> | c++filt
```