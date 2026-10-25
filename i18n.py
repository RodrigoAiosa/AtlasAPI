"""Tradução da interface (i18n).

Para adicionar um idioma: inclua o código em SUPPORTED, uma entrada em
STRINGS com as mesmas chaves e, se quiser traduzir os kits, um bloco em
kits_i18n.py. O que faltar cai no inglês.
"""
from __future__ import annotations

import json
import unicodedata
from functools import lru_cache
from pathlib import Path

import streamlit as st

SUPPORTED = {"pt": "Português", "en": "English"}
DEFAULT = "en"

# País de acesso -> idioma, usado quando o navegador não informa um idioma
# que o site tenha. A Cloudflare envia o país em CF-IPCountry; os outros
# cabeçalhos cobrem CDNs equivalentes.
COUNTRY_HEADERS = ("CF-IPCountry", "CloudFront-Viewer-Country", "X-Vercel-IP-Country", "X-Country-Code")
COUNTRY_LANG = {
    "BR": "pt", "PT": "pt", "AO": "pt", "MZ": "pt", "CV": "pt", "GW": "pt", "ST": "pt", "TL": "pt",
}


def from_accept_language(header: str | None) -> str | None:
    """Primeiro idioma suportado do cabeçalho Accept-Language, por ordem de preferência."""
    ranked = []
    for position, part in enumerate((header or "").split(",")):
        tag, _, params = part.strip().partition(";")
        quality = 1.0
        if params.strip().startswith("q="):
            try:
                quality = float(params.strip()[2:])
            except ValueError:
                quality = 0.0
        if tag:
            ranked.append((-quality, position, tag.split("-")[0].lower()))
    for _, _, primary in sorted(ranked):
        if primary in SUPPORTED:
            return primary
    return None


def from_country(headers) -> str | None:
    for name in COUNTRY_HEADERS:
        country = (headers.get(name) or "").strip().upper()
        if country and country not in {"XX", "T1"}:  # XX = desconhecido, T1 = rede Tor
            return COUNTRY_LANG.get(country, DEFAULT)
    return None


def detect(query_lang: str | None, browser_locale: str | None, headers) -> str:
    """Idioma inicial: ?lang= na URL, depois o navegador, depois o país, depois o padrão."""
    query_lang = (query_lang or "").strip().lower()[:2]
    if query_lang in SUPPORTED:
        return query_lang
    return (
        from_accept_language(browser_locale)
        or from_accept_language(headers.get("Accept-Language"))
        or from_country(headers)
        or DEFAULT
    )


def init() -> str:
    """Define o idioma da sessão na primeira execução."""
    if st.session_state.get("lang") not in SUPPORTED:
        try:
            headers = st.context.headers
        except Exception:  # sem contexto de requisição (testes, versões antigas)
            headers = {}
        # st.context.locale é o idioma do navegador; existe a partir do Streamlit 1.41.
        browser_locale = getattr(st.context, "locale", None)
        st.session_state["lang"] = detect(st.query_params.get("lang"), browser_locale, headers)
    return st.session_state["lang"]


def lang() -> str:
    return st.session_state.get("lang", DEFAULT)


def keyed(name: str) -> str:
    """Chave de widget por idioma, para caixas de seleção com rótulos traduzidos.

    O Streamlit não redesenha os rótulos de uma caixa de seleção quando só o
    texto muda, então cada idioma usa a sua chave.
    """
    return f"{name}__{lang()}"


def _remember() -> None:
    new = st.session_state["lang"]
    old = st.session_state.get("lang_shown", new)
    # Leva as escolhas feitas no idioma anterior para as chaves do novo.
    for key in [k for k in st.session_state if isinstance(k, str) and k.endswith(f"__{old}")]:
        st.session_state[key[: -len(old)] + new] = st.session_state[key]
    st.query_params["lang"] = new


def selector() -> None:
    """Seletor de idioma. A escolha vai para a URL (?lang=) para o link ser compartilhável."""
    st.session_state["lang_shown"] = lang()
    st.selectbox(
        t("lang_label"), list(SUPPORTED), format_func=lambda code: f"🌐  {SUPPORTED[code]}",
        key="lang", on_change=_remember, label_visibility="collapsed",
    )


