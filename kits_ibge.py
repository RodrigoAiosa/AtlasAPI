"""Kits do IBGE montados sobre a API do SIDRA (apisidra.ibge.gov.br).

Toda consulta do SIDRA devolve o mesmo formato: uma lista em que a primeira
linha traz os nomes das colunas ("Município", "Ano", "Valor"...). Por isso os
códigos em Power Query e em Python são gerados a partir de uma descrição
curta de cada tabela, em vez de escritos um a um.
"""
from __future__ import annotations

import re

TERRITORIOS = {
    # nível: (colunas do SIDRA -> nomes finais)
    "municipio": [("Município (Código)", "municipio_id"), ("Município", "municipio_uf")],
    "uf": [("Unidade da Federação (Código)", "uf_id"), ("Unidade da Federação", "uf_nome")],
    "brasil": [],
}
PERIODOS = {
    "ano": ("Ano", "ano"),
    "mes": ("Mês (Código)", "mes_id"),
    "trimestre": ("Trimestre (Código)", "trimestre_id"),
}


def _m_texto(caminho: str, nomes_m: dict[str, str]) -> str:
    """Transforma "a/«X»/b" na expressão M "a/" & X & "/b"."""
    partes = re.split(r"«(\w+)»", caminho)
    termos = []
    for indice, parte in enumerate(partes):
        if indice % 2:
            termos.append(nomes_m[parte])
        elif parte:
            termos.append(f'"{parte}"')
    return " & ".join(termos)


