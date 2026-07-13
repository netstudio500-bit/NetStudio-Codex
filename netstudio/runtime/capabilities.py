"""Capability vocabulary shared by execution policy and tools."""

from enum import Enum


class ToolCapability(str, Enum):
    """Capabilities a tool must explicitly declare."""

    READ = "read"
    WRITE = "write"
    LOCAL_EXECUTION = "local_execution"
    NETWORK = "network"
    ADMINISTRATION = "administration"
    UNCLASSIFIED = "unclassified"
