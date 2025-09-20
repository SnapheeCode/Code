from __future__ import annotations

"""Окно аккаунта с логическими вкладками.

Вкладки:
- Браузер: встроенный QWebEngineView для логина на сайте и кнопка «Скопировать куки»;
- Бот: старт/стоп, интервал, задержка догоняющего, лог событий;
- Шаблоны: выбор .txt файлов для приветствия и догоняющего сообщения;
- Фильтры: типы работ и предметы (ID списки, на этапе MVP — вручную через поля).

Примечание: все операции записи/чтения — в папке аккаунта.
"""

import json
import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QUrl, Signal, QThread
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QWidget,
    QTabWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
    QFileDialog,
    QSpinBox,
    QTextEdit,
    QMessageBox,
    QCheckBox,
    QListWidget,
    QListWidgetItem,
)
from PySide6.QtWebEngineCore import QWebEngineProfile
from PySide6.QtWebEngineWidgets import QWebEngineView

from .core.logging_setup import QtLogProxyHandler, setup_logging
from .core.storage import (
    account_cookies_path,
    account_settings_path,
    load_account_settings,
    save_account_settings,
    load_account_cookies,
)
from .bot.worker import BotWorker
from .network.dictionary import fetch_dictionary


class AccountWindow(QWidget):
    """Окно конкретного аккаунта."""

    # Сигнал для получения логов от бота
    log_signal = Signal(str)

    def __init__(self, account_id: str) -> None:
        super().__init__()
        self._account_id = account_id
        self.setWindowTitle(f"Sloggers — аккаунт {account_id}")
        self.resize(1000, 700)

        setup_logging(to_console=False)

        self._tabs = QTabWidget()

        # Вкладка Браузер
        self._browser = QWebEngineView()
        self._browser_profile = QWebEngineProfile.defaultProfile()
        self._btn_copy_cookies = QPushButton("Скопировать куки")
        self._btn_open_site = QPushButton("Открыть avtor24.ru во внешнем браузере")

        browser_tab = QWidget()
        v1 = QVBoxLayout(browser_tab)
        v1.addWidget(self._browser)
        rowb = QHBoxLayout()
        rowb.addWidget(self._btn_open_site)
        rowb.addStretch(1)
        rowb.addWidget(self._btn_copy_cookies)
        v1.addLayout(rowb)

        # Вкладка Бот
        bot_tab = QWidget()
        v2 = QVBoxLayout(bot_tab)

        self._interval = QSpinBox()
        self._interval.setRange(3, 60)
        self._interval.setValue(3)
        self._followup_delay = QSpinBox()
        self._followup_delay.setRange(1, 120)
        self._followup_delay.setValue(5)

        self._chk_nobids = QCheckBox("Только без откликов")
        self._chk_less3 = QCheckBox("Меньше 3 откликов")
        self._chk_contractual = QCheckBox("Только договорные")
        self._chk_nobids.setChecked(True)
        self._chk_less3.setChecked(True)
        self._chk_contractual.setChecked(True)

        self._types_ids = QLineEdit()
        self._types_ids.setPlaceholderText("ID типов работ через запятую, напр. 9,11")
        self._subjects_ids = QLineEdit()
        self._subjects_ids.setPlaceholderText("ID предметов через запятую")

        self._btn_start = QPushButton("Запустить бота")
        self._btn_stop = QPushButton("Остановить бота")
        self._btn_stop.setEnabled(False)

        self._log_view = QTextEdit()
        self._log_view.setReadOnly(True)

        # Разметка вкладки Бот
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Интервал (сек):"))
        row1.addWidget(self._interval)
        row1.addSpacing(20)
        row1.addWidget(QLabel("Догоняющее (мин):"))
        row1.addWidget(self._followup_delay)
        row1.addStretch(1)
        v2.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(self._chk_nobids)
        row2.addWidget(self._chk_less3)
        row2.addWidget(self._chk_contractual)
        row2.addStretch(1)
        v2.addLayout(row2)

        v2.addWidget(QLabel("Фильтры по ID:"))
        v2.addWidget(self._types_ids)
        v2.addWidget(self._subjects_ids)

        row3 = QHBoxLayout()
        row3.addWidget(self._btn_start)
        row3.addWidget(self._btn_stop)
        row3.addStretch(1)
        v2.addLayout(row3)

        v2.addWidget(QLabel("Журнал событий:"))
        v2.addWidget(self._log_view)

        # Вкладка Шаблоны
        tmpl_tab = QWidget()
        v3 = QVBoxLayout(tmpl_tab)
        self._welcome_path = QLineEdit()
        self._welcome_path.setPlaceholderText("Путь к приветственному шаблону (.txt)")
        self._followup_path = QLineEdit()
        self._followup_path.setPlaceholderText("Путь к догоняющему шаблону (.txt)")
        self._btn_choose_welcome = QPushButton("Выбрать файл приветствия…")
        self._btn_choose_followup = QPushButton("Выбрать файл догоняющего…")
        roww = QHBoxLayout()
        roww.addWidget(self._welcome_path)
        roww.addWidget(self._btn_choose_welcome)
        v3.addLayout(roww)
        rowf = QHBoxLayout()
        rowf.addWidget(self._followup_path)
        rowf.addWidget(self._btn_choose_followup)
        v3.addLayout(rowf)

        # Вкладка Фильтры (справочники)
        filters_tab = QWidget()
        v4 = QVBoxLayout(filters_tab)
        self._btn_reload_dict = QPushButton("Обновить справочники")
        self._types_list = QListWidget()
        self._types_list.setSelectionMode(self._types_list.MultiSelection)
        self._cats_list = QListWidget()
        self._cats_list.setSelectionMode(self._cats_list.MultiSelection)
        self._btn_save_filters = QPushButton("Сохранить фильтры")
        v4.addWidget(self._btn_reload_dict)
        v4.addWidget(QLabel("Типы работ:"))
        v4.addWidget(self._types_list)
        v4.addWidget(QLabel("Предметы/категории:"))
        v4.addWidget(self._cats_list)
        v4.addWidget(self._btn_save_filters)

        self._tabs.addTab(browser_tab, "Браузер")
        self._tabs.addTab(bot_tab, "Бот")
        self._tabs.addTab(tmpl_tab, "Шаблоны")
        self._tabs.addTab(filters_tab, "Фильтры")

        layout = QVBoxLayout(self)
        layout.addWidget(self._tabs)

        # Сигналы UI
        self._btn_open_site.clicked.connect(self._open_external)
        self._btn_copy_cookies.clicked.connect(self._copy_cookies)
        self._btn_choose_welcome.clicked.connect(lambda: self._choose_file(self._welcome_path))
        self._btn_choose_followup.clicked.connect(lambda: self._choose_file(self._followup_path))
        self._btn_start.clicked.connect(self._start_bot)
        self._btn_stop.clicked.connect(self._stop_bot)
        self.log_signal.connect(self._append_log)
        self._btn_reload_dict.clicked.connect(self._on_reload_dict)
        self._btn_save_filters.clicked.connect(self._on_save_filters)

        # Загрузка настроек аккаунта
        self._load_settings()
        # Первичная загрузка сайта во встроенном браузере
        self._browser.setUrl(QUrl("https://avtor24.ru/"))

        # Логгер в UI
        self._qt_handler = QtLogProxyHandler(self.log_signal.emit)
        self._qt_handler.setLevel(logging.INFO)
        logging.getLogger().addHandler(self._qt_handler)

        self._worker: Optional[BotWorker] = None
        self._dict_cache = None

    # Загрузка/сохранение настроек
    def _load_settings(self) -> None:
        data = load_account_settings(self._account_id)
        self._interval.setValue(int(data.get("interval_seconds", 3)))
        self._followup_delay.setValue(int(data.get("followup_delay_minutes", 5)))
        filters = data.get("filters", {})
        if filters.get("types"):
            self._types_ids.setText(",".join(str(i) for i in filters["types"]))
        if filters.get("subjects"):
            self._subjects_ids.setText(",".join(str(i) for i in filters["subjects"]))
        self._chk_nobids.setChecked(bool(filters.get("noBids", True)))
        self._chk_less3.setChecked(bool(filters.get("less3bids", True)))
        self._chk_contractual.setChecked(bool(filters.get("contractual", True)))
        tmpl = data.get("templates", {})
        self._welcome_path.setText(tmpl.get("welcome_path", ""))
        self._followup_path.setText(tmpl.get("followup_path", ""))

    def _save_settings(self) -> None:
        filters = {
            "types": [s.strip() for s in self._types_ids.text().split(",") if s.strip()],
            "subjects": [s.strip() for s in self._subjects_ids.text().split(",") if s.strip()],
            "noBids": self._chk_nobids.isChecked(),
            "less3bids": self._chk_less3.isChecked(),
            "contractual": self._chk_contractual.isChecked(),
        }
        data = {
            "interval_seconds": int(self._interval.value()),
            "followup_delay_minutes": int(self._followup_delay.value()),
            "filters": filters,
            "templates": {
                "welcome_path": self._welcome_path.text(),
                "followup_path": self._followup_path.text(),
            },
        }
        save_account_settings(self._account_id, data)

    # Вкладка Браузер
    def _open_external(self) -> None:
        QDesktopServices.openUrl(QUrl("https://avtor24.ru/"))

    def _copy_cookies(self) -> None:
        """Считывает cookies из профиля QWebEngine и сохраняет их в файл аккаунта."""
        store = self._browser_profile.cookieStore()

        collected = []

        def on_cookie_added(cookie):
            # Преобразуем cookie в простой словарь для дальнейшего использования
            domain = cookie.domain()
            name = bytes(cookie.name()).decode("utf-8", errors="ignore")
            value = bytes(cookie.value()).decode("utf-8", errors="ignore")
            path = cookie.path()
            secure = cookie.isSecure()
            http_only = cookie.isHttpOnly()
            collected.append({
                "domain": domain,
                "name": name,
                "value": value,
                "path": path,
                "secure": secure,
                "httpOnly": http_only,
            })

        def on_loaded():
            # После загрузки всех — сохраняем и показываем сообщение
            path = account_cookies_path(self._account_id)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"cookies": collected}, ensure_ascii=False, indent=2), encoding="utf-8")
            QMessageBox.information(self, "Готово", f"Куки сохранены: {path}")
            store.cookieAdded.disconnect(on_cookie_added)
            store.loaded.disconnect(on_loaded)

        # Подписываемся, инициируем загрузку
        store.cookieAdded.connect(on_cookie_added)
        store.loaded.connect(on_loaded)
        store.loadAllCookies()

    # Вкладка Бот
    def _start_bot(self) -> None:
        # Сохраняем настройки перед стартом
        self._save_settings()

        # Проверяем шаблоны
        if not Path(self._welcome_path.text()).exists():
            QMessageBox.warning(self, "Шаблон", "Укажите корректный файл приветственного сообщения (.txt)")
            return
        if not Path(self._followup_path.text()).exists():
            QMessageBox.warning(self, "Шаблон", "Укажите корректный файл догоняющего сообщения (.txt)")
            return

        # Запускаем воркер в отдельном потоке, чтобы UI не подвисал
        settings = load_account_settings(self._account_id)
        # Добавим base_url из записи аккаунта (если будет отличаться от дефолта)
        try:
            from .core.storage import get_account
            acc = get_account(self._account_id)
            if acc:
                settings["base_url"] = acc.base_url
        except Exception:
            pass
        cookies = load_account_cookies(self._account_id)
        if not cookies:
            QMessageBox.warning(self, "Куки", "Сначала авторизуйтесь во вкладке 'Браузер' и сохраните куки")
            return

        self._worker = BotWorker(account_id=self._account_id, settings=settings, cookies=cookies)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()

        self._btn_start.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._append_log("Бот запущен…")

    def _stop_bot(self) -> None:
        if self._worker:
            self._worker.stop()
        self._btn_stop.setEnabled(False)
        self._btn_start.setEnabled(True)
        self._append_log("Остановка бота…")

    def _on_worker_finished(self) -> None:
        self._append_log("Бот остановлен")
        self._btn_stop.setEnabled(False)
        self._btn_start.setEnabled(True)

    # Логи в UI
    def _append_log(self, text: str) -> None:
        self._log_view.append(text)

    # Вкладка Шаблоны
    def _choose_file(self, target: QLineEdit) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Выбрать .txt файл", "", "TXT (*.txt)")
        if path:
            target.setText(path)
            self._save_settings()

    # Вкладка Фильтры — работа со справочниками
    def _on_reload_dict(self) -> None:
        # Загружаем словари синхронно в простом вызове (на короткое время возможно подвисание UI)
        try:
            from .core.storage import get_account, load_account_cookies
            acc = get_account(self._account_id)
            cookies = load_account_cookies(self._account_id)
            if not acc or not cookies:
                QMessageBox.information(self, "Информация", "Сначала авторизуйтесь и сохраните куки")
                return
            data = fetch_dictionary(acc.base_url, cookies)
            self._dict_cache = data
            self._fill_filters_from_dict(data)
            QMessageBox.information(self, "Готово", "Справочники обновлены")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить справочники: {e}")

    def _fill_filters_from_dict(self, data: dict) -> None:
        # Сохраняем выбранные до перезагрузки
        selected_types = set(s.strip() for s in self._types_ids.text().split(',') if s.strip())
        selected_cats = set(s.strip() for s in self._subjects_ids.text().split(',') if s.strip())

        self._types_list.clear()
        for t in data.get("worktypes", []):
            item = QListWidgetItem(f"{t.get('name')} — {t.get('id')}")
            item.setData(Qt.UserRole, str(t.get('id')))
            if str(t.get('id')) in selected_types:
                item.setSelected(True)
            self._types_list.addItem(item)

        self._cats_list.clear()
        for g in data.get("workcategoriesgroup", []):
            group_name = g.get("name")
            for it in g.get("items", []):
                label = f"{group_name}: {it.get('name')} — {it.get('id')}"
                item = QListWidgetItem(label)
                item.setData(Qt.UserRole, str(it.get('id')))
                if str(it.get('id')) in selected_cats:
                    item.setSelected(True)
                self._cats_list.addItem(item)

    def _on_save_filters(self) -> None:
        # Читаем из списков и сохраняем в поля/настройки
        types = [self._types_list.item(i).data(Qt.UserRole) for i in range(self._types_list.count()) if self._types_list.item(i).isSelected()]
        cats = [self._cats_list.item(i).data(Qt.UserRole) for i in range(self._cats_list.count()) if self._cats_list.item(i).isSelected()]
        self._types_ids.setText(",".join(types))
        self._subjects_ids.setText(",".join(cats))
        self._save_settings()
        QMessageBox.information(self, "Сохранено", "Фильтры обновлены")
