from abc import ABC, abstractmethod


class BaseConnector(ABC):
    provider_name: str = "base"

    @abstractmethod
    async def send(self, to: str, message: str) -> dict:
        """Send an SMS. Return dict with message_id and status."""

    @abstractmethod
    async def get_delivery_status(self, message_id: str) -> str:
        """Return delivery status string: sent | delivered | failed."""
