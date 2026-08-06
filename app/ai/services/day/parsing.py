"""LLM-output parsing for the daily insight/suggestion generation pipeline.

These helpers turn a model's raw reply into clean insight/suggestion dicts. They
live next to their only caller (`insights.py`) rather than in the model-routing
layer (`app/ai/utils.py`).
"""

import json
import logging
import re

from pydantic import ValidationError

from app.schemas.font_awesome import FAIcon


def extract_json_array(text: str) -> list[dict[str, object]]:
    """Extract a JSON array from text that may contain additional content."""
    logging.info(f"Attempting to extract JSON array from text of length {len(text)}")
    logging.debug(f"Text content: {text[:500]}...")

    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            logging.info(f"Successfully parsed JSON directly, found {len(parsed)} items")
            return parsed
    except Exception as e:
        logging.debug(f"Direct JSON parsing failed: {e}")

    match = re.search(r"\[[\s\S]*\]", text)
    if not match:
        logging.error("No JSON array found in text")
        raise ValueError("LLM did not return a JSON array")

    json_str = match.group(0)
    logging.debug(f"Found JSON array: {json_str}")

    try:
        parsed = json.loads(json_str)
    except Exception as e:
        logging.exception("Failed to parse extracted JSON")
        raise ValueError(f"Failed to parse JSON array: {e}") from e

    if not isinstance(parsed, list):
        logging.error(f"Parsed JSON is not an array: {type(parsed)}")
        raise ValueError("LLM did not return a JSON array")  # noqa: TRY004  # matches the branch above

    logging.info(f"Successfully extracted and parsed JSON array with {len(parsed)} items")
    return parsed


def sanitize_items(items: list[dict[str, object]]) -> list[dict[str, object]]:
    """Sanitize a list of items, ensuring proper icon handling."""
    logging.info(f"Sanitizing {len(items)} items")
    sanitized: list[dict[str, object]] = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            logging.warning(f"Item {i + 1} is not a dict: {type(item)}")
            continue

        icon = item.get("icon")
        if icon is not None:
            logging.info(f"Item {i + 1} has icon: {icon} (type: {type(icon)})")
            try:
                if isinstance(icon, FAIcon):
                    item["icon"] = icon
                    logging.info(f"Item {i + 1}: Icon is already valid FAIcon")
                elif isinstance(icon, dict):
                    item["icon"] = FAIcon(**icon)
                    logging.info(f"Item {i + 1}: Icon converted from dict to FAIcon")
                else:
                    logging.warning(
                        f"Item {i + 1}: Invalid icon type {type(icon)}, setting to None"
                    )
                    item["icon"] = None
            except ValidationError:
                logging.exception(f"Item {i + 1}: Icon validation failed, setting to None")
                item["icon"] = None
        else:
            logging.info(f"Item {i + 1}: No icon provided")

        sanitized.append(item)

    logging.info(f"Sanitized {len(sanitized)} items")
    return sanitized
