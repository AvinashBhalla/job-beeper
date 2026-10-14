from abc import ABC, abstractmethod
from typing import Any, Generator
import datetime as dt

class SourceAdapter(ABC):
    """Base class for all job source adapters."""

    def __init__(self, config: dict[str, Any]):
        self.config = config

    @abstractmethod
    def fetch(self) -> Generator[dict[str, Any], None, None]:
        """Fetch raw jobs from the source."""
        pass

    @abstractmethod
    def normalize(self, raw_job: dict[str, Any]) -> dict[str, Any]:
        """Normalize raw job data into the standard internal format."""
        pass

    def get_health(self) -> dict[str, Any]:
        """Check adapter health status."""
        return {"status": "ok", "last_check": dt.datetime.now(dt.timezone.utc).isoformat()}
