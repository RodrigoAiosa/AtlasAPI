"""Kits de projeto para Power BI e gerador de script Python.

Cada kit descreve uma API pública sem autenticação e traz dois modelos de
código, um em Power Query (M) e um em Python, com marcadores «ASSIM» que
são trocados pelos parâmetros escolhidos na tela.
"""
from __future__ import annotations

import datetime as dt
import re
from urllib.parse import parse_qsl, urlsplit

import pandas as pd
import streamlit as st

import kits_i18n
from i18n import keyed, lang, number, t

BI_DATA_GENERATOR_URL = "https://ai-bidatagenerator.streamlit.app/"

CAPITAIS = {
    "São Paulo": {"CIDADE": "São Paulo", "LATITUDE": "-23.55", "LONGITUDE": "-46.63"},
    "Rio de Janeiro": {"CIDADE": "Rio de Janeiro", "LATITUDE": "-22.91", "LONGITUDE": "-43.17"},
    "Brasília": {"CIDADE": "Brasília", "LATITUDE": "-15.78", "LONGITUDE": "-47.93"},
    "Belo Horizonte": {"CIDADE": "Belo Horizonte", "LATITUDE": "-19.92", "LONGITUDE": "-43.94"},
    "Salvador": {"CIDADE": "Salvador", "LATITUDE": "-12.97", "LONGITUDE": "-38.50"},
    "Fortaleza": {"CIDADE": "Fortaleza", "LATITUDE": "-3.73", "LONGITUDE": "-38.52"},
    "Recife": {"CIDADE": "Recife", "LATITUDE": "-8.05", "LONGITUDE": "-34.88"},
    "Manaus": {"CIDADE": "Manaus", "LATITUDE": "-3.10", "LONGITUDE": "-60.02"},
    "Curitiba": {"CIDADE": "Curitiba", "LATITUDE": "-25.43", "LONGITUDE": "-49.27"},
    "Porto Alegre": {"CIDADE": "Porto Alegre", "LATITUDE": "-30.03", "LONGITUDE": "-51.23"},
}

