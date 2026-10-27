"""Ponte entre o código do API Atlas e as funções da Vercel (pasta api/).

As funções chamam os módulos de lógica (catalog, kits, kits_extra,
kits_ibge, kits_i18n, montador e i18n) e devolvem JSON ou o .zip do projeto.

Cada requisição define o idioma em `usar_idioma` antes de chamar a lógica.
"""
from __future__ import annotations

import datetime as dt
import json
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlsplit


import catalog
import i18n
import kits
import montador

PAGINA_PREVIA = 200
LIMITE_CSV = 8_000_000  # bytes; acima disso a prévia não traz o CSV completo


# ---------- Idioma ----------

def usar_idioma(codigo: str | None) -> str:
    return i18n.set_lang(codigo)


def detectar_idioma(cabecalhos) -> str:
    """Idioma do navegador e, se ele não servir, o país de acesso (a Vercel envia X-Vercel-IP-Country)."""
    return i18n.detect(None, None, cabecalhos)


# ---------- Configuração da página: textos e kits ----------

# APIs em destaque na aba Catálogo.
DESTAQUES = [
    {"name": "Open-Meteo", "category": "Weather", "description": "Weather forecasts and historical weather data.", "icon": "🌤️", "url": "https://open-meteo.com/"},
    {"name": "The Cat API", "category": "Animals", "description": "Images, facts, and other data about cats.", "icon": "🐈", "url": "https://thecatapi.com/"},
    {"name": "Frankfurter", "category": "Finance", "description": "Exchange rates and currency conversion data.", "icon": "💱", "url": "https://www.frankfurter.app/"},
    {"name": "PokéAPI", "category": "Games & Comics", "description": "A RESTful Pokémon data source for apps and games.", "icon": "🎮", "url": "https://pokeapi.co/"},
    {"name": "Jikan", "category": "Anime", "description": "Unofficial MyAnimeList API for anime and manga.", "icon": "✨", "url": "https://jikan.moe/"},
    {"name": "Open Library", "category": "Books", "description": "Explore book records, authors, and editions.", "icon": "📚", "url": "https://openlibrary.org/developers/api"},
]

def _parametro(kit: dict, parametro: dict) -> dict:
    saida = {
        "chave": parametro["chave"],
        "tipo": parametro["tipo"],
        "rotulo": kits.tr_parametro(kit, parametro, "rotulo"),
        "ajuda": kits.tr_parametro(kit, parametro, "ajuda") or "",
    }
    if parametro["tipo"] == "opcoes":
        saida["opcoes"] = list(kits.tr_parametro(kit, parametro, "opcoes"))
    for campo in ("padrao", "min", "max"):
        if campo in parametro:
            saida[campo] = parametro[campo]
    return saida


# Ordem dos temas nas listas agrupadas da página (lei de Hick: menos opções de cada vez).
ORDEM_TEMAS = ("economia", "trabalho", "municipios", "agro", "calendario", "internacional", "conhecimento", "politica")
# Kits fora do Montador também precisam de um tema para entrar nos grupos.
TEMA_FORA_DO_MONTADOR = {"municipios": "municipios", "deputados": "politica"}
NOME_POLITICA = {"pt": "Política", "en": "Politics"}


def _tema(kit_id: str) -> str:
    return montador.TEMA_DO_KIT.get(kit_id) or TEMA_FORA_DO_MONTADOR.get(kit_id, "internacional")


def _nome_tema(chave: str, idioma: str) -> str:
    if chave == "politica":
        return NOME_POLITICA.get(idioma, NOME_POLITICA["en"])
    tema = montador.TEMAS[chave]
    return tema.get(idioma, tema["en"])


