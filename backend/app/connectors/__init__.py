"""Connector registry. New sources register here without touching the pipeline."""
from .ashby import AshbyConnector
from .base import BaseConnector, HealthResult, NormalizedJob
from .greenhouse import GreenhouseConnector
from .internshala import InternshalaConnector
from .jobspy_connector import (
    JobSpyIndeedConnector,
    JobSpyLinkedInConnector,
    JobSpyNaukriConnector,
)
from .lever import LeverConnector
from .sample import SampleConnector

# Maps Source.name -> connector class for real sources.
# LinkedIn / Naukri / Indeed are scraped free via JobSpy (no API token);
# Internshala via a direct listing scraper.
CONNECTOR_REGISTRY: dict[str, type[BaseConnector]] = {
    "greenhouse": GreenhouseConnector,
    "lever": LeverConnector,
    "ashby": AshbyConnector,
    "linkedin": JobSpyLinkedInConnector,
    "naukri": JobSpyNaukriConnector,
    "indeed": JobSpyIndeedConnector,
    "internshala": InternshalaConnector,
}

__all__ = [
    "BaseConnector", "NormalizedJob", "HealthResult",
    "GreenhouseConnector", "LeverConnector", "AshbyConnector", "SampleConnector",
    "JobSpyLinkedInConnector", "JobSpyNaukriConnector", "JobSpyIndeedConnector",
    "InternshalaConnector",
    "CONNECTOR_REGISTRY",
]