KITS = [
    {
        "id": "bcb",
        "icone": "🏦",
        "titulo": "Selic, IPCA e dólar",
        "fonte": "Banco Central do Brasil (SGS)",
        "docs": "https://dadosabertos.bcb.gov.br/dataset/432-taxa-de-juros---selic---fixada-pelo-copom",
        "resumo": "Séries históricas oficiais de juros, inflação e câmbio, uma linha por data.",
        "papel": "Fato",
        "tabela": "fIndicador",
        "colunas": "data, valor",
        "parametros": [
            {"chave": "SERIE", "rotulo": "Série", "tipo": "opcoes", "opcoes": {
                "Selic meta (% a.a.)": "432", "IPCA mensal (%)": "433", "Dólar comercial, venda (R$)": "1"}},
            {"chave": "DATA_INICIAL", "rotulo": "Data inicial", "tipo": "data", "padrao": "2020-01-01", "formato": "%d/%m/%Y"},
            {"chave": "DATA_FINAL", "rotulo": "Data final", "tipo": "data", "padrao": "2025-12-31", "formato": "%d/%m/%Y"},
        ],
        "observacao": "Séries diárias, como o dólar, aceitam no máximo 10 anos por consulta.",
        "ponte": "Gere uma base de vendas no BI Data Generator e relacione esta tabela à dCalendario pela data. "
                 "Com o IPCA você deflaciona o faturamento; com a Selic, compara o resultado com o custo do dinheiro.",
        "visuais": ["Linha do indicador ao longo do tempo", "Cartão com o valor mais recente",
                    "Faturamento nominal x faturamento corrigido pelo IPCA"],
        "dax": '''Valor Mais Recente =
VAR UltimaData = MAX ( fIndicador[data] )
RETURN
    CALCULATE ( MAX ( fIndicador[valor] ), fIndicador[data] = UltimaData )

-- Use com a série do IPCA mensal
IPCA Acumulado =
PRODUCTX ( fIndicador, 1 + fIndicador[valor] / 100 ) - 1''',
        "m": '''let
    Serie = "«SERIE»",
    DataInicial = "«DATA_INICIAL»",
    DataFinal = "«DATA_FINAL»",
    Fonte = Json.Document(Web.Contents("https://api.bcb.gov.br", [
        RelativePath = "dados/serie/bcdata.sgs." & Serie & "/dados",
        Query = [formato = "json", dataInicial = DataInicial, dataFinal = DataFinal]
    ])),
    Tabela = Table.FromRecords(Fonte),
    ComData = Table.TransformColumnTypes(Tabela, {{"data", type date}}, "pt-BR"),
    Resultado = Table.TransformColumnTypes(ComData, {{"valor", type number}}, "en-US")
in
    Resultado''',
        "python": '''import pandas as pd
import requests

SERIE = «SERIE»  # 432 = Selic meta, 433 = IPCA mensal, 1 = dólar (venda)
DATA_INICIAL = "«DATA_INICIAL»"
DATA_FINAL = "«DATA_FINAL»"

resposta = requests.get(
    f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{SERIE}/dados",
    params={"formato": "json", "dataInicial": DATA_INICIAL, "dataFinal": DATA_FINAL},
    timeout=30,
)
resposta.raise_for_status()

df = pd.DataFrame(resposta.json())
df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y")
df["valor"] = pd.to_numeric(df["valor"])''',
    },
    {
        "id": "cambio",
        "icone": "💱",
        "titulo": "Câmbio diário",
        "fonte": "Frankfurter (taxas do Banco Central Europeu)",
        "docs": "https://frankfurter.dev/",
        "resumo": "Cotação diária de várias moedas em relação a uma moeda base, em formato longo.",
        "papel": "Fato",
        "tabela": "fCambio",
        "colunas": "data, moeda, taxa",
        "parametros": [
            {"chave": "BASE", "rotulo": "Moeda base", "tipo": "texto", "padrao": "USD", "padrao_re": r"[A-Z]{3}",
             "ajuda": "Código de 3 letras, como USD ou EUR."},
            {"chave": "MOEDAS", "rotulo": "Moedas cotadas", "tipo": "texto", "padrao": "BRL,EUR",
             "padrao_re": r"[A-Z]{3}(,[A-Z]{3})*", "ajuda": "Códigos de 3 letras separados por vírgula."},
            {"chave": "DATA_INICIAL", "rotulo": "Data inicial", "tipo": "data", "padrao": "2025-01-01", "formato": "%Y-%m-%d"},
            {"chave": "DATA_FINAL", "rotulo": "Data final", "tipo": "data", "padrao": "2025-12-31", "formato": "%Y-%m-%d"},
        ],
        "observacao": "Só há cotação em dias úteis.",
        "ponte": "Gere uma base de vendas em reais no BI Data Generator e use esta tabela para converter o "
                 "faturamento para dólar ou euro pela data da venda.",
        "visuais": ["Linha da cotação por moeda", "Faturamento em R$ x faturamento em US$",
                    "Variação percentual da moeda no período"],
        "dax": '''Taxa Média = AVERAGE ( fCambio[taxa] )

Taxa no Fim do Período =
VAR UltimaData = MAX ( fCambio[data] )
RETURN
    CALCULATE ( AVERAGE ( fCambio[taxa] ), fCambio[data] = UltimaData )''',
        "m": '''let
    Base = "«BASE»",
    Moedas = "«MOEDAS»",
    DataInicial = "«DATA_INICIAL»",
    DataFinal = "«DATA_FINAL»",
    Fonte = Json.Document(Web.Contents("https://api.frankfurter.dev", [
        RelativePath = "v1/" & DataInicial & ".." & DataFinal,
        Query = [base = Base, symbols = Moedas]
    ])),
    PorData = Record.ToTable(Fonte[rates]),
    Expandida = Table.ExpandRecordColumn(PorData, "Value", Text.Split(Moedas, ",")),
    Longa = Table.UnpivotOtherColumns(Expandida, {"Name"}, "moeda", "taxa"),
    Renomeada = Table.RenameColumns(Longa, {{"Name", "data"}}),
    Resultado = Table.TransformColumnTypes(Renomeada, {{"data", type date}, {"moeda", type text}, {"taxa", type number}}, "en-US")
in
    Resultado''',
        "python": '''import pandas as pd
import requests

BASE = "«BASE»"
MOEDAS = "«MOEDAS»"
DATA_INICIAL = "«DATA_INICIAL»"
DATA_FINAL = "«DATA_FINAL»"

resposta = requests.get(
    f"https://api.frankfurter.dev/v1/{DATA_INICIAL}..{DATA_FINAL}",
    params={"base": BASE, "symbols": MOEDAS},
    timeout=30,
)
resposta.raise_for_status()

df = (
    pd.DataFrame.from_dict(resposta.json()["rates"], orient="index")
    .rename_axis("data")
    .reset_index()
    .melt(id_vars="data", var_name="moeda", value_name="taxa")
    .dropna(subset=["taxa"])
)
df["data"] = pd.to_datetime(df["data"])
df = df.sort_values(["data", "moeda"]).reset_index(drop=True)''',
    },
    {
        "id": "feriados",
        "icone": "📅",
        "titulo": "Feriados nacionais",
        "fonte": "BrasilAPI",
        "docs": "https://brasilapi.com.br/docs#tag/Feriados-Nacionais",
        "resumo": "Lista de feriados nacionais de cada ano, para enriquecer a tabela calendário.",
        "papel": "Dimensão",
        "tabela": "dFeriado",
        "colunas": "data, feriado, tipo",
        "parametros": [
            {"chave": "ANO_INICIAL", "rotulo": "Ano inicial", "tipo": "inteiro", "padrao": 2024, "min": 1900, "max": 2199},
            {"chave": "ANO_FINAL", "rotulo": "Ano final", "tipo": "inteiro", "padrao": 2026, "min": 1900, "max": 2199},
        ],
        "observacao": "Traz só feriados nacionais; estaduais e municipais ficam de fora.",
        "ponte": "O BI Data Generator já entrega a dCalendario. Relacione esta tabela a ela pela data e crie a "
                 "coluna de dia útil, para medir vendas por dia útil e comparar meses de forma justa.",
        "visuais": ["Vendas em feriado x dia comum", "Média de vendas por dia útil no mês",
                    "Calendário com os feriados marcados"],
        "dax": '''-- Coluna calculada na dCalendario
É Dia Útil =
VAR Feriado = NOT ISEMPTY ( RELATEDTABLE ( dFeriado ) )
RETURN
    WEEKDAY ( dCalendario[Data], 2 ) <= 5 && NOT Feriado

Dias Úteis =
CALCULATE ( COUNTROWS ( dCalendario ), dCalendario[É Dia Útil] = TRUE () )''',
        "m": '''let
    AnoInicial = «ANO_INICIAL»,
    AnoFinal = «ANO_FINAL»,
    PorAno = List.Transform({AnoInicial..AnoFinal}, each Json.Document(Web.Contents("https://brasilapi.com.br", [
        RelativePath = "api/feriados/v1/" & Text.From(_)
    ]))),
    Tabela = Table.FromRecords(List.Combine(PorAno), null, MissingField.UseNull),
    Renomeada = Table.RenameColumns(Tabela, {{"date", "data"}, {"name", "feriado"}, {"type", "tipo"}}, MissingField.Ignore),
    Resultado = Table.TransformColumnTypes(Renomeada, {{"data", type date}})
in
    Resultado''',
        "python": '''import pandas as pd
import requests

ANO_INICIAL = «ANO_INICIAL»
ANO_FINAL = «ANO_FINAL»

registros = []
for ano in range(ANO_INICIAL, ANO_FINAL + 1):
    resposta = requests.get(f"https://brasilapi.com.br/api/feriados/v1/{ano}", timeout=30)
    resposta.raise_for_status()
    registros.extend(resposta.json())

df = pd.DataFrame(registros).rename(columns={"date": "data", "name": "feriado", "type": "tipo"})
df["data"] = pd.to_datetime(df["data"])''',
    },
    {
        "id": "municipios",
        "icone": "🗺️",
        "titulo": "Municípios do Brasil",
        "fonte": "IBGE (API de localidades)",
        "docs": "https://servicodados.ibge.gov.br/api/docs/localidades",
        "resumo": "Todos os municípios com código IBGE, UF e região, prontos para virar dimensão geográfica.",
        "papel": "Dimensão",
        "tabela": "dMunicipio",
        "colunas": "código e nome do município, microrregião, mesorregião, UF e região",
        "parametros": [],
        "observacao": "São cerca de 5.570 linhas. O código IBGE do município é a melhor chave de relacionamento.",
        "ponte": "Use como dimensão de geografia no lugar de uma lista de cidades digitada à mão. Se a base gerada "
                 "no BI Data Generator tiver cidade ou UF, relacione por esse campo e ganhe a hierarquia "
                 "região > UF > município.",
        "visuais": ["Mapa por UF ou município", "Matriz com hierarquia região > UF > município",
                    "Ranking de municípios por faturamento"],
        "dax": '''Municípios = COUNTROWS ( dMunicipio )

-- Supondo uma medida [Faturamento] no seu modelo
Faturamento por Município =
DIVIDE ( [Faturamento], [Municípios] )''',
        "m": '''let
    Fonte = Json.Document(Web.Contents("https://servicodados.ibge.gov.br", [
        RelativePath = "api/v1/localidades/municipios",
        Query = [view = "nivelado"]
    ])),
    Resultado = Table.FromRecords(Fonte, null, MissingField.UseNull)
in
    Resultado''',
        "python": '''import pandas as pd
import requests

resposta = requests.get(
    "https://servicodados.ibge.gov.br/api/v1/localidades/municipios",
    params={"view": "nivelado"},
    timeout=60,
)
resposta.raise_for_status()

df = pd.DataFrame(resposta.json())''',
    },
    {
        "id": "clima",
        "icone": "🌦️",
        "titulo": "Clima histórico",
        "fonte": "Open-Meteo",
        "docs": "https://open-meteo.com/en/docs/historical-weather-api",
        "resumo": "Temperatura máxima, mínima e chuva por dia em uma capital brasileira.",
        "papel": "Fato",
        "tabela": "fClima",
        "colunas": "cidade, data, temp_max_c, temp_min_c, chuva_mm",
        "parametros": [
            {"chave": "CIDADE", "rotulo": "Cidade", "tipo": "opcoes", "opcoes": CAPITAIS},
            {"chave": "DATA_INICIAL", "rotulo": "Data inicial", "tipo": "data", "padrao": "2025-01-01", "formato": "%Y-%m-%d"},
            {"chave": "DATA_FINAL", "rotulo": "Data final", "tipo": "data", "padrao": "2025-12-31", "formato": "%Y-%m-%d"},
        ],
        "observacao": "O histórico tem alguns dias de atraso; evite datas da última semana. "
                      "Para outra cidade, troque a latitude e a longitude no código.",
        "ponte": "Gere uma base de vendas no BI Data Generator e cruze com o clima pela data: dá para investigar "
                 "se dias de chuva ou de calor mudam o volume vendido. Combina bem com a ferramenta Dados Causais.",
        "visuais": ["Vendas x chuva em gráfico de dispersão", "Temperatura média por mês",
                    "Vendas em dias com chuva x dias sem chuva"],
        "dax": '''Chuva Total (mm) = SUM ( fClima[chuva_mm] )

Dias com Chuva =
CALCULATE ( COUNTROWS ( fClima ), fClima[chuva_mm] > 0 )''',
        "m": '''let
    Cidade = "«CIDADE»",
    Latitude = "«LATITUDE»",
    Longitude = "«LONGITUDE»",
    DataInicial = "«DATA_INICIAL»",
    DataFinal = "«DATA_FINAL»",
    Fonte = Json.Document(Web.Contents("https://archive-api.open-meteo.com", [
        RelativePath = "v1/archive",
        Query = [
            latitude = Latitude,
            longitude = Longitude,
            start_date = DataInicial,
            end_date = DataFinal,
            daily = "temperature_2m_max,temperature_2m_min,precipitation_sum",
            timezone = "America/Sao_Paulo"
        ]
    ])),
    Diario = Fonte[daily],
    Tabela = Table.FromColumns(Record.FieldValues(Diario), Record.FieldNames(Diario)),
    Renomeada = Table.RenameColumns(Tabela, {
        {"time", "data"},
        {"temperature_2m_max", "temp_max_c"},
        {"temperature_2m_min", "temp_min_c"},
        {"precipitation_sum", "chuva_mm"}
    }),
    ComCidade = Table.AddColumn(Renomeada, "cidade", each Cidade, type text),
    Resultado = Table.TransformColumnTypes(ComCidade, {
        {"data", type date},
        {"temp_max_c", type number},
        {"temp_min_c", type number},
        {"chuva_mm", type number}
    })
in
    Resultado''',
        "python": '''import pandas as pd
import requests

CIDADE = "«CIDADE»"
LATITUDE = «LATITUDE»
LONGITUDE = «LONGITUDE»
DATA_INICIAL = "«DATA_INICIAL»"
DATA_FINAL = "«DATA_FINAL»"

resposta = requests.get(
    "https://archive-api.open-meteo.com/v1/archive",
    params={
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "start_date": DATA_INICIAL,
        "end_date": DATA_FINAL,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
        "timezone": "America/Sao_Paulo",
    },
    timeout=30,
)
resposta.raise_for_status()

df = pd.DataFrame(resposta.json()["daily"]).rename(columns={
    "time": "data",
    "temperature_2m_max": "temp_max_c",
    "temperature_2m_min": "temp_min_c",
    "precipitation_sum": "chuva_mm",
})
df["data"] = pd.to_datetime(df["data"])
df.insert(0, "cidade", CIDADE)''',
    },
    {
        "id": "indicadores",
        "icone": "🌍",
        "titulo": "Indicadores de países",
        "fonte": "Banco Mundial",
        "docs": "https://datahelpdesk.worldbank.org/knowledgebase/articles/889392",
        "resumo": "PIB, população ou inflação por país e ano, para comparar economias.",
        "papel": "Fato",
        "tabela": "fIndicadorPais",
        "colunas": "pais_iso3, pais, indicador_id, indicador, ano, valor",
        "parametros": [
            {"chave": "INDICADOR", "rotulo": "Indicador", "tipo": "opcoes", "opcoes": {
                "PIB (US$ correntes)": "NY.GDP.MKTP.CD", "População total": "SP.POP.TOTL",
                "Inflação anual (%)": "FP.CPI.TOTL.ZG"}},
            {"chave": "PAISES", "rotulo": "Países", "tipo": "texto", "padrao": "BR;AR;CL;MX;US",
             "padrao_re": r"[A-Za-z]{2,3}(;[A-Za-z]{2,3})*", "ajuda": "Códigos de 2 ou 3 letras separados por ponto e vírgula."},
            {"chave": "ANO_INICIAL", "rotulo": "Ano inicial", "tipo": "inteiro", "padrao": 2000, "min": 1960, "max": 2100},
            {"chave": "ANO_FINAL", "rotulo": "Ano final", "tipo": "inteiro", "padrao": 2024, "min": 1960, "max": 2100},
        ],
        "observacao": "Os anos mais recentes podem vir sem valor, porque o Banco Mundial publica com atraso.",
        "ponte": "Bom para um projeto de portfólio com dados reais. Combine com o kit Países, que serve de "
                 "dimensão, e peça as medidas no Pergunte aos Dados do BI Data Generator.",
        "visuais": ["Linha do indicador por país", "Ranking de países no último ano",
                    "Crescimento percentual entre dois anos"],
        "dax": '''Valor = SUM ( fIndicadorPais[valor] )

Variação Anual % =
VAR AnoAtual = MAX ( fIndicadorPais[ano] )
VAR Anterior = CALCULATE ( [Valor], fIndicadorPais[ano] = AnoAtual - 1 )
RETURN
    DIVIDE ( [Valor] - Anterior, Anterior )''',
        "m": '''let
    Paises = "«PAISES»",
    Indicador = "«INDICADOR»",
    AnoInicial = "«ANO_INICIAL»",
    AnoFinal = "«ANO_FINAL»",
    Fonte = Json.Document(Web.Contents("https://api.worldbank.org", [
        RelativePath = "v2/country/" & Paises & "/indicator/" & Indicador,
        Query = [format = "json", per_page = "10000", date = AnoInicial & ":" & AnoFinal]
    ])),
    Tabela = Table.FromRecords(Fonte{1}, null, MissingField.UseNull),
    ComPais = Table.ExpandRecordColumn(Tabela, "country", {"value"}, {"pais"}),
    ComIndicador = Table.ExpandRecordColumn(ComPais, "indicator", {"id", "value"}, {"indicador_id", "indicador"}),
    Colunas = Table.SelectColumns(ComIndicador, {"countryiso3code", "pais", "indicador_id", "indicador", "date", "value"}),
    Renomeada = Table.RenameColumns(Colunas, {{"countryiso3code", "pais_iso3"}, {"date", "ano"}, {"value", "valor"}}),
    Resultado = Table.TransformColumnTypes(Renomeada, {{"ano", Int64.Type}, {"valor", type number}})
in
    Resultado''',
        "python": '''import pandas as pd
import requests

PAISES = "«PAISES»"
INDICADOR = "«INDICADOR»"
ANO_INICIAL = «ANO_INICIAL»
ANO_FINAL = «ANO_FINAL»

resposta = requests.get(
    f"https://api.worldbank.org/v2/country/{PAISES}/indicator/{INDICADOR}",
    params={"format": "json", "per_page": 10000, "date": f"{ANO_INICIAL}:{ANO_FINAL}"},
    timeout=30,
)
resposta.raise_for_status()

df = pd.json_normalize(resposta.json()[1]).rename(columns={
    "countryiso3code": "pais_iso3",
    "country.value": "pais",
    "indicator.id": "indicador_id",
    "indicator.value": "indicador",
    "date": "ano",
    "value": "valor",
})[["pais_iso3", "pais", "indicador_id", "indicador", "ano", "valor"]]
df["ano"] = df["ano"].astype(int)
df = df.sort_values(["pais", "ano"]).reset_index(drop=True)''',
    },
    {
        "id": "paises",
        "icone": "🏳️",
        "titulo": "Países",
        "fonte": "Banco Mundial",
        "docs": "https://datahelpdesk.worldbank.org/knowledgebase/articles/898590",
        "resumo": "Cadastro de países com região, faixa de renda, capital e coordenadas.",
        "papel": "Dimensão",
        "tabela": "dPais",
        "colunas": "pais_iso3, pais_iso2, pais, regiao, nivel_renda, capital, latitude, longitude",
        "parametros": [],
        "observacao": "Os agregados do Banco Mundial, como \"Mundo\" e \"América Latina\", já são removidos.",
        "ponte": "É a dimensão do kit Indicadores de países: relacione pelo código pais_iso3. Depois passe o "
                 "modelo pelo Auditor de Modelo do BI Data Generator para conferir os relacionamentos.",
        "visuais": ["Mapa com a capital de cada país", "Indicadores agrupados por região",
                    "Comparação entre faixas de renda"],
        "dax": '''Países = DISTINCTCOUNT ( dPais[pais_iso3] )

Países de Renda Alta =
CALCULATE ( [Países], dPais[nivel_renda] = "High income" )''',
        "m": '''let
    Fonte = Json.Document(Web.Contents("https://api.worldbank.org", [
        RelativePath = "v2/country",
        Query = [format = "json", per_page = "400"]
    ])),
    Tabela = Table.FromRecords(Fonte{1}, null, MissingField.UseNull),
    ComRegiao = Table.ExpandRecordColumn(Tabela, "region", {"value"}, {"regiao"}),
    ComRenda = Table.ExpandRecordColumn(ComRegiao, "incomeLevel", {"value"}, {"nivel_renda"}),
    SemAgregados = Table.SelectRows(ComRenda, each [regiao] <> "Aggregates"),
    Colunas = Table.SelectColumns(SemAgregados, {"id", "iso2Code", "name", "regiao", "nivel_renda", "capitalCity", "latitude", "longitude"}),
    Renomeada = Table.RenameColumns(Colunas, {{"id", "pais_iso3"}, {"iso2Code", "pais_iso2"}, {"name", "pais"}, {"capitalCity", "capital"}}),
    Limpa = Table.TransformColumns(Renomeada, {{"regiao", Text.Trim, type text}}),
    Resultado = Table.TransformColumnTypes(Limpa, {{"latitude", type number}, {"longitude", type number}}, "en-US")
in
    Resultado''',
        "python": '''import pandas as pd
import requests

resposta = requests.get(
    "https://api.worldbank.org/v2/country",
    params={"format": "json", "per_page": 400},
    timeout=30,
)
resposta.raise_for_status()

df = pd.json_normalize(resposta.json()[1]).rename(columns={
    "id": "pais_iso3",
    "iso2Code": "pais_iso2",
    "name": "pais",
    "region.value": "regiao",
    "incomeLevel.value": "nivel_renda",
    "capitalCity": "capital",
})
df = df[df["regiao"] != "Aggregates"]
df = df[["pais_iso3", "pais_iso2", "pais", "regiao", "nivel_renda", "capital", "latitude", "longitude"]]
df["regiao"] = df["regiao"].str.strip()
df[["latitude", "longitude"]] = df[["latitude", "longitude"]].apply(pd.to_numeric, errors="coerce")
df = df.reset_index(drop=True)''',
    },
    {
        "id": "terremotos",
        "icone": "🌋",
        "titulo": "Terremotos no mundo",
        "fonte": "USGS (Serviço Geológico dos EUA)",
        "docs": "https://earthquake.usgs.gov/fdsnws/event/1/",
        "resumo": "Um evento por linha, com magnitude, local, data e coordenadas para mapa.",
        "papel": "Fato",
        "tabela": "fTerremoto",
        "colunas": "id, data_hora, magnitude, local, latitude, longitude, profundidade_km, tsunami, relevancia, url",
        "parametros": [
            {"chave": "MAGNITUDE_MINIMA", "rotulo": "Magnitude mínima", "tipo": "opcoes", "opcoes": {
                "5,0": "5", "4,5": "4.5", "6,0": "6", "7,0": "7"}},
            {"chave": "DATA_INICIAL", "rotulo": "Data inicial", "tipo": "data", "padrao": "2025-01-01", "formato": "%Y-%m-%d"},
            {"chave": "DATA_FINAL", "rotulo": "Data final", "tipo": "data", "padrao": "2025-12-31", "formato": "%Y-%m-%d"},
        ],
        "observacao": "A API devolve no máximo 20.000 eventos por consulta. Datas e horas vêm em UTC.",
        "ponte": "Projeto de portfólio com mapa e dados reais. Monte a dCalendario no BI Data Generator e "
                 "relacione pela data do evento para analisar por mês e ano.",
        "visuais": ["Mapa de bolhas com tamanho pela magnitude", "Eventos por mês",
                    "Os 10 maiores terremotos do período"],
        "dax": '''Terremotos = COUNTROWS ( fTerremoto )

Maior Magnitude = MAX ( fTerremoto[magnitude] )''',
        "m": '''let
    MagnitudeMinima = "«MAGNITUDE_MINIMA»",
    DataInicial = "«DATA_INICIAL»",
    DataFinal = "«DATA_FINAL»",
    Fonte = Json.Document(Web.Contents("https://earthquake.usgs.gov", [
        RelativePath = "fdsnws/event/1/query",
        Query = [format = "geojson", starttime = DataInicial, endtime = DataFinal, minmagnitude = MagnitudeMinima, orderby = "time"]
    ])),
    Eventos = Table.FromList(Fonte[features], Splitter.SplitByNothing(), {"evento"}),
    Expandida = Table.ExpandRecordColumn(Eventos, "evento", {"id", "properties", "geometry"}),
    Propriedades = Table.ExpandRecordColumn(Expandida, "properties", {"mag", "place", "time", "tsunami", "sig", "url"}, {"magnitude", "local", "time", "tsunami", "relevancia", "url"}),
    Geometria = Table.ExpandRecordColumn(Propriedades, "geometry", {"coordinates"}),
    ComLongitude = Table.AddColumn(Geometria, "longitude", each [coordinates]{0}, type number),
    ComLatitude = Table.AddColumn(ComLongitude, "latitude", each [coordinates]{1}, type number),
    ComProfundidade = Table.AddColumn(ComLatitude, "profundidade_km", each [coordinates]{2}, type number),
    ComDataHora = Table.AddColumn(ComProfundidade, "data_hora", each #datetime(1970, 1, 1, 0, 0, 0) + #duration(0, 0, 0, [time] / 1000), type datetime),
    Colunas = Table.SelectColumns(ComDataHora, {"id", "data_hora", "magnitude", "local", "latitude", "longitude", "profundidade_km", "tsunami", "relevancia", "url"}),
    Resultado = Table.TransformColumnTypes(Colunas, {{"magnitude", type number}, {"tsunami", Int64.Type}, {"relevancia", Int64.Type}})
in
    Resultado''',
        "python": '''import pandas as pd
import requests

MAGNITUDE_MINIMA = «MAGNITUDE_MINIMA»
DATA_INICIAL = "«DATA_INICIAL»"
DATA_FINAL = "«DATA_FINAL»"

resposta = requests.get(
    "https://earthquake.usgs.gov/fdsnws/event/1/query",
    params={
        "format": "geojson",
        "starttime": DATA_INICIAL,
        "endtime": DATA_FINAL,
        "minmagnitude": MAGNITUDE_MINIMA,
        "orderby": "time",
    },
    timeout=60,
)
resposta.raise_for_status()

registros = [
    {
        "id": evento["id"],
        "data_hora": evento["properties"]["time"],
        "magnitude": evento["properties"]["mag"],
        "local": evento["properties"]["place"],
        "latitude": evento["geometry"]["coordinates"][1],
        "longitude": evento["geometry"]["coordinates"][0],
        "profundidade_km": evento["geometry"]["coordinates"][2],
        "tsunami": evento["properties"]["tsunami"],
        "relevancia": evento["properties"]["sig"],
        "url": evento["properties"]["url"],
    }
    for evento in resposta.json()["features"]
]
df = pd.DataFrame(registros)
df["data_hora"] = pd.to_datetime(df["data_hora"], unit="ms")''',
    },
    {
        "id": "deputados",
        "icone": "🏛️",
        "titulo": "Deputados federais",
        "fonte": "Câmara dos Deputados (Dados Abertos)",
        "docs": "https://dadosabertos.camara.leg.br/swagger/api.html",
        "resumo": "Deputados em exercício com partido e UF, para análises de política e dados públicos.",
        "papel": "Dimensão",
        "tabela": "dDeputado",
        "colunas": "id, nome, siglaPartido, siglaUf, idLegislatura, urlFoto, email",
        "parametros": [],
        "observacao": "A mesma API tem despesas, votações e proposições, que servem de tabelas fato.",
        "ponte": "Ponto de partida para um projeto com dados públicos: esta tabela é a dimensão, e as despesas "
                 "da cota parlamentar entram como fato. Use o Formatador DAX e M do BI Data Generator para "
                 "organizar as consultas à medida que o projeto cresce.",
        "visuais": ["Deputados por partido", "Mapa de deputados por UF", "Cartões com foto usando urlFoto"],
        "dax": '''Deputados = COUNTROWS ( dDeputado )

Partidos = DISTINCTCOUNT ( dDeputado[siglaPartido] )''',
        "m": '''let
    Fonte = Json.Document(Web.Contents("https://dadosabertos.camara.leg.br", [
        RelativePath = "api/v2/deputados",
        Query = [itens = "1000", ordem = "ASC", ordenarPor = "nome"],
        Headers = [Accept = "application/json"]
    ])),
    Resultado = Table.FromRecords(Fonte[dados], null, MissingField.UseNull)
in
    Resultado''',
        "python": '''import pandas as pd
import requests

resposta = requests.get(
    "https://dadosabertos.camara.leg.br/api/v2/deputados",
    params={"itens": 1000, "ordem": "ASC", "ordenarPor": "nome"},
    headers={"Accept": "application/json"},
    timeout=30,
)
resposta.raise_for_status()

df = pd.DataFrame(resposta.json()["dados"])''',
    },
]


