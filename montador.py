"""Montador de Projeto: junta vários kits em um projeto do Power BI (.pbip).

O projeto sai com uma consulta por tabela, uma tabela calendário, as
dimensões compartilhadas, os relacionamentos entre as chaves comuns e as
medidas DAX de cada kit. O modelo usa o formato model.bim (TMSL), que o
Power BI Desktop abre a partir do arquivo .pbip.
"""
from __future__ import annotations

import io
import json
import re
import uuid
import zipfile

import streamlit as st

import kits
from i18n import lang, t

PROJETO = "AtlasProjeto"

# Colunas das tabelas dos kits escritos à mão. Os kits do IBGE trazem as
# colunas no próprio nome das medidas (ver `esquema`). Ficam fora do
# montador os kits cujas colunas dependem de uma API que não devolve nomes
# fixos (Municípios do Brasil e Deputados federais).
ESQUEMAS = {
    "bcb": [("data", "date"), ("valor", "double")],
    "cambio": [("data", "date"), ("moeda", "string"), ("taxa", "double")],
    "feriados": [("data", "date"), ("feriado", "string"), ("tipo", "string")],
    "populacao": [("municipio_id", "int64"), ("municipio", "string"), ("uf", "string"), ("ano", "int64"),
                  ("populacao", "int64")],
    "clima": [("cidade", "string"), ("data", "date"), ("temp_max_c", "double"), ("temp_min_c", "double"),
              ("chuva_mm", "double")],
    "indicadores": [("pais_iso3", "string"), ("pais", "string"), ("indicador_id", "string"),
                    ("indicador", "string"), ("ano", "int64"), ("valor", "double")],
    "paises": [("pais_iso3", "string"), ("pais_iso2", "string"), ("pais", "string"), ("regiao", "string"),
               ("nivel_renda", "string"), ("capital", "string"), ("latitude", "double"), ("longitude", "double")],
    "terremotos": [("id", "string"), ("data_hora", "datetime"), ("magnitude", "double"), ("local", "string"),
                   ("latitude", "double"), ("longitude", "double"), ("profundidade_km", "double"),
                   ("tsunami", "int64"), ("relevancia", "int64"), ("url", "string")],
}
TEXTO_IBGE = {"municipio", "uf", "uf_nome", "produto", "rebanho"}
INTEIRO_IBGE = {"municipio_id", "uf_id", "ano", "trimestre", "populacao", "pib_mil_reais", "pib_milhoes_reais", "cabecas"}
# Colunas numéricas que identificam ou localizam; somar não faz sentido.
SEM_SOMA = {"municipio_id", "uf_id", "ano", "trimestre", "latitude", "longitude", "tsunami", "relevancia"}

M_CALENDARIO = '''let
    Inicio = #date(1980, 1, 1),
    Fim = #date(Date.Year(DateTime.LocalNow()), 12, 31),
    Datas = List.Dates(Inicio, Duration.Days(Fim - Inicio) + 1, #duration(1, 0, 0, 0)),
    Tabela = Table.FromList(Datas, Splitter.SplitByNothing(), {"Data"}),
    ComData = Table.TransformColumnTypes(Tabela, {{"Data", type date}}),
    ComAno = Table.AddColumn(ComData, "Ano", each Date.Year([Data]), Int64.Type),
    ComMes = Table.AddColumn(ComAno, "Mes", each Date.Month([Data]), Int64.Type),
    ComNomeMes = Table.AddColumn(ComMes, "NomeMes", each Date.MonthName([Data], "pt-BR"), type text),
    ComTrimestre = Table.AddColumn(ComNomeMes, "Trimestre", each Date.QuarterOfYear([Data]), Int64.Type),
    Resultado = Table.AddColumn(ComTrimestre, "AnoMes", each Date.Year([Data]) * 100 + Date.Month([Data]), Int64.Type)
in
    Resultado'''

