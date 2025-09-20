"""Хранение данных (аккаунты и их настройки).

Хранение реализовано на JSON для простоты и прозрачности. Для каждого аккаунта
создаётся отдельная папка с `cookies.json` и `settings.json`.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional

from .settings import PATHS


@dataclass
class AccountRecord:
    """Короткая карточка аккаунта, хранится в общем `accounts.json`.

    id: внутренний идентификатор (UUID);
    name: отображаемое имя аккаунта;
    base_url: базовый URL сайта (по умолчанию https://avtor24.ru);
    """

    id: str
    name: str
    base_url: str = "https://avtor24.ru"


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


def list_accounts() -> List[AccountRecord]:
    raw = _read_json(PATHS.accounts_index)
    items = raw.get("accounts", [])
    return [AccountRecord(**item) for item in items]


def save_accounts(items: List[AccountRecord]) -> None:
    data = {"accounts": [asdict(a) for a in items]}
    _write_json(PATHS.accounts_index, data)


def get_account(acc_id: str) -> Optional[AccountRecord]:
    for a in list_accounts():
        if a.id == acc_id:
            return a
    return None


def create_account(name: str, base_url: str = "https://avtor24.ru") -> AccountRecord:
    """Создаёт запись аккаунта и возвращает её.

    Физические файлы аккаунта (cookies/settings) появятся при сохранении в окне аккаунта.
    """
    new = AccountRecord(id=str(uuid.uuid4()), name=name, base_url=base_url)
    items = list_accounts()
    items.append(new)
    save_accounts(items)
    return new


def delete_account(acc_id: str) -> None:
    items = [a for a in list_accounts() if a.id != acc_id]
    save_accounts(items)
    # Удаляем папку аккаунта аккуратно (если есть)
    acc_dir = account_dir(acc_id)
    if acc_dir.exists():
        for p in sorted(acc_dir.glob("**/*"), reverse=True):
            try:
                p.unlink()
            except IsADirectoryError:
                p.rmdir()
        try:
            acc_dir.rmdir()
        except OSError:
            pass


def account_dir(acc_id: str) -> Path:
    return PATHS.accounts_dir / acc_id


def account_cookies_path(acc_id: str) -> Path:
    return account_dir(acc_id) / "cookies.json"


def account_settings_path(acc_id: str) -> Path:
    return account_dir(acc_id) / "settings.json"


def load_account_settings(acc_id: str) -> dict:
    path = account_settings_path(acc_id)
    if not path.exists():
        # Значения по умолчанию — минимально необходимые для старта
        return {
            "interval_seconds": 3,
            "followup_delay_minutes": 5,
            "filters": {
                "types": [],  # список ID типов работ
                "subjects": [],  # список ID предметов
                "noBids": True,
                "less3bids": True,
                "contractual": True,
            },
            "templates": {
                "welcome_path": "",  # путь к txt файлу с приветствием
                "followup_path": "",  # путь к txt файлу с догоняющим
            },
        }
    return _read_json(path)


def save_account_settings(acc_id: str, data: dict) -> None:
    _write_json(account_settings_path(acc_id), data)


def save_account_cookies(acc_id: str, cookies: List[Dict]) -> None:
    _write_json(account_cookies_path(acc_id), {"cookies": cookies})


def load_account_cookies(acc_id: str) -> List[Dict]:
    raw = _read_json(account_cookies_path(acc_id))
    return raw.get("cookies", [])
