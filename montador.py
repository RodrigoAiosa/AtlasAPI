"""Montador de Projeto: junta vários kits em um projeto do Power BI (.pbip).

O projeto sai com uma consulta por tabela, uma tabela calendário, as
dimensões compartilhadas, os relacionamentos entre as chaves comuns e as
medidas DAX de cada kit. O modelo usa o formato model.bim (TMSL), que o
Power BI Desktop abre a partir do arquivo .pbip.
"""
from __future__ import annotations

import io
import datetime
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
    "previsao_clima": [("cidade", "string"), ("data", "date"), ("temp_max_c", "double"),
                       ("temp_min_c", "double"), ("chuva_mm", "double")],
    "livros": [("obra_id", "string"), ("titulo", "string"), ("autor", "string"),
               ("ano_publicacao", "int64"), ("edicoes", "int64"), ("data", "date")],
    "crossref": [("doi", "string"), ("titulo", "string"), ("editora", "string"),
                 ("tipo", "string"), ("citacoes", "int64"), ("data", "date")],
    "focus": [("data", "date"), ("indicador", "string"), ("ano_referencia", "int64"), ("media", "double"),
              ("mediana", "double"), ("minimo", "double"), ("maximo", "double"), ("respondentes", "int64")],
    "ipea": [("data", "date"), ("serie", "string"), ("valor", "double")],
    "cripto": [("data", "date"), ("moeda", "string"), ("abertura", "double"), ("maxima", "double"),
               ("minima", "double"), ("fechamento", "double"), ("volume", "double")],
    "feriados_mundo": [("data", "date"), ("pais_iso2", "string"), ("feriado", "string"), ("feriado_local", "string"),
                       ("abrangencia", "string"), ("tipo", "string")],
    "owid": [("pais_iso3", "string"), ("pais", "string"), ("indicador", "string"), ("ano", "int64"), ("valor", "double")],
    "indicadores": [("pais_iso3", "string"), ("pais", "string"), ("indicador_id", "string"),
                    ("indicador", "string"), ("ano", "int64"), ("valor", "double")],
    "paises": [("pais_iso3", "string"), ("pais_iso2", "string"), ("pais", "string"), ("regiao", "string"),
               ("nivel_renda", "string"), ("capital", "string"), ("latitude", "double"), ("longitude", "double")],
    "terremotos": [("id", "string"), ("data_hora", "datetime"), ("magnitude", "double"), ("local", "string"),
                   ("latitude", "double"), ("longitude", "double"), ("profundidade_km", "double"),
                   ("tsunami", "int64"), ("relevancia", "int64"), ("url", "string")],
    "worldbank": [("pais_iso3", "string"), ("pais", "string"), ("indicador", "string"), ("ano", "int64"), ("valor", "double")],
    "wikimedia": [("data", "date"), ("artigo", "string"), ("visualizacoes", "int64")],
    "qualidade_ar": [("data_hora", "datetime"), ("cidade", "string"), ("latitude", "double"), ("longitude", "double"),
                     ("pm2_5", "double"), ("pm10", "double"), ("nitrogen_dioxide", "double"), ("ozone", "double")],
}
TEXTO_IBGE = {"municipio", "uf", "uf_nome", "produto", "rebanho"}
INTEIRO_IBGE = {"municipio_id", "uf_id", "ano", "trimestre", "populacao", "pib_mil_reais", "pib_milhoes_reais", "cabecas"}
# Colunas numéricas que identificam ou localizam; somar não faz sentido.
SEM_SOMA = {"municipio_id", "uf_id", "ano", "ano_publicacao", "ano_referencia", "respondentes", "trimestre", "latitude", "longitude", "tsunami", "relevancia"}

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


TABELA_MEDIDAS = "Medidas"
_CODIGO_MEDIDAS = "let\n    Fonte = #table(type table [Coluna = text], {})\nin\n    Fonte"


