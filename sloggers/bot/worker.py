from __future__ import annotations

"""Рабочий поток бота для аккаунта.

Воркер запускается в QThread, внутри которого крутится asyncio‑цикл.
Задачи:
- периодически опрашивать ленту заказов (GraphQL);
- сортировать/приоритизировать новые заказы;
- отправлять отклики и планировать догоняющие сообщения;
- соблюдать настраиваемый интервал (минимум 3 секунды).

Примечание: схема GraphQL может отличаться; при интеграции проверьте в инструментах сети.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

from PySide6.QtCore import QThread, Signal

from ..network.graphql_client import GraphQLClient
from ..network.queries import (
    GET_AUCTION_WITH_CONSTRAINTS,
    GET_ORDER_FOR_BID,
    MAKE_OFFER,
    ADD_COMMENT,
)
from .filters import build_graphql_filters, order_passes_local_filters
from .messages import load_text_file, render_template


log = logging.getLogger(__name__)


@dataclass
class _Runtime:
    processed_ids: set[str]
    page: int


class BotWorker(QThread):
    """Воркер бота, исполняемый в отдельном потоке.

    Параметры конструктора передаются из окна аккаунта и валидируются на стороне UI.
    """

    def __init__(self, account_id: str, settings: dict, cookies: List[Dict]):
        super().__init__()
        self._account_id = account_id
        self._settings = settings
        self._cookies = cookies
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._stop_event: Optional[asyncio.Event] = None
        self._pending_stop: bool = False

    def stop(self) -> None:
        """Запрос на остановку воркера."""
        # Сигналим из главного потока — установим флаг или событие, если доступно
        loop = self._loop
        if loop and self._stop_event:
            if loop.is_running():
                loop.call_soon_threadsafe(self._stop_event.set)
        else:
            self._pending_stop = True

    def run(self) -> None:  # QThread API
        """Точка входа потока. Создаёт и запускает asyncio‑цикл."""
        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._stop_event = asyncio.Event()
            if self._pending_stop:
                # Если запрос на остановку пришёл до старта цикла
                self._stop_event.set()
            self._loop.run_until_complete(self._main())
        except Exception as e:
            log.exception("Ошибка в воркере бота: %s", e)
        finally:
            try:
                self._loop.close()
            except Exception:
                pass

    async def _main(self) -> None:
        base_url = self._settings.get("base_url", "https://avtor24.ru")
        # Основной клиент для аукциона
        client = GraphQLClient(base_url=base_url, cookies=self._cookies, endpoint="/graphql")
        # Клиент чата/комментариев — отдельный endpoint
        self._chat_client = GraphQLClient(base_url=base_url, cookies=self._cookies, endpoint="/graphqlapi")

        runtime = _Runtime(processed_ids=set(), page=1)
        interval = max(3, int(self._settings.get("interval_seconds", 3)))

        try:
            assert self._stop_event is not None
            while not self._stop_event.is_set():
                try:
                    await self._poll_once(client, runtime)
                except Exception as e:
                    log.warning("Проблема при опросе: %s", e)

                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=interval)
                except asyncio.TimeoutError:
                    pass
        finally:
            await client.aclose()
            await self._chat_client.aclose()

    async def _poll_once(self, client: GraphQLClient, rt: _Runtime) -> None:
        """Один цикл опроса ленты заказов и попытка отклика."""
        f_filter, f_constraints = build_graphql_filters(self._settings)
        variables = {
            "filter": f_filter,
            "constraintsFilter": f_constraints,
            "limit": 30,
            "pagination": {"pageTo": rt.page},
            "skip": None,
        }

        data = await client.call(GET_AUCTION_WITH_CONSTRAINTS, variables, operation_name="GetAuctionWithConstraints")
        block = data.get("orders", {})
        orders: List[dict] = block.get("orders", [])
        if not orders:
            log.info("Заказы не найдены на странице %s", rt.page)
            # Переходим на первую страницу снова
            rt.page = 1
            return

        # Приоритизация: сначала самые свежие (creation по убыванию)
        orders.sort(key=lambda x: x.get("creation", 0), reverse=True)

        processed_any = False
        for order in orders:
            oid = str(order.get("id"))
            if oid in rt.processed_ids:
                continue
            if not order_passes_local_filters(order, self._settings):
                continue
            # Доп. приоритет: если нет откликов или меньше 3
            if order.get("countOffers", 99) > 0 and self._settings.get("filters", {}).get("noBids", True):
                continue

            ok = await self._try_make_offer(client, order)
            rt.processed_ids.add(oid)
            processed_any = processed_any or ok
            # Соблюдаем минимальный интервал между ставками: одна ставка за цикл
            if ok:
                break

        # Если на текущей странице не было подходящих — перелистываем
        if not processed_any:
            rt.page = 1 if rt.page >= 10 else rt.page + 1
        else:
            # После успешной обработки — вернёмся к началу, чтобы ловить новые
            rt.page = 1

    async def _try_make_offer(self, client: GraphQLClient, order: dict) -> bool:
        """Пробует отправить отклик по заказу и запланировать догоняющее сообщение."""
        oid = order.get("id")
        if not oid:
            return False
        # Уточним параметры для ставки
        bid_info = await client.call(GET_ORDER_FOR_BID, {"id": oid}, operation_name="getOrderForBid")
        node = bid_info.get("getOrderForBid", {})

        # Простая стратегия: берём recommendedBudget, снижаем на 5% и округляем вниз до целого
        rec = node.get("recommendedBudget") or order.get("recommendedBudget") or order.get("budget") or 0
        bid = max(1, int(rec * 0.95))

        # Формируем приветственное сообщение из шаблона
        tmpl_welcome_path = self._settings.get("templates", {}).get("welcome_path", "")
        welcome = load_text_file(tmpl_welcome_path)
        ctx = {
            "order_id": str(oid),
            "order_title": order.get("title", ""),
        }
        msg = render_template(welcome, ctx) or "Здравствуйте! Готов выполнить ваш заказ."

        try:
            variables = {"orderId": oid, "bid": bid, "message": msg, "expired": None, "subscribe": False}
            resp = await client.call(MAKE_OFFER, variables, operation_name="makeOffer")
            _ = resp.get("makeOffer")
            log.info("Отклик отправлен по заказу %s (ставка %s)", oid, bid)

            # Планируем догоняющее сообщение в фоне (best effort)
            asyncio.create_task(self._send_followup_later(client, oid, order))
            return True
        except Exception as e:
            log.warning("Не удалось отправить отклик по %s: %s", oid, e)
            return False

    async def _send_followup_later(self, client: GraphQLClient, oid: str, order: dict) -> None:
        """Отправка догоняющего сообщения через заданное время.

        Реальная мутация чата может отличаться; здесь — заглушка/шаблон.
        """
        delay_min = int(self._settings.get("followup_delay_minutes", 5))
        await asyncio.sleep(max(1, delay_min) * 60)

        followup_path = self._settings.get("templates", {}).get("followup_path", "")
        text = render_template(load_text_file(followup_path), {
            "order_id": str(oid),
            "order_title": order.get("title", ""),
        }) or "Готов обсудить детали и приступить."

        try:
            variables = {"orderId": oid, "text": text}
            await self._chat_client.call(ADD_COMMENT, variables, operation_name="addComment")
            log.info("Догоняющее сообщение отправлено по заказу %s", oid)
        except Exception as e:
            log.warning("Не удалось отправить догоняющее по %s: %s", oid, e)
