from __future__ import annotations

import re
from html import escape
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

import i18n
import kits
from i18n import t

ROOT = Path(__file__).parent
PAGE_SIZE = 24
i18n.init()
st.set_page_config(
    page_title=t("page_title"),
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="collapsed",
)

def load_css() -> None:
    css_path = ROOT / "style.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

load_css()

README_URLS = (
    "https://raw.githubusercontent.com/public-apis/public-apis/master/README.md",
    "https://raw.githubusercontent.com/public-apis/public-apis/main/README.md",
)

FEATURED = [
    {"name": "Open-Meteo", "category": "Weather", "description": "Weather forecasts and historical weather data.", "icon": "🌤️", "url": "https://open-meteo.com/"},
    {"name": "The Cat API", "category": "Animals", "description": "Images, facts, and other data about cats.", "icon": "🐈", "url": "https://thecatapi.com/"},
    {"name": "Frankfurter", "category": "Finance", "description": "Exchange rates and currency conversion data.", "icon": "💱", "url": "https://www.frankfurter.app/"},
    {"name": "PokéAPI", "category": "Games & Comics", "description": "A RESTful Pokémon data source for apps and games.", "icon": "🎮", "url": "https://pokeapi.co/"},
    {"name": "Jikan", "category": "Anime", "description": "Unofficial MyAnimeList API for anime and manga.", "icon": "✨", "url": "https://jikan.moe/"},
    {"name": "Open Library", "category": "Books", "description": "Explore book records, authors, and editions.", "icon": "📚", "url": "https://openlibrary.org/developers/api"},
]

def clean_cell(value: str) -> str:
    value = re.sub(r"<br\s*/?>", " ", str(value), flags=re.I)
    value = re.sub(r"`([^`]*)`", r"\1", value)
    value = re.sub(r"\*\*(.*?)\*\*", r"\1", value)
    value = re.sub(r"\*(.*?)\*", r"\1", value)
    return re.sub(r"\s+", " ", value).strip()

def split_row(line: str) -> list[str]:
    return [part.strip() for part in line.strip().strip("|").split("|")]

def markdown_link(value: str) -> tuple[str, str]:
    match = re.search(r"\[([^\]]+)\]\((https?://[^)]+)\)", value)
    if match:
        return clean_cell(match.group(1)), match.group(2).strip()
    return clean_cell(value), ""

class CatalogError(RuntimeError):
    """Catalog failure; `key` is the i18n message so the cached loader stays language-neutral."""

    def __init__(self, key: str, detail: str = "") -> None:
        super().__init__(key)
        self.key, self.detail = key, detail

@st.cache_data(ttl=1800, show_spinner=False)
def load_apis() -> pd.DataFrame:
    """Parse every category table from the upstream public-apis README."""
    content = None
    last_error = None
    for url in README_URLS:
        try:
            response = requests.get(url, timeout=25, headers={"User-Agent": "API-Atlas-Streamlit"})
            response.raise_for_status()
            content = response.text
            break
        except requests.RequestException as exc:
            last_error = exc

    if content is None:
        raise CatalogError("err_load", str(last_error))

    rows: list[dict] = []
    category = ""
    lines = content.splitlines()
    i = 0

    def normalize_header(value: str) -> str:
        return clean_cell(value).strip().lower()

    while i < len(lines):
        raw_line = lines[i].strip()

        # The repository uses ### headings for actual categories.
        heading = re.match(r"^#{2,4}\s+(.+?)\s*#*\s*$", raw_line)
        if heading:
            heading_text = clean_cell(heading.group(1))
            # The index and non-catalog sections are not API categories.
            if heading_text.casefold() not in {
                "index", "mcp servers", "apilayer apis", "learn more about public apis",
                "table of contents", "contents", "contributing", "license",
            }:
                category = heading_text

        # Category tables have five columns. The header row in the current README
        # may or may not start with a leading pipe, so do not require one.
        candidate = raw_line.strip("|").strip()
        header_cells = [normalize_header(cell) for cell in candidate.split("|")]
        is_api_header = (
            len(header_cells) >= 5
            and header_cells[0] == "api"
            and "description" in header_cells
            and "auth" in header_cells
            and "https" in header_cells
            and "cors" in header_cells
        )

        if is_api_header and category:
            headers = header_cells
            j = i + 1

            # Skip the Markdown separator row, if present.
            if j < len(lines) and re.match(r"^\s*\|?\s*:?-{2,}", lines[j]):
                j += 1

            while j < len(lines):
                table_line = lines[j].strip()
                if not table_line.startswith("|"):
                    break

                cells = split_row(table_line)
                if len(cells) < len(headers):
                    j += 1
                    continue

                row = dict(zip(headers, cells))
                name, api_url = markdown_link(row.get("api", ""))
                description = clean_cell(row.get("description", ""))
                auth = clean_cell(row.get("auth", "Unknown")) or "Unknown"
                https = clean_cell(row.get("https", "Unknown")) or "Unknown"
                cors = clean_cell(row.get("cors", "Unknown")) or "Unknown"

                if name and name.casefold() not in {"api", "name"}:
                    rows.append({
                        "name": name,
                        "description": description,
                        "auth": auth,
                        "https": https,
                        "cors": cors,
                        "url": api_url,
                        "category": category,
                    })
                j += 1

            i = j
            continue

        i += 1

    df = pd.DataFrame(rows, columns=[
        "name", "description", "auth", "https", "cors", "url", "category"
    ])
    if df.empty:
        raise CatalogError("err_parse")

    # Keep all listed entries; duplicate names in different categories or URLs are valid.
    df = df.drop_duplicates(subset=["name", "category", "url"], keep="first")
    return df.reset_index(drop=True)

