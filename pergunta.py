"""Da pergunta ao projeto: transforma uma pergunta em português (ou inglês) num
projeto do Power BI.

Esta primeira versão não usa IA. Palavras-chave escolhem os kits, nomes de
produtos, cidades, moedas e países escolhem as opções dos kits, e expressões de
tempo ("desde 2020", "entre 2018 e 2023", "últimos 5 anos") viram o período.
O projeto em si é montado pelo Montador (montador.py).
"""

from __future__ import annotations

import datetime as dt
import re
import unicodedata

import kits
import montador
from i18n import lang


def normalizar(texto: str) -> str:
    """Minúsculas e sem acentos, com o mesmo tamanho do texto original."""
    saida = []
    for letra in texto:
        base = unicodedata.normalize("NFKD", letra)
        saida.append((base[0] if base else letra).lower())
    return "".join(saida)


# ---------- Palavras que escolhem os kits ----------
# Expressões regulares aplicadas ao texto normalizado; \b marca o início da palavra.
PALAVRAS = {
    "ipca": [r"\bipca\b", r"\binflac", r"\bcusto de vida", r"\bprecos? ao consumidor", r"\binflation\b"],
    "inpc": [r"\binpc\b"],
    "bcb": [r"\bselic\b", r"\bjuros\b", r"\bcopom\b", r"\btaxa basica", r"\binterest rate"],
    "cambio": [r"\bdolar", r"\beuro\b", r"\blibra\b", r"\biene\b", r"\byuan\b", r"\bcambi", r"\bcotac",
               r"\bmoedas?\b", r"\bexchange rate", r"\bcurrenc", r"\bdollar"],
    "pib_trimestral": [r"\bcrescimento economico", r"\beconomia brasileira", r"\brecessao", r"\beconomic growth"],
    "desemprego": [r"\bdesempreg", r"\bdesocupac", r"\bmercado de trabalho", r"\bemprego\b", r"\bunemploy"],
    "rendimento": [r"\brenda\b", r"\bsalari(?!o minimo)", r"\brendimento", r"\bremunerac", r"\bincome\b", r"\bwages?\b"],
    "populacao": [r"\bpopulac", r"\bhabitantes", r"\bdemograf", r"\bper capita", r"\bpopulation"],
    "censo2022": [r"\bcenso\b", r"\bdensidade", r"\bcensus\b", r"\bdensity"],
    "alfabetizacao": [r"\balfabetiz", r"\banalfabet", r"\bescolaridade", r"\bliteracy"],
    "comercio": [r"\bvarejo", r"\bcomercio\b", r"\bvendas", r"\bconsumo\b", r"\bretail"],
    "industria": [r"\bindustri"],
    "producao_agricola": [r"\bsafra", r"\bagricol", r"\bagricultura", r"\blavoura", r"\bcolheita", r"\bplantac",
                          r"\bcrops?\b", r"\bharvest"],
    "rebanhos": [r"\brebanho", r"\bpecuaria", r"\bgado\b", r"\bbois?\b", r"\bfrango", r"\bgalinha", r"\bporcos?\b",
                 r"\blivestock", r"\bcattle"],
    "feriados": [r"\bferiado", r"\bdias? uteis", r"\bdia util", r"\bholiday", r"\bbusiness days?"],
    "clima": [r"\bclima", r"\bchuva", r"\bchove", r"\btemperatura", r"\bcalor\b", r"\bfrio\b", r"\bprecipitac",
              r"\bweather", r"\brain"],
    "terremotos": [r"\bterremoto", r"\bsismo", r"\babalos? sismic", r"\btremores? de terra", r"\bearthquake"],
    "focus": [r"\bfocus\b", r"\bexpectativas? (?:de|do) mercado", r"\bprojec\w* (?:de|do) mercado",
              r"\bprevis\w* (?:de|do) mercado", r"\bmarket expectations?", r"\bmarket forecasts?"],
    "ipea": [r"\bipea", r"\bigp-?m\b", r"\bsalario minimo", r"\bminimum wage"],
    "cripto": [r"\bcripto", r"\bbitcoin", r"\bbtc\b", r"\bethereum", r"\bsolana", r"\bcrypto"],
    "feriados_mundo": [r"\bferiados? (?:no|do|pelo) mundo", r"\bholidays? (?:worldwide|around the world)"],
    "owid": [r"\bexpectativa de vida", r"\blife expectancy", r"\bemiss\w* de (?:co2|carbono)", r"\bco2\b",
             r"\bcarbono", r"\bcarbon", r"\binternet", r"\bour world in data"],
    "indicadores": [r"\bbanco mundial", r"\bworld bank", r"\bentre paises", r"\boutros paises", r"\bcountries"],
}
# "PIB" sozinho: nos municípios quando a pergunta fala de cidades ou estados, senão o PIB do Brasil.
_PIB = r"\bpib\b|\bgdp\b"
_CONTEXTO_LOCAL = r"\bmunicip|\bcidade|\bestado|\bufs?\b|\bregia|\bper capita|\bcit(?:y|ies)\b|\bstates?\b"

