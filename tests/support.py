import json

def ticket_output(category="account", **overrides):
    result = {
        "answer": "We can help you recover access to your account.",
        "confidence": 0.95,
        "category": category,
        "actions": ["Guide the user through the password recovery process."],
    }
    result.update(overrides)
    return result


def response_body(text=None, status="completed", refusal=False):
    if text is None:
        text = json.dumps(ticket_output())
    content = (
        {"type": "refusal", "refusal": "Cannot process this request."}
        if refusal
        else {"type": "output_text", "text": text, "annotations": []}
    )
    return {
        "id": "resp_test",
        "object": "response",
        "created_at": 1.0,
        "model": "gpt-6-luna",
        "status": status,
        "output": [
            {
                "id": "rs_test",
                "type": "reasoning",
                "summary": [],
                "encrypted_content": "test-encrypted-content",
            },
            {
                "id": "msg_test",
                "type": "message",
                "status": "completed",
                "role": "assistant",
                "content": [content],
            },
        ],
        "metadata": {"test": "raw-body-field"},
    }




def provider_response(body):
    from entities.response import OpenAIResponse
    from clients.result import ProviderResponse
    parsed = OpenAIResponse.model_validate(body)
    return ProviderResponse(
        status=parsed.status, output_text=parsed.output_text,
        refused=any(content.type == "refusal"
                    for item in parsed.output if item.type == "message"
                    for content in item.content),
    )
