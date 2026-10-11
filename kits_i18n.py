"""Traduções dos kits. O texto original, em português, fica em kits.py.

Cada idioma traz só os campos traduzidos; o que faltar usa o original.
Em "parametros", "opcoes" lista os rótulos na mesma ordem do kit.
"""

KITS = {
    "en": {
        "bcb": {
            "titulo": "Selic rate, IPCA inflation and US dollar",
            "fonte": "Central Bank of Brazil (SGS)",
            "resumo": "Official Brazilian time series for interest rates, inflation and the exchange rate, one row per date.",
            "observacao": "Daily series, such as the dollar, accept at most 10 years per query.",
            "ponte": "Generate a sales dataset in BI Data Generator and relate this table to dCalendario by date. "
                     "With IPCA you deflate revenue; with Selic you compare results against the cost of money.",
            "visuais": ["Line chart of the indicator over time", "Card with the latest value",
                        "Nominal revenue vs. revenue adjusted by IPCA"],
            "dax": '''Valor Mais Recente =
VAR UltimaData = MAX ( fIndicador[data] )
RETURN
    CALCULATE ( MAX ( fIndicador[valor] ), fIndicador[data] = UltimaData )

-- Use with the monthly IPCA series
IPCA Acumulado =
PRODUCTX ( fIndicador, 1 + fIndicador[valor] / 100 ) - 1''',
            "parametros": {
                "SERIE": {"rotulo": "Series", "opcoes": [
                    "Selic target rate (% p.a.)", "IPCA, monthly (%)", "US dollar, selling rate (R$)"]},
                "DATA_INICIAL": {"rotulo": "Start date"},
                "DATA_FINAL": {"rotulo": "End date"},
            },
        },
        "cambio": {
            "titulo": "Daily exchange rates",
            "fonte": "Frankfurter (European Central Bank rates)",
            "resumo": "Daily rates of several currencies against a base currency, in long format.",
            "observacao": "Rates exist only for business days.",
            "ponte": "Generate a sales dataset in Brazilian reais in BI Data Generator and use this table to convert "
                     "revenue to dollars or euros by sale date.",
            "visuais": ["Line chart of the rate by currency", "Revenue in R$ vs. revenue in US$",
                        "Percentage change of the currency in the period"],
            "parametros": {
                "BASE": {"rotulo": "Base currency", "ajuda": "3-letter code, such as USD or EUR."},
                "MOEDAS": {"rotulo": "Quoted currencies", "ajuda": "3-letter codes separated by commas."},
                "DATA_INICIAL": {"rotulo": "Start date"},
                "DATA_FINAL": {"rotulo": "End date"},
            },
        },
        "feriados": {
            "titulo": "Brazilian national holidays",
            "resumo": "National holidays for each year, to enrich the calendar table.",
            "observacao": "Only national holidays; state and municipal ones are not included.",
            "ponte": "BI Data Generator already delivers dCalendario. Relate this table to it by date and create the "
                     "business-day column, to measure sales per business day and compare months fairly.",
            "visuais": ["Sales on holidays vs. regular days", "Average sales per business day in the month",
                        "Calendar with holidays highlighted"],
            "dax": '''-- Calculated column in dCalendario
É Dia Útil =
VAR Feriado = NOT ISEMPTY ( RELATEDTABLE ( dFeriado ) )
RETURN
    WEEKDAY ( dCalendario[Data], 2 ) <= 5 && NOT Feriado

Dias Úteis =
CALCULATE ( COUNTROWS ( dCalendario ), dCalendario[É Dia Útil] = TRUE () )''',
            "parametros": {
                "ANO_INICIAL": {"rotulo": "Start year"},
                "ANO_FINAL": {"rotulo": "End year"},
            },
        },
        "municipios": {
            "titulo": "Municipalities of Brazil",
            "fonte": "IBGE (localities API)",
            "resumo": "Every municipality with its IBGE code, state and region, ready to become a geography dimension.",
            "colunas": "municipality code and name, micro-region, meso-region, state and region",
            "observacao": "About 5,570 rows. The municipality's IBGE code is the best relationship key.",
            "ponte": "Use it as the geography dimension instead of a hand-typed city list. If the dataset generated "
                     "in BI Data Generator has city or state, relate by that field and get the "
                     "region > state > municipality hierarchy.",
            "visuais": ["Map by state or municipality", "Matrix with the region > state > municipality hierarchy",
                        "Ranking of municipalities by revenue"],
            "dax": '''Municípios = COUNTROWS ( dMunicipio )

-- Assuming a [Faturamento] measure in your model
Faturamento por Município =
DIVIDE ( [Faturamento], [Municípios] )''',
        },
        "populacao": {
            "titulo": "Population by municipality (Brazil)",
            "fonte": "IBGE (SIDRA, table 6579)",
            "resumo": "Estimated resident population of every Brazilian municipality in a given year.",
            "observacao": "About 5,570 rows per year. IBGE did not publish estimates for 2022 and 2023; "
                          "for 2022 use the Census. The query may take a few seconds.",
            "ponte": "Relate it to the Municipalities of Brazil kit by the municipality code (municipio_id) and use "
                     "the population to compute per-inhabitant indicators over a dataset generated in "
                     "BI Data Generator, such as revenue per capita by city or state.",
            "visuais": ["Municipality map with bubbles sized by population", "Ranking of the 20 largest cities",
                        "Revenue per inhabitant by state"],
            "dax": '''População = SUM ( fPopulacao[populacao] )

-- Assuming a [Faturamento] measure in your model
Faturamento per Capita =
DIVIDE ( [Faturamento], [População] )''',
            "parametros": {
                "PERIODO": {"rotulo": "Year", "opcoes": ["Latest", "2025", "2024", "2021", "2020", "2019", "2018"]},
            },
        },
        "clima": {
            "titulo": "Historical weather",
            "resumo": "Daily maximum and minimum temperature and rainfall for a Brazilian state capital.",
            "observacao": "The archive lags a few days behind; avoid dates from the last week. "
                          "For another city, change the latitude and longitude in the code.",
            "ponte": "Generate a sales dataset in BI Data Generator and join it with the weather by date: you can "
                     "investigate whether rainy or hot days change sales volume. It pairs well with the "
                     "Dados Causais tool.",
            "visuais": ["Sales vs. rainfall scatter plot", "Average temperature by month",
                        "Sales on rainy days vs. dry days"],
            "parametros": {
                "CIDADE": {"rotulo": "City"},
                "DATA_INICIAL": {"rotulo": "Start date"},
                "DATA_FINAL": {"rotulo": "End date"},
            },
        },
        "indicadores": {
            "titulo": "Country indicators",
            "fonte": "World Bank",
            "resumo": "GDP, population or inflation by country and year, to compare economies.",
            "observacao": "The most recent years may come without a value, because the World Bank publishes with a delay.",
            "ponte": "Good for a portfolio project with real data. Combine it with the Countries kit, which works "
                     "as the dimension, and ask for measures in BI Data Generator's Pergunte aos Dados.",
            "visuais": ["Line chart of the indicator by country", "Country ranking in the latest year",
                        "Percentage growth between two years"],
            "parametros": {
                "INDICADOR": {"rotulo": "Indicator", "opcoes": [
                    "GDP (current US$)", "Total population", "Annual inflation (%)"]},
                "PAISES": {"rotulo": "Countries", "ajuda": "2- or 3-letter codes separated by semicolons."},
                "ANO_INICIAL": {"rotulo": "Start year"},
                "ANO_FINAL": {"rotulo": "End year"},
            },
        },
        "paises": {
            "titulo": "Countries",
            "fonte": "World Bank",
            "resumo": "Country list with region, income level, capital and coordinates.",
            "observacao": "World Bank aggregates, such as \"World\" and \"Latin America\", are already removed.",
            "ponte": "It is the dimension for the Country indicators kit: relate by the pais_iso3 code. Then run "
                     "the model through BI Data Generator's Auditor de Modelo to check the relationships.",
            "visuais": ["Map with each country's capital", "Indicators grouped by region",
                        "Comparison between income levels"],
        },
        "terremotos": {
            "titulo": "Earthquakes worldwide",
            "fonte": "USGS (U.S. Geological Survey)",
            "resumo": "One event per row, with magnitude, place, date and coordinates for a map.",
            "observacao": "The API returns at most 20,000 events per query. Dates and times are in UTC.",
            "ponte": "A portfolio project with a map and real data. Build dCalendario in BI Data Generator and "
                     "relate it by event date to analyze by month and year.",
            "visuais": ["Bubble map sized by magnitude", "Events per month",
                        "The 10 largest earthquakes in the period"],
            "parametros": {
                "MAGNITUDE_MINIMA": {"rotulo": "Minimum magnitude", "opcoes": ["5.0", "4.5", "6.0", "7.0"]},
                "DATA_INICIAL": {"rotulo": "Start date"},
                "DATA_FINAL": {"rotulo": "End date"},
            },
        },
        "deputados": {
            "titulo": "Brazilian federal deputies",
            "fonte": "Chamber of Deputies (Open Data)",
            "resumo": "Sitting deputies with party and state, for politics and public-data analyses.",
            "observacao": "The same API has expenses, votes and bills, which work as fact tables.",
            "ponte": "A starting point for a public-data project: this table is the dimension, and parliamentary "
                     "allowance expenses come in as the fact. Use BI Data Generator's Formatador DAX e M to keep "
                     "the queries tidy as the project grows.",
            "visuais": ["Deputies by party", "Map of deputies by state", "Cards with photos using urlFoto"],
        },
    },
}

# Kits do IBGE gerados em kits_ibge.py.
from kits_ibge import KITS_EN as _IBGE_EN  # noqa: E402

KITS["en"].update(_IBGE_EN)