# ---------- Tradução ----------

def tr(kit: dict, campo: str):
    """Campo do kit no idioma atual; sem tradução, vale o original."""
    return kits_i18n.KITS.get(lang(), {}).get(kit["id"], {}).get(campo, kit.get(campo))


def tr_parametro(kit: dict, parametro: dict, campo: str):
    traducao = kits_i18n.KITS.get(lang(), {}).get(kit["id"], {}).get("parametros", {}).get(parametro["chave"], {})
    if campo == "opcoes":
        return traducao.get("opcoes", list(parametro["opcoes"]))
    return traducao.get(campo, parametro.get(campo))


# ---------- Geração de código ----------

def preencher(modelo: str, valores: dict[str, str]) -> str:
    for chave, valor in valores.items():
        modelo = modelo.replace(f"«{chave}»", valor)
    return modelo


def validar(parametro: dict, valor, rotulo: str = "", ajuda: str = "") -> dict[str, str]:
    """Converte o valor da tela nos marcadores do kit.

    Só passam datas, inteiros, opções fixas (pelo índice) e textos que casam
    com a expressão do parâmetro. É isso que permite executar o código gerado
    na prévia.
    """
    tipo = parametro["tipo"]
    if tipo == "data":
        return {parametro["chave"]: valor.strftime(parametro["formato"])}
    if tipo == "inteiro":
        return {parametro["chave"]: str(int(valor))}
    if tipo == "opcoes":
        escolhido = list(parametro["opcoes"].values())[int(valor)]
        return dict(escolhido) if isinstance(escolhido, dict) else {parametro["chave"]: escolhido}
    texto = str(valor).strip()
    if not re.fullmatch(parametro["padrao_re"], texto):
        raise ValueError(t("invalid_format", label=rotulo or parametro["rotulo"], help=ajuda or parametro.get("ajuda", "")))
    return {parametro["chave"]: texto}


