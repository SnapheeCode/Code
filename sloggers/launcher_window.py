from __future__ import annotations

"""Окно лаунчера аккаунтов.

Функции:
- Просмотр списка аккаунтов;
- Добавление/удаление аккаунтов;
- Запуск отдельного окна аккаунта (в новом процессе).
"""

import subprocess
import sys
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QLineEdit,
    QLabel,
    QMessageBox,
)

from .core.storage import list_accounts, create_account, delete_account, AccountRecord


class LauncherWindow(QWidget):
    """Простое окно‑лаунчер с CRUD операций по аккаунтам."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Sloggers — лаунчер аккаунтов")
        self.resize(520, 420)

        self._list = QListWidget()
        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("Имя аккаунта")

        self._btn_add = QPushButton("Добавить аккаунт")
        self._btn_del = QPushButton("Удалить выбранный")
        self._btn_open = QPushButton("Открыть окно аккаунта")

        top = QVBoxLayout(self)
        top.addWidget(QLabel("Список аккаунтов:"))
        top.addWidget(self._list)

        row = QHBoxLayout()
        row.addWidget(self._name_input)
        row.addWidget(self._btn_add)
        top.addLayout(row)

        row2 = QHBoxLayout()
        row2.addWidget(self._btn_del)
        row2.addWidget(self._btn_open)
        top.addLayout(row2)

        # Сигналы
        self._btn_add.clicked.connect(self._on_add)
        self._btn_del.clicked.connect(self._on_del)
        self._btn_open.clicked.connect(self._on_open)

        self._refresh()

    # Внутренняя утилита: загрузка списка
    def _refresh(self) -> None:
        self._list.clear()
        for acc in list_accounts():
            item = QListWidgetItem(f"{acc.name} — {acc.id}")
            item.setData(Qt.UserRole, acc)
            self._list.addItem(item)

    def _selected(self) -> Optional[AccountRecord]:
        item = self._list.currentItem()
        if not item:
            return None
        return item.data(Qt.UserRole)

    # Обработчики
    def _on_add(self) -> None:
        name = self._name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Внимание", "Введите имя аккаунта")
            return
        create_account(name)
        self._name_input.clear()
        self._refresh()

    def _on_del(self) -> None:
        acc = self._selected()
        if not acc:
            QMessageBox.information(self, "Информация", "Выберите аккаунт для удаления")
            return
        ok = QMessageBox.question(self, "Подтверждение", f"Удалить аккаунт: {acc.name}?")
        if ok == QMessageBox.StandardButton.Yes:
            delete_account(acc.id)
            self._refresh()

    def _on_open(self) -> None:
        acc = self._selected()
        if not acc:
            QMessageBox.information(self, "Информация", "Выберите аккаунт для открытия")
            return
        # Запускаем новый процесс с аргументом --account <id>
        # Используем ту же интерпретацию, что и текущий процесс
        # Если запаковано PyInstaller'ом — перезапускаем тот же .exe
        if getattr(sys, "frozen", False):
            exe = sys.executable
            subprocess.Popen([exe, "--account", acc.id])
        else:
            python_exe = sys.executable
            subprocess.Popen([python_exe, "-m", "sloggers", "--account", acc.id])
