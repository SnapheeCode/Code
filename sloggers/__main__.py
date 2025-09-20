"""Точка входа приложения.

Без аргументов — запускает лаунчер аккаунтов.
С аргументом `--account <id>` — открывает окно конкретного аккаунта.
"""
from __future__ import annotations

import sys
from argparse import ArgumentParser

from PySide6.QtWidgets import QApplication

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