def _codigos(caminho, territorio, periodo, dimensoes, medidas, inteiros, parametros):
    """Gera (código M, código Python) de uma consulta ao SIDRA.

    medidas: nome da coluna de valor, ou {código da variável: nome da coluna}
    para abrir cada variável em uma coluna.
    """
    largo = isinstance(medidas, dict)
    origem = TERRITORIOS[territorio] + [PERIODOS[periodo]] + list(dimensoes)
    if largo:
        origem.append(("Variável (Código)", "variavel_id"))
    origem.append(("Valor", "valor"))
    colunas_medida = list(medidas.values()) if largo else [medidas]

    finais = []
    if territorio == "municipio":
        finais += ["municipio_id", "municipio", "uf"]
    elif territorio == "uf":
        finais += ["uf_id", "uf_nome"]
    finais += {"ano": ["ano"], "mes": ["data"], "trimestre": ["ano", "trimestre"]}[periodo]
    finais += [nome for _, nome in dimensoes] + colunas_medida
    ids = [c for c in ("municipio_id", "uf_id") if c in finais] + (["ano"] if periodo == "ano" else [])

    lista = lambda itens: "{" + ", ".join(f'"{i}"' for i in itens) + "}"
    pares = lambda itens: "{" + ", ".join(f'{{"{a}", "{b}"}}' for a, b in itens) + "}"

    # ---------- Power Query ----------
    nomes_m = {p["chave"]: p["nome_m"] for p in parametros}
    m = ["let"]
    m += [f'    {p["nome_m"]} = "«{p["chave"]}»",' for p in parametros]
    m += [
        '    Fonte = Json.Document(Web.Contents("https://apisidra.ibge.gov.br", [',
        f"        RelativePath = {_m_texto(caminho, nomes_m)}",
        "    ])),",
        "    // A primeira linha da resposta traz os nomes das colunas.",
        "    Tabela = Table.PromoteHeaders(Table.FromRecords(Fonte), [PromoteAllScalars = true]),",
        f"    Colunas = Table.SelectColumns(Tabela, {lista(a for a, _ in origem)}),",
        f"    Renomeada = Table.RenameColumns(Colunas, {pares(origem)}),",
        '    // Valores ausentes vêm como "..." ou "-" e viram nulos.',
        '    Valores = Table.TransformColumns(Renomeada, {{"valor", each try Number.FromText(_, "en-US") otherwise null, type number}}),',
    ]
    passo = "Valores"
    if largo:
        m += [
            "    // Cada variável vira uma coluna.",
            f'    Larga = Table.Pivot({passo}, {lista(medidas)}, "variavel_id", "valor"),',
            f"    Medidas = Table.RenameColumns(Larga, {pares(medidas.items())}),",
        ]
        passo = "Medidas"
    else:
        m.append(f'    Medidas = Table.RenameColumns({passo}, {{{{"valor", "{medidas}"}}}}),')
        passo = "Medidas"
    if territorio == "municipio":
        m += [
            '    // O nome vem como "São Paulo (SP)".',
            f'    ComMunicipio = Table.AddColumn({passo}, "municipio", each Text.BeforeDelimiter([municipio_uf], " (", {{0, RelativePosition.FromEnd}}), type text),',
            '    ComUF = Table.AddColumn(ComMunicipio, "uf", each Text.BetweenDelimiters([municipio_uf], "(", ")", {0, RelativePosition.FromEnd}, 0), type text),',
        ]
        passo = "ComUF"
    if periodo == "mes":
        m += [
            '    // O mês vem como "202609".',
            f'    ComData = Table.AddColumn({passo}, "data", each #date(Number.FromText(Text.Start([mes_id], 4)), Number.FromText(Text.End([mes_id], 2)), 1), type date),',
        ]
        passo = "ComData"
    if periodo == "trimestre":
        m += [
            '    // O trimestre vem como "202602".',
            f'    ComAno = Table.AddColumn({passo}, "ano", each Int64.From(Text.Start([trimestre_id], 4)), Int64.Type),',
            '    ComTrimestre = Table.AddColumn(ComAno, "trimestre", each Int64.From(Text.End([trimestre_id], 2)), Int64.Type),',
        ]
        passo = "ComTrimestre"
    tipos = [(c, "Int64.Type") for c in ids] + [(c, "Int64.Type") for c in colunas_medida if c in inteiros]
    if tipos:
        m.append(f"    Tipos = Table.TransformColumnTypes({passo}, {{" + ", ".join(f'{{"{c}", {t}}}' for c, t in tipos) + "}),")
        passo = "Tipos"
    m += [f"    Resultado = Table.SelectColumns({passo}, {lista(finais)})", "in", "    Resultado"]

    # ---------- Python ----------
    py = ["import pandas as pd", "import requests", ""]
    py += [f'{p["chave"]} = "«{p["chave"]}»"' for p in parametros]
    if parametros:
        py.append("")
    url = re.sub(r"«(\w+)»", r"{\1}", caminho)
    prefixo = "f" if parametros else ""
    py += [
        "resposta = requests.get(",
        f'    {prefixo}"https://apisidra.ibge.gov.br/{url}",',
        "    timeout=120,",
        ")",
        "resposta.raise_for_status()",
        "dados = resposta.json()",
        "",
        "# A primeira linha da resposta traz os nomes das colunas.",
        "df = pd.DataFrame(dados[1:]).rename(columns=dados[0])",
        "df = df[[" + ", ".join(f'"{a}"' for a, _ in origem) + "]]",
        "df.columns = [" + ", ".join(f'"{b}"' for _, b in origem) + "]",
        '# Valores ausentes vêm como "..." ou "-" e viram nulos.',
        'df["valor"] = pd.to_numeric(df["valor"], errors="coerce")',
    ]
    if largo:
        chaves = [b for _, b in origem if b not in {"variavel_id", "valor"}]
        py += [
            "# Cada variável vira uma coluna.",
            "df = (",
            "    df.pivot(index=[" + ", ".join(f'"{c}"' for c in chaves) + '], columns="variavel_id", values="valor")',
            "    .rename(columns={" + ", ".join(f'"{k}": "{v}"' for k, v in medidas.items()) + "})",
            "    .reset_index()",
            ")",
            "df.columns.name = None",
        ]
    else:
        py.append(f'df = df.rename(columns={{"valor": "{medidas}"}})')
    if territorio == "municipio":
        py += ['# O nome vem como "São Paulo (SP)".',
               'df[["municipio", "uf"]] = df["municipio_uf"].str.extract(r"^(.*) \\((\\w{2})\\)$")']
    if periodo == "mes":
        py += ['# O mês vem como "202609".', 'df["data"] = pd.to_datetime(df["mes_id"], format="%Y%m")']
    if periodo == "trimestre":
        py += ['# O trimestre vem como "202602".',
               'df["ano"] = df["trimestre_id"].str[:4].astype(int)',
               'df["trimestre"] = df["trimestre_id"].str[4:].astype(int)']
    for coluna in ids:
        py.append(f'df["{coluna}"] = df["{coluna}"].astype(int)')
    for coluna in colunas_medida:
        if coluna in inteiros:
            py.append(f'df["{coluna}"] = df["{coluna}"].round().astype("Int64")')
    py.append("df = df[[" + ", ".join(f'"{c}"' for c in finais) + "]]")
    return "\n".join(m), "\n".join(py), ", ".join(finais)


