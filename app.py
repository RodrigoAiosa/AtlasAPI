from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import requests
import streamlit as st

ROOT = Path(__file__).parent
st.set_page_config(
    page_title="API Atlas — Free Public APIs",
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

@st.cache_data(ttl=1800, show_spinner=False)
def load_apis() -> pd.DataFrame:
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
        raise RuntimeError(f"Não foi possível carregar o README do GitHub: {last_error}")

    rows: list[dict] = []
    category = "Other"
    lines = content.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        heading = re.match(r"^##\s+(.+?)\s*#*\s*$", line)
        if heading:
            possible_category = clean_cell(heading.group(1))
            if possible_category.lower() not in {"table of contents", "contents", "contributing", "license"}:
                category = possible_category

        if line.startswith("|"):
            headers = [clean_cell(x).lower() for x in split_row(line)]
            if any(x in headers for x in ("api", "name")) and any("description" in x for x in headers):
                j = i + 1
                if j < len(lines) and re.match(r"^\s*\|?[\s:|-]+\|?\s*$", lines[j]):
                    j += 1
                while j < len(lines) and lines[j].strip().startswith("|"):
                    cells = split_row(lines[j])
                    if len(cells) >= len(headers):
                        row = dict(zip(headers, cells))
                        raw_name = row.get("api", row.get("name", ""))
                        name, api_url = markdown_link(raw_name)
                        raw_link = row.get("link", "")
                        _, link_url = markdown_link(raw_link)
                        if not api_url:
                            api_url = link_url or (raw_link.strip() if raw_link.strip().startswith("http") else "")
                        if name and name.lower() not in {"api", "name"}:
                            rows.append({
                                "name": name,
                                "description": clean_cell(row.get("description", "")),
                                "auth": clean_cell(row.get("auth", "Unknown")) or "Unknown",
                                "https": clean_cell(row.get("https", "Unknown")) or "Unknown",
                                "cors": clean_cell(row.get("cors", "Unknown")) or "Unknown",
                                "url": api_url,
                                "category": category,
                            })
                    j += 1
                i = j
                continue
        i += 1

    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError("O README foi carregado, mas nenhuma tabela de APIs foi identificada.")
    return df.drop_duplicates(subset=["name", "category"]).reset_index(drop=True)

def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")

def meta_badge(label: str, value: str) -> str:
    value = value or "Unknown"
    normalized = value.casefold()
    status_class = "status-neutral"
    if normalized in {"yes", "true"}:
        status_class = "status-good"
    elif normalized in {"no", "false"}:
        status_class = "status-warn"
    return f'<span class="meta-pill {status_class}"><span class="meta-label">{label}</span>{value}</span>'

def render_card(name: str, description: str, category: str, auth: str, https: str, cors: str, url: str) -> None:
    safe_name = name.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    safe_desc = description.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    safe_cat = category.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    title = f'<a href="{url}" target="_blank" rel="noopener noreferrer">{safe_name} ↗</a>' if url.startswith("https://") or url.startswith("http://") else safe_name
    st.markdown(
        f"""
        <article class="api-card">
          <div class="api-card-top">
            <div class="api-icon">{safe_name[:1].upper()}</div>
            <div class="api-heading">
              <div class="api-name">{title}</div>
              <div class="api-category">{safe_cat}</div>
            </div>
          </div>
          <p class="api-description">{safe_desc or "No description available."}</p>
          <div class="meta-row">
            {meta_badge("Auth", auth)}
            {meta_badge("HTTPS", https)}
            {meta_badge("CORS", cors)}
          </div>
        </article>
        """,
        unsafe_allow_html=True,
    )

# Header / search
st.markdown(
    """
    <div class="hero">
      <div class="eyebrow"><span class="eyebrow-dot"></span> THE OPEN API DIRECTORY</div>
      <h1>A world of APIs.<br><span>One search away.</span></h1>
      <p class="hero-subtitle">A collective list of free APIs for software and web development.</p>
    </div>
    """,
    unsafe_allow_html=True,
)
search = st.text_input(
    "Search APIs",
    placeholder="⌕   Find development, games, images APIs...",
    label_visibility="collapsed",
    key="global_search",
)

try:
    with st.spinner("Loading the public API catalog…"):
        apis = load_apis()
    source_error = None
except Exception as exc:
    apis = pd.DataFrame(columns=["name", "description", "auth", "https", "cors", "url", "category"])
    source_error = str(exc)

if source_error:
    st.error(source_error)
    st.info("Confira a conexão com a internet. O catálogo é obtido diretamente do GitHub.")

# Search intentionally takes precedence over category selection and searches the full catalog.
query = search.strip().casefold()
if query:
    fields = ["name", "description", "category", "auth", "https", "cors"]
    searchable = apis[fields].fillna("").astype(str)
    mask = searchable.apply(lambda col: col.str.casefold().str.contains(re.escape(query), na=False)).any(axis=1)
    results = apis[mask].copy()
    st.markdown(f'<div class="section-heading"><h2>Search results</h2><span>{len(results)} APIs found</span></div>', unsafe_allow_html=True)
    if results.empty:
        st.markdown('<div class="empty-state"><div class="empty-icon">⌕</div><h3>No APIs found</h3><p>Try another name or keyword.</p></div>', unsafe_allow_html=True)
    else:
        for _, item in results.sort_values("name", key=lambda col: col.str.casefold()).iterrows():
            render_card(str(item["name"]), str(item["description"]), str(item["category"]), str(item["auth"]), str(item["https"]), str(item["cors"]), str(item["url"]))
else:
    st.markdown('<div class="section-heading"><h2>Featured APIs</h2><span>A few places to start exploring</span></div>', unsafe_allow_html=True)
    featured_cols = st.columns(3, gap="medium")
    for idx, item in enumerate(FEATURED):
        with featured_cols[idx % 3]:
            st.markdown(
                f"""
                <a class="featured-card" href="{item['url']}" target="_blank" rel="noopener noreferrer">
                  <div class="featured-icon">{item['icon']}</div>
                  <div class="featured-content">
                    <div class="featured-name">{item['name']}</div>
                    <div class="featured-category">{item['category']}</div>
                    <p>{item['description']}</p>
                    <span class="featured-link">API documentation ↗</span>
                  </div>
                </a>
                """,
                unsafe_allow_html=True,
            )

    st.markdown('<div class="section-heading categories-heading"><h2>Browse by category</h2><span>Explore the full collection</span></div>', unsafe_allow_html=True)
    if not apis.empty:
        category_counts = apis.groupby("category").size().sort_index(key=lambda idx: idx.str.casefold())
        cols = st.columns(4, gap="small")
        for idx, (category, count) in enumerate(category_counts.items()):
            with cols[idx % 4]:
                if st.button(f"{category}  ·  {count}", key=f"category_{slug(str(category))}", use_container_width=True):
                    st.session_state["selected_category"] = str(category)
                    st.rerun()

        selected = st.session_state.get("selected_category")
        if selected:
            st.markdown(f'<div class="section-heading category-results"><h2>{selected}</h2><span>{int(category_counts.get(selected, 0))} APIs</span></div>', unsafe_allow_html=True)
            subset = apis[apis["category"] == selected]
            for _, item in subset.sort_values("name", key=lambda col: col.str.casefold()).iterrows():
                render_card(str(item["name"]), str(item["description"]), str(item["category"]), str(item["auth"]), str(item["https"]), str(item["cors"]), str(item["url"]))
            if st.button("← Back to all categories", key="back_categories"):
                st.session_state.pop("selected_category", None)
                st.rerun()
    else:
        st.caption("As categorias serão exibidas quando o catálogo do GitHub estiver disponível.")

st.markdown(
    """
    <footer class="site-footer">
      <div><strong>API Atlas</strong><span>Built for curious developers.</span></div>
      <a href="https://github.com/public-apis/public-apis" target="_blank" rel="noopener noreferrer">Data source: public-apis on GitHub ↗</a>
    </footer>
    """,
    unsafe_allow_html=True,
)
