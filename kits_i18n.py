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
        "previsao_clima": {
            "titulo": "Weather forecast",
            "resumo": "Daily temperature and precipitation forecasts for up to 16 days in a Brazilian state capital.",
            "observacao": "The free API provides forecasts for up to 16 days. Forecasts change with each update and are not observed historical data.",
            "ponte": "Relate date to dCalendario and use the forecast to plan sales, inventory or staffing for the coming days.",
            "visuais": ["Forecast maximum temperature by day", "Forecast precipitation by day", "Days with the highest forecast precipitation"],
            "parametros": {"CIDADE": {"rotulo": "City"}, "DIAS": {"rotulo": "Forecast days", "opcoes": ["7 days", "10 days", "16 days"]}},
        },
        "livros": {
            "titulo": "Books by subject",
            "resumo": "Works matching a subject, with author, first publication year and edition count.",
            "observacao": "Search results are relevant works, not every edition. The search schema can change; check the documentation if a field disappears.",
            "ponte": "Compare works by first publication year and frequent authors. The limit avoids loading excessive results on refresh.",
            "visuais": ["Works by first publication year", "Works by author", "Editions per work"],
            "parametros": {"CONSULTA": {"rotulo": "Subject or term", "ajuda": "Use 2 to 80 letters, numbers or spaces."}, "LIMITE": {"rotulo": "Maximum works", "opcoes": ["25 works", "50 works", "100 works"]}},
        },
        "crossref": {
            "titulo": "Scholarly publications by subject",
            "resumo": "Metadata for articles, books and other scholarly works, with publisher, type, year and citations.",
            "observacao": "No registration is required. Search returns relevance-ranked results up to the selected limit; metadata and citations are supplied by depositors.",
            "ponte": "Analyze yearly publication and citation counts for a topic. Relate date to dCalendario and compare terms, publishers or work types in separate queries.",
            "visuais": ["Publications by year", "Citations by year", "Publications by publisher"],
            "parametros": {
                "CONSULTA": {"rotulo": "Subject or term", "ajuda": "Use 2 to 80 letters, numbers or spaces."},
                "ANO_INICIAL": {"rotulo": "Start year"}, "ANO_FINAL": {"rotulo": "End year"},
                "LIMITE": {"rotulo": "Maximum records", "opcoes": ["25 records", "50 records", "100 records"]},
            },
        },
    },
}

# Kits do IBGE gerados em kits_ibge.py.
KITS["en"].update({
    "focus": {
        "titulo": "Market expectations (Focus survey)",
        "resumo": "What the market expects for IPCA, GDP, Selic, the exchange rate and IGP-M each year, day by day.",
        "observacao": "Each row is the Focus statistic on a date for a reference year, based on all respondents in the last 30 days (baseCalculo = 0).",
        "ponte": "Compare expectations with what happened: combine this kit with IPCA or Selic and show the gap between the forecast and the outcome.",
        "visuais": ["Median expectation by reference year over time", "Range between minimum and maximum", "Card with the latest expectation"],
        "parametros": {
            "INDICADOR": {"rotulo": "Indicator", "opcoes": ["IPCA (inflation)", "Total GDP", "Selic", "Exchange rate", "IGP-M"]},
            "DATA_INICIAL": {"rotulo": "Start date"},
        },
    },
    "ipea": {
        "titulo": "Ipeadata series (Brazil)",
        "resumo": "Monthly series from Ipeadata: IGP-M, minimum wage, monthly Selic and average dollar rate.",
        "observacao": "Ipeadata has thousands of series. To use another one, change the series code (SERCODIGO) in the query; codes are listed at ipeadata.gov.br.",
        "ponte": "The real minimum wage is great for deflating values from a BI Data Generator dataset and comparing periods in reais of equal purchasing power.",
        "visuais": ["Series over time", "Card with the latest value", "12-month change"],
        "parametros": {
            "SERIE": {"rotulo": "Series", "opcoes": ["IGP-M (% per month)", "Minimum wage in force (R$)", "Real minimum wage (R$ of latest month)",
                                                    "Selic accumulated in the month (% per month)", "Commercial dollar, monthly average (R$)"]},
        },
    },
    "cripto": {
        "titulo": "Cryptocurrencies in Brazilian reais",
        "resumo": "Daily open, high, low, close and volume of cryptocurrencies in reais.",
        "observacao": "Prices from the Mercado Bitcoin exchange, in daily candles (UTC). Volume is in the cryptocurrency itself.",
        "ponte": "Use it as a price series to practice investment analysis: return, volatility and comparison with the dollar (Daily exchange rates kit) on the same dCalendario.",
        "visuais": ["Closing price line", "Daily volume columns", "Change over the period"],
        "parametros": {
            "MOEDA": {"rotulo": "Cryptocurrency"},
            "DATA_INICIAL": {"rotulo": "Start date"}, "DATA_FINAL": {"rotulo": "End date"},
        },
    },
    "feriados_mundo": {
        "titulo": "Public holidays worldwide",
        "resumo": "Public holidays for over 100 countries by year, with local name, English name and scope.",
        "observacao": "Scope \"Regional\" means the holiday applies only to part of the country. Countries outside Nager.Date coverage return no data.",
        "ponte": "For companies operating in several countries: flag non-working days per country and relate pais_iso2 to the Countries kit dimension.",
        "visuais": ["Holidays by country", "Holiday list", "Holidays by month"],
        "parametros": {
            "PAISES": {"rotulo": "Countries", "ajuda": "2-letter codes separated by semicolons, such as US;AR;PT."},
            "ANO_INICIAL": {"rotulo": "Start year"}, "ANO_FINAL": {"rotulo": "End year"},
        },
    },
    "owid": {
        "titulo": "Our World in Data",
        "resumo": "Life expectancy, GDP per capita, CO₂ emissions, internet use and population for every country, year by year.",
        "observacao": "Only countries (3-letter code) are kept; regions and aggregates such as \"World\" are dropped. Our World in Data charts are CC BY: credit the source in the report.",
        "ponte": "Combine with the Countries kit, which works as a dimension through pais_iso3, and with World Bank indicators to compare Brazil with the rest of the world.",
        "visuais": ["Country ranking in the latest year", "Average across countries by year", "Map by country"],
        "parametros": {
            "GRAFICO": {"rotulo": "Indicator", "opcoes": ["Life expectancy (years)", "GDP per capita (2021 PPP US$)",
                                                         "CO₂ emissions per capita (t)", "Internet use (% of population)", "Population"]},
            "ANO_INICIAL": {"rotulo": "Start year"},
        },
    },
})

from kits_ibge import KITS_EN as _IBGE_EN  # noqa: E402

KITS["en"].update(_IBGE_EN)