M_UF = '''let
    Fonte = Json.Document(Web.Contents("https://apisidra.ibge.gov.br", [
        RelativePath = "values/t/4099/n3/all/v/4099/p/last"
    ])),
    // A primeira linha da resposta traz os nomes das colunas.
    Tabela = Table.PromoteHeaders(Table.FromRecords(Fonte), [PromoteAllScalars = true]),
    Colunas = Table.SelectColumns(Tabela, {"Unidade da Federação (Código)", "Unidade da Federação"}),
    Renomeada = Table.RenameColumns(Colunas, {{"Unidade da Federação (Código)", "uf_id"}, {"Unidade da Federação", "uf_nome"}}),
    Resultado = Table.TransformColumnTypes(Renomeada, {{"uf_id", Int64.Type}, {"uf_nome", type text}})
in
    Resultado'''

CALENDARIO = {
    "nome": "dCalendario", "m": M_CALENDARIO, "dax": "",
    "esquema": [("Data", "date"), ("Ano", "int64"), ("Mes", "int64"), ("NomeMes", "string"),
                ("Trimestre", "int64"), ("AnoMes", "int64")],
}
DIM_UF = {"nome": "dUF", "m": M_UF, "dax": "", "esquema": [("uf_id", "int64"), ("uf_nome", "string")]}
DIM_MUNICIPIO = "censo2022"  # uma linha por município: serve de dimensão geográfica

# Coluna calculada que só existe quando o kit de feriados entra no projeto.
COLUNA_DIA_UTIL = {
    "name": "É Dia Útil", "type": "calculated", "dataType": "boolean",
    "expression": [
        "VAR Feriado = NOT ISEMPTY ( RELATEDTABLE ( dFeriado ) )",
        "RETURN",
        "    WEEKDAY ( dCalendario[Data], 2 ) <= 5 && NOT Feriado",
    ],
}


def montaveis() -> list[dict]:
    return [kit for kit in kits.KITS if esquema(kit)]


def esquema(kit: dict) -> list[tuple[str, str]]:
    if kit["id"] in ESQUEMAS:
        return ESQUEMAS[kit["id"]]
    if "SIDRA" not in kit["fonte"]:
        return []
    colunas = []
    for nome in kit["colunas"].split(", "):
        if nome == "data":
            tipo = "date"
        elif nome in TEXTO_IBGE:
            tipo = "string"
        elif nome in INTEIRO_IBGE:
            tipo = "int64"
        else:
            tipo = "double"
        colunas.append((nome, tipo))
    return colunas


def medidas(dax: str) -> list[tuple[str, list[str]]]:
    """Separa o texto de DAX de um kit em (nome, linhas da expressão).

    Blocos marcados como coluna calculada ficam fora: não são medidas.
    """
    resultado = []
    for bloco in re.split(r"\n\s*\n", dax.strip()):
        linhas = bloco.splitlines()
        comentarios = [linha for linha in linhas if linha.strip().startswith("--")]
        corpo = [linha for linha in linhas if not linha.strip().startswith("--")]
        if not corpo or any("coluna calculada" in c.casefold() or "calculated column" in c.casefold() for c in comentarios):
            continue
        inicio = re.match(r"^(.+?)\s*=\s*(.*)$", corpo[0])
        if not inicio:
            continue
        expressao = ([inicio.group(2)] if inicio.group(2) else []) + corpo[1:]
        resultado.append((inicio.group(1).strip(), expressao))
    return resultado


def _resolvidas(candidatas: list[dict], tabelas: set[str]) -> list[dict]:
    """Mantém só as medidas cujas tabelas e medidas citadas existem no projeto."""
    validas = list(candidatas)
    while True:
        nomes = {m["name"] for m in validas}
        restantes = []
        for medida in validas:
            texto = re.sub(r'"[^"]*"', '""', "\n".join(medida["expression"]))
            tabelas_citadas = set(re.findall(r"\b([A-Za-z_]\w*)\[", texto))
            medidas_citadas = set(re.findall(r"(?<![\w\]])\[([^\]]+)\]", texto))
            if tabelas_citadas <= tabelas and medidas_citadas <= nomes:
                restantes.append(medida)
        if len(restantes) == len(validas):
            return restantes
        validas = restantes


def _coluna(nome: str, tipo: str) -> dict:
    coluna = {"name": nome, "dataType": {"date": "dateTime", "datetime": "dateTime"}.get(tipo, tipo),
              "sourceColumn": nome}
    if tipo == "date":
        coluna["formatString"] = "Short Date"
    if tipo == "datetime":
        coluna["formatString"] = "General Date"
    if tipo not in {"int64", "double"} or nome in SEM_SOMA or nome.endswith("_id"):
        coluna["summarizeBy"] = "none"
    return coluna


