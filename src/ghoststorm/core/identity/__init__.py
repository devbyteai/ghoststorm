"""Identity coherence orchestration for anti-detection.

Ensures proxy geolocation, fingerprint locale/timezone, HTTP headers,
and browser context are all coherent - preventing detection from
parameter mismatches.
"""

from ghoststorm.core.identity.coherence_orchestrator import (
    CoherentIdentity,
    IdentityCoherenceOrchestrator,
)

__all__ = [
    "CoherentIdentity",
    "IdentityCoherenceOrchestrator",
]
