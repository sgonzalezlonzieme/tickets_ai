from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

Model = TypeVar("Model", bound=BaseModel)


class DataValidationError(ValueError):


    def __init__(self, errors: list[dict[str, Any]]) -> None:
        self.errors = errors
        super().__init__("Data does not match the expected schema.")


def _category(error_type: str) -> str:
    if error_type in {"json_invalid", "json_type"}:
        return "invalid_json"

    if error_type == "missing":
        return "missing_field"

    if error_type == "extra_forbidden":
        return "extra_field"

    if error_type.endswith("_type"):
        return "invalid_type"

    if error_type.endswith("_parsing"):
        return "parsing_error"

    return "invalid_value"


def validate_data(model: type[Model], data: Any) -> Model:

    try:
        if isinstance(data, (str, bytes, bytearray)):
            return model.model_validate_json(data)

        return model.model_validate(data)

    except ValidationError as error:
        details = [
            {
                "category": _category(item["type"]),
                "type": item["type"],
                "loc": list(item["loc"]),
                "msg": item["msg"],
            }
            for item in error.errors(include_input=False, include_context=False)
        ]

        raise DataValidationError(details) from error
