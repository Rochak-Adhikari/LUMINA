"""
core/metadata.py — Lumina V2 Service Metadata (Phase 1.8)

Descriptive metadata for the infrastructure services registered by the
Bootstrapper: lifecycle, owner, description, and registration mode. This
is documentation/introspection data only — it does NOT affect how the
DependencyContainer registers or resolves anything.

The metadata registry lives as a standalone object (populated by the
Bootstrapper and itself registered into the container). The container's
own behaviour is left completely unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


# Registration lifecycle of a service within the container.
LIFECYCLE_SINGLETON = "singleton"
LIFECYCLE_TRANSIENT = "transient"
LIFECYCLE_INSTANCE = "instance"


@dataclass(frozen=True)
class ServiceMetadata:
    """
    Immutable descriptor for one registered infrastructure service.

    name           Short human-readable name (e.g. "BrainState").
    key            The container key it is registered under (repr of the
                    interface/concrete type), for correlation with the
                    container registry.
    lifecycle      One of LIFECYCLE_* — how the container returns it.
    owner          The subsystem/phase that owns it (e.g. "Phase 1.2").
    description    One-line description of the service's role.
    """

    name: str
    key: str
    lifecycle: str
    owner: str
    description: str


class ServiceMetadataRegistry:
    """
    In-memory registry of ServiceMetadata records.

    Purely additive and independent of the DI container: registering
    metadata here has no effect on service resolution. Keyed by the
    metadata `key` string.
    """

    def __init__(self) -> None:
        self._records: Dict[str, ServiceMetadata] = {}

    def register(self, metadata: ServiceMetadata) -> None:
        """Store a metadata record (overwrites any existing record for its key)."""
        self._records[metadata.key] = metadata

    def get(self, key: str) -> Optional[ServiceMetadata]:
        """Return the metadata record for *key*, or None if absent."""
        return self._records.get(key)

    def all(self) -> List[ServiceMetadata]:
        """Return all metadata records in registration order of insertion."""
        return list(self._records.values())

    def __len__(self) -> int:
        return len(self._records)
