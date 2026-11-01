import logging
from collections.abc import Callable, Mapping

from pydantic import BaseModel, ValidationError

from clients.base import LLMClient
from clients.errors import ParsingRetriesExhaustedError
from entities.ticket_contracts import TicketOutput
from clients.result import ProviderResponse

logger = logging.getLogger(__name__)


class ParsingRetryClient(LLMClient):
    MAX_RETRIES = 2

    def __init__(self, factory: Callable[[], LLMClient], response_models: Mapping[str, type[BaseModel]]):
        self._factory = factory
        self._response_models = response_models
        self._client: LLMClient | None = None

    def _call(
        self,
        operation: str,
        value: str | TicketOutput,
    ) -> ProviderResponse:
        if self._client is None:
            self._client = self._factory()
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                response = getattr(self._client, operation)(value)
                if response.status == "completed" and not response.refused:
                    self._response_models[operation].model_validate_json(response.output_text)
                return response
            except ValidationError:
                logger.warning(
                    "Stage=%s | Invalid model output | Attempt=%s/%s",
                    operation, attempt + 1, self.MAX_RETRIES + 1,
                )
        raise ParsingRetriesExhaustedError("Model output remained invalid after two retries.") from None

    def moderate_input(self, text: str) -> ProviderResponse:
        return self._call("moderate_input", text)

    def generate(self, text: str) -> ProviderResponse:
        return self._call("generate", text)

    def moderate_output(self, draft: TicketOutput) -> ProviderResponse:
        return self._call("moderate_output", draft)

    def close(self) -> None:
        if self._client is not None:
            try:
                self._client.close()
            finally:
                self._client = None
