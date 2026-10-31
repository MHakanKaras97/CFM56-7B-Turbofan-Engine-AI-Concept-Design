"""Language handling for the public UI: Turkish / English texts from content/strings.yaml."""

from functools import lru_cache
from pathlib import Path

import streamlit as st
import yaml

CONTENT = Path(__file__).resolve().parent / "content"
LANGS = {"tr": "Türkçe", "en": "English"}


@lru_cache(maxsize=1)
def strings() -> dict:
    return yaml.safe_load((CONTENT / "strings.yaml").read_text(encoding="utf-8"))


def lang() -> str:
    return st.session_state.get("lang", "tr")


def t(key: str, default: str | None = None) -> str:
    """Text for 'group.key' in the current language (falls back to English, then to the default or the key)."""
    group, _, item = key.partition(".")
    entry = strings().get(group, {}).get(item)
    if not entry:
        return default if default is not None else item
    return entry.get(lang()) or entry.get("en") or item


def num(value: float, digits: int = 2) -> str:
    """Number with the decimal separator of the current language."""
    text = f"{value:,.{digits}f}"
    if lang() == "tr":
        text = text.replace(",", " ").replace(".", ",")
    return text


def learning_text(topic: str) -> str:
    path = CONTENT / "learning" / lang() / f"{topic}.md"
    if not path.is_file():
        path = CONTENT / "learning" / "en" / f"{topic}.md"
    return path.read_text(encoding="utf-8")