def t(key: str, **values) -> str:
    text = STRINGS.get(lang(), {}).get(key)
    if text is None:
        text = STRINGS[DEFAULT].get(key, key)
    return text.format(**values) if values else text


def number(value: int) -> str:
    formatted = f"{value:,}"
    return formatted.replace(",", ".") if lang() == "pt" else formatted


STRINGS = {
    "en": {
        "lang_label": "Language",
        "page_title": "API Atlas — Free Public APIs",
        "loading": "Loading the public API catalog…",
        "err_load": "Could not load the catalog from GitHub.",
        "err_parse": "The catalog was downloaded, but no category table was found. The source repository may have changed its structure.",
        "err_hint": "Check your internet connection. The catalog is fetched directly from GitHub.",
        "sources_partial": "Some sources could not be loaded right now ({sources}); the catalog is temporarily smaller.",
        "yes": "Yes", "no": "No", "unknown": "Unknown",
        "no_description": "No description available.",
        "load_more": "Load more  ·  {n} left",
        "eyebrow": "THE OPEN API DIRECTORY",
        "hero_l1": "A world of APIs.",
        "hero_l2": "One search away.",
        "hero_sub": "A collective list of free APIs for software and web development.",
        "stat_apis": "free APIs",
        "stat_categories": "categories",
        "tab_catalog": "API catalog",
        "tab_kits": "Power BI kits",
        "tab_python": "Python generator",
        "tab_montador": "Project builder",
        "tab_ask": "Question to project",
        "ask_title": "From question to project",
        "ask_sub": "Describe what you want to find out",
        "ask_intro": "Write a business question and get a Power BI project ready to answer it: the right public data sources, the period you mentioned, relationships, measures, a page built around your question and one page per source. This first version reads keywords; review what it understood before downloading.",
        "ask_label": "Your question",
        "ask_placeholder": "e.g. Do the states with the most unemployment have the lowest income? How has it changed since 2020?",
        "ask_examples": "Or start from an example:",
        "ask_nothing": "I couldn't link this question to any kit yet. Try mentioning the topic, such as unemployment, income, inflation, GDP, population, harvest, livestock, holidays, weather, exchange rates or other countries.",
        "ask_understood": "What I understood",
        "ask_because": "because of {words}",
        "ask_period": "Period: {start} to {end}",
        "ask_period_one": "Period: {year}",
        "ask_adjust": "Kits in the project (add or remove)",
        "ask_params": "Parameters set from the question ({n})",
        "ask_full_series": "These kits always bring the full series, whatever the period: {kits}. Filter the period in the report.",
        "mont_page_question": "Your question",
        "mont_title": "Project builder",
        "mont_sub": "Several kits, one Power BI project",
        "mont_intro": "Pick the kits you want and download a Power BI project with one query per table, a calendar table, the relationships between shared keys, the DAX measures and a report page per kit with starter visuals.",
        "mont_select": "Kits in the project",
        "mont_empty": "Pick at least one kit to build the project.",
        "mont_tables": "Tables",
        "mont_pages": "Report pages",
        "mont_visuals": "visuals",
        "mont_page_summary": "Summary",
        "mont_page_blank": "Page 1",
        "mont_page_cover": "Cover",
        "mont_cover_title": "Project title (shown on the cover)",
        "mont_cover_default": "Data project",
        "mont_cover_stats": "{tables} tables  ·  {measures} measures  ·  {pages} pages",
        "mont_cover_contents": "In this report",
        "mont_cover_sources": "Sources: {sources}",
        "mont_cover_made": "Built with API Atlas on {date}  ·  atlasapi.streamlit.app",
        "mont_columns": "columns",
        "mont_auto": "added automatically",
        "mont_rels": "Relationships",
        "mont_no_rels": "No relationships: the selected tables do not share keys.",
        "mont_measures": "DAX measures",
        "mont_no_measures": "No measures for this selection.",
        "mont_aviso_censo": "dCenso2022 was added to work as the municipality dimension: it has one row per municipality.",
        "mont_aviso_anos": "PIB per Capita divides GDP by population: pick the same year in both kits, otherwise the measure mixes different years.",
        "mont_loose": "Not related to other tables: {tables}. They have year or quarter columns instead of a date.",
        "mont_download": "Download the Power BI project (.zip)",
        "mont_how": "Unzip the file and open AtlasProjeto.pbip in Power BI Desktop. Then click Refresh to load the data; the first time, choose anonymous access for each source.",
        "mont_bridge": "Generate a fictitious sales dataset in BI Data Generator and add it to this project: relate it to dCalendario by date and to dCenso2022 or dUF by location to analyse it next to the real data.",
        "mont_readme_title": "API Atlas - Power BI project",
        "mont_readme_open": "HOW TO OPEN\n1. Unzip this file into a folder.\n2. Open AtlasProjeto.pbip in Power BI Desktop.\n3. Click Refresh to load the data. The first time, choose anonymous access and the privacy level Public for each source.\n4. The report already has one page per kit, with cards, charts and tables to start from. Edit them freely.\nIf Power BI does not open the .pbip file, enable File > Options > Preview features > Power BI Project (.pbip) save option and restart.",
        "mont_readme_tables": "TABLES",
        "mont_readme_rels": "RELATIONSHIPS (many -> one)",
        "mont_readme_extra": "ALSO IN THIS FILE\n  - consultas_power_query/: the Power Query (M) code of each table, to paste into another file.\n  - scripts_python/: the same data in Python (requests + pandas).\n  - medidas.dax: the DAX measures of the project.",
        "mont_readme_source": "Generated at https://atlasapi.streamlit.app/",
        "search_label": "Search APIs",
        "search_placeholder": "Find development, games, images APIs...",
        "results_title": "Search results",
        "results_count": "{n} APIs found",
        "results_count_one": "1 API found",
        "empty_title": "No APIs found",
        "empty_text": "Try another name or keyword.",
        "featured_title": "Featured APIs",
        "featured_sub": "A few places to start exploring",
        "featured_link": "API documentation ↗",
        "browse_title": "Browse by category",
        "browse_sub": "Explore the full collection",
        "n_apis": "{n} APIs",
        "back": "← Back to all categories",
        "categories_unavailable": "Categories will appear once the GitHub catalog is available.",
        "footer_tag": "Built for curious developers.",
        "ux_search_hint": "Tip: press / to search and Esc to clear. Several words narrow the results.",
        "ux_popular": "Most popular",
        "ux_all_cats": "Show all {n} categories",
        "ux_fewer_cats": "Show only the most popular",
        "ux_clear_filter": "Clear filter",
        "ux_clear_search": "Clear search",
        "ux_select_theme": "Select all",
        "ux_clear_selection": "Clear selection",
        "ux_selected_one": "1 kit selected",
        "ux_selected": "{n} kits selected",
        "ux_use_in_builder": "Add to the Project builder",
        "ux_added_builder": "Kit added to the Project builder with the same parameters.",
        "ux_copy_code": "Copy code",
        "ux_copied": "Copied to the clipboard.",
        "ux_copied_m": "Code copied. In Power BI: Get data → Blank query → Advanced Editor → paste.",
        "ux_done_title": "Project downloaded",
        "ux_done_steps": "Unzip AtlasProjeto.zip|Open AtlasProjeto.pbip in Power BI Desktop|Click Refresh and choose anonymous access for each source",
        "ux_url_fixed": "https:// was added to the address.",
        "ux_github": "Source code on GitHub",
        "ux_back_top": "Back to top",
        "ux_updating": "Updating…",
        # Kits
        "kits_title": "Project kits for Power BI",
        "kits_sub": "APIs with no sign-up, code included",
        "kits_intro": "Pick an API, adjust the parameters and copy the query in Power Query or Python. Each kit shows how to fit the data into a star schema built with {link}.",
        "kit_select": "Kit",
        "docs": "documentation ↗",
        "card_script": "Python script",
        "role": "Role", "role_fact": "Fact", "role_dimension": "Dimension",
        "table": "Table",
        "no_auth": "No authentication",
        "columns": "Columns",
        "tab_m": "Power Query (M)",
        "tab_py": "Python",
        "tab_model": "Model and ideas",
        "tab_preview": "Data preview",
        "m_how": "In Power BI: Get data → Blank query → Advanced Editor. Paste the code and rename the query to {table}.",
        "m_note": "The query uses RelativePath and Query, the format the Power BI Service accepts for scheduled refresh.",
        "py_how": "In Power BI: Get data → Python script. The result is the df table. pandas and requests must be installed in the Python that Power BI uses.",
        "code_names_note": "Table, column and variable names in the code are in Portuguese.",
        "bridge_title": "With BI Data Generator",
        "visuals_title": "Visual ideas",
        "dax_title": "DAX measures to start with",
        "open_bdg": "Open BI Data Generator ↗",
        "preview_caption": "Runs this kit's Python script and shows the first rows.",
        "preview_button": "Load preview",
        "preview_spinner": "Calling the API…",
        "preview_error": "Could not reach the API right now. Check the selected period or try again in a moment.",
        "preview_detail": "Detail: {detail}",
        "preview_shape": "{rows} rows · {cols} columns",
        "download_csv": "Download CSV",
        "period_error": "The start of the period must come before the end.",
        "invalid_format": "{label}: invalid format. {help}",
        # Gerador Python
        "gen_title": "Python script generator",
        "gen_sub": "For any API in the catalog",
        "gen_intro": "Paste the URL of an endpoint that returns JSON and get the script in requests + pandas, ready for a notebook or for the Power BI Python connector.",
        "gen_url": "Endpoint URL",
        "gen_url_ph": "https://api.example.com/v1/data?year=2025",
        "gen_path": "Where the list of records is (optional)",
        "gen_path_help": "Keys separated by dots down to the list inside the JSON. Leave empty if the response already is the list.",
        "gen_csv": "Also save as CSV",
        "gen_auth": "Authentication",
        "auth_none": "None", "auth_header": "Key in header", "auth_query": "Key in URL",
        "gen_key_name": "Header or parameter name",
        "gen_hint": "The endpoint address is in the documentation of each API in the catalog.",
        "gen_how": "In Power BI: Get data → Python script. The result is the df table.",
        "gen_swap_key": "Replace {placeholder} with your key before running.",
        "next_title": "Next step",
        "next_text": "With the data loaded, generate the calendar table and the DAX measures in BI Data Generator to complete the star schema.",
        "err_url": "Enter a full URL, starting with https://",
        "err_key_name": "Enter the name of the header or parameter that carries the key.",
        "code_key_placeholder": "PASTE_YOUR_KEY_HERE",
        "code_comment_path": "# Walk down to the list of records inside the JSON",
        "code_comment_normalize": "# Nested columns become dotted names, such as address.city",
        "code_var_params": "params", "code_var_headers": "headers",
        "code_var_response": "response", "code_var_data": "data", "code_csv_name": "data.csv",
    },
    "pt": {
        "lang_label": "Idioma",
        "page_title": "API Atlas — APIs públicas e gratuitas",
        "loading": "Carregando o catálogo de APIs públicas…",
        "err_load": "Não foi possível carregar o catálogo do GitHub.",
        "err_parse": "O catálogo foi baixado, mas nenhuma tabela de categorias foi identificada. A estrutura do repositório de origem pode ter mudado.",
        "err_hint": "Confira a conexão com a internet. O catálogo é obtido diretamente do GitHub.",
        "sources_partial": "Algumas fontes não puderam ser carregadas agora ({sources}); o catálogo está temporariamente menor.",
        "yes": "Sim", "no": "Não", "unknown": "Não informado",
        "no_description": "Sem descrição disponível.",
        "load_more": "Carregar mais  ·  restam {n}",
        "eyebrow": "O DIRETÓRIO ABERTO DE APIS",
        "hero_l1": "Um mundo de APIs.",
        "hero_l2": "A uma busca de distância.",
        "hero_sub": "Uma lista coletiva de APIs gratuitas para desenvolvimento de software e web.",
        "stat_apis": "APIs gratuitas",
        "stat_categories": "categorias",
        "tab_catalog": "Catálogo de APIs",
        "tab_kits": "Kits Power BI",
        "tab_python": "Gerador Python",
        "tab_montador": "Montador de Projeto",
        "tab_ask": "Pergunta → Projeto",
        "ask_title": "Da pergunta ao projeto",
        "ask_sub": "Diga o que você quer descobrir",
        "ask_intro": "Escreva uma pergunta de negócio e receba um projeto do Power BI pronto para respondê-la: as fontes de dados públicas certas, o período citado, os relacionamentos, as medidas, uma página montada para a sua pergunta e uma página por fonte. Esta primeira versão lê palavras-chave; confira o que foi entendido antes de baixar.",
        "ask_label": "Sua pergunta",
        "ask_placeholder": "Ex.: Os estados com mais desemprego são os de menor renda? Como isso mudou desde 2020?",
        "ask_examples": "Ou comece por um exemplo:",
        "ask_nothing": "Ainda não consegui ligar essa pergunta a nenhum kit. Tente citar o tema, como desemprego, renda, inflação, PIB, população, safra, rebanho, feriados, clima, câmbio ou outros países.",
        "ask_understood": "O que eu entendi",
        "ask_because": "por causa de {words}",
        "ask_period": "Período: de {start} a {end}",
        "ask_period_one": "Período: {year}",
        "ask_adjust": "Kits do projeto (inclua ou retire)",
        "ask_params": "Parâmetros definidos pela pergunta ({n})",
        "ask_full_series": "Estes kits sempre trazem a série completa, qualquer que seja o período: {kits}. Filtre o período no relatório.",
        "mont_page_question": "Sua pergunta",
        "mont_title": "Montador de Projeto",
        "mont_sub": "Vários kits, um projeto Power BI",
        "mont_intro": "Escolha os kits que quiser e baixe um projeto do Power BI com uma consulta por tabela, a tabela calendário, os relacionamentos entre as chaves em comum, as medidas DAX e uma página de relatório por kit, com visuais iniciais.",
        "mont_select": "Kits do projeto",
        "mont_empty": "Escolha pelo menos um kit para montar o projeto.",
        "mont_tables": "Tabelas",
        "mont_pages": "Páginas do relatório",
        "mont_visuals": "visuais",
        "mont_page_summary": "Resumo",
        "mont_page_blank": "Página 1",
        "mont_page_cover": "Capa",
        "mont_cover_title": "Título do projeto (aparece na capa)",
        "mont_cover_default": "Projeto de dados",
        "mont_cover_stats": "{tables} tabelas  ·  {measures} medidas  ·  {pages} páginas",
        "mont_cover_contents": "Neste relatório",
        "mont_cover_sources": "Fontes: {sources}",
        "mont_cover_made": "Gerado no API Atlas em {date}  ·  atlasapi.streamlit.app",
        "mont_columns": "colunas",
        "mont_auto": "incluída automaticamente",
        "mont_rels": "Relacionamentos",
        "mont_no_rels": "Sem relacionamentos: as tabelas escolhidas não têm chaves em comum.",
        "mont_measures": "Medidas DAX",
        "mont_no_measures": "Nenhuma medida para esta seleção.",
        "mont_aviso_censo": "A dCenso2022 foi incluída para servir de dimensão de municípios: ela tem uma linha por município.",
        "mont_aviso_anos": "A medida PIB per Capita divide o PIB pela população: escolha o mesmo ano nos dois kits, senão ela mistura anos diferentes.",
        "mont_loose": "Sem relacionamento com outras tabelas: {tables}. Elas têm colunas de ano ou trimestre, não de data.",
        "mont_download": "Baixar o projeto Power BI (.zip)",
        "mont_how": "Descompacte o arquivo e abra AtlasProjeto.pbip no Power BI Desktop. Depois clique em Atualizar para carregar os dados; na primeira vez, escolha acesso anônimo para cada fonte.",
        "mont_bridge": "Gere uma base fictícia de vendas no BI Data Generator e acrescente a este projeto: relacione com a dCalendario pela data e com a dCenso2022 ou a dUF pela localidade para analisar ao lado dos dados reais.",
        "mont_readme_title": "API Atlas - Projeto Power BI",
        "mont_readme_open": "COMO ABRIR\n1. Descompacte este arquivo em uma pasta.\n2. Abra AtlasProjeto.pbip no Power BI Desktop.\n3. Clique em Atualizar para carregar os dados. Na primeira vez, escolha acesso anônimo e o nível de privacidade Público para cada fonte.\n4. O relatório já traz uma página por kit, com cartões, gráficos e tabelas para começar. Edite à vontade.\nSe o Power BI não abrir o arquivo .pbip, ative Arquivo > Opções > Recursos de visualização > Opção de salvar Projeto do Power BI (.pbip) e reinicie.",
        "mont_readme_tables": "TABELAS",
        "mont_readme_rels": "RELACIONAMENTOS (muitos -> um)",
        "mont_readme_extra": "TAMBÉM NESTE ARQUIVO\n  - consultas_power_query/: o código Power Query (M) de cada tabela, para colar em outro arquivo.\n  - scripts_python/: os mesmos dados em Python (requests + pandas).\n  - medidas.dax: as medidas DAX do projeto.",
        "mont_readme_source": "Gerado em https://atlasapi.streamlit.app/",
        "search_label": "Buscar APIs",
        "search_placeholder": "Busque APIs de desenvolvimento, jogos, imagens...",
        "results_title": "Resultados da busca",
        "results_count": "{n} APIs encontradas",
        "results_count_one": "1 API encontrada",
        "empty_title": "Nenhuma API encontrada",
        "empty_text": "Tente outro nome ou palavra-chave.",
        "featured_title": "APIs em destaque",
        "featured_sub": "Alguns pontos de partida para explorar",
        "featured_link": "Documentação da API ↗",
        "browse_title": "Navegar por categoria",
        "browse_sub": "Explore a coleção completa",
        "n_apis": "{n} APIs",
        "back": "← Voltar para todas as categorias",
        "categories_unavailable": "As categorias serão exibidas quando o catálogo do GitHub estiver disponível.",
        "footer_tag": "Feito para devs curiosos.",
        "ux_search_hint": "Dica: tecle / para buscar e Esc para limpar. Várias palavras refinam o resultado.",
        "ux_popular": "Mais populares",
        "ux_all_cats": "Ver todas as {n} categorias",
        "ux_fewer_cats": "Mostrar só as mais populares",
        "ux_clear_filter": "Limpar filtro",
        "ux_clear_search": "Limpar busca",
        "ux_select_theme": "Selecionar todos",
        "ux_clear_selection": "Limpar seleção",
        "ux_selected_one": "1 kit selecionado",
        "ux_selected": "{n} kits selecionados",
        "ux_use_in_builder": "Usar no Montador de Projeto",
        "ux_added_builder": "Kit incluído no Montador com os mesmos parâmetros.",
        "ux_copy_code": "Copiar código",
        "ux_copied": "Copiado para a área de transferência.",
        "ux_copied_m": "Código copiado. No Power BI: Obter dados → Consulta em branco → Editor Avançado → colar.",
        "ux_done_title": "Projeto baixado",
        "ux_done_steps": "Descompacte o AtlasProjeto.zip|Abra o AtlasProjeto.pbip no Power BI Desktop|Clique em Atualizar e escolha acesso anônimo em cada fonte",
        "ux_url_fixed": "Acrescentei https:// ao endereço.",
        "ux_github": "Código no GitHub",
        "ux_back_top": "Voltar ao topo",
        "ux_updating": "Atualizando…",
        # Kits
        "kits_title": "Kits de projeto para Power BI",
        "kits_sub": "APIs sem cadastro, com o código pronto",
        "kits_intro": "Escolha uma API, ajuste os parâmetros e copie a consulta em Power Query ou em Python. Cada kit indica como encaixar os dados em um modelo estrela criado no {link}.",
        "kit_select": "Kit",
        "docs": "documentação ↗",
        "card_script": "Script Python",
        "role": "Papel", "role_fact": "Fato", "role_dimension": "Dimensão",
        "table": "Tabela",
        "no_auth": "Sem autenticação",
        "columns": "Colunas",
        "tab_m": "Power Query (M)",
        "tab_py": "Python",
        "tab_model": "Modelo e ideias",
        "tab_preview": "Prévia dos dados",
        "m_how": "No Power BI: Obter dados → Consulta em branco → Editor Avançado. Cole o código e renomeie a consulta para {table}.",
        "m_note": "A consulta usa RelativePath e Query, o formato que o Power BI Service aceita na atualização agendada.",
        "py_how": "No Power BI: Obter dados → Script Python. O resultado fica na tabela df. É preciso ter pandas e requests instalados no Python que o Power BI usa.",
        "code_names_note": "",
        "bridge_title": "Com o BI Data Generator",
        "visuals_title": "Ideias de visuais",
        "dax_title": "Medidas DAX para começar",
        "open_bdg": "Abrir o BI Data Generator ↗",
        "preview_caption": "Roda o script Python deste kit e mostra as primeiras linhas.",
        "preview_button": "Carregar prévia",
        "preview_spinner": "Consultando a API…",
        "preview_error": "Não foi possível consultar a API agora. Confira o período escolhido ou tente de novo em instantes.",
        "preview_detail": "Detalhe: {detail}",
        "preview_shape": "{rows} linhas · {cols} colunas",
        "download_csv": "Baixar CSV",
        "period_error": "O início do período precisa ser anterior ao fim.",
        "invalid_format": "{label}: formato inválido. {help}",
        # Gerador Python
        "gen_title": "Gerador de script Python",
        "gen_sub": "Para qualquer API do catálogo",
        "gen_intro": "Cole a URL de um endpoint que devolve JSON e receba o script em requests + pandas, pronto para um notebook ou para o conector Python do Power BI.",
        "gen_url": "URL do endpoint",
        "gen_url_ph": "https://api.exemplo.com/v1/dados?ano=2025",
        "gen_path": "Onde está a lista de registros (opcional)",
        "gen_path_help": "Chaves separadas por ponto até a lista dentro do JSON. Deixe vazio se a resposta já for a lista.",
        "gen_csv": "Salvar também em CSV",
        "gen_auth": "Autenticação",
        "auth_none": "Nenhuma", "auth_header": "Chave no cabeçalho", "auth_query": "Chave na URL",
        "gen_key_name": "Nome do cabeçalho ou do parâmetro",
        "gen_hint": "O endereço do endpoint está na documentação de cada API do catálogo.",
        "gen_how": "No Power BI: Obter dados → Script Python. O resultado fica na tabela df.",
        "gen_swap_key": "Troque {placeholder} pela sua chave antes de rodar.",
        "next_title": "Próximo passo",
        "next_text": "Com os dados carregados, gere a tabela calendário e as medidas DAX no BI Data Generator para fechar o modelo estrela.",
        "err_url": "Informe uma URL completa, começando com https://",
        "err_key_name": "Informe o nome do cabeçalho ou do parâmetro que leva a chave.",
        "code_key_placeholder": "COLE_SUA_CHAVE_AQUI",
        "code_comment_path": "# Desce até a lista de registros dentro do JSON",
        "code_comment_normalize": "# Colunas aninhadas viram nomes com ponto, como endereco.cidade",
        "code_var_params": "parametros", "code_var_headers": "cabecalhos",
        "code_var_response": "resposta", "code_var_data": "dados", "code_csv_name": "dados.csv",
    },
}