def _pasta(kit: dict) -> str:
    """Pasta da medida na tabela Medidas: tema e, dentro dele, o kit (ex.: Municípios\\PIB dos municípios)."""
    tema = TEMAS[TEMA_DO_KIT.get(kit["id"], "resumo")]
    titulo = kits.tr(kit, "titulo") if lang() != "pt" else kit["titulo"]
    # A barra invertida separa pastas e subpastas no Power BI.
    return f"{tema.get(lang(), tema['en'])}\\{titulo.replace(chr(92), '/')}"


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
        if item["kit"]["id"] in {"indicadores", "owid"} and "paises" in ids:
            relacionamentos.append((item["nome"], "pais_iso3", "dPais", "pais_iso3"))
        if item["kit"]["id"] == "feriados_mundo" and "paises" in ids:
            relacionamentos.append((item["nome"], "pais_iso2", "dPais", "pais_iso2"))

    ligadas = {a for a, _, _, _ in relacionamentos} | {c for _, _, c, _ in relacionamentos}
    soltas = [i["nome"] for i in itens if i["nome"] not in ligadas]

    tabelas = [dict(i, nome=i["nome"]) for i in itens] + extras
    nomes_tabelas = {tb["nome"] for tb in tabelas}
    candidatas, vistos = [], set()
    for item in itens:
        for nome, expressao in medidas(item["dax"]):
            if nome not in vistos:
                vistos.add(nome)
                candidatas.append({"name": nome, "expression": expressao, "tabela": item["nome"],
                                   "pasta": _pasta(item["kit"])})
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
        tabelas.append(tabela)
    if plano["medidas"]:
        # Todas as medidas ficam numa tabela só, organizadas em pastas por tema e kit.
        # Com a única coluna oculta, o Power BI mostra a tabela com o ícone de calculadora, no topo da lista.
        tabela = _tabela(TABELA_MEDIDAS, [("Coluna", "string")], _CODIGO_MEDIDAS)
        tabela["columns"][0]["isHidden"] = True
        tabela["measures"] = [{"name": m["name"], "expression": m["expression"], "displayFolder": m["pasta"]}
                              for m in plano["medidas"]]
        tabelas.insert(0, tabela)
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
    "previsao_clima": {"cartoes": ["Temperatura Máxima Prevista", "Chuva Prevista (mm)"],
                       "principais": [("linha", "Temperatura máxima prevista", _DATA, "Temperatura Máxima Prevista"),
                                      ("colunas", "Chuva prevista por dia (mm)", _DATA, "Chuva Prevista (mm)")]},
    "livros": {"cartoes": ["Obras", "Edições"],
               "principais": [("linha", "Obras por ano de publicação", _DATA, "Obras"),
                              ("tabela", "Obras encontradas", [("fLivros", "titulo"), ("fLivros", "autor")], ["Edições"])]},
    "crossref": {"cartoes": ["Publicações", "Citações"],
                 "principais": [("linha", "Publicações por ano", _DATA, "Publicações"),
                                ("colunas", "Citações por ano", _DATA, "Citações")]},
    "focus": {"cartoes": ["Expectativa Mais Recente", "Respondentes"],
              "principais": [("linha", "Mediana da expectativa por ano de referência", _DATA, "Expectativa (Mediana)",
                              ("fExpectativa", "ano_referencia"))]},
    "ipea": {"cartoes": ["Último Valor da Série"],
             "principais": [("linha", "Série ao longo do tempo", _DATA, "Valor da Série")]},
    "cripto": {"cartoes": ["Último Preço", "Variação no Período %"],
               "principais": [("linha", "Preço de fechamento (R$)", _DATA, "Preço de Fechamento", ("fCripto", "moeda")),
                              ("colunas", "Volume negociado por dia", _DATA, "Volume Negociado")]},
    "feriados_mundo": {"cartoes": ["Feriados", "Feriados Nacionais"],
                       "principais": [("barras", "Feriados por país", ("fFeriadoPais", "pais_iso2"), "Feriados"),
                                      ("tabela", "Feriados no período", [("fFeriadoPais", "data"), ("fFeriadoPais", "pais_iso2"),
                                                                          ("fFeriadoPais", "feriado")], [])]},
    "owid": {"cartoes": ["Valor no Último Ano"],
             "principais": [("barras", "Países no último ano", ("fIndicadorOWID", "pais"), "Valor no Último Ano"),
                            ("linha", "Média dos países por ano", ("fIndicadorOWID", "ano"), "Valor do Indicador")]},
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


