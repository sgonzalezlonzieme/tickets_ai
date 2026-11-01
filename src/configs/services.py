from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services import TicketService


@lru_cache(maxsize=1)
def get_ticket_service() -> "TicketService":
    from services import TicketService

    return TicketService()