# ---------- Palavras que escolhem opções dos kits ----------
OPCOES = {
    ("bcb", "SERIE"): {"Selic meta (% a.a.)": [r"\bselic", r"\bjuros", r"\bcopom", r"\btaxa basica"]},
    ("producao_agricola", "PRODUTO"): {
        "Soja": [r"\bsoja", r"\bsoy"], "Milho": [r"\bmilho", r"\bcorn\b", r"\bmaize"],
        "Cana-de-açúcar": [r"\bcana\b", r"\bcana-de", r"\bsugarcane"], "Café (total)": [r"\bcafe\b", r"\bcoffee"],
        "Arroz": [r"\barroz", r"\brice\b"], "Feijão": [r"\bfeijao", r"\bbeans?\b"], "Trigo": [r"\btrigo", r"\bwheat"],
        "Algodão herbáceo": [r"\balgodao", r"\bcotton"], "Laranja": [r"\blaranja", r"\boranges?\b"],
        "Mandioca": [r"\bmandioca", r"\bcassava"],
    },
    ("rebanhos", "REBANHO"): {
        "Bovino": [r"\bbovin", r"\bgado\b", r"\bbois?\b", r"\bvacas?\b", r"\bcattle", r"\bcows?\b"],
        "Suíno": [r"\bsuin", r"\bporcos?\b", r"\bpigs?\b", r"\bhogs?\b"],
        "Galináceos": [r"\bgalin", r"\bfrango", r"\bchicken", r"\bpoultry"], "Ovino": [r"\bovin", r"\bovelha", r"\bsheep"],
        "Caprino": [r"\bcaprin", r"\bcabra", r"\bgoats?\b"], "Equino": [r"\bequin", r"\bcavalo", r"\bhorses?\b"], "Bubalino": [r"\bbubalin", r"\bbufal"], "Codornas": [r"\bcodorn"],
    },
    ("clima", "CIDADE"): {
        "São Paulo": [r"\bsao paulo"], "Rio de Janeiro": [r"\brio de janeiro", r"\bno rio\b"], "Brasília": [r"\bbrasilia"],
        "Belo Horizonte": [r"\bbelo horizonte", r"\bbh\b"], "Salvador": [r"\bsalvador"], "Fortaleza": [r"\bfortaleza"],
        "Recife": [r"\brecife"], "Manaus": [r"\bmanaus"], "Curitiba": [r"\bcuritiba"], "Porto Alegre": [r"\bporto alegre"],
    },
    ("focus", "INDICADOR"): {
        "IGP-M": [r"\bigp-?m"], "IPCA": [r"\bipca\b", r"\binflac", r"\binflation"], "PIB Total": [r"\bpib\b", r"\bgdp\b"],
        "Selic": [r"\bselic", r"\bjuros", r"\binterest"], "Câmbio": [r"\bdolar", r"\bcambi", r"\bdollar", r"\bexchange"],
    },
    ("ipea", "SERIE"): {
        "Salário mínimo real (R$ do último mês)": [r"\bsalario minimo real", r"\breal minimum wage"],
        "Salário mínimo vigente (R$)": [r"\bsalario minimo", r"\bminimum wage"],
        "IGP-M (% ao mês)": [r"\bigp-?m"],
    },
    ("cripto", "MOEDA"): {
        "Bitcoin (BTC)": [r"\bbitcoin", r"\bbtc\b"],
        "Ethereum (ETH)": [r"\bethereum", r"\beth\b"], "Solana (SOL)": [r"\bsolana", r"\bsol\b"],
        "XRP": [r"\bxrp\b", r"\bripple"], "Tether (USDT)": [r"\btether", r"\busdt\b"],
    },
    ("owid", "GRAFICO"): {
        "Expectativa de vida (anos)": [r"\bexpectativa de vida", r"\blife expectancy"],
        "Emissões de CO₂ per capita (t)": [r"\bco2\b", r"\bcarbon", r"\bemiss"],
        "Uso de internet (% da população)": [r"\binternet"],
        "PIB per capita (US$ PPC de 2021)": [r"\bpib per capita", r"\bgdp per capita"],
        "População": [r"\bpopulac", r"\bpopulation"],
    },
    ("indicadores", "INDICADOR"): {"População total": [r"\bpopulac", r"\bpopulation"],
                                   "Inflação anual (%)": [r"\binflac", r"\binflation"]},
}
MOEDAS = {"EUR": [r"\beuro"], "GBP": [r"\blibra", r"\bpound"], "JPY": [r"\biene", r"\byen\b"],
          "CNY": [r"\byuan", r"\brenminbi"], "ARS": [r"\bpeso argentino"], "CHF": [r"\bfranco suico"]}
