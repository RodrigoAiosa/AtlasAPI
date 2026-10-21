"""Kits de outras APIs gratuitas, sem cadastro nem chave.

- Expectativas de mercado (Boletim Focus) — Banco Central, API Olinda
- Séries do Ipeadata — Ipea
- Criptomoedas — Mercado Bitcoin
- Feriados no mundo — Nager.Date
- Indicadores do Our World in Data

Mesmo formato dos kits de kits.py: parâmetros como «MARCADOR» nos modelos em
M e em Python, medidas DAX e textos de apoio. As traduções ficam em
kits_i18n.py.
"""

KITS = [
    {
        "id": "focus",
        "icone": "🔮",
        "titulo": "Expectativas de mercado (Focus)",
        "fonte": "Banco Central do Brasil (Boletim Focus, API Olinda)",
        "docs": "https://dadosabertos.bcb.gov.br/dataset/expectativas-mercado",
        "resumo": "O que o mercado espera para IPCA, PIB, Selic, câmbio e IGP-M em cada ano, dia a dia.",
        "papel": "Fato",
        "tabela": "fExpectativa",
        "colunas": "data, indicador, ano_referencia, media, mediana, minimo, maximo, respondentes",
        "parametros": [
            {"chave": "INDICADOR", "rotulo": "Indicador", "tipo": "opcoes", "opcoes": {
                "IPCA": "IPCA", "PIB Total": "PIB Total", "Selic": "Selic", "Câmbio": "Câmbio", "IGP-M": "IGP-M"}},
            {"chave": "DATA_INICIAL", "rotulo": "Data inicial", "tipo": "data", "padrao": "2024-01-01",
             "formato": "%Y-%m-%d"},
        ],
        "observacao": "Cada linha é a estatística do Focus em uma data para um ano de referência. A base de cálculo é a "
                      "de todos os respondentes dos últimos 30 dias (baseCalculo = 0).",
        "ponte": "Compare a expectativa com o realizado: junte este kit ao IPCA ou à Selic e mostre a distância "
                 "entre o que o mercado previa e o que aconteceu.",
        "visuais": ["Mediana da expectativa por ano de referência ao longo do tempo",
                    "Faixa entre mínimo e máximo", "Cartão com a expectativa mais recente"],
        "dax": '''Expectativa (Mediana) = AVERAGE ( fExpectativa[mediana] )

Expectativa Mais Recente =
VAR UltimaData = MAX ( fExpectativa[data] )
RETURN
    CALCULATE ( [Expectativa (Mediana)], fExpectativa[data] = UltimaData )

Respondentes = MAX ( fExpectativa[respondentes] )''',
        "m": '''let
    Indicador = "«INDICADOR»",
    DataInicial = "«DATA_INICIAL»",
    Campos = {"Indicador", "Data", "DataReferencia", "Media", "Mediana", "Minimo", "Maximo", "numeroRespondentes"},
    Fonte = Json.Document(Web.Contents("https://olinda.bcb.gov.br", [
        RelativePath = "olinda/servico/Expectativas/versao/v1/odata/ExpectativasMercadoAnuais",
        Query = [
            #"$filter" = "Indicador eq '" & Indicador & "' and Data ge '" & DataInicial & "' and baseCalculo eq 0",
            #"$select" = Text.Combine(Campos, ","),
            #"$orderby" = "Data",
            #"$top" = "100000",
            #"$format" = "json"
        ]
    ])),
    Tabela = Table.FromRecords(Fonte[value], Campos, MissingField.UseNull),
    Renomeada = Table.RenameColumns(Tabela, {
        {"Indicador", "indicador"}, {"Data", "data"}, {"DataReferencia", "ano_referencia"},
        {"Media", "media"}, {"Mediana", "mediana"}, {"Minimo", "minimo"}, {"Maximo", "maximo"},
        {"numeroRespondentes", "respondentes"}
    }),
    Colunas = Table.SelectColumns(Renomeada, {"data", "indicador", "ano_referencia", "media", "mediana", "minimo", "maximo", "respondentes"}),
    Resultado = Table.TransformColumnTypes(Colunas, {
        {"data", type date}, {"indicador", type text}, {"ano_referencia", Int64.Type},
        {"media", type number}, {"mediana", type number}, {"minimo", type number}, {"maximo", type number},
        {"respondentes", Int64.Type}
    }, "en-US")
in
    Resultado''',
        "python": '''import pandas as pd
import requests

INDICADOR = "«INDICADOR»"
DATA_INICIAL = "«DATA_INICIAL»"

resposta = requests.get(
    "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/ExpectativasMercadoAnuais",
    params={
        "$filter": f"Indicador eq '{INDICADOR}' and Data ge '{DATA_INICIAL}' and baseCalculo eq 0",
        "$select": "Indicador,Data,DataReferencia,Media,Mediana,Minimo,Maximo,numeroRespondentes",
        "$orderby": "Data",
        "$top": 100000,
        "$format": "json",
    },
    timeout=60,
)
resposta.raise_for_status()

df = pd.DataFrame(resposta.json()["value"]).rename(columns={
    "Indicador": "indicador", "Data": "data", "DataReferencia": "ano_referencia",
    "Media": "media", "Mediana": "mediana", "Minimo": "minimo", "Maximo": "maximo",
    "numeroRespondentes": "respondentes",
})
df = df[["data", "indicador", "ano_referencia", "media", "mediana", "minimo", "maximo", "respondentes"]]
df["data"] = pd.to_datetime(df["data"])
df["ano_referencia"] = df["ano_referencia"].astype(int)''',
    },
    {
        "id": "ipea",
        "icone": "📈",
        "titulo": "Séries do Ipeadata",
        "fonte": "Ipea (Ipeadata, API OData)",
        "docs": "http://www.ipeadata.gov.br/api/",
        "resumo": "Séries mensais do Ipeadata: IGP-M, salário mínimo, Selic acumulada e dólar médio.",
        "papel": "Fato",
        "tabela": "fIpea",
        "colunas": "data, serie, valor",
        "parametros": [
            {"chave": "SERIE", "rotulo": "Série", "tipo": "opcoes", "opcoes": {
                "IGP-M (% ao mês)": "IGP12_IGPMG12",
                "Salário mínimo vigente (R$)": "MTE12_SALMIN12",
                "Salário mínimo real (R$ do último mês)": "GAC12_SALMINRE12",
                "Selic acumulada no mês (% ao mês)": "BM12_TJOVER12",
                "Dólar comercial, média mensal (R$)": "BM12_ERC12",
            }},
        ],
        "observacao": "O Ipeadata tem milhares de séries. Para usar outra, troque o código da série (SERCODIGO) na "
                      "consulta; os códigos aparecem em ipeadata.gov.br.",
        "ponte": "O salário mínimo real é ótimo para deflacionar valores de uma base criada no BI Data Generator "
                 "e comparar períodos em reais do mesmo poder de compra.",
        "visuais": ["Linha da série ao longo do tempo", "Cartão com o último valor", "Variação em 12 meses"],
        "dax": '''Valor da Série = AVERAGE ( fIpea[valor] )

Último Valor da Série =
VAR UltimaData = MAX ( fIpea[data] )
RETURN
    CALCULATE ( [Valor da Série], fIpea[data] = UltimaData )''',
        "m": '''let
    Serie = "«SERIE»",
    Fonte = Json.Document(Web.Contents("https://www.ipeadata.gov.br", [
        RelativePath = "api/odata4/ValoresSerie(SERCODIGO='" & Serie & "')"
    ])),
    Tabela = Table.FromRecords(Fonte[value], {"SERCODIGO", "VALDATA", "VALVALOR"}, MissingField.UseNull),
    // A data vem como "2026-07-01T00:00:00-03:00": só os 10 primeiros caracteres interessam.
    ComData = Table.AddColumn(Tabela, "data", each Date.FromText(Text.Start([VALDATA], 10)), type date),
    Renomeada = Table.RenameColumns(ComData, {{"SERCODIGO", "serie"}, {"VALVALOR", "valor"}}),
    Colunas = Table.SelectColumns(Renomeada, {"data", "serie", "valor"}),
    Resultado = Table.TransformColumnTypes(Colunas, {{"serie", type text}, {"valor", type number}})
in
    Resultado''',
        "python": '''import pandas as pd
import requests

SERIE = "«SERIE»"

resposta = requests.get(
    f"https://www.ipeadata.gov.br/api/odata4/ValoresSerie(SERCODIGO='{SERIE}')",
    timeout=60,
)
resposta.raise_for_status()

df = pd.DataFrame(resposta.json()["value"])
df["data"] = pd.to_datetime(df["VALDATA"].str[:10])
df = df.rename(columns={"SERCODIGO": "serie", "VALVALOR": "valor"})[["data", "serie", "valor"]]''',
    },
    {
        "id": "cripto",
        "icone": "₿",
        "titulo": "Criptomoedas em reais",
        "fonte": "Mercado Bitcoin (API pública v4)",
        "docs": "https://api.mercadobitcoin.net/api/v4/docs",
        "resumo": "Preço diário de abertura, máxima, mínima, fechamento e volume de criptomoedas em reais.",
        "papel": "Fato",
        "tabela": "fCripto",
        "colunas": "data, moeda, abertura, maxima, minima, fechamento, volume",
        "parametros": [
            {"chave": "MOEDA", "rotulo": "Criptomoeda", "tipo": "opcoes", "opcoes": {
                "Bitcoin (BTC)": "BTC", "Ethereum (ETH)": "ETH", "Solana (SOL)": "SOL",
                "Tether (USDT)": "USDT", "XRP": "XRP"}},
            {"chave": "DATA_INICIAL", "rotulo": "Data inicial", "tipo": "data", "padrao": "2025-01-01",
             "formato": "%Y-%m-%d"},
            {"chave": "DATA_FINAL", "rotulo": "Data final", "tipo": "data", "padrao": "2025-12-31",
             "formato": "%Y-%m-%d"},
        ],
        "observacao": "Cotações da corretora Mercado Bitcoin, em candles diários (horário UTC). O volume é na "
                      "própria criptomoeda.",
        "ponte": "Use como série de preços para praticar análise de investimentos: retorno, volatilidade e "
                 "comparação com o dólar (kit Câmbio diário) na mesma dCalendario.",
        "visuais": ["Linha do preço de fechamento", "Colunas de volume diário", "Variação no período"],
        "dax": '''Preço de Fechamento = AVERAGE ( fCripto[fechamento] )

Último Preço =
VAR UltimaData = MAX ( fCripto[data] )
RETURN
    CALCULATE ( [Preço de Fechamento], fCripto[data] = UltimaData )

Variação no Período % =
VAR PrimeiraData = MIN ( fCripto[data] )
VAR UltimaData = MAX ( fCripto[data] )
VAR Inicio = CALCULATE ( [Preço de Fechamento], fCripto[data] = PrimeiraData )
VAR Fim = CALCULATE ( [Preço de Fechamento], fCripto[data] = UltimaData )
RETURN
    DIVIDE ( Fim - Inicio, Inicio )

Volume Negociado = SUM ( fCripto[volume] )''',
        "m": '''let
    Moeda = "«MOEDA»",
    Epoca = #datetime(1970, 1, 1, 0, 0, 0),
    Segundos = (data as date) => Number.ToText(Duration.TotalSeconds(DateTime.From(data) - Epoca), "0"),
    Fonte = Json.Document(Web.Contents("https://api.mercadobitcoin.net", [
        RelativePath = "api/v4/candles",
        Query = [
            symbol = Moeda & "-BRL",
            resolution = "1d",
            from = Segundos(Date.FromText("«DATA_INICIAL»")),
            to = Segundos(Date.FromText("«DATA_FINAL»"))
        ]
    ])),
    // A resposta traz uma lista por campo: t (data em segundos), o, h, l, c (preços) e v (volume).
    Tabela = Table.FromColumns(
        {Fonte[t], Fonte[o], Fonte[h], Fonte[l], Fonte[c], Fonte[v]},
        {"t", "abertura", "maxima", "minima", "fechamento", "volume"}
    ),
    ComData = Table.AddColumn(Tabela, "data", each Date.From(Epoca + #duration(0, 0, 0, [t])), type date),
    ComMoeda = Table.AddColumn(ComData, "moeda", each Moeda, type text),
    Colunas = Table.SelectColumns(ComMoeda, {"data", "moeda", "abertura", "maxima", "minima", "fechamento", "volume"}),
    Resultado = Table.TransformColumnTypes(Colunas, {
        {"abertura", type number}, {"maxima", type number}, {"minima", type number},
        {"fechamento", type number}, {"volume", type number}
    }, "en-US")
in
    Resultado''',
        "python": '''from datetime import datetime, timezone

import pandas as pd
import requests

MOEDA = "«MOEDA»"
DATA_INICIAL = "«DATA_INICIAL»"
DATA_FINAL = "«DATA_FINAL»"


def segundos(texto: str) -> int:
    return int(datetime.fromisoformat(texto).replace(tzinfo=timezone.utc).timestamp())


resposta = requests.get(
    "https://api.mercadobitcoin.net/api/v4/candles",
    params={"symbol": f"{MOEDA}-BRL", "resolution": "1d",
            "from": segundos(DATA_INICIAL), "to": segundos(DATA_FINAL)},
    timeout=30,
)
resposta.raise_for_status()
dados = resposta.json()

df = pd.DataFrame({
    "data": pd.to_datetime(dados["t"], unit="s").normalize(),
    "moeda": MOEDA,
    "abertura": pd.to_numeric(dados["o"]),
    "maxima": pd.to_numeric(dados["h"]),
    "minima": pd.to_numeric(dados["l"]),
    "fechamento": pd.to_numeric(dados["c"]),
    "volume": pd.to_numeric(dados["v"]),
})''',
    },
    {
        "id": "feriados_mundo",
        "icone": "🗺️",
        "titulo": "Feriados no mundo",
        "fonte": "Nager.Date",
        "docs": "https://date.nager.at/Api",
        "resumo": "Feriados de mais de 100 países, por ano, com nome local, nome em inglês e abrangência.",
        "papel": "Fato",
        "tabela": "fFeriadoPais",
        "colunas": "data, pais_iso2, feriado, feriado_local, abrangencia, tipo",
        "parametros": [
            {"chave": "PAISES", "rotulo": "Países", "tipo": "texto", "padrao": "US;AR;PT",
             "padrao_re": r"[A-Za-z]{2}(;[A-Za-z]{2})*",
             "ajuda": "Códigos de 2 letras separados por ponto e vírgula, como US;AR;PT."},
            {"chave": "ANO_INICIAL", "rotulo": "Ano inicial", "tipo": "inteiro", "padrao": 2025, "min": 1975, "max": 2100},
            {"chave": "ANO_FINAL", "rotulo": "Ano final", "tipo": "inteiro", "padrao": 2026, "min": 1975, "max": 2100},
        ],
        "observacao": "Abrangência \"Regional\" indica feriado que vale só em parte do país. Países fora da cobertura "
                      "da Nager.Date não devolvem dados.",
        "ponte": "Para empresas com operação em vários países: marque dias sem expediente em cada país e "
                 "relacione pais_iso2 com a dimensão do kit Países.",
        "visuais": ["Feriados por país", "Lista de feriados", "Feriados por mês"],
        "dax": '''Feriados = COUNTROWS ( fFeriadoPais )

Feriados Nacionais = CALCULATE ( [Feriados], fFeriadoPais[abrangencia] = "Nacional" )''',
        "m": '''let
    Paises = Text.Split(Text.Upper("«PAISES»"), ";"),
    Anos = {«ANO_INICIAL»..«ANO_FINAL»},
    Consultar = (pais as text, ano as number) => Json.Document(Web.Contents("https://date.nager.at", [
        RelativePath = "api/v3/PublicHolidays/" & Text.From(ano) & "/" & pais
    ])),
    Registros = List.Combine(List.Transform(Paises, (pais) =>
        List.Combine(List.Transform(Anos, (ano) => Consultar(pais, ano))))),
    Tabela = Table.FromRecords(Registros, {"date", "localName", "name", "countryCode", "global", "types"}, MissingField.UseNull),
    Ajustada = Table.TransformColumns(Tabela, {
        {"global", each if _ = true then "Nacional" else "Regional", type text},
        {"types", each if _ = null then "" else Text.Combine(_, ", "), type text}
    }),
    Renomeada = Table.RenameColumns(Ajustada, {
        {"date", "data"}, {"localName", "feriado_local"}, {"name", "feriado"},
        {"countryCode", "pais_iso2"}, {"global", "abrangencia"}, {"types", "tipo"}
    }),
    Colunas = Table.SelectColumns(Renomeada, {"data", "pais_iso2", "feriado", "feriado_local", "abrangencia", "tipo"}),
    Resultado = Table.TransformColumnTypes(Colunas, {
        {"data", type date}, {"pais_iso2", type text}, {"feriado", type text}, {"feriado_local", type text}
    }, "en-US")
in
    Resultado''',
        "python": '''import pandas as pd
import requests

PAISES = "«PAISES»".upper().split(";")
ANO_INICIAL = «ANO_INICIAL»
ANO_FINAL = «ANO_FINAL»

registros = []
for pais in PAISES:
    for ano in range(ANO_INICIAL, ANO_FINAL + 1):
        resposta = requests.get(f"https://date.nager.at/api/v3/PublicHolidays/{ano}/{pais}", timeout=30)
        resposta.raise_for_status()
        registros += resposta.json() if resposta.content else []

df = pd.DataFrame(registros, columns=["date", "localName", "name", "countryCode", "global", "types"])
df["global"] = df["global"].map(lambda nacional: "Nacional" if nacional else "Regional")
df["types"] = df["types"].map(lambda tipos: ", ".join(tipos) if isinstance(tipos, list) else "")
df = df.rename(columns={
    "date": "data", "localName": "feriado_local", "name": "feriado",
    "countryCode": "pais_iso2", "global": "abrangencia", "types": "tipo",
})[["data", "pais_iso2", "feriado", "feriado_local", "abrangencia", "tipo"]]
df["data"] = pd.to_datetime(df["data"])''',
    },
    {
        "id": "owid",
        "icone": "🌐",
        "titulo": "Our World in Data",
        "fonte": "Our World in Data",
        "docs": "https://docs.owid.io/projects/etl/api/",
        "resumo": "Expectativa de vida, PIB per capita, emissões de CO₂, uso de internet e população de todos os países, ano a ano.",
        "papel": "Fato",
        "tabela": "fIndicadorOWID",
        "colunas": "pais_iso3, pais, indicador, ano, valor",
        "parametros": [
            {"chave": "GRAFICO", "rotulo": "Indicador", "tipo": "opcoes", "opcoes": {
                "Expectativa de vida (anos)": {"GRAFICO": "life-expectancy", "INDICADOR": "Expectativa de vida (anos)"},
                "PIB per capita (US$ PPC de 2021)": {"GRAFICO": "gdp-per-capita-worldbank",
                                                     "INDICADOR": "PIB per capita (US$ PPC de 2021)"},
                "Emissões de CO₂ per capita (t)": {"GRAFICO": "co2-emissions-per-capita",
                                                   "INDICADOR": "Emissões de CO₂ per capita (t)"},
                "Uso de internet (% da população)": {"GRAFICO": "share-of-individuals-using-the-internet",
                                                     "INDICADOR": "Uso de internet (% da população)"},
                "População": {"GRAFICO": "population", "INDICADOR": "População"},
            }},
            {"chave": "ANO_INICIAL", "rotulo": "Ano inicial", "tipo": "inteiro", "padrao": 1990, "min": 1800, "max": 2100},
        ],
        "observacao": "Ficam só os países (código de 3 letras); regiões e agregados como \"World\" são descartados. "
                      "Os gráficos do Our World in Data têm licença CC BY: cite a fonte no relatório.",
        "ponte": "Combine com o kit Países, que serve de dimensão pelo pais_iso3, e com os Indicadores do Banco "
                 "Mundial para comparar o Brasil com o resto do mundo.",
        "visuais": ["Ranking de países no último ano", "Linha da média dos países por ano", "Mapa por país"],
        "dax": '''Valor do Indicador = AVERAGE ( fIndicadorOWID[valor] )

Valor no Último Ano =
VAR UltimoAno = MAX ( fIndicadorOWID[ano] )
RETURN
    CALCULATE ( [Valor do Indicador], fIndicadorOWID[ano] = UltimoAno )''',
        "m": '''let
    Grafico = "«GRAFICO»",
    Indicador = "«INDICADOR»",
    AnoInicial = «ANO_INICIAL»,
    Fonte = Csv.Document(Web.Contents("https://ourworldindata.org", [
        RelativePath = "grapher/" & Grafico & ".csv",
        Query = [v = "1", csvType = "full", useColumnShortNames = "true"]
    ]), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Cabecalho = Table.PromoteHeaders(Fonte, [PromoteAllScalars = true]),
    // As quatro primeiras colunas são sempre país, código, ano e valor; o nome da coluna de valor muda com o gráfico.
    Originais = List.FirstN(Table.ColumnNames(Cabecalho), 4),
    Colunas = Table.SelectColumns(Cabecalho, Originais),
    Renomeada = Table.RenameColumns(Colunas, List.Zip({Originais, {"pais", "pais_iso3", "ano", "valor"}})),
    SoPaises = Table.SelectRows(Renomeada, each [pais_iso3] <> null and Text.Length([pais_iso3]) = 3),
    Tipada = Table.TransformColumnTypes(SoPaises, {{"ano", Int64.Type}, {"valor", type number}}, "en-US"),
    Periodo = Table.SelectRows(Tipada, each [ano] >= AnoInicial),
    ComIndicador = Table.AddColumn(Periodo, "indicador", each Indicador, type text),
    Resultado = Table.SelectColumns(ComIndicador, {"pais_iso3", "pais", "indicador", "ano", "valor"})
in
    Resultado''',
        "python": '''import io

import pandas as pd
import requests

GRAFICO = "«GRAFICO»"
INDICADOR = "«INDICADOR»"
ANO_INICIAL = «ANO_INICIAL»

resposta = requests.get(
    f"https://ourworldindata.org/grapher/{GRAFICO}.csv",
    params={"v": 1, "csvType": "full", "useColumnShortNames": "true"},
    timeout=60,
)
resposta.raise_for_status()

bruto = pd.read_csv(io.StringIO(resposta.text))
df = bruto.iloc[:, :4].copy()
df.columns = ["pais", "pais_iso3", "ano", "valor"]
df = df[df["pais_iso3"].str.len() == 3]
df = df[df["ano"] >= ANO_INICIAL]
df["indicador"] = INDICADOR
df = df[["pais_iso3", "pais", "indicador", "ano", "valor"]].reset_index(drop=True)''',
    },
]
