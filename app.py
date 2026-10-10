import datetime as dt
import random

import streamlit as st

from atlas import catalog, ui

PAGE_SIZE = 24
FEATURED = 9
ALL = "Todas as categorias"

st.set_page_config(
    page_title="API Atlas — Diretório de APIs públicas",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="collapsed",
)
st.markdown(ui.load_css(), unsafe_allow_html=True)


@st.cache_data(ttl=1800, show_spinner=False)
def load_apis() -> list[dict]:
    return catalog.parse_readme(catalog.fetch_readme())


def featured_of_the_week(apis: list[dict]) -> list[dict]:
    """Seleção que muda a cada semana, igual para todos os visitantes."""
    year, week, _ = dt.date.today().isocalendar()
    pool = [a for a in apis if a["url"] and a["description"]]
    return random.Random(f"{year}-{week}").sample(pool, min(FEATURED, len(pool)))


def fmt(number: int) -> str:
    return f"{number:,}".replace(",", ".")


st.markdown(
    '<div class="atlas-hero"><h1>Uma lista coletiva de APIs gratuitas para '
    "desenvolvimento de software e web.</h1></div>",
    unsafe_allow_html=True,
)

try:
    with st.spinner("Carregando o catálogo..."):
        apis = load_apis()
except Exception as exc:
    st.error(str(exc))
    st.info("Verifique sua conexão com a internet e tente novamente.")
    st.stop()

categories = sorted({a["category"] for a in apis}, key=str.casefold)

_, center, _ = st.columns([1, 2, 1])
with center:
    query = st.text_input(
        "Pesquisar APIs",
        placeholder="Busque por clima, moedas, jogos, imagens...",
        label_visibility="collapsed",
    ).strip()
    category = st.selectbox("Categoria", [ALL] + categories, label_visibility="collapsed")

# A busca é global; a categoria só vale quando não há busca.
if query:
    title, results = f"Resultados para “{query}”", catalog.search(apis, query)
elif category != ALL:
    title, results = category, [a for a in apis if a["category"] == category]
else:
    st.markdown('<h2 class="atlas-section">APIs em destaque desta semana</h2>', unsafe_allow_html=True)
    st.markdown(ui.grid(featured_of_the_week(apis)), unsafe_allow_html=True)
    title, results = "Todas as APIs", apis

results = sorted(results, key=lambda a: a["name"].casefold())

# Volta para a primeira página quando a busca ou a categoria mudam.
view = (query, category)
if st.session_state.get("view") != view:
    st.session_state.view = view
    st.session_state.limit = PAGE_SIZE

st.markdown(
    f'<h2 class="atlas-section">{ui._text(title)} <small>{fmt(len(results))}</small></h2>',
    unsafe_allow_html=True,
)

if not results:
    st.markdown(
        '<div class="atlas-empty">Nenhuma API encontrada. Tente outra palavra-chave.</div>',
        unsafe_allow_html=True,
    )
else:
    st.markdown(ui.grid(results[: st.session_state.limit]), unsafe_allow_html=True)
    if st.session_state.limit < len(results):
        _, middle, _ = st.columns([2, 1, 2])
        if middle.button("Carregar mais", use_container_width=True):
            st.session_state.limit += PAGE_SIZE
            st.rerun()

st.markdown(
    '<footer class="atlas-footer-bar">'
    f"<span><strong>API Atlas</strong> · {fmt(len(apis))} APIs em {len(categories)} categorias</span>"
    '<span>Dados de <a href="https://github.com/public-apis/public-apis" target="_blank" '
    'rel="noopener noreferrer">public-apis</a>, atualizados a cada 30 minutos. '
    "Confirme autenticação, HTTPS e CORS na documentação de cada API.</span>"
    "</footer>",
    unsafe_allow_html=True,
)