# Design por tema: cor de destaque, fundo da página e nome exibido no cabeçalho.
TEMAS = {
    "economia": {"cor_clara": "#60A5FA", "cor": "#1D4ED8", "fundo": "#F3F6FD", "pt": "Economia do Brasil", "en": "Brazilian economy"},
    "trabalho": {"cor_clara": "#A78BFA", "cor": "#7C3AED", "fundo": "#F7F4FE", "pt": "Trabalho e renda", "en": "Labor and income"},
    "municipios": {"cor_clara": "#2DD4BF", "cor": "#0F766E", "fundo": "#F1F8F7", "pt": "Municípios", "en": "Municipalities"},
    "agro": {"cor_clara": "#A3E635", "cor": "#4D7C0F", "fundo": "#F5F8EF", "pt": "Agronegócio", "en": "Agribusiness"},
    "calendario": {"cor_clara": "#FB923C", "cor": "#C2410C", "fundo": "#FDF5F0", "pt": "Calendário e clima", "en": "Calendar and weather"},
    "internacional": {"cor_clara": "#F472B6", "cor": "#BE185D", "fundo": "#FDF3F7", "pt": "Internacional", "en": "International"},
    "conhecimento": {"cor_clara": "#818CF8", "cor": "#4338CA", "fundo": "#F5F5FF", "pt": "Conhecimento e pesquisa", "en": "Knowledge and research"},
    "resumo": {"cor_clara": "#D1D5DB", "cor": "#111827", "fundo": "#F5F6F8", "pt": "Visão geral", "en": "Overview"},
}
TEMA_DO_KIT = {
    "bcb": "economia", "ipca": "economia", "inpc": "economia", "pib_trimestral": "economia",
    "comercio": "economia", "industria": "economia",
    "desemprego": "trabalho", "rendimento": "trabalho",
    "populacao": "municipios", "censo2022": "municipios", "pib_municipios": "municipios", "alfabetizacao": "municipios",
    "producao_agricola": "agro", "rebanhos": "agro",
    "feriados": "calendario", "clima": "calendario", "previsao_clima": "calendario", "feriados_mundo": "calendario",
    "focus": "economia", "ipea": "economia", "cripto": "economia", "owid": "internacional",
    "cambio": "internacional", "indicadores": "internacional", "paises": "internacional", "terremotos": "internacional",
    "livros": "conhecimento", "crossref": "conhecimento",
}
_TEXTO, _TEXTO_SUAVE, _LINHA, _BRANCO = "#111827", "#6B7280", "#E5E7EB", "#FFFFFF"
_FONTE = "Segoe UI"
CABECALHO, ALTURA_CARTAO = 64, 104


def _lit(valor) -> dict:
    """Valor literal no formato do relatório: texto entre aspas simples, número com sufixo D."""
    if isinstance(valor, bool):
        bruto = "true" if valor else "false"
    elif isinstance(valor, (int, float)):
        bruto = f"{valor}D"
    else:
        bruto = "'" + str(valor).replace("'", "''") + "'"
    return {"expr": {"Literal": {"Value": bruto}}}


def _cor(hexa: str) -> dict:
    return {"solid": {"color": _lit(hexa)}}


def _props(**propriedades) -> list[dict]:
    return [{"properties": propriedades}]


