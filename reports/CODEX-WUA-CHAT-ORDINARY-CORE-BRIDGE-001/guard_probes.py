"""All probes must be refused before any external effect or protected read."""
import os
from pathlib import Path
import socket
import subprocess

root = Path.cwd()
probes = {
    "socket": lambda: socket.create_connection(("203.0.113.1", 443), timeout=.1),
    "dns": lambda: socket.getaddrinfo("provider.invalid", 443),
    "credentials": lambda: os.environ["GIGACHAT_CREDENTIALS"],
    "dotenv": lambda: (root / ".env").read_bytes(),
    "live_storage": lambda: (root / ".ultra/bridge-guard-probe.json").write_bytes(b"forbidden"),
    "external_process": lambda: subprocess.run(["cmd.exe", "/c", "exit", "0"]),
}
for name, probe in probes.items():
    try:
        probe()
    except PermissionError:
        print(name, "BLOCKED")
    else:
        raise AssertionError(name + " was not blocked")
print("6 guard probes PASS")