PAISES = {
    "AR": [r"\bargentin"], "CL": [r"\bchile"], "MX": [r"\bmexic"], "US": [r"\bestados unidos", r"\beua\b", r"\busa\b",
    r"\bunited states"], "CN": [r"\bchina\b", r"\bchines"], "IN": [r"\bindia\b"], "JP": [r"\bjapao", r"\bjapan"],
    "DE": [r"\balemanha", r"\bgermany"], "FR": [r"\bfranca\b", r"\bfrance"], "GB": [r"\breino unido", r"\binglaterra",
    r"\buk\b"], "CA": [r"\bcanada"], "CO": [r"\bcolombia"], "PE": [r"\bperu\b"], "UY": [r"\buruguai", r"\buruguay"],
    "PY": [r"\bparaguai", r"\bparaguay"], "PT": [r"\bportugal"], "ES": [r"\bespanha", r"\bspain"],
    "IT": [r"\bitalia", r"\bitaly"], "RU": [r"\brussia"], "ZA": [r"\bafrica do sul", r"\bsouth africa"],
    "KR": [r"\bcoreia do sul", r"\bsouth korea"], "AU": [r"\baustralia"],
}

EXEMPLOS = {
    "pt": [
        "Os estados com mais desemprego são os de menor renda? Como isso mudou desde 2020?",
        "Qual o PIB per capita dos municípios e onde estão as maiores economias?",
        "Como a produção de soja e o rebanho bovino se distribuem entre os estados?",
    ],
    "en": [
        "Do the states with the most unemployment have the lowest income? How has it changed since 2020?",
        "What is the GDP per capita of Brazilian municipalities and where are the largest economies?",
        "How do soybean production and cattle herds spread across Brazilian states?",
    ],
}


def _achar(padroes: list[str], normal: str, original: str) -> str | None:
    """Primeiro trecho do texto original que casa com algum padrão."""
    for padrao in padroes:
        achado = re.search(padrao + r"\w*", normal)
        if achado:
            return original[achado.start():achado.end()]
    return None