def checar_intervalos(brutos: dict) -> None:
    for inicio, fim in (("DATA_INICIAL", "DATA_FINAL"), ("ANO_INICIAL", "ANO_FINAL")):
        if inicio in brutos and fim in brutos and brutos[inicio] > brutos[fim]:
            raise ValueError(t("period_error"))


@st.cache_data(ttl=3600, show_spinner=False)
def executar_previa(codigo: str) -> pd.DataFrame:
    """Roda o script Python do kit e devolve o DataFrame `df`."""
    ambiente: dict = {"__name__": "kit"}
    exec(codigo, ambiente)  # noqa: S102 - código dos modelos acima, com parâmetros validados
    return ambiente["df"]


def gerar_script_generico(url: str, caminho: str, autenticacao: str, nome_chave: str, salvar_csv: bool) -> str:
    """Script requests + pandas para um endpoint qualquer.

    `autenticacao` é "none", "header" ou "query". Comentários e nomes de
    variáveis seguem o idioma da interface.
    """
    partes = urlsplit(url.strip())
    if partes.scheme not in {"http", "https"} or not partes.netloc:
        raise ValueError(t("err_url"))
    base = f"{partes.scheme}://{partes.netloc}{partes.path}"
    parametros = dict(parse_qsl(partes.query, keep_blank_values=True))
    chaves = [parte.strip() for parte in caminho.split(".") if parte.strip()]
    nome_chave = nome_chave.strip()
    v_params, v_headers = t("code_var_params"), t("code_var_headers")
    v_resposta, v_dados = t("code_var_response"), t("code_var_data")

    linhas = ["import pandas as pd", "import requests", "", f"URL = {base!r}"]
    if autenticacao != "none":
        if not nome_chave:
            raise ValueError(t("err_key_name"))
        linhas.append(f'API_KEY = "{t("code_key_placeholder")}"')
    if autenticacao == "query":
        parametros.pop(nome_chave, None)

    linhas.append("")
    itens = [f"    {k!r}: {v!r}," for k, v in parametros.items()]
    if autenticacao == "query":
        itens.append(f"    {nome_chave!r}: API_KEY,")
    if itens:
        linhas += [f"{v_params} = {{", *itens, "}"]
    if autenticacao == "header":
        linhas.append(f"{v_headers} = {{{nome_chave!r}: API_KEY}}")
    if itens or autenticacao == "header":
        linhas.append("")

    argumentos = ["URL"]
    if itens:
        argumentos.append(f"params={v_params}")
    if autenticacao == "header":
        argumentos.append(f"headers={v_headers}")
    argumentos.append("timeout=30")
    linhas += [
        f"{v_resposta} = requests.get({', '.join(argumentos)})",
        f"{v_resposta}.raise_for_status()",
        f"{v_dados} = {v_resposta}.json()",
    ]
    if chaves:
        linhas += ["", t("code_comment_path")]
        for chave in chaves:
            indice = int(chave) if chave.lstrip("-").isdigit() else chave
            linhas.append(f"{v_dados} = {v_dados}[{indice!r}]")
    linhas += ["", t("code_comment_normalize"), f"df = pd.json_normalize({v_dados})"]
    if salvar_csv:
        linhas += ["", f'df.to_csv("{t("code_csv_name")}", index=False, encoding="utf-8-sig")']
    return "\n".join(linhas)


