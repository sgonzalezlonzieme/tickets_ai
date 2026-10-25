from functools import lru_cache

from clients import OpenAIClient


@lru_cache(maxsize=1)
def get_openai_client() -> OpenAIClient:
    return OpenAIClient()


def close_openai_client() -> None:
    if not get_openai_client.cache_info().currsize:
        return

    try:
        get_openai_client().close()

    finally:
        get_openai_client.cache_clear()
