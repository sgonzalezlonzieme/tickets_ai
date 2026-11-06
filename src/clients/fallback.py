import logging
from collections.abc import Callable

from clients.base import LLMClient
from entities.ticket_contracts import TicketOutput
from clients.result import ProviderResponse

logger = logging.getLogger(__name__)


class FallbackHandler:
    def __init__(self, backup: Callable[[], LLMClient], *,
                 primary_name: str = "OpenAI", backup_name: str = "Gemini"):
        self._primary_name = primary_name
        self._backup_name = backup_name
        self._factory = backup
        self._client: LLMClient | None = None

    def execute(self, operation: str, value: str | TicketOutput) -> ProviderResponse:
        logger.warning("Stage=%s | %s unavailable; trying %s",
                       operation, self._primary_name, self._backup_name)
        if self._client is None:
            self._client = self._factory()
        logger.info("Stage=%s | Provider=%s", operation, self._backup_name)
        return getattr(self._client, operation)(value)

    def close(self) -> None:
        if self._client is not None:
            try:
                self._client.close()
            finally:
                self._client = None