def configuracao(idioma: str) -> dict:
    usar_idioma(idioma)
    montaveis = {kit["id"] for kit in montador.montaveis()}
    lista = []
    for kit in kits.KITS:
        lista.append({
            "id": kit["id"], "icone": kit["icone"],
            "titulo": kits.tr(kit, "titulo"), "fonte": kits.tr(kit, "fonte"), "docs": kit["docs"],
            "resumo": kits.tr(kit, "resumo"), "papel": kit["papel"], "tabela": kit["tabela"],
            "colunas": kits.tr(kit, "colunas"), "observacao": kits.tr(kit, "observacao") or "",
            "ponte": kits.tr(kit, "ponte") or "", "visuais": kits.tr(kit, "visuais") or [],
            "dax": kits.tr(kit, "dax") or "",
            "parametros": [_parametro(kit, p) for p in kit["parametros"]],
            "montavel": kit["id"] in montaveis,
            "tema": _tema(kit["id"]),
        })
    return {
        "lang": i18n.lang(),
        "idiomas": i18n.SUPPORTED,
        "textos": {**i18n.STRINGS[i18n.DEFAULT], **i18n.STRINGS.get(i18n.lang(), {})},
        "destaques": [{"nome": d["name"], "icone": d["icon"], "url": d["url"],
                       "categoria": i18n.category(d["category"]),
                       "descricao": i18n.featured_description(d["name"], d["description"])} for d in DESTAQUES],
        "kits": lista,
        "temas": [{"id": chave, "nome": _nome_tema(chave, i18n.lang())}
                  for chave in ORDEM_TEMAS if any(k["tema"] == chave for k in lista)],
        "bdg": kits.BI_DATA_GENERATOR_URL,
        "padrao_montador": [i for i in ("populacao", "pib_municipios", "ipca") if i in montaveis],
    }


# ---------- Kits: valores da tela -> código ----------

def _kit(kit_id: str) -> dict:
    for kit in kits.KITS:
        if kit["id"] == kit_id:
            return kit
    raise ValueError(f"Kit desconhecido: {kit_id}")


def _bruto(parametro: dict, valor):
    """Converte o valor que vem do navegador no tipo que kits.validar espera."""
    tipo = parametro["tipo"]
    if tipo == "data":
        if valor in (None, ""):
            valor = parametro["padrao"]
        return dt.date.fromisoformat(str(valor)[:10])
    if tipo == "inteiro":
        numero = int(parametro["padrao"] if valor in (None, "") else valor)
        return max(parametro["min"], min(parametro["max"], numero))
    if tipo == "opcoes":
        indice = int(valor or 0)
        if not 0 <= indice < len(parametro["opcoes"]):
            indice = 0
        return indice
    return parametro["padrao"] if valor is None else str(valor)


def valores_do_kit(kit: dict, recebidos: dict | None) -> tuple[dict, dict]:
    """(valores dos marcadores, valores brutos). Levanta ValueError com a mensagem traduzida."""
    recebidos = recebidos or {}
    brutos, valores = {}, {}
    for parametro in kit["parametros"]:
        brutos[parametro["chave"]] = _bruto(parametro, recebidos.get(parametro["chave"]))
    for parametro in kit["parametros"]:
        valores.update(kits.validar(
            parametro, brutos[parametro["chave"]],
            kits.tr_parametro(kit, parametro, "rotulo"), kits.tr_parametro(kit, parametro, "ajuda") or "",
        ))
    kits.checar_intervalos(brutos)
    return valores, brutos


def codigo_do_kit(kit_id: str, recebidos: dict | None, idioma: str) -> dict:
    usar_idioma(idioma)
    kit = _kit(kit_id)
    try:
        valores, _ = valores_do_kit(kit, recebidos)
    except ValueError as erro:
        return {"erro": str(erro)}
    return {"m": kits.preencher(kit["m"], valores), "python": kits.preencher(kit["python"], valores)}