# ---------- Telas ----------

def _campo(kit: dict, parametro: dict):
    chave = f"kit_{kit['id']}_{parametro['chave']}"
    rotulo = tr_parametro(kit, parametro, "rotulo")
    tipo = parametro["tipo"]
    if tipo == "data":
        formato = "DD/MM/YYYY" if lang() == "pt" else "YYYY-MM-DD"
        return st.date_input(rotulo, value=dt.date.fromisoformat(parametro["padrao"]),
                             min_value=dt.date(1950, 1, 1), max_value=dt.date.today(), format=formato, key=chave)
    if tipo == "inteiro":
        return st.number_input(rotulo, value=parametro["padrao"], min_value=parametro["min"],
                               max_value=parametro["max"], step=1, key=chave)
    if tipo == "opcoes":
        rotulos = tr_parametro(kit, parametro, "opcoes")
        return st.selectbox(rotulo, range(len(rotulos)), format_func=lambda i: rotulos[i], key=keyed(chave))
    return st.text_input(rotulo, value=parametro["padrao"], help=tr_parametro(kit, parametro, "ajuda"), key=chave)


def render_kits() -> None:
    link = f'<a href="{BI_DATA_GENERATOR_URL}" target="_blank" rel="noopener noreferrer">BI Data Generator</a>'
    st.markdown(
        f'<div class="section-heading"><h2>{t("kits_title")}</h2><span>{t("kits_sub")}</span></div>'
        f'<p class="kit-intro">{t("kits_intro", link=link)}</p>',
        unsafe_allow_html=True,
    )

    kit = KITS[st.selectbox(
        t("kit_select"), range(len(KITS)),
        format_func=lambda i: f"{KITS[i]['icone']}  {tr(KITS[i], 'titulo')}", key=keyed("kit_escolhido"),
    )]
    papel = t("role_fact") if kit["papel"] == "Fato" else t("role_dimension")

    st.markdown(
        '<div class="kit-card">'
        f'<div class="kit-icon">{kit["icone"]}</div>'
        '<div class="kit-body">'
        f'<div class="kit-title">{tr(kit, "titulo")}</div>'
        f'<div class="kit-source">{tr(kit, "fonte")} · <a href="{kit["docs"]}" target="_blank" rel="noopener noreferrer">{t("docs")}</a></div>'
        f'<p>{tr(kit, "resumo")}</p>'
        '<div class="meta-row">'
        f'<span class="meta-pill status-neutral"><span class="meta-label">{t("role")}</span>{papel}</span>'
        f'<span class="meta-pill status-neutral"><span class="meta-label">{t("table")}</span>{kit["tabela"]}</span>'
        f'<span class="meta-pill status-good">{t("no_auth")}</span>'
        "</div>"
        f'<div class="kit-columns"><span class="meta-label">{t("columns")}</span> {tr(kit, "colunas")}</div>'
        "</div></div>",
        unsafe_allow_html=True,
    )

    valores: dict[str, str] = {}
    brutos: dict = {}
    if kit["parametros"]:
        colunas = st.columns(len(kit["parametros"]))
        for coluna, parametro in zip(colunas, kit["parametros"]):
            with coluna:
                brutos[parametro["chave"]] = _campo(kit, parametro)
    try:
        for parametro in kit["parametros"]:
            valores.update(validar(
                parametro, brutos[parametro["chave"]],
                tr_parametro(kit, parametro, "rotulo"), tr_parametro(kit, parametro, "ajuda") or "",
            ))
        checar_intervalos(brutos)
    except ValueError as erro:
        st.warning(str(erro))
        return
    if kit.get("observacao"):
        st.caption(tr(kit, "observacao"))

    codigo_m = preencher(kit["m"], valores)
    codigo_python = preencher(kit["python"], valores)
    nota_nomes = t("code_names_note")

    aba_m, aba_python, aba_modelo, aba_previa = st.tabs(
        [t("tab_m"), t("tab_py"), t("tab_model"), t("tab_preview")]
    )
    with aba_m:
        st.caption(t("m_how", table=kit["tabela"]))
        st.code(codigo_m, language="powerquery")
        st.caption(f'{t("m_note")} {nota_nomes}'.strip())
    with aba_python:
        st.caption(f'{t("py_how")} {nota_nomes}'.strip())
        st.code(codigo_python, language="python")
    with aba_modelo:
        st.markdown(f'<div class="kit-bridge"><strong>{t("bridge_title")}</strong><p>{tr(kit, "ponte")}</p></div>',
                    unsafe_allow_html=True)
        esquerda, direita = st.columns(2)
        with esquerda:
            st.markdown(f'**{t("visuals_title")}**')
            st.markdown("\n".join(f"- {item}" for item in tr(kit, "visuais")))
        with direita:
            st.markdown(f'**{t("dax_title")}**')
            st.code(tr(kit, "dax"), language="dax")
        st.link_button(t("open_bdg"), BI_DATA_GENERATOR_URL)
    with aba_previa:
        st.caption(t("preview_caption"))
        if st.button(t("preview_button"), key=f"previa_{kit['id']}"):
            st.session_state["previa_codigo"] = codigo_python
        if st.session_state.get("previa_codigo") == codigo_python:
            try:
                with st.spinner(t("preview_spinner")):
                    tabela = executar_previa(codigo_python)
            except Exception as erro:  # a API pode estar fora do ar ou recusar o período
                st.error(t("preview_error"))
                st.caption(t("preview_detail", detail=f"{type(erro).__name__}: {str(erro)[:200]}"))
            else:
                st.caption(t("preview_shape", rows=number(len(tabela)), cols=len(tabela.columns)))
                st.dataframe(tabela.head(200), use_container_width=True, hide_index=True)
                st.download_button(t("download_csv"), tabela.to_csv(index=False).encode("utf-8-sig"),
                                   file_name=f"{kit['tabela']}.csv", mime="text/csv", key=f"csv_{kit['id']}")