def _kit(id, icone, titulo, tabela_sidra, resumo, papel, tabela, caminho, territorio, periodo, medidas,
         observacao, ponte, visuais, dax, dimensoes=(), inteiros=(), parametros=()):
    parametros = [dict(p) for p in parametros]
    m, python, colunas = _codigos(caminho, territorio, periodo, dimensoes, medidas, set(inteiros), parametros)
    return {
        "id": id, "icone": icone, "titulo": titulo,
        "fonte": f"IBGE (SIDRA, tabela {tabela_sidra})",
        "docs": f"https://sidra.ibge.gov.br/tabela/{tabela_sidra}",
        "resumo": resumo, "papel": papel, "tabela": tabela, "colunas": colunas,
        "parametros": [{"tipo": "opcoes", **{k: v for k, v in p.items() if k != "nome_m"}} for p in parametros],
        "observacao": observacao, "ponte": ponte, "visuais": visuais, "dax": dax, "m": m, "python": python,
    }


_ANOS = lambda *anos: {"Mais recente": "last", **{a: a for a in anos}}
_ANOS_EN = lambda *anos: ["Latest", *anos]

PRODUTOS = {
    "Soja": "40124", "Milho": "40122", "Cana-de-açúcar": "40106", "Café (total)": "40139", "Arroz": "40102",
    "Feijão": "40112", "Trigo": "40127", "Algodão herbáceo": "40099", "Laranja": "40151", "Mandioca": "40119",
}
PRODUTOS_EN = ["Soybean", "Corn", "Sugarcane", "Coffee (total)", "Rice", "Beans", "Wheat", "Upland cotton", "Orange", "Cassava"]
REBANHOS = {
    "Bovino": "2670", "Suíno": "32794", "Galináceos": "32796", "Ovino": "2677",
    "Caprino": "2681", "Equino": "2672", "Bubalino": "2675", "Codornas": "2680",
}
REBANHOS_EN = ["Cattle", "Pigs", "Poultry", "Sheep", "Goats", "Horses", "Buffalo", "Quails"]

