"""Sandbox isolation policies and constraints."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class IsolationPolicy:
    allow_network: bool = False
    allow_filesystem_write_outside: bool = False
    allowed_extensions: tuple[str, ...] = (".py", ".md", ".yaml", ".json")
    max_memory_mb: int = 512
    max_cpu_count: int = 2
    max_disk_mb: int = 100
    max_processes: int = 10
    read_only_paths: tuple[str, ...] = ("/etc", "/usr", "/lib")
    writeable_paths: tuple[str, ...] = ("/tmp", "/home")
    blocked_syscalls: tuple[str, ...] = (
        "mount", "umount", "ptrace", "perf_event_open",
        "bpf", "reboot", "swapon", "swapoff",
    )


class IsolationEnforcer:
    def __init__(self, policy: IsolationPolicy | None = None):
        self.policy = policy or IsolationPolicy()

    def validate_file_access(self, filepath: str) -> bool:
        ext = Path(filepath).suffix
        return ext in self.policy.allowed_extensions

    def validate_path(self, path: str) -> bool:
        abs_path = Path(path).resolve()
        for ro_path in self.policy.read_only_paths:
            if str(abs_path).startswith(ro_path):
                return False
        return True

    def get_resource_limits(self) -> dict:
        return {
            "memory_mb": self.policy.max_memory_mb,
            "cpu_count": self.policy.max_cpu_count,
            "disk_mb": self.policy.max_disk_mb,
            "processes": self.policy.max_processes,
        }
