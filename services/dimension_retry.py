"""Retry only malformed/missing 4S dimensions once in the async pipeline."""

from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable, Dict, Iterable, List

from domain.stype_prompt import STYPE_SYSTEM_PROMPT, build_stype_user_prompt
from domain.subzone_prompt import SUBZONE_SYSTEM_PROMPT, build_subzone_user_prompt
from domain.struct_prompt import STRUCT_SYSTEM_PROMPT, build_struct_user_prompt
from domain.style_detail_prompt import (
    STYLE_DETAIL_SYSTEM_PROMPT,
    build_style_detail_user_prompt,
)


async def retry_missing_dimensions_once(
    completion_call: Callable[..., Awaitable[Any]],
    missing_dimensions: Iterable[str],
    *,
    client: Any,
    model: str,
    image_url: str,
    final_style: str,
    style_top3: List[Dict[str, Any]],
    responses: Dict[str, Any],
) -> Dict[str, Any]:
    """Return response mapping with only requested dimensions replaced."""
    specs = {
        "style": {
            "system_prompt": STYLE_DETAIL_SYSTEM_PROMPT,
            "user_prompt": build_style_detail_user_prompt(
                fixed_style=final_style,
                style_top3=style_top3,
            ),
            "max_tokens": 600,
        },
        "stype": {
            "system_prompt": STYPE_SYSTEM_PROMPT,
            "user_prompt": build_stype_user_prompt(final_style),
            "max_tokens": 500,
        },
        "subzone": {
            "system_prompt": SUBZONE_SYSTEM_PROMPT,
            "user_prompt": build_subzone_user_prompt(final_style),
            "max_tokens": 800,
        },
        "struct": {
            "system_prompt": STRUCT_SYSTEM_PROMPT,
            "user_prompt": build_struct_user_prompt(final_style),
            "max_tokens": 600,
        },
    }
    retry_dimensions = [
        dimension
        for dimension in missing_dimensions
        if dimension in specs
    ]
    if not retry_dimensions:
        return responses

    tasks = []
    for dimension in retry_dimensions:
        spec = specs[dimension]
        tasks.append(
            completion_call(
                client=client,
                model=model,
                image_url=image_url,
                system_prompt=spec["system_prompt"],
                user_prompt=spec["user_prompt"],
                max_tokens=spec["max_tokens"],
                temperature=0.20,
            )
        )

    retried = await asyncio.gather(*tasks)
    updated = dict(responses)
    updated.update(dict(zip(retry_dimensions, retried)))
    return updated
