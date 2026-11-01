from abc import ABC, abstractmethod

from entities.ticket_contracts import TicketOutput
from clients.result import ProviderResponse


class LLMClient(ABC):


    @abstractmethod
    def moderate_input(self, text: str) -> ProviderResponse:
        pass

    @abstractmethod
    def generate(self, text: str) -> ProviderResponse:
        pass

    @abstractmethod
    def moderate_output(self, draft: TicketOutput) -> ProviderResponse:
        pass

    @abstractmethod
    def close(self) -> None:
        pass
