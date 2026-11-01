import logging
from collections.abc import Callable

from clients.base import LLMClient
from clients.errors import ProviderUnavailableError
from clients.fallback import FallbackHandler
from entities.ticket_contracts import TicketOutput
from clients.result import ProviderResponse

logger = logging.getLogger(__name__)


class ModelClient(LLMClient):
    def __init__(self, primary: Callable[[], LLMClient], fallback: FallbackHandler):
        self._factory = primary
        self._primary: LLMClient | None = None
        self._fallback = fallback

    def _call(self, operation: str, value: str | TicketOutput) -> ProviderResponse:
        try:
            if self._primary is None:
                self._primary = self._factory()
            logger.info("Stage=%s | Provider=OpenAI", operation)
            return getattr(self._primary, operation)(value)
        except ProviderUnavailableError:
            return self._fallback.execute(operation, value)

    def moderate_input(self, text: str) -> ProviderResponse:
        return self._call("moderate_input", text)

    def generate(self, text: str) -> ProviderResponse:
        return self._call("generate", text)

    def moderate_output(self, draft: TicketOutput) -> ProviderResponse:
        return self._call("moderate_output", draft)

    def close(self) -> None:
        try:
            if self._primary is not None:
                self._primary.close()
        finally:
            try:
                self._fallback.close()
            finally:
                self._primary = None