def periodo(normal: str, hoje: dt.date) -> tuple[int, int] | None:
    """Anos inicial e final citados na pergunta, ou None."""
    ano_atual = hoje.year
    ano = r"((?:19|20)\d{2})"
    intervalo = re.search(rf"\b(?:entre|de|from|between)\s+{ano}\s+(?:e|a|ate|to|and)\s+{ano}", normal) \
        or re.search(rf"\b{ano}\s*[-–]\s*{ano}\b", normal)
    if intervalo:
        a, b = sorted((int(intervalo.group(1)), int(intervalo.group(2))))
        return a, b
    desde = re.search(rf"\b(?:desde|a partir de|since|from)\s+{ano}", normal)
    if desde:
        return int(desde.group(1)), ano_atual
    ultimos = re.search(r"\b(?:ultimos|last|past)\s+(\d{1,2})\s+(?:anos|years)", normal)
    if ultimos:
        return ano_atual - int(ultimos.group(1)), ano_atual
    if re.search(r"\b(?:este ano|neste ano|this year)\b", normal):
        return ano_atual, ano_atual
    anos = sorted({int(a) for a in re.findall(rf"\b{ano}\b", normal)})
    if anos:
        return anos[0], anos[-1]
    return None


def interpretar(pergunta: str, hoje: dt.date | None = None) -> dict:
    """Kits, motivos, opções e período entendidos na pergunta."""
    hoje = hoje or dt.date.today()
    normal = normalizar(pergunta)
    montaveis = {k["id"] for k in montador.montaveis()}
    motivos: dict[str, list[str]] = {}

    def marcar(kit_id: str, trecho: str | None) -> None:
        if trecho and kit_id in montaveis:
            lista = motivos.setdefault(kit_id, [])
            if trecho not in lista:
                lista.append(trecho)

    for kit_id, padroes in PALAVRAS.items():
        for padrao in padroes:
            marcar(kit_id, _achar([padrao], normal, pergunta))
    pib = _achar([_PIB], normal, pergunta)
    if pib:
        marcar("pib_municipios" if re.search(_CONTEXTO_LOCAL, normal) else "pib_trimestral", pib)
    if "pib_municipios" in motivos and re.search(r"\bper capita", normal):
        marcar("populacao", _achar([r"\bper capita"], normal, pergunta))

    # "per capita" com um indicador mundial não pede a população dos municípios.
    if "owid" in motivos and all("capita" in m.lower() for m in motivos.get("populacao", ["capita"])):
        motivos.pop("populacao", None)

    # Opções: o produto, o rebanho ou a cidade citada também escolhe o kit.
    opcoes: dict[tuple[str, str], str] = {}
    for (kit_id, chave), rotulos in OPCOES.items():
        for rotulo, padroes in rotulos.items():
            trecho = _achar(padroes, normal, pergunta)
            if not trecho:
                continue
            if kit_id in {"producao_agricola", "rebanhos"}:
                marcar(kit_id, trecho)
            if kit_id in motivos:
                opcoes[(kit_id, chave)] = rotulo
                break

    # Outros países: a comparação vai para os indicadores do Banco Mundial.
    paises = [codigo for codigo, padroes in PAISES.items() if _achar(padroes, normal, pergunta)]
    if paises:
        trecho_pais = _achar([p for c in paises for p in PAISES[c]], normal, pergunta)
        if "feriados" in motivos:
            # Feriados com outros países citados: vão para o kit mundial.
            marcar("feriados_mundo", trecho_pais)
            if not re.search(r"\bbrasil|\bbrazil", normal):
                motivos.pop("feriados")
        if not {"feriados_mundo", "owid"} & set(motivos):
            marcar("indicadores", trecho_pais)
        for kit_id in ("pib_trimestral", "ipca", "populacao"):
            # Termos gerais (PIB, inflação, população) passam a valer para os países.
            if kit_id in motivos and not re.search(r"\bipca\b|\bmunicip|\bestado|\bufs?\b", normal):
                motivos.pop(kit_id)
        if ("indicadores", "INDICADOR") not in opcoes:
            for rotulo, padroes in OPCOES[("indicadores", "INDICADOR")].items():
                if _achar(padroes, normal, pergunta):
                    opcoes[("indicadores", "INDICADOR")] = rotulo
                    break
        marcar("paises", _achar([p for c in paises for p in PAISES[c]], normal, pergunta))
    moedas = [codigo for codigo, padroes in MOEDAS.items() if _achar(padroes, normal, pergunta)]

    return {
        "kits": [k for k in PALAVRAS if k in motivos] + [k for k in motivos if k not in PALAVRAS],
        "motivos": motivos,
        "opcoes": opcoes,
        "periodo": periodo(normal, hoje),
        "paises": paises,
        "moedas": moedas,
    }


