from __future__ import annotations

"""Асинхронный GraphQL‑клиент на httpx.

Клиент использует cookies, сохранённые из встроенного браузера, чтобы работать от имени
пользовательской сессии. В случае необходимости можно добавить Bearer‑авторизацию.
"""

import asyncio
import logging
from typing import Any, Dict, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


log = logging.getLogger(__name__)


class GraphQLClient:
    """Минималистичный GraphQL‑клиент c повторными попытками на сетевых ошибках.

    Можно указать конкретный endpoint (по умолчанию `/graphql`). Для чата
    на avtor24.ru используется `/graphqlapi`.
    """

    def __init__(self, base_url: str, cookies: list[dict], endpoint: str = "/graphql"):
        self._endpoint = endpoint if endpoint.startswith("/") else "/" + endpoint
        self._base_url = base_url.rstrip("/") + self._endpoint
        self._client = httpx.AsyncClient(timeout=20.0, http2=True)
        # Восстанавливаем cookies в сессию
        for c in cookies:
            try:
                self._client.cookies.set(name=c["name"], value=c["value"], domain=c.get("domain"), path=c.get("path", "/"))
            except Exception:
                pass

    async def aclose(self) -> None:
        await self._client.aclose()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type((httpx.TransportError, httpx.ReadTimeout)),
        reraise=True,
    )
    async def call(self, query: str, variables: Optional[Dict[str, Any]] = None, operation_name: Optional[str] = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"query": query}
        if variables is not None:
            payload["variables"] = variables
        if operation_name is not None:
            payload["operationName"] = operation_name

        log.debug("GraphQL call: %s", operation_name or query[:60])
        resp = await self._client.post(self._base_url, json=payload, headers={"Content-Type": "application/json"})
        resp.raise_for_status()
        data = resp.json()
        if "errors" in data:
            raise RuntimeError(f"GraphQL errors: {data['errors']}")
        return data.get("data", {})
