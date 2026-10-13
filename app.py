from __future__ import annotations

import re
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

import catalog
import i18n
import kits
import montador
import rolagem
from esconder_selo import esconder_selo_streamlit
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

FEATURED = [
    {"name": "Open-Meteo", "category": "Weather", "description": "Weather forecasts and historical weather data.", "icon": "🌤️", "url": "https://open-meteo.com/"},
    {"name": "The Cat API", "category": "Animals", "description": "Images, facts, and other data about cats.", "icon": "🐈", "url": "https://thecatapi.com/"},
    {"name": "Frankfurter", "category": "Finance", "description": "Exchange rates and currency conversion data.", "icon": "💱", "url": "https://www.frankfurter.app/"},
    {"name": "PokéAPI", "category": "Games & Comics", "description": "A RESTful Pokémon data source for apps and games.", "icon": "🎮", "url": "https://pokeapi.co/"},
    {"name": "Jikan", "category": "Anime", "description": "Unofficial MyAnimeList API for anime and manga.", "icon": "✨", "url": "https://jikan.moe/"},
    {"name": "Open Library", "category": "Books", "description": "Explore book records, authors, and editions.", "icon": "📚", "url": "https://openlibrary.org/developers/api"},
]

@st.cache_data(ttl=1800, show_spinner=False)
def load_apis() -> tuple[pd.DataFrame, list[str]]:
    """Catalog from every source, plus the extra sources that could not be read."""
    rows, failed = catalog.load()
    return pd.DataFrame(rows, columns=catalog.COLUMNS), failed

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

def script_html(item) -> str:
    """Script Python recolhido no cartão, só para endereços que devolvem JSON direto."""
    if str(item.get("source")) != catalog.JSON_DATASETS:
        return ""
    try:
        codigo = kits.gerar_script_generico(str(item["url"]), "", "none", "", False) + "\n\nprint(df.head())"
    except ValueError:
        return ""
    # Quebras de linha viram entidades: uma linha em branco encerraria o bloco HTML no Markdown.
    codigo = escape(codigo).replace("\n", "&#10;")
    return (f'<details class="api-script"><summary>{t("card_script")}</summary>'
            f'<pre><code>{codigo}</code></pre></details>')


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
        + "</div>"
        + script_html(item)
        + "</article>"
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
        apis, failed_sources = load_apis()
    source_error = None
except Exception as exc:
    apis, failed_sources = pd.DataFrame(columns=catalog.COLUMNS), []
    source_error = t(exc.key) if isinstance(exc, catalog.CatalogError) else str(exc)

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
tab_catalog, tab_kits, tab_montador, tab_python = st.tabs(
    [t("tab_catalog"), t("tab_kits"), t("tab_montador"), t("tab_python")]
)

with tab_montador:
    montador.render()

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

    if failed_sources:
        st.caption(t("sources_partial", sources=", ".join(failed_sources)))
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
        st.markdown(f'<div class="section-heading"><h2>{t("results_title")}</h2><span>{t("results_count_one") if len(results) == 1 else t("results_count", n=i18n.number(len(results)))}</span></div>', unsafe_allow_html=True)
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

        st.markdown(f'<div id="categorias" class="section-heading categories-heading"><h2>{t("browse_title")}</h2><span>{t("browse_sub")}</span></div>', unsafe_allow_html=True)
        rolagem.executar("categorias")
        if not apis.empty:
            category_counts = apis.groupby("category").size().sort_index(
                key=lambda idx: idx.map(lambda name: i18n.sort_key(i18n.category(name)))
            )
            cols = st.columns(4, gap="small")
            for idx, (category, count) in enumerate(category_counts.items()):
                with cols[idx % 4]:
                    if st.button(f"{i18n.category(str(category))}  ·  {count}", key=f"category_{slug(str(category))}", use_container_width=True):
                        st.session_state["selected_category"] = str(category)
                        rolagem.pedir("lista-categoria")
                        st.rerun()

            selected = st.session_state.get("selected_category")
            if selected:
                st.markdown(f'<div id="lista-categoria" class="section-heading category-results"><h2>{text(i18n.category(selected))}</h2><span>{t("n_apis", n=i18n.number(int(category_counts.get(selected, 0))))}</span></div>', unsafe_allow_html=True)
                rolagem.executar("lista-categoria")
                subset = apis[apis["category"] == selected]
                render_grid(subset, f"category:{selected}")
                if st.button(t("back"), key="back_categories"):
                    st.session_state.pop("selected_category", None)
                    rolagem.pedir("categorias")
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

esconder_selo_streamlit()
