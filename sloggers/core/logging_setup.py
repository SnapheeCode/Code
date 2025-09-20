"""Настройка логирования.

Логи пишутся в файл пользователя и могут дублироваться в интерфейс.
"""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from .settings import PATHS


def setup_logging(name: str = "sloggers", to_console: bool = False) -> None:
    """Глобальная настройка логгера.

    - Пишем в файл с ротацией;
    - При необходимости — дублируем в консоль (для разработки).
    """
    PATHS.logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = PATHS.logs_dir / f"{name}.log"

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    file_handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    if to_console:
        console = logging.StreamHandler()
        console.setFormatter(fmt)
        logger.addHandler(console)


class QtLogProxyHandler(logging.Handler):
    """Прокси‑хендлер для отправки логов в UI через колбэк."""

    def __init__(self, send_fn):
        super().__init__()
        self._send = send_fn

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            self._send(msg)
        except Exception:
            pass