def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")

def meta_badge(label: str, value: str) -> str:
    value = value or "Unknown"
    normalized = value.casefold()
    if normalized in {"yes", "no", "unknown"}:
        value = t(normalized)
    status_class = "status-neutral"
    if normalized in {"yes", "true"}:
        status_class = "status-good"
    elif normalized in {"no", "false"}:
        status_class = "status-warn"
    return f'<span class="meta-pill {status_class}"><span class="meta-label">{label}</span>{value}</span>'

def text(value: str) -> str:
    # "$" is escaped so Streamlit does not read it as a math formula.
    return escape(value).replace("$", "&#36;")

def card_html(item) -> str:
    name = text(str(item["name"]))
    url = str(item["url"])
    if url.startswith(("https://", "http://")):
        title = f'<a href="{escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">{name} ↗</a>'
    else:
        title = name
    return (
        '<article class="api-card">'
        '<div class="api-card-top">'
        f'<div class="api-icon">{name[:1].upper()}</div>'
        '<div class="api-heading">'
        f'<div class="api-name">{title}</div>'
        f'<div class="api-category">{text(i18n.category(str(item["category"])))}</div>'
        "</div></div>"
        f'<p class="api-description">{text(i18n.description(str(item["description"]))) or t("no_description")}</p>'
        '<div class="meta-row">'
        + meta_badge("Auth", str(item["auth"]))
        + meta_badge("HTTPS", str(item["https"]))
        + meta_badge("CORS", str(item["cors"]))
        + "</div></article>"
    )

def render_grid(items: pd.DataFrame, view: str) -> None:
    """Three-column card grid, shown one page at a time."""
    if st.session_state.get("grid_view") != view:
        st.session_state["grid_view"] = view
        st.session_state["grid_limit"] = PAGE_SIZE
    limit = st.session_state["grid_limit"]
    items = items.sort_values("name", key=lambda col: col.str.casefold())
    cards = "".join(card_html(item) for _, item in items.head(limit).iterrows())
    st.markdown(f'<div class="api-grid">{cards}</div>', unsafe_allow_html=True)
    if limit < len(items):
        _, middle, _ = st.columns([2, 1, 2])
        if middle.button(t("load_more", n=len(items) - limit), key="load_more", use_container_width=True):
            st.session_state["grid_limit"] = limit + PAGE_SIZE
            st.rerun()

# The catalog is loaded first so the header can show its real size.
try:
    with st.spinner(t("loading")):
        apis = load_apis()
    source_error = None
except Exception as exc:
    apis = pd.DataFrame(columns=["name", "description", "auth", "https", "cors", "url", "category"])
    source_error = t(exc.key) if isinstance(exc, CatalogError) else str(exc)

_, language_column = st.columns([5, 1])
with language_column:
    i18n.selector()

hero_stats = ""
if not apis.empty:
    hero_stats = (
        '<div class="hero-stats">'
        f'<div class="hero-stat"><strong>{i18n.number(len(apis))}</strong><span>{t("stat_apis")}</span></div>'
        '<div class="hero-stat-divider"></div>'
        f'<div class="hero-stat"><strong>{i18n.number(apis["category"].nunique())}</strong><span>{t("stat_categories")}</span></div>'
        "</div>"
    )