def _moldura(titulo: str | None, fundo: str = _BRANCO) -> dict:
    """Aparência comum: fundo branco, cantos arredondados, sem sombra e título discreto."""
    objetos = {
        "background": _props(show=_lit(True), color=_cor(fundo), transparency=_lit(0)),
        "border": _props(show=_lit(True), color=_cor(_LINHA), radius=_lit(12)),
        "dropShadow": _props(show=_lit(False)),
        "title": _props(show=_lit(False)),
    }
    if titulo:
        objetos["title"] = _props(show=_lit(True), text=_lit(titulo), fontColor=_cor(_TEXTO_SUAVE),
                                  fontSize=_lit(11), fontFamily=_lit(_FONTE))
    return objetos


def _estilo(tipo: str, cor: str, com_serie: bool) -> dict:
    """Formatação do conteúdo do visual, por tipo."""
    if tipo == "card":
        return {"labels": _props(color=_cor(cor), fontSize=_lit(26), fontFamily=_lit(_FONTE)),
                "categoryLabels": _props(show=_lit(False))}
    if tipo == "tableEx":
        return {"stylePreset": _props(name=_lit("Minimal")),
                "columnHeaders": _props(fontColor=_cor(cor), fontFamily=_lit(_FONTE)),
                "grid": _props(gridVertical=_lit(False), gridHorizontalColor=_cor(_LINHA))}
    eixo = dict(showAxisTitle=_lit(False), labelColor=_cor(_TEXTO_SUAVE), fontFamily=_lit(_FONTE))
    objetos = {
        "categoryAxis": _props(**eixo),
        "valueAxis": _props(gridlineColor=_cor(_LINHA), **eixo),
        "legend": _props(show=_lit(com_serie), position=_lit("Top"), labelColor=_cor(_TEXTO_SUAVE)),
    }
    if not com_serie:
        objetos["dataPoint"] = _props(defaultColor=_cor(cor))
    if tipo == "lineChart":
        objetos["lineStyles"] = _props(strokeWidth=_lit(3))
    return objetos


def _container(pagina: str, indice: int, chave: str, miolo: dict, caixa: tuple) -> dict:
    x, y, largura, altura = caixa
    posicao = {"x": x, "y": y, "z": indice * 1000, "width": largura, "height": altura, "tabOrder": indice * 1000}
    config = {"name": _id(pagina, indice, chave), "layouts": [{"id": 0, "position": posicao}], "singleVisual": miolo}
    return {"config": json.dumps(config, ensure_ascii=False), "filters": "[]",
            "x": x, "y": y, "z": posicao["z"], "width": largura, "height": altura, "tabOrder": posicao["tabOrder"]}


def _visual(pagina, indice, tipo, titulo, papeis, consulta, caixa, cor) -> dict:
    return _container(pagina, indice, titulo, {
        "visualType": tipo,
        "projections": papeis,
        "prototypeQuery": consulta,
        "drillFilterOtherVisuals": True,
        "objects": _estilo(tipo, cor, "Series" in papeis),
        "vcObjects": _moldura(titulo),
    }, caixa)


def _caixa_texto(pagina, indice, chave, paragrafos, caixa, fundo=None, raio=0) -> dict:
    borda = _props(show=_lit(True), color=_cor(fundo), radius=_lit(raio)) if fundo and raio else _props(show=_lit(False))
    moldura = {"background": _props(show=_lit(bool(fundo)), color=_cor(fundo or _BRANCO), transparency=_lit(0)),
               "border": borda, "dropShadow": _props(show=_lit(False)),
               "title": _props(show=_lit(False)), "visualHeader": _props(show=_lit(False))}
    return _container(pagina, indice, chave, {
        "visualType": "textbox", "drillFilterOtherVisuals": True,
        "objects": {"general": _props(paragraphs=paragrafos)}, "vcObjects": moldura,
    }, caixa)


