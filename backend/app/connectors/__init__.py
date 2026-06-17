"""Connector registry. New sources register here without touching the pipeline."""
from .apify_linkedin import (
    ApifyLinkedInConnector,
    InternshalaConnector,
    NaukriConnector,
)
from .ashby import AshbyConnector
from .base import BaseConnector, HealthResult, NormalizedJob
from .greenhouse import GreenhouseConnector
from .lever import LeverConnector
from .sample import SampleConnector

# Maps Source.name -> connector class for real sources.
CONNECTOR_REGISTRY: dict[str, type[BaseConnector]] = {
    "greenhouse": GreenhouseConnector,
    "lever": LeverConnector,
    "ashby": AshbyConnector,
    "linkedin": ApifyLinkedInConnector,
    "naukri": NaukriConnector,
    "internshala": InternshalaConnector,
}

__all__ = [
    "BaseConnector", "NormalizedJob", "HealthResult",
    "GreenhouseConnector", "LeverConnector", "AshbyConnector", "SampleConnector",
    "ApifyLinkedInConnector", "NaukriConnector", "InternshalaConnector",
    "CONNECTOR_REGISTRY",
]
