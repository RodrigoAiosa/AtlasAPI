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
        raise RuntimeError(f"Não foi possível carregar o README do GitHub: {last_error}")

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
        raise RuntimeError(
            "O README do GitHub foi carregado, mas nenhuma tabela de categorias foi identificada. "
            "A estrutura do repositório pode ter mudado."
        )

    # Keep all listed entries; duplicate names in different categories or URLs are valid.
    df = df.drop_duplicates(subset=["name", "category", "url"], keep="first")
    return df.reset_index(drop=True)

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
