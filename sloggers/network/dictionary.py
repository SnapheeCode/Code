from __future__ import annotations

"""Загрузка справочников (типы работ и категории) через GraphQL."""

import asyncio
from typing import Dict, List

import httpx

from .graphql_client import GraphQLClient
from .queries import GET_DICTIONARY


async def fetch_dictionary_async(base_url: str, cookies: list[dict]) -> Dict[str, List[dict]]:
    client = GraphQLClient(base_url=base_url, cookies=cookies, endpoint="/graphql")
    try:
        data = await client.call(GET_DICTIONARY, operation_name="getDictionary")
        d = data.get("dictionarylist", {})
        return {
            "worktypes": d.get("worktypes", []),
            "workcategoriesgroup": d.get("workcategoriesgroup", []),
        }
    finally:
        await client.aclose()


def fetch_dictionary(base_url: str, cookies: list[dict]) -> Dict[str, List[dict]]:
    """Синхронная обёртка для использования из UI-потока (через вспомогательный поток)."""
    return asyncio.run(fetch_dictionary_async(base_url, cookies))