def _tabela(nome: str, colunas: list[tuple[str, str]], codigo_m: str) -> dict:
    return {
        "name": nome,
        "columns": [_coluna(coluna, tipo) for coluna, tipo in colunas],
        "partitions": [{"name": nome, "mode": "import",
                        "source": {"type": "m", "expression": codigo_m.splitlines()}}],
    }


def planejar(selecao: list[tuple[dict, dict]]) -> dict:
    """Decide tabelas, relacionamentos e medidas do projeto.

    `selecao` é a lista de (kit, valores dos parâmetros). Devolve um dicionário
    com `tabelas`, `relacionamentos`, `medidas`, `avisos` e os códigos por kit.
    """
    itens = []
    ids = set()
    for kit, valores in selecao:
        if kit["id"] in ids:
            continue
        ids.add(kit["id"])
        itens.append({
            "kit": kit, "nome": kit["tabela"], "esquema": esquema(kit),
            "m": kits.preencher(kit["m"], valores), "python": kits.preencher(kit["python"], valores),
            "dax": kit["dax"],
        })

    avisos = []
    colunas_de = lambda item: {nome for nome, _ in item["esquema"]}
    # Dimensão de municípios: o Censo 2022 tem uma linha por município.
    if any("municipio_id" in colunas_de(i) for i in itens) and DIM_MUNICIPIO not in ids:
        censo = next(k for k in kits.KITS if k["id"] == DIM_MUNICIPIO)
        itens.append({"kit": censo, "nome": censo["tabela"], "esquema": esquema(censo), "m": censo["m"],
                      "python": censo["python"], "dax": censo["dax"], "automatica": True})
        ids.add(DIM_MUNICIPIO)
        avisos.append("aviso_censo")
    if {"populacao", "pib_municipios"} <= ids:
        avisos.append("aviso_anos")
    extras = []
    if any("uf_id" in colunas_de(i) for i in itens):
        extras.append(dict(DIM_UF, automatica=True))
    com_data = [i for i in itens if ("data", "date") in i["esquema"]]
    extras.append(dict(CALENDARIO, automatica=True))

    relacionamentos = []
    for item in itens:
        colunas = colunas_de(item)
        if ("data", "date") in item["esquema"]:
            relacionamentos.append((item["nome"], "data", "dCalendario", "Data"))
        if "municipio_id" in colunas and item["kit"]["id"] != DIM_MUNICIPIO:
            relacionamentos.append((item["nome"], "municipio_id", "dCenso2022", "municipio_id"))
        if "uf_id" in colunas:
            relacionamentos.append((item["nome"], "uf_id", "dUF", "uf_id"))
        if item["kit"]["id"] == "indicadores" and "paises" in ids:
            relacionamentos.append((item["nome"], "pais_iso3", "dPais", "pais_iso3"))

    ligadas = {a for a, _, _, _ in relacionamentos} | {c for _, _, c, _ in relacionamentos}
    soltas = [i["nome"] for i in itens if i["nome"] not in ligadas]

    tabelas = [dict(i, nome=i["nome"]) for i in itens] + extras
    nomes_tabelas = {tb["nome"] for tb in tabelas}
    candidatas, vistos = [], set()
    for item in itens:
        for nome, expressao in medidas(item["dax"]):
            if nome not in vistos:
                vistos.add(nome)
                candidatas.append({"name": nome, "expression": expressao, "tabela": item["nome"]})
    if "feriados" not in ids:
        candidatas = [m for m in candidatas if "É Dia Útil" not in "\n".join(m["expression"])]
    return {
        "tabelas": tabelas, "relacionamentos": relacionamentos, "soltas": soltas, "avisos": avisos,
        "medidas": _resolvidas(candidatas, nomes_tabelas), "feriados": "feriados" in ids,
        "sem_data": not com_data,
    }


