from configs import clients


def close_openai_client() -> None:
    if not clients.get_openai_client.cache_info().currsize:
        return
    try:
        clients.get_openai_client().close()
    finally:
        clients.get_openai_client.cache_clear()


def close_llm_client() -> None:
    try:
        if clients.get_llm_client.cache_info().currsize:
            clients.get_llm_client().close()
        else:
            try:
                close_openai_client()
            finally:
                if clients.get_gemini_client.cache_info().currsize:
                    clients.get_gemini_client().close()
    finally:
        clients.get_llm_client.cache_clear()
        clients.get_openai_client.cache_clear()
        clients.get_gemini_client.cache_clear()