def _cabecalho(pagina: str, titulo: str, tema: dict, rotulo: str | None = None) -> list[dict]:
    """Barra na cor do tema, nome do tema e título da página."""
    rotulo = (rotulo or tema.get(lang(), tema["en"])).upper()
    tamanho = "18pt" if len(titulo) <= 80 else "13pt"  # perguntas longas cabem em duas linhas
    paragrafos = [
        {"textRuns": [{"value": rotulo, "textStyle": {"fontFamily": _FONTE, "fontSize": "9pt",
                                                       "fontWeight": "bold", "color": tema["cor"]}}]},
        {"textRuns": [{"value": titulo, "textStyle": {"fontFamily": _FONTE, "fontSize": tamanho,
                                                       "fontWeight": "bold", "color": _TEXTO}}]},
    ]
    return [
        _caixa_texto(pagina, 0, "barra", [{"textRuns": [{"value": ""}]}], (MARGEM, MARGEM, 6, CABECALHO), tema["cor"]),
        _caixa_texto(pagina, 1, "titulo", paragrafos, (MARGEM + 14, MARGEM - 4, LARGURA - 2 * MARGEM - 14, CABECALHO + 8)),
    ]


def _cartao(pagina, indice, medida, tabela, caixa, cor) -> dict:
    consulta = _Consulta()
    ref = consulta.medida(tabela, medida)
    return _visual(pagina, indice, "card", medida, {"Values": [{"queryRef": ref}]}, consulta.pronta(), caixa, cor)


def _principal(pagina, indice, spec, dono, tabelas, caixa, cor) -> dict | None:
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
                       consulta.pronta(ordenar), caixa, cor)
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
    return _visual(pagina, indice, _TIPOS[tipo], titulo, papeis, consulta.pronta(ordenar), caixa, cor)


def _pagina(nome: str, titulo: str, ordem: int, visuais: list[dict], fundo: str = _BRANCO) -> dict:
    config = {"objects": {"background": _props(color=_cor(fundo), transparency=_lit(0))}}
    return {"config": json.dumps(config), "displayName": titulo[:50], "displayOption": 1, "filters": "[]",
            "ordinal": ordem, "height": float(ALTURA), "name": nome, "visualContainers": visuais,
            "width": float(LARGURA)}