def modelo(plano: dict) -> dict:
    """Modelo tabular (conteúdo do model.bim)."""
    tabelas = []
    for item in plano["tabelas"]:
        tabela = _tabela(item["nome"], item["esquema"], item["m"])
        if item["nome"] == "dCalendario":
            tabela["dataCategory"] = "Time"
            tabela["columns"][0]["isKey"] = True
            if plano["feriados"]:
                tabela["columns"].append(COLUNA_DIA_UTIL)
        proprias = [{"name": m["name"], "expression": m["expression"]}
                    for m in plano["medidas"] if m["tabela"] == item["nome"]]
        if proprias:
            tabela["measures"] = proprias
        tabelas.append(tabela)
    relacionamentos = [
        {"name": str(uuid.uuid5(uuid.NAMESPACE_URL, f"{de}.{coluna_de}>{para}.{coluna_para}")),
         "fromTable": de, "fromColumn": coluna_de, "toTable": para, "toColumn": coluna_para}
        for de, coluna_de, para, coluna_para in plano["relacionamentos"]
    ]
    return {
        "compatibilityLevel": 1567,
        "model": {
            "culture": "pt-BR",
            "dataAccessOptions": {"legacyRedirects": True, "returnErrorValuesAsNull": True},
            "defaultPowerBIDataSourceVersion": "powerBI_V3",
            "sourceQueryCulture": "pt-BR",
            "tables": tabelas,
            "relationships": relacionamentos,
            # Sem as tabelas de data automáticas: o projeto já tem a dCalendario.
            "annotations": [{"name": "__PBI_TimeIntelligenceEnabled", "value": "0"}],
        },
    }


# ---------- Relatório: uma página por kit, com visuais iniciais ----------

# Categorias usadas nos gráficos.
_DATA = ("dCalendario", "Data")
_UF_MUNICIPIOS = ("dCenso2022", "uf")
_MUNICIPIO = ("dCenso2022", "municipio")
_UF = ("dUF", "uf_nome")

