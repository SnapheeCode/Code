from __future__ import annotations

"""Загрузка и подготовки текстов сообщений из .txt файлов.

На данном этапе шаблонизация минимальная — просто подстановка переменных по словарю.
"""

from pathlib import Path
from typing import Dict


def load_text_file(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8")


def render_template(text: str, ctx: Dict[str, str]) -> str:
    """Простейшая подстановка переменных вида {var} в тексте."""
    if not text:
        return text
    try:
        return text.format(**ctx)
    except Exception:
        return text

