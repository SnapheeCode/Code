from __future__ import annotations

"""Применение фильтров к заказам.

Фильтры задаются через настройки аккаунта (ID типов и предметов и флаги).
"""

from typing import Any, Dict, List


def build_graphql_filters(settings: dict) -> tuple[dict, dict]:
    """Готовит `filter` и `constraintsFilter` для запроса GetAuctionWithConstraints.

    Возвращает кортеж (filter, constraintsFilter).
    """
    f = settings.get("filters", {})
    filter_obj = {
        "types": f.get("types", []),
        # Используем категории (как "предметы") при наличии
        "categories": f.get("categories", []),
        "budgetFrom": 0,
        "budgetTo": 200000,
        "deadlineFrom": 0,
        "deadlineTo": 365,
        "contractual": bool(f.get("contractual", True)),
        "noBids": bool(f.get("noBids", True)),
        "less3bids": bool(f.get("less3bids", True)),
    }
    constraints = {
        "withoutMyBids": True,
    }
    return filter_obj, constraints


def order_passes_local_filters(order: dict, settings: dict) -> bool:
    """Локальная валидация заказа по спискам ID.

    Минимально: если заданы типы/предметы — проверяем соответствие по id.
    """
    f = settings.get("filters", {})
    types: List[str] = [str(x) for x in f.get("types", [])]
    categories: List[str] = [str(x) for x in f.get("categories", [])]

    if types:
        t_id = str(order.get("type", {}).get("id"))
        if t_id and t_id not in types:
            return False
    if categories:
        c_id = str(order.get("category", {}).get("id"))
        if c_id and c_id not in categories:
            return False
    return True