# Por kit: medidas que viram cartões e até dois visuais principais.
# Gráfico: (tipo, título, categoria, medida[, série]). Tabela: ("tabela", título, colunas, medidas).
VISUAIS = {
    "ipca": {"cartoes": ["IPCA 12 Meses"],
             "principais": [("linha", "IPCA acumulado em 12 meses", _DATA, "IPCA 12 Meses")]},
    "inpc": {"cartoes": ["INPC 12 Meses"],
             "principais": [("linha", "INPC acumulado em 12 meses", _DATA, "INPC 12 Meses")]},
    "comercio": {"cartoes": ["Índice de Volume"],
                 "principais": [("linha", "Volume de vendas do varejo (2022 = 100)", _DATA, "Índice de Volume")]},
    "industria": {"cartoes": ["Índice de Produção"],
                  "principais": [("linha", "Produção industrial (2022 = 100)", _DATA, "Índice de Produção")]},
    "bcb": {"cartoes": ["Valor Mais Recente"],
            "principais": [("linha", "Indicador ao longo do tempo", _DATA, "Valor Mais Recente")]},
    "cambio": {"cartoes": ["Taxa no Fim do Período", "Taxa Média"],
               "principais": [("linha", "Cotação por moeda", _DATA, "Taxa Média", ("fCambio", "moeda"))]},
    "clima": {"cartoes": ["Chuva Total (mm)", "Dias com Chuva"],
              "principais": [("colunas", "Chuva por dia (mm)", _DATA, "Chuva Total (mm)")]},
    "feriados": {"cartoes": ["Dias Úteis"],
                 "principais": [("tabela", "Feriados nacionais",
                                 [("dFeriado", "data"), ("dFeriado", "feriado"), ("dFeriado", "tipo")], [])]},
    "populacao": {"cartoes": ["População"],
                  "principais": [("barras", "População por UF", _UF_MUNICIPIOS, "População"),
                                 ("tabela", "Maiores municípios", [_MUNICIPIO, _UF_MUNICIPIOS], ["População"])]},
    "pib_municipios": {"cartoes": ["PIB (R$)", "PIB per Capita"],
                       "principais": [("barras", "PIB por UF", _UF_MUNICIPIOS, "PIB (R$)"),
                                      ("tabela", "Maiores economias municipais", [_MUNICIPIO, _UF_MUNICIPIOS], ["PIB (R$)"])]},
    "alfabetizacao": {"cartoes": ["Taxa de Alfabetização Média", "Municípios Abaixo de 90%"],
                      "principais": [("barras", "Taxa de alfabetização média por UF", _UF_MUNICIPIOS, "Taxa de Alfabetização Média"),
                                     ("tabela", "Taxa por município", [_MUNICIPIO, _UF_MUNICIPIOS], ["Taxa de Alfabetização Média"])]},
    "censo2022": {"cartoes": ["População 2022", "Densidade Média"],
                  "principais": [("barras", "População em 2022 por UF", _UF_MUNICIPIOS, "População 2022"),
                                 ("tabela", "Municípios no Censo 2022", [_MUNICIPIO, _UF_MUNICIPIOS], ["População 2022", "Densidade Média"])]},
    "desemprego": {"cartoes": ["Taxa no Último Trimestre"],
                   "principais": [("barras", "Taxa de desemprego no último trimestre por UF", _UF, "Taxa no Último Trimestre"),
                                  ("linha", "Taxa média de desemprego por ano", ("fDesemprego", "ano"), "Taxa de Desemprego")]},
    "producao_agricola": {"cartoes": ["Quantidade (t)", "Preço Médio por Tonelada (R$)"],
                          "principais": [("barras", "Quantidade produzida por UF (t)", _UF, "Quantidade (t)"),
                                         ("tabela", "Produção por UF", [_UF], ["Quantidade (t)", "Preço Médio por Tonelada (R$)"])]},
    "rebanhos": {"cartoes": ["Cabeças"],
                 "principais": [("barras", "Rebanho por UF (cabeças)", _UF, "Cabeças"),
                                ("tabela", "Participação de cada UF", [_UF], ["Cabeças", "Participação da UF"])]},
    "rendimento": {"cartoes": ["Rendimento Médio"],
                   "principais": [("linha", "Rendimento médio real por ano (R$)", ("fRendimento", "ano"), "Rendimento Médio")]},
    "pib_trimestral": {"cartoes": ["PIB (R$ milhões)"],
                       "principais": [("colunas", "PIB por ano (R$ milhões)", ("fPIBTrimestral", "ano"), "PIB (R$ milhões)")]},
    "indicadores": {"cartoes": [],
                    "principais": [("linha", "Indicador por país", ("fIndicadorPais", "ano"), "Valor", ("fIndicadorPais", "pais"))]},
    "paises": {"cartoes": ["Países", "Países de Renda Alta"],
               "principais": [("barras", "Países por região", ("dPais", "regiao"), "Países")]},
    "terremotos": {"cartoes": ["Terremotos", "Maior Magnitude"],
                   "principais": [("tabela", "Maiores terremotos", [("fTerremoto", "local"), ("fTerremoto", "data_hora")], ["Maior Magnitude"])]},
}
_TIPOS = {"linha": "lineChart", "barras": "clusteredBarChart", "colunas": "clusteredColumnChart"}
LARGURA, ALTURA, MARGEM = 1280, 720, 20


def _id(*partes) -> str:
    return uuid.uuid5(uuid.NAMESPACE_URL, "/".join(str(p) for p in partes)).hex[:20]


class _Consulta:
    """Monta o prototypeQuery de um visual: tabelas usadas e campos selecionados."""

    def __init__(self) -> None:
        self.apelidos: dict[str, str] = {}
        self.campos: list[dict] = []

    def _fonte(self, tabela: str) -> dict:
        apelido = self.apelidos.setdefault(tabela, f"t{len(self.apelidos)}")
        return {"SourceRef": {"Source": apelido}}

    def coluna(self, tabela: str, coluna: str) -> str:
        nome = f"{tabela}.{coluna}"
        self.campos.append({"Column": {"Expression": self._fonte(tabela), "Property": coluna},
                            "Name": nome, "NativeReferenceName": coluna})
        return nome

    def medida(self, tabela: str, medida: str) -> str:
        nome = f"{tabela}.{medida}"
        self.campos.append({"Measure": {"Expression": self._fonte(tabela), "Property": medida},
                            "Name": nome, "NativeReferenceName": medida})
        return nome

    def pronta(self, ordenar_por: str | None = None) -> dict:
        consulta = {
            "Version": 2,
            "From": [{"Name": apelido, "Entity": tabela, "Type": 0} for tabela, apelido in self.apelidos.items()],
            "Select": self.campos,
        }
        if ordenar_por:
            campo = next(c for c in self.campos if c["Name"] == ordenar_por)
            expressao = {k: v for k, v in campo.items() if k in {"Column", "Measure"}}
            consulta["OrderBy"] = [{"Direction": 2, "Expression": expressao}]  # 2 = decrescente
        return consulta


