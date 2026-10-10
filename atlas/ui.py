"""Geração do HTML dos cartões. O visual fica em assets/style.css."""
from __future__ import annotations

import zlib
from html import escape
from pathlib import Path

CSS_PATH = Path(__file__).resolve().parent.parent / "assets" / "style.css"
ARROW = '<svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path d="M5.5 2.5 11 8l-5.5 5.5" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>'


def load_css() -> str:
    return f"<style>{CSS_PATH.read_text(encoding='utf-8')}</style>"


def _text(value: str) -> str:
    # "$" é escapado para o Streamlit não interpretar como fórmula.
    return escape(value).replace("$", "&#36;")


def _initial(name: str) -> str:
    for char in name:
        if char.isalnum():
            return char.upper()
    return "#"


def card(api: dict) -> str:
    hue = zlib.crc32(api["name"].encode("utf-8")) % 360
    auth = api["auth"]
    chips = ["Sem autenticação" if auth.casefold() in {"", "no", "unknown"} else f"Auth: {auth}"]
    if api["https"]:
        chips.append("HTTPS")
    if api["cors"]:
        chips.append("CORS")
    chips_html = "".join(f'<span class="atlas-chip">{_text(c)}</span>' for c in chips)
    description = _text(api["description"] or "Sem descrição disponível.")
    inner = (
        f'<span class="atlas-logo" style="--h:{hue}" aria-hidden="true">{_text(_initial(api["name"]))}</span>'
        '<span class="atlas-body">'
        f'<span class="atlas-name">{_text(api["name"])}</span>'
        f'<span class="atlas-category">{_text(api["category"])}</span>'
        f'<span class="atlas-desc">{description}</span>'
        "</span>"
        f'<span class="atlas-footer"><span class="atlas-chips">{chips_html}</span>'
        + (f'<span class="atlas-docs">Ver API {ARROW}</span>' if api["url"] else "")
        + "</span>"
    )
    if api["url"]:
        return f'<a class="atlas-card" href="{escape(api["url"], quote=True)}" target="_blank" rel="noopener noreferrer">{inner}</a>'
    return f'<div class="atlas-card">{inner}</div>'


def grid(apis: list[dict]) -> str:
    return '<div class="atlas-grid">' + "".join(card(api) for api in apis) + "</div>"
