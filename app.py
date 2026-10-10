import re
from urllib.parse import urlparse

import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="API Atlas — Diretório de APIs públicas",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded",
)

README_URLS = [
    "https://raw.githubusercontent.com/public-apis/public-apis/master/README.md",
    "https://raw.githubusercontent.com/public-apis/public-apis/main/README.md",
]

st.markdown(
    """
    <style>
      .block-container {padding-top: 1.2rem; padding-bottom: 3rem; max-width: 1440px;}
      [data-testid="stHeader"] {background: rgba(255,255,255,0.92);}
      .hero {padding: 1.2rem 0 .6rem 0;}
      .hero h1 {font-size: 2.25rem; letter-spacing: -0.04em; margin-bottom: .25rem;}
      .muted {color: #667085; font-size: .95rem;}
      .api-card {border: 1px solid #e5e7eb; border-radius: 14px; padding: 1rem 1.1rem;
                 margin: .65rem 0; background: var(--secondary-background-color);}
      .api-title {font-size: 1.1rem; font-weight: 700; margin-bottom: .3rem;}
      .api-description {color: var(--text-color); opacity: .85; margin-bottom: .8rem;}
      .pill {display:inline-block; padding: .22rem .55rem; margin: .12rem .25rem .12rem 0;
             border: 1px solid #d0d5dd; border-radius: 999px; font-size: .78rem;}
      div[data-testid="stTextInput"] input {border-radius: 12px; min-height: 3rem;}
      div[data-testid="stMetric"] {border: 1px solid #e5e7eb; padding: .8rem; border-radius: 12px;}
      a {text-decoration: none;}
    </style>
    """,
    unsafe_allow_html=True,
)

def clean_cell(value: str) -> str:
    value = value.strip()
    value = re.sub(r"<br\s*/?>", " ", value, flags=re.I)
    value = re.sub(r"`([^`]*)`", r"\1", value)
    value = re.sub(r"\*\*(.*?)\*\*", r"\1", value)
    value = re.sub(r"\*(.*?)\*", r"\1", value)
    return re.sub(r"\s+", " ", value).strip()

def markdown_link(value: str):
    """Return display text and first Markdown URL, if present."""
    match = re.search(r"\[([^\]]+)\]\((https?://[^)]+)\)", value)
    if match:
        return clean_cell(match.group(1)), match.group(2).strip()
    return clean_cell(value), ""

def split_row(line: str):
    line = line.strip()
    if not line.startswith("|"):
        return []
    return [part.strip() for part in line.strip("|").split("|")]

@st.cache_data(ttl=1800, show_spinner=False)
def load_apis():
    last_error = None
    content = None
    for url in README_URLS:
        try:
            response = requests.get(url, timeout=20, headers={"User-Agent": "API-Atlas-Streamlit"})
            response.raise_for_status()
            content = response.text
            break
        except requests.RequestException as exc:
            last_error = exc
    if content is None:
        raise RuntimeError(f"Não foi possível carregar o README do GitHub. Detalhe: {last_error}")

    records = []
    category = "Outros"
    lines = content.splitlines()
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # Categories are usually second-level headings in the public-apis README.
        heading = re.match(r"^##\s+(.+?)\s*#*\s*$", line)
        if heading:
            title = clean_cell(heading.group(1))
            if title.lower() not in {"table of contents", "contents", "contributing", "license"}:
                category = title

        if line.startswith("|"):
            headers = [clean_cell(x).lower() for x in split_row(line)]
            if any(h in headers for h in ("api", "name")) and any("description" in h for h in headers):
                j = i + 1
                # Skip Markdown table separator.
                if j < len(lines) and re.match(r"^\s*\|?[\s:|-]+\|?\s*$", lines[j]):
                    j += 1
                while j < len(lines) and lines[j].strip().startswith("|"):
                    cells = split_row(lines[j])
                    if len(cells) >= len(headers):
                        row = dict(zip(headers, cells))
                        api_raw = row.get("api", row.get("name", ""))
                        api_name, api_url = markdown_link(api_raw)
                        if not api_name or api_name.lower() in {"api", "name"}:
                            j += 1
                            continue
                        desc = clean_cell(row.get("description", ""))
                        link_raw = row.get("link", "")
                        link_text, link_url = markdown_link(link_raw)
                        if not api_url and link_url:
                            api_url = link_url
                        if not api_url and link_raw.startswith("http"):
                            api_url = link_raw.strip()
                        records.append({
                            "name": api_name,
                            "description": desc,
                            "auth": clean_cell(row.get("auth", "Unknown")) or "No especificado",
                            "https": clean_cell(row.get("https", "Unknown")) or "No especificado",
                            "cors": clean_cell(row.get("cors", "Unknown")) or "No especificado",
                            "url": api_url,
                            "category": category,
                        })
                    j += 1
                i = j
                continue
        i += 1

    # Remove duplicates while preserving the first occurrence.
    df = pd.DataFrame(records)
    if df.empty:
        raise RuntimeError("O README foi carregado, mas não foi possível identificar as tabelas de APIs.")
    df = df.drop_duplicates(subset=["name", "category"], keep="first").reset_index(drop=True)
    return df