# Header / search
st.markdown(
    '<div class="hero">'
    f'<div class="eyebrow"><span class="eyebrow-dot"></span> {t("eyebrow")}</div>'
    f'<h1>{t("hero_l1")}<br><span class="soft">{t("hero_l2")}</span></h1>'
    f'<p class="hero-subtitle">{t("hero_sub")}</p>'
    f"{hero_stats}"
    "</div>",
    unsafe_allow_html=True,
)
tab_catalog, tab_kits, tab_python = st.tabs([t("tab_catalog"), t("tab_kits"), t("tab_python")])

with tab_kits:
    kits.render_kits()

with tab_python:
    kits.render_gerador_python()

with tab_catalog:
    search = st.text_input(
        t("search_label"),
        placeholder=t("search_placeholder"),
        label_visibility="collapsed",
        key="global_search",
    )

    if source_error:
        st.error(source_error)
        st.info(t("err_hint"))

    # Search intentionally takes precedence over category selection and searches the full catalog.
    query = search.strip().casefold()
    if query:
        fields = ["name", "description", "category", "auth", "https", "cors"]
        searchable = apis[fields].fillna("").astype(str)
        # The search also matches the translated description and category.
        searchable["description_local"] = searchable["description"].map(i18n.description)
        searchable["category_local"] = searchable["category"].map(i18n.category)
        mask = searchable.apply(lambda col: col.str.casefold().str.contains(re.escape(query), na=False)).any(axis=1)
        results = apis[mask].copy()
        st.markdown(f'<div class="section-heading"><h2>{t("results_title")}</h2><span>{t("results_count", n=i18n.number(len(results)))}</span></div>', unsafe_allow_html=True)
        if results.empty:
            st.markdown(f'<div class="empty-state"><div class="empty-icon">⌕</div><h3>{t("empty_title")}</h3><p>{t("empty_text")}</p></div>', unsafe_allow_html=True)
        else:
            render_grid(results, f"search:{query}")
    else:
        st.markdown(f'<div class="section-heading"><h2>{t("featured_title")}</h2><span>{t("featured_sub")}</span></div>', unsafe_allow_html=True)
        featured_cols = st.columns(3, gap="medium")
        for idx, item in enumerate(FEATURED):
            with featured_cols[idx % 3]:
                st.markdown(
                    f"""
                    <a class="featured-card" href="{item['url']}" target="_blank" rel="noopener noreferrer">
                      <div class="featured-icon">{item['icon']}</div>
                      <div class="featured-content">
                        <div class="featured-name">{item['name']}</div>
                        <div class="featured-category">{i18n.category(item['category'])}</div>
                        <p>{i18n.featured_description(item['name'], item['description'])}</p>
                        <span class="featured-link">{t("featured_link")}</span>
                      </div>
                    </a>
                    """,
                    unsafe_allow_html=True,
                )

        st.markdown(f'<div class="section-heading categories-heading"><h2>{t("browse_title")}</h2><span>{t("browse_sub")}</span></div>', unsafe_allow_html=True)
        if not apis.empty:
            category_counts = apis.groupby("category").size().sort_index(
                key=lambda idx: idx.map(lambda name: i18n.sort_key(i18n.category(name)))
            )
            cols = st.columns(4, gap="small")
            for idx, (category, count) in enumerate(category_counts.items()):
                with cols[idx % 4]:
                    if st.button(f"{i18n.category(str(category))}  ·  {count}", key=f"category_{slug(str(category))}", use_container_width=True):
                        st.session_state["selected_category"] = str(category)
                        st.rerun()

            selected = st.session_state.get("selected_category")
            if selected:
                st.markdown(f'<div class="section-heading category-results"><h2>{text(i18n.category(selected))}</h2><span>{t("n_apis", n=i18n.number(int(category_counts.get(selected, 0))))}</span></div>', unsafe_allow_html=True)
                subset = apis[apis["category"] == selected]
                render_grid(subset, f"category:{selected}")
                if st.button(t("back"), key="back_categories"):
                    st.session_state.pop("selected_category", None)
                    st.rerun()
        else:
            st.caption(t("categories_unavailable"))

st.markdown(
    f"""
    <footer class="site-footer">
      <div><strong>API Atlas</strong><span>{t("footer_tag")}</span></div>
    </footer>
    """,
    unsafe_allow_html=True,
)