def _visual(pagina: str, indice: int, tipo: str, titulo: str, papeis: dict, consulta: dict, caixa: tuple) -> dict:
    x, y, largura, altura = caixa
    posicao = {"x": x, "y": y, "z": indice * 1000, "width": largura, "height": altura, "tabOrder": indice * 1000}
    literal = "'" + titulo.replace("'", "''") + "'"
    config = {
        "name": _id(pagina, indice, titulo),
        "layouts": [{"id": 0, "position": posicao}],
        "singleVisual": {
            "visualType": tipo,
            "projections": papeis,
            "prototypeQuery": consulta,
            "drillFilterOtherVisuals": True,
            "vcObjects": {"title": [{"properties": {
                "show": {"expr": {"Literal": {"Value": "true"}}},
                "text": {"expr": {"Literal": {"Value": literal}}},
            }}]},
        },
    }
    return {"config": json.dumps(config, ensure_ascii=False), "filters": "[]",
            "x": x, "y": y, "z": posicao["z"], "width": largura, "height": altura, "tabOrder": posicao["tabOrder"]}


def _cartao(pagina, indice, medida, tabela, caixa) -> dict:
    consulta = _Consulta()
    ref = consulta.medida(tabela, medida)
    return _visual(pagina, indice, "card", medida, {"Values": [{"queryRef": ref}]}, consulta.pronta(), caixa)


def _principal(pagina, indice, spec, dono, tabelas, caixa) -> dict | None:
    """Gráfico ou tabela. Devolve None se alguma tabela ou medida não estiver no projeto."""
    tipo, titulo = spec[0], spec[1]
    consulta = _Consulta()
    if tipo == "tabela":
        colunas, nomes_medidas = spec[2], spec[3]
        if any(tb not in tabelas for tb, _ in colunas) or any(m not in dono for m in nomes_medidas):
            return None
        refs = [consulta.coluna(tb, col) for tb, col in colunas]
        refs_medidas = [consulta.medida(dono[m], m) for m in nomes_medidas]
        ordenar = refs_medidas[0] if refs_medidas else None
        return _visual(pagina, indice, "tableEx", titulo, {"Values": [{"queryRef": r} for r in refs + refs_medidas]},
                       consulta.pronta(ordenar), caixa)
    categoria, medida = spec[2], spec[3]
    serie = spec[4] if len(spec) > 4 else None
    if categoria[0] not in tabelas or medida not in dono or (serie and serie[0] not in tabelas):
        return None
    papeis = {"Category": [{"queryRef": consulta.coluna(*categoria), "active": True}]}
    if serie:
        papeis["Series"] = [{"queryRef": consulta.coluna(*serie)}]
    ref = consulta.medida(dono[medida], medida)
    papeis["Y"] = [{"queryRef": ref}]
    ordenar = ref if tipo == "barras" else None
    return _visual(pagina, indice, _TIPOS[tipo], titulo, papeis, consulta.pronta(ordenar), caixa)


def _pagina(nome: str, titulo: str, ordem: int, visuais: list[dict]) -> dict:
    return {"config": "{}", "displayName": titulo[:50], "displayOption": 1, "filters": "[]", "ordinal": ordem,
            "height": float(ALTURA), "name": nome, "visualContainers": visuais, "width": float(LARGURA)}


