"""Настройки приложения и пути хранения.

Все пути вычисляются относительного профиля пользователя с помощью platformdirs.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

from platformdirs import user_data_dir, user_log_dir


APP_NAME: Final[str] = "Sloggers"
APP_AUTHOR: Final[str] = "Sloggers"  # используется для каталога


@dataclass(frozen=True)
class AppPaths:
    """Абсолютные пути приложения.

    Не содержат логики — только предвычисленные пути к файлам/папкам.
    """

    root: Path
    accounts_dir: Path
    logs_dir: Path
    accounts_index: Path


def _compute_paths() -> AppPaths:
    root = Path(user_data_dir(APP_NAME, APP_AUTHOR))
    accounts_dir = root / "accounts"
    logs_dir = Path(user_log_dir(APP_NAME, APP_AUTHOR))
    accounts_index = root / "accounts.json"
    return AppPaths(root=root, accounts_dir=accounts_dir, logs_dir=logs_dir, accounts_index=accounts_index)


PATHS: AppPaths = _compute_paths()


def ensure_app_dirs() -> None:
    """Создаёт необходимые каталоги, если их нет."""
    PATHS.root.mkdir(parents=True, exist_ok=True)
    PATHS.accounts_dir.mkdir(parents=True, exist_ok=True)
    PATHS.logs_dir.mkdir(parents=True, exist_ok=True)