def previa(kit_id: str, recebidos: dict | None, idioma: str) -> dict:
    """Roda o script Python do kit. O código é gerado aqui a partir dos parâmetros validados,
    nunca recebido do navegador."""
    usar_idioma(idioma)
    kit = _kit(kit_id)
    try:
        valores, _ = valores_do_kit(kit, recebidos)
    except ValueError as erro:
        return {"erro": str(erro)}
    codigo = kits.preencher(kit["python"], valores)
    try:
        tabela = kits.executar_previa(codigo)
    except Exception as erro:  # a API de origem pode estar fora do ar ou recusar o período
        return {"falha": i18n.t("preview_error"),
                "detalhe": i18n.t("preview_detail", detail=f"{type(erro).__name__}: {str(erro)[:200]}")}
    inicio = json.loads(tabela.head(PAGINA_PREVIA).to_json(orient="split", date_format="iso",
                                                           default_handler=str, force_ascii=False))
    csv = tabela.to_csv(index=False)
    return {
        "aviso": i18n.t("preview_empty") if tabela.empty else "",
        "resumo": i18n.t("preview_shape", rows=i18n.number(len(tabela)), cols=len(tabela.columns)),
        "colunas": [str(c) for c in inicio["columns"]],
        "linhas": inicio["data"],
        "csv": csv if len(csv.encode("utf-8")) <= LIMITE_CSV else None,
        "arquivo": f"{kit['tabela']}.csv",
    }


# ---------- Montador de Projeto ----------

def _plano(escolhas: list[dict], titulo: str) -> tuple[dict | None, str | None]:
    disponiveis = {kit["id"]: kit for kit in montador.montaveis()}
    selecao = []
    for escolha in escolhas:
        kit = disponiveis.get(str(escolha.get("id")))
        if not kit:
            continue
        try:
            valores, _ = valores_do_kit(kit, escolha.get("valores"))
        except ValueError as erro:
            return None, f"{kits.tr(kit, 'titulo')}: {erro}"
        selecao.append((kit, valores))
    if not selecao:
        return None, i18n.t("mont_empty")
    plano = montador.planejar(selecao)
    plano["titulo"] = (titulo or "").strip()[:60] or i18n.t("mont_cover_default")
    return plano, None


def resumo_projeto(escolhas: list[dict], titulo: str, idioma: str) -> dict:
    usar_idioma(idioma)
    plano, erro = _plano(escolhas, titulo)
    if erro:
        return {"erro": erro}
    secoes = montador.paginas(plano)
    return {
        "tabelas": [{"nome": item["nome"], "colunas": len(item["esquema"]), "automatica": bool(item.get("automatica"))}
                    for item in plano["tabelas"]],
        "relacionamentos": [list(r) for r in plano["relacionamentos"]],
        "medidas": [m["name"] for m in plano["medidas"]],
        "paginas": [{"nome": secao["displayName"],
                     "visuais": sum("prototypeQuery" in v["config"] for v in secao["visualContainers"])}
                    for secao in secoes],
        "avisos": [i18n.t(f"mont_{aviso}") for aviso in plano["avisos"]]
                  + ([i18n.t("mont_loose", tables=", ".join(plano["soltas"]))] if plano["soltas"] else []),
    }


def zip_projeto(escolhas: list[dict], titulo: str, idioma: str) -> tuple[bytes | None, str | None]:
    usar_idioma(idioma)
    plano, erro = _plano(escolhas, titulo)
    if erro:
        return None, erro
    return montador.compactar(montador.arquivos(plano, montador._leiame(plano))), None


# ---------- Gerador Python ----------

def script(dados: dict, idioma: str) -> dict:
    usar_idioma(idioma)
    try:
        codigo = kits.gerar_script_generico(
            str(dados.get("url") or ""), str(dados.get("caminho") or ""),
            dados.get("autenticacao") if dados.get("autenticacao") in {"none", "header", "query"} else "none",
            str(dados.get("nome_chave") or ""), bool(dados.get("csv")),
        )
    except ValueError as erro:
        return {"erro": str(erro)}
    return {"codigo": codigo}


# ---------- Catálogo ----------