def valores(kit: dict, entendido: dict, hoje: dt.date | None = None) -> tuple[dict, list[str]]:
    """Parâmetros do kit a partir do que foi entendido. Devolve os valores e o que foi ajustado."""
    hoje = hoje or dt.date.today()
    inicio_fim = entendido.get("periodo")
    resultado, ajustes = {}, []
    for parametro in kit["parametros"]:
        chave, tipo = parametro["chave"], parametro["tipo"]
        bruto = parametro.get("padrao")
        rotulo = kits.tr_parametro(kit, parametro, "rotulo")
        if tipo == "opcoes":
            nomes = list(parametro["opcoes"])
            indice = 0
            escolhido = entendido["opcoes"].get((kit["id"], chave))
            if escolhido in nomes:
                indice = nomes.index(escolhido)
            elif inicio_fim and str(inicio_fim[1]) in nomes:  # ano específico (PIB, safra, população)
                indice = nomes.index(str(inicio_fim[1]))
            if indice:
                ajustes.append(f"{rotulo}: {nomes[indice]}")
            bruto = indice
        elif tipo == "data":
            bruto = dt.date.fromisoformat(parametro["padrao"])
            if inicio_fim:
                if chave == "DATA_INICIAL":
                    bruto = dt.date(inicio_fim[0], 1, 1)
                elif chave == "DATA_FINAL":
                    bruto = min(dt.date(inicio_fim[1], 12, 31), hoje)
                ajustes.append(f"{rotulo}: {bruto.strftime('%d/%m/%Y' if lang() == 'pt' else '%Y-%m-%d')}")
        elif tipo == "inteiro" and inicio_fim and chave in {"ANO_INICIAL", "ANO_FINAL"}:
            ano = inicio_fim[0] if chave == "ANO_INICIAL" else inicio_fim[1]
            bruto = max(parametro.get("min", ano), min(parametro.get("max", ano), ano))
            ajustes.append(f"{rotulo}: {bruto}")
        elif chave == "PAISES" and entendido.get("paises"):
            bruto = ";".join(dict.fromkeys(["BR", *entendido["paises"]]))
            ajustes.append(f"{rotulo}: {bruto}")
        elif chave == "MOEDAS" and entendido.get("moedas"):
            bruto = ",".join(dict.fromkeys(["BRL", *entendido["moedas"]]))
            ajustes.append(f"{rotulo}: {bruto}")
        resultado.update(kits.validar(parametro, bruto, rotulo, kits.tr_parametro(kit, parametro, "ajuda") or ""))
    return resultado, ajustes


def titulo_curto(pergunta: str, limite: int = 60) -> str:
    texto = " ".join(pergunta.split())
    if len(texto) <= limite:
        return texto
    frase = re.match(r"(.{10,%d}?[?.!])(\s|$)" % limite, texto)  # primeira frase, se couber
    if frase:
        return frase.group(1)
    return texto[:limite].rsplit(" ", 1)[0].rstrip(",;:") + "…"