def normalize(value):
    return str(value).casefold().strip()

def pill(label, value):
    value = value if value else "Não especificado"
    return f'<span class="pill"><b>{label}:</b> {value}</span>'

st.markdown(
    '<div class="hero"><h1>🌐 API Atlas</h1>'
    '<div class="muted">Explore APIs públicas para seus projetos, estudos e protótipos.</div></div>',
    unsafe_allow_html=True,
)

# The search field remains at the top of the main page and searches every category.
search = st.text_input(
    "Pesquisar em todas as APIs",
    placeholder="Ex.: clima, moedas, gatos, geolocalização...",
    help="A busca considera nome, descrição e categoria.",
)

try:
    with st.spinner("Carregando o catálogo do GitHub..."):
        apis = load_apis()
except Exception as exc:
    st.error(str(exc))
    st.info("Verifique sua conexão com a internet e tente novamente.")
    st.stop()

# A sidebar selector makes category navigation explicit; global search ignores it.
categories = sorted(apis["category"].dropna().unique().tolist(), key=str.casefold)
with st.sidebar:
    st.title("Navegação")
    selected_category = st.radio(
        "Categorias",
        ["Todas as categorias"] + categories,
        index=0,
    )
    st.divider()
    st.caption("Fonte de dados")
    st.markdown("[public-apis no GitHub](https://github.com/public-apis/public-apis)")
    st.caption("Os dados são atualizados automaticamente a cada 30 minutos.")

filtered = apis.copy()
if selected_category != "Todas as categorias":
    filtered = filtered[filtered["category"] == selected_category]

if search.strip():
    needle = normalize(search)
    search_cols = ["name", "description", "category", "auth", "https", "cors"]
    mask = filtered[search_cols].fillna("").astype(str).apply(
        lambda col: col.map(lambda value: needle in normalize(value))
    ).any(axis=1)
    # Search globally across all categories, even if a category is selected.
    filtered = apis[
        apis[search_cols].fillna("").astype(str).apply(
            lambda col: col.map(lambda value: needle in normalize(value))
        ).any(axis=1)
    ]

total_apis = len(apis)
total_categories = apis["category"].nunique()
https_count = (apis["https"].str.casefold() == "yes").sum()

m1, m2, m3 = st.columns(3)
m1.metric("APIs no catálogo", f"{total_apis:,}".replace(",", "."))
m2.metric("Categorias", f"{total_categories:,}".replace(",", "."))
m3.metric("Com HTTPS", f"{https_count:,}".replace(",", "."))

if search.strip():
    st.subheader(f"Resultados para “{search.strip()}”")
elif selected_category == "Todas as categorias":
    st.subheader("Todas as APIs")
else:
    st.subheader(selected_category)

st.caption(f"{len(filtered):,} resultado(s)".replace(",", "."))

if filtered.empty:
    st.warning("Nenhuma API encontrada. Tente outro nome ou palavra-chave.")
else:
    # Compact, readable cards with the essential metadata.
    for _, item in filtered.sort_values(["category", "name"], key=lambda s: s.str.casefold()).iterrows():
        name = str(item["name"])
        desc = str(item["description"] or "Sem descrição disponível.")
        url = str(item["url"] or "")
        auth = str(item["auth"] or "Não especificado")
        https = str(item["https"] or "Não especificado")
        cors = str(item["cors"] or "Não especificado")
        category = str(item["category"] or "Outros")

        st.markdown('<div class="api-card">', unsafe_allow_html=True)
        if url:
            st.markdown(f'<div class="api-title"><a href="{url}" target="_blank" rel="noopener noreferrer">{name} ↗</a></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="api-title">{name}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="api-description">{desc}</div>', unsafe_allow_html=True)
        st.markdown(
            pill("Categoria", category)
            + pill("Autenticação", auth)
            + pill("HTTPS", https)
            + pill("CORS", cors),
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

st.divider()
st.caption(
    "Catálogo baseado no README do repositório public-apis. "
    "Disponibilidade, políticas de autenticação e CORS podem mudar; confirme os detalhes na documentação de cada API."
)