def render_gerador_python() -> None:
    st.markdown(
        f'<div class="section-heading"><h2>{t("gen_title")}</h2><span>{t("gen_sub")}</span></div>'
        f'<p class="kit-intro">{t("gen_intro")}</p>',
        unsafe_allow_html=True,
    )
    url = st.text_input(t("gen_url"), placeholder=t("gen_url_ph"), key="gerador_url")
    esquerda, direita = st.columns(2)
    with esquerda:
        caminho = st.text_input(t("gen_path"), placeholder="data.items", help=t("gen_path_help"), key="gerador_caminho")
        salvar_csv = st.checkbox(t("gen_csv"), key="gerador_csv")
    with direita:
        autenticacao = st.selectbox(t("gen_auth"), ["none", "header", "query"],
                                    format_func=lambda codigo: t(f"auth_{codigo}"), key=keyed("gerador_auth"))
        nome_chave = ""
        if autenticacao != "none":
            exemplo = "X-API-Key" if autenticacao == "header" else "apikey"
            nome_chave = st.text_input(t("gen_key_name"), placeholder=exemplo, key="gerador_nome_chave")

    if not url.strip():
        st.caption(t("gen_hint"))
        return
    try:
        codigo = gerar_script_generico(url, caminho, autenticacao, nome_chave, salvar_csv)
    except ValueError as erro:
        st.warning(str(erro))
        return
    st.code(codigo, language="python")
    dica = t("gen_how")
    if autenticacao != "none":
        dica += " " + t("gen_swap_key", placeholder=t("code_key_placeholder"))
    st.caption(dica)
    st.markdown(f'<div class="kit-bridge"><strong>{t("next_title")}</strong><p>{t("next_text")}</p></div>',
                unsafe_allow_html=True)
    st.link_button(t("open_bdg"), BI_DATA_GENERATOR_URL)