KITS = [
    _kit(
        "censo2022", "🏘️", "Censo 2022: população, área e densidade", "4714",
        "População, área territorial e densidade demográfica de cada município no Censo 2022.",
        "Dimensão", "dCenso2022",
        "values/t/4714/n6/all/v/93,6318,614/p/2022", "municipio", "ano",
        {"93": "populacao", "6318": "area_km2", "614": "densidade_hab_km2"}, inteiros=["populacao"],
        observacao="Uma linha por município (cerca de 5.570). É o dado oficial de 2022, ano sem estimativa anual.",
        ponte="Relacione pelo código do município (municipio_id) com o kit Municípios do Brasil. Sobre uma base "
              "gerada no BI Data Generator, a área e a densidade ajudam a comparar cidades de portes diferentes.",
        visuais=["Mapa de densidade demográfica por município", "Dispersão de população x área",
                 "Ranking das cidades mais densas"],
        dax='''População 2022 = SUM ( dCenso2022[populacao] )

Densidade Média =
DIVIDE ( [População 2022], SUM ( dCenso2022[area_km2] ) )''',
    ),
    _kit(
        "pib_municipios", "💰", "PIB dos municípios", "5938",
        "Produto Interno Bruto a preços correntes de cada município, em mil reais.",
        "Fato", "fPIBMunicipio",
        "values/t/5938/n6/all/v/37/p/«ANO»", "municipio", "ano", "pib_mil_reais", inteiros=["pib_mil_reais"],
        parametros=[{"chave": "ANO", "nome_m": "Ano", "rotulo": "Ano",
                     "opcoes": _ANOS("2023", "2022", "2021", "2020", "2019", "2018")}],
        observacao="O valor vem em mil reais. O IBGE divulga o PIB municipal com cerca de dois anos de defasagem.",
        ponte="Junte com o kit População por município do mesmo ano para calcular o PIB per capita, e compare "
              "com o faturamento por cidade de uma base gerada no BI Data Generator.",
        visuais=["Mapa do PIB por município", "As 20 maiores economias municipais", "PIB per capita por UF"],
        dax='''PIB (R$) = SUM ( fPIBMunicipio[pib_mil_reais] ) * 1000

-- Supondo a medida [População] do kit População por município
PIB per Capita =
DIVIDE ( [PIB (R$)], [População] )''',
    ),
    _kit(
        "ipca", "📈", "IPCA: inflação mensal", "1737",
        "Série histórica completa do IPCA: variação mensal, acumulado em 12 meses e número-índice.",
        "Fato", "fIPCA",
        "values/t/1737/n1/all/v/63,2265,2266/p/all", "brasil", "mes",
        {"63": "variacao_mensal", "2265": "acumulado_12m", "2266": "numero_indice"},
        observacao="Uma linha por mês, desde 1979. O número-índice é o mais indicado para corrigir valores entre duas datas.",
        ponte="Relacione a coluna data com a dCalendario do BI Data Generator para deflacionar o faturamento: "
              "divida o número-índice do mês de referência pelo do mês da venda.",
        visuais=["Linha do acumulado em 12 meses", "Colunas da variação mensal no último ano",
                 "Faturamento nominal x corrigido pelo IPCA"],
        dax='''IPCA 12 Meses =
VAR UltimaData = MAX ( fIPCA[data] )
RETURN
    CALCULATE ( MAX ( fIPCA[acumulado_12m] ), fIPCA[data] = UltimaData )

IPCA Acumulado no Período =
PRODUCTX ( fIPCA, 1 + fIPCA[variacao_mensal] / 100 ) - 1''',
    ),
    _kit(
        "inpc", "🧾", "INPC: inflação mensal", "1736",
        "Série histórica do INPC, o índice usado em reajustes salariais: variação mensal e acumulado em 12 meses.",
        "Fato", "fINPC",
        "values/t/1736/n1/all/v/44,2292/p/all", "brasil", "mes",
        {"44": "variacao_mensal", "2292": "acumulado_12m"},
        observacao="Uma linha por mês, desde 1979. O acumulado em 12 meses não existe nos primeiros meses da série.",
        ponte="Use com a dCalendario do BI Data Generator para comparar a evolução de salários ou preços de uma "
              "base gerada com a inflação medida pelo INPC.",
        visuais=["Linha do INPC acumulado em 12 meses", "IPCA x INPC no mesmo gráfico",
                 "Reajuste salarial x INPC do período"],
        dax='''INPC 12 Meses =
VAR UltimaData = MAX ( fINPC[data] )
RETURN
    CALCULATE ( MAX ( fINPC[acumulado_12m] ), fINPC[data] = UltimaData )''',
    ),
    _kit(
        "desemprego", "👷", "Taxa de desemprego por UF", "4099",
        "Taxa de desocupação trimestral de cada unidade da federação, pela PNAD Contínua.",
        "Fato", "fDesemprego",
        "values/t/4099/n3/all/v/4099/p/all", "uf", "trimestre", "taxa_desocupacao",
        observacao="Uma linha por UF e trimestre, desde 2012. A taxa é o percentual das pessoas de 14 anos ou mais na força de trabalho que estão desocupadas.",
        ponte="Cruze com as vendas por UF de uma base gerada no BI Data Generator para investigar se o desemprego "
              "acompanha a queda de faturamento em cada estado.",
        visuais=["Mapa da taxa de desemprego por UF", "Linha da taxa ao longo dos trimestres",
                 "Ranking das UFs no último trimestre"],
        dax='''Taxa de Desemprego = AVERAGE ( fDesemprego[taxa_desocupacao] )

Taxa no Último Trimestre =
VAR UltimoAno = MAX ( fDesemprego[ano] )
VAR UltimoTrimestre =
    CALCULATE ( MAX ( fDesemprego[trimestre] ), fDesemprego[ano] = UltimoAno )
RETURN
    CALCULATE (
        [Taxa de Desemprego],
        fDesemprego[ano] = UltimoAno,
        fDesemprego[trimestre] = UltimoTrimestre
    )''',
    ),
    _kit(
        "rendimento", "💵", "Rendimento médio do trabalho", "5436",
        "Rendimento médio mensal real do trabalho no Brasil, por trimestre, pela PNAD Contínua.",
        "Fato", "fRendimento",
        "values/t/5436/n1/all/v/5933/p/all", "brasil", "trimestre", "rendimento_medio_reais",
        observacao="Uma linha por trimestre, desde 2012. É o rendimento habitualmente recebido em todos os trabalhos, já corrigido pela inflação.",
        ponte="Serve de referência de poder de compra: compare o tíquete médio de uma base gerada no BI Data "
              "Generator com a evolução do rendimento médio.",
        visuais=["Linha do rendimento médio real", "Variação em relação ao mesmo trimestre do ano anterior",
                 "Rendimento médio x tíquete médio"],
        dax='''Rendimento Médio = AVERAGE ( fRendimento[rendimento_medio_reais] )''',
    ),
    _kit(
        "pib_trimestral", "🏦", "PIB trimestral do Brasil", "1846",
        "PIB do Brasil a preços de mercado, em valores correntes, por trimestre.",
        "Fato", "fPIBTrimestral",
        "values/t/1846/n1/all/v/585/p/all/c11255/90707", "brasil", "trimestre", "pib_milhoes_reais",
        inteiros=["pib_milhoes_reais"],
        observacao="Uma linha por trimestre, desde 1996. O valor vem em milhões de reais e não é corrigido pela inflação.",
        ponte="Dá o contexto macroeconômico de um painel: compare o crescimento do faturamento de uma base do "
              "BI Data Generator com o crescimento nominal do PIB.",
        visuais=["Colunas do PIB por trimestre", "PIB acumulado no ano", "Crescimento do faturamento x PIB"],
        dax='''PIB (R$ milhões) = SUM ( fPIBTrimestral[pib_milhoes_reais] )

PIB Mesmo Trimestre Ano Anterior =
VAR AnoAtual = MAX ( fPIBTrimestral[ano] )
RETURN
    CALCULATE ( [PIB (R$ milhões)], fPIBTrimestral[ano] = AnoAtual - 1 )''',
    ),
    _kit(
        "producao_agricola", "🌾", "Produção agrícola por UF", "5457",
        "Quantidade produzida e valor da produção de uma lavoura em cada UF, pela Produção Agrícola Municipal.",
        "Fato", "fProducaoAgricola",
        "values/t/5457/n3/all/v/214,215/p/«ANO»/c782/«PRODUTO»", "uf", "ano",
        {"214": "quantidade_t", "215": "valor_mil_reais"},
        dimensoes=[("Produto das lavouras temporárias e permanentes", "produto")],
        parametros=[
            {"chave": "PRODUTO", "nome_m": "Produto", "rotulo": "Produto", "opcoes": PRODUTOS},
            {"chave": "ANO", "nome_m": "Ano", "rotulo": "Ano", "opcoes": _ANOS("2025", "2024", "2023", "2022", "2021", "2020")},
        ],
        observacao="Quantidade em toneladas e valor em mil reais. Para outra lavoura, troque o código do produto no código gerado.",
        ponte="Bom para um projeto de agronegócio: gere uma base de vendas de insumos no BI Data Generator e "
              "relacione por UF para ver onde a produção justifica o esforço comercial.",
        visuais=["Mapa da produção por UF", "Ranking dos estados produtores", "Preço médio por tonelada por UF"],
        dax='''Quantidade (t) = SUM ( fProducaoAgricola[quantidade_t] )

Preço Médio por Tonelada (R$) =
DIVIDE ( SUM ( fProducaoAgricola[valor_mil_reais] ) * 1000, [Quantidade (t)] )''',
    ),
    _kit(
        "rebanhos", "🐄", "Rebanhos por UF", "3939",
        "Efetivo de um tipo de rebanho em cada UF, pela Pesquisa da Pecuária Municipal.",
        "Fato", "fRebanho",
        "values/t/3939/n3/all/v/105/p/«ANO»/c79/«REBANHO»", "uf", "ano", "cabecas", inteiros=["cabecas"],
        dimensoes=[("Tipo de rebanho", "rebanho")],
        parametros=[
            {"chave": "REBANHO", "nome_m": "Rebanho", "rotulo": "Rebanho", "opcoes": REBANHOS},
            {"chave": "ANO", "nome_m": "Ano", "rotulo": "Ano", "opcoes": _ANOS("2025", "2024", "2023", "2022", "2021", "2020")},
        ],
        observacao="O efetivo é contado em cabeças, na data de referência de 31 de dezembro de cada ano.",
        ponte="Combina com o kit Produção agrícola por UF em um painel de agronegócio, sobre a dimensão de UFs "
              "de uma base gerada no BI Data Generator.",
        visuais=["Mapa do rebanho por UF", "Participação de cada UF no total", "Evolução ao trocar o ano"],
        dax='''Cabeças = SUM ( fRebanho[cabecas] )

Participação da UF =
DIVIDE ( [Cabeças], CALCULATE ( [Cabeças], ALL ( fRebanho[uf_id], fRebanho[uf_nome] ) ) )''',
    ),
    _kit(
        "alfabetizacao", "📚", "Taxa de alfabetização por município", "9543",
        "Taxa de alfabetização das pessoas de 15 anos ou mais em cada município, no Censo 2022.",
        "Fato", "fAlfabetizacao",
        "values/t/9543/n6/all/v/2513/p/2022", "municipio", "ano", "taxa_alfabetizacao",
        observacao="Uma linha por município, com o total da população (todos os sexos, cores ou raças e idades).",
        ponte="Indicador social para enriquecer a dimensão de municípios: relacione por municipio_id e segmente "
              "os resultados de uma base do BI Data Generator por faixa de alfabetização.",
        visuais=["Mapa da taxa de alfabetização", "Os 20 municípios com menor taxa",
                 "Dispersão de alfabetização x PIB per capita"],
        dax='''Taxa de Alfabetização Média = AVERAGE ( fAlfabetizacao[taxa_alfabetizacao] )

Municípios Abaixo de 90% =
CALCULATE ( COUNTROWS ( fAlfabetizacao ), fAlfabetizacao[taxa_alfabetizacao] < 90 )''',
    ),
    _kit(
        "comercio", "🛒", "Vendas do comércio varejista", "8880",
        "Índice mensal de volume de vendas do comércio varejista no Brasil, pela Pesquisa Mensal de Comércio.",
        "Fato", "fComercio",
        "values/t/8880/n1/all/v/7169/p/all/c11046/56734", "brasil", "mes", "indice_volume",
        observacao="Número-índice com base 2022 = 100, sem ajuste sazonal. Serve para comparar variações, não valores em reais.",
        ponte="Referência de mercado para varejo: compare a variação das vendas de uma base gerada no BI Data "
              "Generator com a do comércio brasileiro no mesmo mês.",
        visuais=["Linha do índice de volume", "Variação contra o mesmo mês do ano anterior",
                 "Suas vendas x o varejo nacional, em base 100"],
        dax='''Índice de Volume = AVERAGE ( fComercio[indice_volume] )

Variação 12 Meses % =
VAR Anterior =
    CALCULATE ( [Índice de Volume], DATEADD ( dCalendario[Data], -1, YEAR ) )
RETURN
    DIVIDE ( [Índice de Volume] - Anterior, Anterior )''',
    ),
    _kit(
        "industria", "🏭", "Produção industrial", "8888",
        "Índice mensal de produção física da indústria geral no Brasil, pela Pesquisa Industrial Mensal.",
        "Fato", "fIndustria",
        "values/t/8888/n1/all/v/12606/p/all/c544/129314", "brasil", "mes", "indice_producao",
        observacao="Número-índice com base 2022 = 100, sem ajuste sazonal, para a indústria geral.",
        ponte="Referência de atividade para empresas industriais: acompanhe o indicador ao lado da produção ou "
              "do faturamento de uma base gerada no BI Data Generator.",
        visuais=["Linha do índice de produção", "Sazonalidade por mês do ano", "Sua produção x a indústria nacional"],
        dax='''Índice de Produção = AVERAGE ( fIndustria[indice_producao] )''',
    ),
]