def _grade(quantidade: int, y: int, altura: int, colunas: int | None = None) -> list[tuple]:
    """Caixas de mesma largura lado a lado (quebra em linhas quando `colunas` é informado)."""
    por_linha = colunas or max(quantidade, 1)
    largura = (LARGURA - MARGEM * (por_linha + 1)) // por_linha
    return [(MARGEM + (i % por_linha) * (largura + MARGEM), y + (i // por_linha) * (altura + MARGEM), largura, altura)
            for i in range(quantidade)]


def paginas(plano: dict) -> list[dict]:
    """Página de resumo com os principais cartões e uma página por kit."""
    dono = {m["name"]: m["tabela"] for m in plano["medidas"]}
    tabelas = {tb["nome"] for tb in plano["tabelas"]}
    resultado, destaques = [], []
    for item in plano["tabelas"]:
        spec = VISUAIS.get(item.get("kit", {}).get("id"))
        if not spec:
            continue
        pagina = f"ReportSection{_id('pagina', item['nome'])}"
        cartoes = [m for m in spec["cartoes"] if m in dono]
        destaques += [(m, dono[m]) for m in cartoes[:2]]
        visuais = [_cartao(pagina, i, m, dono[m], caixa)
                   for i, (m, caixa) in enumerate(zip(cartoes, _grade(len(cartoes), MARGEM, 120)))]
        topo = MARGEM + (140 if cartoes else 0)
        possiveis = [s for s in spec["principais"]
                     if _principal(pagina, 0, s, dono, tabelas, (0, 0, 1, 1)) is not None]
        for i, (s, caixa) in enumerate(zip(possiveis, _grade(len(possiveis), topo, ALTURA - topo - MARGEM))):
            visuais.append(_principal(pagina, len(cartoes) + i, s, dono, tabelas, caixa))
        if visuais:
            resultado.append((pagina, kits.tr(item["kit"], "titulo") if lang() != "pt" else item["kit"]["titulo"], visuais))
    secoes = []
    if len(resultado) > 1 and destaques:
        pagina = f"ReportSection{_id('pagina', 'resumo')}"
        destaques = destaques[:12]
        caixas = _grade(len(destaques), MARGEM, 150, colunas=4)
        secoes.append(_pagina(pagina, t("mont_page_summary"), 0,
                              [_cartao(pagina, i, m, tb, caixa) for i, ((m, tb), caixa) in enumerate(zip(destaques, caixas))]))
    for nome, titulo, visuais in resultado:
        secoes.append(_pagina(nome, titulo, len(secoes), visuais))
    if not secoes:
        secoes.append(_pagina("ReportSection", t("mont_page_blank"), 0, []))
    return secoes


def _relatorio(plano: dict) -> dict:
    return {"config": json.dumps({"version": "5.37", "themeCollection": {}, "activeSectionIndex": 0}),
            "layoutOptimization": 0, "sections": paginas(plano)}


def arquivos(plano: dict, leiame: str) -> dict[str, str]:
    """Arquivos do projeto: caminho dentro do .zip -> conteúdo."""
    j = lambda dados: json.dumps(dados, ensure_ascii=False, indent=2)
    saida = {
        f"{PROJETO}.pbip": j({"version": "1.0", "artifacts": [{"report": {"path": f"{PROJETO}.Report"}}],
                              "settings": {"enableAutoRecovery": True}}),
        f"{PROJETO}.SemanticModel/definition.pbism": j({"version": "1.0", "settings": {}}),
        f"{PROJETO}.SemanticModel/model.bim": j(modelo(plano)),
        f"{PROJETO}.Report/definition.pbir": j({"version": "1.0", "datasetReference": {
            "byPath": {"path": f"../{PROJETO}.SemanticModel"}}}),
        f"{PROJETO}.Report/report.json": j(_relatorio(plano)),
        "LEIAME.txt": leiame,
    }
    for item in plano["tabelas"]:
        saida[f"consultas_power_query/{item['nome']}.pq"] = item["m"]
        if item.get("python"):
            saida[f"scripts_python/{item['nome']}.py"] = item["python"] + "\n"
    if plano["medidas"]:
        saida["medidas.dax"] = "\n\n".join(
            f"-- {m['tabela']}\n{m['name']} =\n" + "\n".join(m["expression"]) if len(m["expression"]) > 1
            else f"-- {m['tabela']}\n{m['name']} = {m['expression'][0]}" for m in plano["medidas"]
        ) + "\n"
    return saida


def compactar(conteudo: dict[str, str]) -> bytes:
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w", zipfile.ZIP_DEFLATED) as pacote:
        for caminho, texto in conteudo.items():
            pacote.writestr(caminho, texto.encode("utf-8"))
    return memoria.getvalue()


def _leiame(plano: dict) -> str:
    linhas = [t("mont_readme_title"), "", t("mont_readme_open"), "", t("mont_readme_tables")]
    linhas += [f"  - {item['nome']}" for item in plano["tabelas"]]
    linhas += ["", t("mont_readme_rels")]
    linhas += [f"  - {a}[{b}] -> {c}[{d}]" for a, b, c, d in plano["relacionamentos"]] or ["  -"]
    linhas += ["", t("mont_readme_extra"), "", t("mont_readme_source")]
    return "\n".join(linhas) + "\n"


def render() -> None:
    st.markdown(
        f'<div class="section-heading"><h2>{t("mont_title")}</h2><span>{t("mont_sub")}</span></div>'
        f'<p class="kit-intro">{t("mont_intro")}</p>',
        unsafe_allow_html=True,
    )
    disponiveis = montaveis()
    por_id = {kit["id"]: kit for kit in disponiveis}
    padrao = [i for i in ("populacao", "pib_municipios", "ipca") if i in por_id]
    escolhidos = st.multiselect(
        t("mont_select"), list(por_id), default=padrao,
        format_func=lambda i: f"{por_id[i]['icone']}  {kits.tr(por_id[i], 'titulo')}", key=f"mont_kits__{lang()}",
    )
    if not escolhidos:
        st.info(t("mont_empty"))
        return

    selecao = []
    for kit in (por_id[i] for i in escolhidos):
        valores, brutos = {}, {}
        if kit["parametros"]:
            with st.expander(f"{kit['icone']}  {kits.tr(kit, 'titulo')}"):
                colunas = st.columns(len(kit["parametros"]))
                for coluna, parametro in zip(colunas, kit["parametros"]):
                    with coluna:
                        brutos[parametro["chave"]] = kits._campo(kit, parametro, "mont")
        try:
            for parametro in kit["parametros"]:
                valores.update(kits.validar(
                    parametro, brutos[parametro["chave"]],
                    kits.tr_parametro(kit, parametro, "rotulo"), kits.tr_parametro(kit, parametro, "ajuda") or "",
                ))
            kits.checar_intervalos(brutos)
        except ValueError as erro:
            st.warning(f"{kits.tr(kit, 'titulo')}: {erro}")
            return
        selecao.append((kit, valores))

    plano = planejar(selecao)
    esquerda, direita = st.columns(2)
    with esquerda:
        st.markdown(f"**{t('mont_tables')}**")
        linhas = []
        for item in plano["tabelas"]:
            nota = f" · {t('mont_auto')}" if item.get("automatica") else ""
            linhas.append(f"- `{item['nome']}` ({len(item['esquema'])} {t('mont_columns')}){nota}")
        st.markdown("\n".join(linhas))
    with direita:
        st.markdown(f"**{t('mont_rels')}**")
        if plano["relacionamentos"]:
            st.markdown("\n".join(f"- `{a}[{b}]` → `{c}[{d}]`" for a, b, c, d in plano["relacionamentos"]))
        else:
            st.caption(t("mont_no_rels"))
        st.markdown(f"**{t('mont_measures')}**")
        if plano["medidas"]:
            st.markdown("\n".join(f"- {m['name']}" for m in plano["medidas"]))
        else:
            st.caption(t("mont_no_measures"))
    secoes = paginas(plano)
    st.markdown(f"**{t('mont_pages')}**")
    st.markdown("\n".join(
        f"- {secao['displayName']} ({len(secao['visualContainers'])} {t('mont_visuals')})" for secao in secoes
    ))
    for aviso in plano["avisos"]:
        st.caption(t(f"mont_{aviso}"))
    if plano["soltas"]:
        st.caption(t("mont_loose", tables=", ".join(plano["soltas"])))

    pacote = compactar(arquivos(plano, _leiame(plano)))
    st.download_button(t("mont_download"), pacote, file_name=f"{PROJETO}.zip", mime="application/zip",
                       key="mont_download", type="primary")
    st.caption(t("mont_how"))
    st.markdown(f'<div class="kit-bridge"><strong>{t("bridge_title")}</strong><p>{t("mont_bridge")}</p></div>',
                unsafe_allow_html=True)
    st.link_button(t("open_bdg"), kits.BI_DATA_GENERATOR_URL)
