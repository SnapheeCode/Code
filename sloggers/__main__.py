"""Точка входа приложения.

Без аргументов — запускает лаунчер аккаунтов.
С аргументом `--account <id>` — открывает окно конкретного аккаунта.

Дополнительный блок внизу позволяет корректно работать в режиме одиночного
скрипта (PyInstaller), когда `__package__` не определён.
"""
from __future__ import annotations

import sys
from argparse import ArgumentParser
from pathlib import Path

from PySide6.QtWidgets import QApplication


if __package__ in (None, ""):
    # Когда модуль запускается как обычный скрипт (например, в exe), нужно вручную
    # добавить родительский каталог в sys.path, чтобы сработали относительные импорты.
    package_root = Path(__file__).resolve().parent
    parent = package_root.parent
    if str(parent) not in sys.path:
        sys.path.insert(0, str(parent))
    __package__ = "sloggers"

from .launcher_window import LauncherWindow
from .account_window import AccountWindow
from .core.settings import ensure_app_dirs


def main() -> int:
    # Обязательная инициализация каталогов приложения (логика хранения и логов)
    ensure_app_dirs()

    parser = ArgumentParser(description="Sloggers — лаунчер и окна аккаунтов")
    parser.add_argument("--account", dest="account_id", help="ID аккаунта для запуска окна", default=None)
    args = parser.parse_args()

    app = QApplication(sys.argv)

    if args.account_id:
        # Запускаем окно аккаунта (отдельный экземпляр)
        win = AccountWindow(account_id=args.account_id)
        win.show()
    else:
        # Запускаем лаунчер (управление аккаунтами)
        win = LauncherWindow()
        win.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