# Descrições das APIs em destaque (o original, em inglês, fica no app.py).
FEATURED = {
    "pt": {
        "Open-Meteo": "Previsão do tempo e dados climáticos históricos.",
        "The Cat API": "Imagens, fatos e outros dados sobre gatos.",
        "Frankfurter": "Taxas de câmbio e conversão de moedas.",
        "PokéAPI": "Fonte de dados RESTful de Pokémon para apps e jogos.",
        "Jikan": "API não oficial do MyAnimeList para animes e mangás.",
        "Open Library": "Explore registros de livros, autores e edições.",
    },
}


def featured_description(name: str, original: str) -> str:
    return FEATURED.get(lang(), {}).get(name, original)


# ---------- Catálogo (categorias e descrições das APIs) ----------

@lru_cache(maxsize=None)
def _catalog(language: str) -> dict:
    """Lê catalog_<idioma>.json: {"categories": {...}, "descriptions": {...}}.

    As chaves são os textos originais em inglês do repositório de origem.
    APIs novas ou com descrição alterada lá ficam em inglês até serem traduzidas.
    """
    path = Path(__file__).parent / f"catalog_{language}.json"
    if not path.exists():
        return {"categories": {}, "descriptions": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def category(name: str) -> str:
    return _catalog(lang())["categories"].get(name, name)


def description(text: str) -> str:
    return _catalog(lang())["descriptions"].get(text, text)


def sort_key(text: str) -> str:
    """Chave de ordenação que ignora acentos, para "Câmbio" ficar junto de "Calendário"."""
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().casefold()
