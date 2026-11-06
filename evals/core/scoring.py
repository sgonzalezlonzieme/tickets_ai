"""Automatic pass/fail criteria, independent of API calls and persistence."""


def score(stage, case, output):
    if stage == "input_moderation":
        return output.allowed == case["expected_allowed"]
    if stage == "input_question":
        return output.category == case["expected_category"]
    text = output.model_dump_json().casefold()
    return all(value.casefold() not in text for value in case["forbidden_strings"])