def _ler_fonte(fonte: dict) -> list[dict]:
    try:
        return catalog.PARSERS[fonte["format"]](catalog.fetch(fonte["urls"]))
    except (catalog.CatalogError, ValueError, KeyError, AttributeError, IndexError):
        return []


def carregar_catalogo() -> tuple[list[dict], list[str]]:
    """Igual a catalog.load, baixando a fonte principal e as fontes extras em paralelo."""
    with ThreadPoolExecutor(max_workers=len(catalog.EXTRAS) + 1) as grupo:
        principal = grupo.submit(lambda: catalog.parse_readme(catalog.fetch(catalog.PRIMARY["urls"])))
        extras = [(fonte, grupo.submit(_ler_fonte, fonte)) for fonte in catalog.EXTRAS]
        linhas_principais = principal.result()
        if not linhas_principais:
            raise catalog.CatalogError("err_parse")
        unidas, falhas = [], []
        for fonte, futuro in extras:
            linhas = futuro.result()
            if linhas:
                unidas.append((fonte["name"], linhas, fonte.get("dedupe_host", True)))
            else:
                falhas.append(fonte["name"])
    return catalog.merge(linhas_principais, unidas, catalog.PRIMARY["name"]), falhas


def _script_cartao(item: dict) -> str:
    if str(item.get("source")) != catalog.JSON_DATASETS:
        return ""
    try:
        return kits.gerar_script_generico(str(item["url"]), "", "none", "", False) + "\n\nprint(df.head())"
    except ValueError:
        return ""


def catalogo(idioma: str) -> dict:
    usar_idioma(idioma)
    try:
        linhas, falhas = carregar_catalogo()
    except catalog.CatalogError as erro:
        return {"erro": i18n.t(erro.key), "dica": i18n.t("err_hint"), "apis": []}
    apis = []
    for item in linhas:
        descricao = str(item.get("description") or "")
        categoria = str(item.get("category") or "")
        registro = {
            "n": str(item.get("name") or ""), "u": str(item.get("url") or ""),
            "c": i18n.category(categoria), "d": i18n.description(descricao),
            "a": str(item.get("auth") or ""), "h": str(item.get("https") or ""), "o": str(item.get("cors") or ""),
        }
        # Texto original, para a busca também achar pelo termo em inglês.
        if registro["d"] != descricao:
            registro["d0"] = descricao
        if registro["c"] != categoria:
            registro["c0"] = categoria
        codigo = _script_cartao(item)
        if codigo:
            registro["s"] = codigo
        apis.append(registro)
    aviso = i18n.t("sources_partial", sources=", ".join(falhas)) if falhas else ""
    return {"apis": apis, "aviso": aviso}


# ---------- HTTP ----------

class Base(BaseHTTPRequestHandler):
    """Respostas JSON com cache na borda da Vercel quando `cache` é informado."""

    def consulta(self) -> dict:
        return {k: v[-1] for k, v in parse_qs(urlsplit(self.path).query).items()}

    def corpo(self) -> dict:
        tamanho = int(self.headers.get("Content-Length") or 0)
        if tamanho <= 0 or tamanho > 200_000:
            return {}
        try:
            dados = json.loads(self.rfile.read(tamanho).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return {}
        return dados if isinstance(dados, dict) else {}

    def json(self, dados, status: int = 200, cache: int = 0) -> None:
        conteudo = json.dumps(dados, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        if cache:
            self.send_header("Cache-Control", f"public, max-age=300, s-maxage={cache}, stale-while-revalidate=86400")
        else:
            self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(conteudo)))
        self.end_headers()
        self.wfile.write(conteudo)

    def binario(self, conteudo: bytes, tipo: str, nome: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Disposition", f'attachment; filename="{nome}"')
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(conteudo)))
        self.end_headers()
        self.wfile.write(conteudo)

    def log_message(self, *args) -> None:  # silencia o log padrão de cada requisição
        pass