# Traduções para o inglês (o código gerado não muda).
KITS_EN = {
    "censo2022": {
        "titulo": "2022 Census: population, area and density",
        "resumo": "Population, land area and population density of every Brazilian municipality in the 2022 Census.",
        "observacao": "One row per municipality (about 5,570). It is the official figure for 2022, a year without an annual estimate.",
        "ponte": "Relate it by the municipality code (municipio_id) to the Municipalities of Brazil kit. Over a dataset "
                 "generated in BI Data Generator, area and density help compare cities of different sizes.",
        "visuais": ["Population density map by municipality", "Population vs. area scatter plot", "Ranking of the densest cities"],
    },
    "pib_municipios": {
        "titulo": "GDP of Brazilian municipalities",
        "resumo": "Gross Domestic Product at current prices of every municipality, in thousands of reais.",
        "observacao": "Values are in thousands of reais. IBGE publishes municipal GDP about two years late.",
        "ponte": "Join it with the Population by municipality kit for the same year to compute GDP per capita, and "
                 "compare it with revenue by city from a dataset generated in BI Data Generator.",
        "visuais": ["GDP map by municipality", "The 20 largest municipal economies", "GDP per capita by state"],
        "parametros": {"ANO": {"rotulo": "Year", "opcoes": _ANOS_EN("2023", "2022", "2021", "2020", "2019", "2018")}},
    },
    "ipca": {
        "titulo": "IPCA: monthly inflation (Brazil)",
        "resumo": "Full history of IPCA, Brazil's official inflation index: monthly change, 12-month rate and index number.",
        "observacao": "One row per month, since 1979. The index number is the best choice to adjust values between two dates.",
        "ponte": "Relate the data column to BI Data Generator's dCalendario to deflate revenue: divide the index "
                 "number of the reference month by the one of the sale month.",
        "visuais": ["Line of the 12-month rate", "Columns of monthly change in the last year", "Nominal vs. inflation-adjusted revenue"],
    },
    "inpc": {
        "titulo": "INPC: monthly inflation (Brazil)",
        "resumo": "History of INPC, the index used for wage adjustments in Brazil: monthly change and 12-month rate.",
        "observacao": "One row per month, since 1979. The 12-month rate does not exist for the first months of the series.",
        "ponte": "Use it with BI Data Generator's dCalendario to compare the evolution of wages or prices in a "
                 "generated dataset with inflation measured by INPC.",
        "visuais": ["Line of INPC 12-month rate", "IPCA vs. INPC on the same chart", "Wage adjustment vs. INPC in the period"],
    },
    "desemprego": {
        "titulo": "Unemployment rate by Brazilian state",
        "resumo": "Quarterly unemployment rate of each Brazilian state, from the Continuous PNAD survey.",
        "observacao": "One row per state and quarter, since 2012. The rate is the share of people aged 14 or over in the labour force who are unemployed.",
        "ponte": "Cross it with sales by state from a dataset generated in BI Data Generator to investigate whether "
                 "unemployment follows revenue drops in each state.",
        "visuais": ["Unemployment rate map by state", "Line of the rate over the quarters", "State ranking in the latest quarter"],
    },
    "rendimento": {
        "titulo": "Average labour income (Brazil)",
        "resumo": "Real average monthly labour income in Brazil, by quarter, from the Continuous PNAD survey.",
        "observacao": "One row per quarter, since 2012. It is the income usually received from all jobs, already adjusted for inflation.",
        "ponte": "A purchasing-power reference: compare the average ticket of a dataset generated in BI Data "
                 "Generator with the evolution of average income.",
        "visuais": ["Line of real average income", "Change against the same quarter of the previous year", "Average income vs. average ticket"],
    },
    "pib_trimestral": {
        "titulo": "Quarterly GDP of Brazil",
        "resumo": "Brazil's GDP at market prices, in current values, by quarter.",
        "observacao": "One row per quarter, since 1996. Values are in millions of reais and are not adjusted for inflation.",
        "ponte": "It gives a dashboard its macroeconomic context: compare the revenue growth of a BI Data Generator "
                 "dataset with nominal GDP growth.",
        "visuais": ["Columns of GDP by quarter", "Year-to-date GDP", "Revenue growth vs. GDP"],
    },
    "producao_agricola": {
        "titulo": "Crop production by Brazilian state",
        "resumo": "Quantity produced and production value of a crop in each state, from the Municipal Agricultural Production survey.",
        "observacao": "Quantity in tonnes and value in thousands of reais. For another crop, change the product code in the generated code.",
        "ponte": "Good for an agribusiness project: generate an input-sales dataset in BI Data Generator and relate "
                 "it by state to see where production justifies the commercial effort.",
        "visuais": ["Production map by state", "Ranking of producing states", "Average price per tonne by state"],
        "parametros": {
            "PRODUTO": {"rotulo": "Crop", "opcoes": PRODUTOS_EN},
            "ANO": {"rotulo": "Year", "opcoes": _ANOS_EN("2025", "2024", "2023", "2022", "2021", "2020")},
        },
    },
    "rebanhos": {
        "titulo": "Livestock by Brazilian state",
        "resumo": "Herd size of a type of livestock in each state, from the Municipal Livestock survey.",
        "observacao": "The herd is counted in heads, on the reference date of 31 December of each year.",
        "ponte": "It pairs with the Crop production by state kit in an agribusiness dashboard, over the state "
                 "dimension of a dataset generated in BI Data Generator.",
        "visuais": ["Herd map by state", "Share of each state in the total", "Evolution when changing the year"],
        "parametros": {
            "REBANHO": {"rotulo": "Livestock", "opcoes": REBANHOS_EN},
            "ANO": {"rotulo": "Year", "opcoes": _ANOS_EN("2025", "2024", "2023", "2022", "2021", "2020")},
        },
    },
    "alfabetizacao": {
        "titulo": "Literacy rate by municipality (Brazil)",
        "resumo": "Literacy rate of people aged 15 or over in each municipality, in the 2022 Census.",
        "observacao": "One row per municipality, for the whole population (all sexes, colours or races and ages).",
        "ponte": "A social indicator to enrich the municipality dimension: relate by municipio_id and segment the "
                 "results of a BI Data Generator dataset by literacy band.",
        "visuais": ["Literacy rate map", "The 20 municipalities with the lowest rate", "Literacy vs. GDP per capita scatter plot"],
    },
    "comercio": {
        "titulo": "Retail sales (Brazil)",
        "resumo": "Monthly volume index of retail sales in Brazil, from the Monthly Trade Survey.",
        "observacao": "Index number with base 2022 = 100, not seasonally adjusted. Use it to compare changes, not values in reais.",
        "ponte": "A market reference for retail: compare the sales change of a dataset generated in BI Data "
                 "Generator with Brazilian retail in the same month.",
        "visuais": ["Line of the volume index", "Change against the same month of the previous year", "Your sales vs. national retail, base 100"],
    },
    "industria": {
        "titulo": "Industrial production (Brazil)",
        "resumo": "Monthly physical production index of general industry in Brazil, from the Monthly Industrial Survey.",
        "observacao": "Index number with base 2022 = 100, not seasonally adjusted, for general industry.",
        "ponte": "An activity reference for industrial companies: follow the indicator next to the production or "
                 "revenue of a dataset generated in BI Data Generator.",
        "visuais": ["Line of the production index", "Seasonality by month of the year", "Your production vs. national industry"],
    },
}
for _traducao in KITS_EN.values():
    _traducao["fonte"] = "IBGE (SIDRA)"