def _grade(quantidade: int, y: int, altura: int, colunas: int | None = None) -> list[tuple]:
    """Caixas de mesma largura lado a lado (quebra em linhas quando `colunas` é informado)."""
    por_linha = colunas or max(quantidade, 1)
    largura = (LARGURA - MARGEM * (por_linha + 1)) // por_linha
    return [(MARGEM + (i % por_linha) * (largura + MARGEM), y + (i // por_linha) * (altura + MARGEM), largura, altura)
            for i in range(quantidade)]


def _texto(valor: str, tamanho: int, cor: str, negrito: bool = False) -> dict:
    estilo = {"fontFamily": _FONTE, "fontSize": f"{tamanho}pt", "color": cor}
    if negrito:
        estilo["fontWeight"] = "bold"
    return {"textRuns": [{"value": valor, "textStyle": estilo}]}


def _capa(plano: dict, resultado: list[tuple], total_paginas: int) -> dict:
    """Capa escura com título, números do projeto, páginas agrupadas por tema e fontes."""
    pagina = f"ReportSection{_id('pagina', 'capa')}"
    fundo, painel, claro, suave = "#111827", "#1F2937", "#F9FAFB", "#9CA3AF"
    largura = LARGURA - 2 * 60
    titulo = (plano.get("titulo") or "").strip() or t("mont_cover_default")
    numeros = t("mont_cover_stats", tables=len(plano["tabelas"]), measures=len(plano["medidas"]), pages=total_paginas)
    hoje = datetime.date.today()
    data = hoje.strftime("%d/%m/%Y") if lang() == "pt" else hoje.isoformat()
    visuais = [
        _caixa_texto(pagina, 0, "barra", [_texto("", 9, claro)], (60, 78, 6, 150), claro),
        _caixa_texto(pagina, 1, "titulo", [
            _texto("API ATLAS  ·  POWER BI", 10, suave, True),
            _texto(titulo, 40 if len(titulo) <= 30 else 26, claro, True),
            _texto(numeros, 14, "#D1D5DB"),
        ], (82, 66, largura - 22, 176)),
        _caixa_texto(pagina, 2, "conteudo", [_texto(t("mont_cover_contents").upper(), 9, suave, True)],
                     (60, 270, largura, 34)),
    ]
    grupos: dict[str, list[str]] = {}
    for _, titulo_pagina, _, _, chave in resultado:
        grupos.setdefault(chave, []).append(titulo_pagina)
    por_linha = (min(len(grupos), 3) if len(grupos) <= 6 else 4) or 1
    linhas = -(-len(grupos) // por_linha)
    vao = 20
    altura = 220 if linhas == 1 else (650 - 310 - vao * (linhas - 1)) // linhas
    largura_cartao = (largura - vao * (por_linha - 1)) // por_linha
    for i, (chave, titulos) in enumerate(grupos.items()):
        tema = TEMAS[chave]
        x = 60 + (i % por_linha) * (largura_cartao + vao)
        y = 310 + (i // por_linha) * (altura + vao)
        paragrafos = [_texto(tema.get(lang(), tema["en"]), 13, claro, True)]
        paragrafos += [_texto(nome[:44], 10, "#D1D5DB") for nome in titulos]
        visuais.append(_caixa_texto(pagina, 10 + 2 * i, f"tema-{chave}", paragrafos,
                                    (x, y, largura_cartao, altura), painel, 12))
        visuais.append(_caixa_texto(pagina, 11 + 2 * i, f"cor-{chave}", [_texto("", 9, claro)],
                                    (x + 16, y + altura - 14, 48, 5), tema["cor_clara"]))
    fontes = list(dict.fromkeys(re.sub(r", (tabela|table) \d+", "", kits.tr(tb["kit"], "fonte")) for tb in plano["tabelas"] if tb.get("kit", {}).get("fonte")))
    rodape = [_texto(t("mont_cover_sources", sources=", ".join(fontes))[:230], 9, suave),
              _texto(t("mont_cover_made", date=data), 9, suave)]
    visuais.append(_caixa_texto(pagina, 40, "rodape", rodape, (60, 660, largura, 52)))
    return _pagina(pagina, t("mont_page_cover"), 0, visuais, fundo)


def _pagina_pergunta(pergunta: str, por_kit: list[tuple], dono: dict, tabelas: set) -> dict:
    """Página com a pergunta no título, o principal cartão de cada kit e até dois gráficos."""
    tema = TEMAS["resumo"]
    pagina = f"ReportSection{_id('pagina', 'pergunta')}"
    inicio = MARGEM + CABECALHO + MARGEM
    cartoes = [(c[0], cor) for c, _, cor in por_kit if c][:4]
    graficos = [(s[0], cor) for _, s, cor in por_kit if s][:2]
    if len(graficos) == 1:  # um kit só: usa os dois visuais dele
        _, s, cor = next(k for k in por_kit if k[1])
        graficos = [(x, cor) for x in s[:2]]
    visuais = [_cartao(pagina, 2 + i, m, dono[m], caixa, cor)
               for i, ((m, cor), caixa) in enumerate(zip(cartoes, _grade(len(cartoes), inicio, ALTURA_CARTAO)))]
    topo = inicio + (ALTURA_CARTAO + MARGEM if cartoes else 0)
    for i, ((spec, cor), caixa) in enumerate(zip(graficos, _grade(len(graficos), topo, ALTURA - topo - MARGEM))):
        visuais.append(_principal(pagina, 10 + i, spec, dono, tabelas, caixa, cor))
    titulo = pergunta if len(pergunta) <= 160 else pergunta[:157] + "..."
    return _pagina(pagina, t("mont_page_question"), 1,
                   _cabecalho(pagina, titulo, tema, t("mont_page_question")) + visuais, tema["fundo"])


def paginas(plano: dict) -> list[dict]:
    """Capa, página de resumo com os principais cartões e uma página por kit, no design do seu tema."""
    dono = {m["name"]: TABELA_MEDIDAS for m in plano["medidas"]}
    tabelas = {tb["nome"] for tb in plano["tabelas"]}
    inicio = MARGEM + CABECALHO + MARGEM
    resultado, destaques, por_kit = [], [], []
    for item in plano["tabelas"]:
        kit = item.get("kit", {})
        spec = VISUAIS.get(kit.get("id"))
        if not spec:
            continue
        chave = TEMA_DO_KIT.get(kit["id"], "resumo")
        tema = TEMAS[chave]
        cor = tema["cor"]
        pagina = f"ReportSection{_id('pagina', item['nome'])}"
        titulo = kits.tr(kit, "titulo") if lang() != "pt" else kit["titulo"]
        cartoes = [m for m in spec["cartoes"] if m in dono]
        destaques += [(m, dono[m], cor) for m in cartoes[:2]]
        visuais = [_cartao(pagina, 2 + i, m, dono[m], caixa, cor)
                   for i, (m, caixa) in enumerate(zip(cartoes, _grade(len(cartoes), inicio, ALTURA_CARTAO)))]
        topo = inicio + (ALTURA_CARTAO + MARGEM if cartoes else 0)
        possiveis = [s for s in spec["principais"]
                     if _principal(pagina, 0, s, dono, tabelas, (0, 0, 1, 1), cor) is not None]
        for i, (s, caixa) in enumerate(zip(possiveis, _grade(len(possiveis), topo, ALTURA - topo - MARGEM))):
            visuais.append(_principal(pagina, 2 + len(cartoes) + i, s, dono, tabelas, caixa, cor))
        if cartoes or possiveis:
            por_kit.append((cartoes, possiveis, cor))
        if visuais:
            resultado.append((pagina, titulo, _cabecalho(pagina, titulo, tema) + visuais, tema["fundo"], chave))
    secoes = []
    if plano.get("pergunta") and por_kit:
        # A pergunta substitui o resumo: cartões e gráficos dos kits que respondem a ela.
        secoes.append(_pagina_pergunta(plano["pergunta"], por_kit, dono, tabelas))
    elif len(resultado) > 1 and destaques:
        tema = TEMAS["resumo"]
        pagina = f"ReportSection{_id('pagina', 'resumo')}"
        destaques = destaques[:12]
        caixas = _grade(len(destaques), inicio, 130, colunas=4)
        cartoes = [_cartao(pagina, 2 + i, m, tb, caixa, cor) for i, ((m, tb, cor), caixa) in enumerate(zip(destaques, caixas))]
        secoes.append(_pagina(pagina, t("mont_page_summary"), 1,
                              _cabecalho(pagina, t("mont_page_summary"), tema) + cartoes, tema["fundo"]))
    for nome, titulo, visuais, fundo, _ in resultado:
        secoes.append(_pagina(nome, titulo, len(secoes) + 1, visuais, fundo))
    if secoes:
        secoes.insert(0, _capa(plano, resultado, len(secoes) + 1))
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
    plano["titulo"] = st.text_input(t("mont_cover_title"), value=t("mont_cover_default"), max_chars=60,
                                    key=f"mont_titulo__{lang()}")
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
        f"- {secao['displayName']}" + (f" ({n} {t('mont_visuals')})" if n else "")
        for secao in secoes for n in [sum("prototypeQuery" in v["config"] for v in secao["visualContainers"])]
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
