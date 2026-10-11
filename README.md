# API Atlas

Diretório de APIs públicas e gratuitas, com consultas prontas para Power BI. Feito em Python com Streamlit.

**Acesse:** https://atlasapi.streamlit.app/

Em outubro de 2026 o catálogo reúne mais de 3.100 APIs em 56 categorias. Os números aparecem no topo do site e mudam sozinhos conforme as fontes são atualizadas.

## O que o site oferece

O site tem quatro abas.

### Catálogo de APIs

- Busca global por nome, descrição, categoria e autenticação, em português e em inglês.
- Navegação por categoria, com a quantidade de APIs em cada uma.
- Cartões em grade com descrição, autenticação, HTTPS, CORS e link para a documentação.
- Resultados paginados de 24 em 24.

### Kits Power BI

22 kits de APIs que não exigem cadastro nem chave. Em cada kit a pessoa ajusta os parâmetros (período, cidade, moeda, produto) e recebe:

- a consulta em **Power Query (M)**, com colunas nomeadas e tipadas, no formato `RelativePath` que o Power BI Service aceita na atualização agendada;
- o mesmo resultado em **Python** (`requests` + `pandas`);
- uma **prévia dos dados**, com download em CSV;
- o papel da tabela no modelo (fato ou dimensão), ideias de visuais e medidas DAX iniciais;
- como combinar os dados com uma base criada no [BI Data Generator](https://ai-bidatagenerator.streamlit.app/).

| Tema | Kits | Fonte |
|---|---|---|
| Economia do Brasil | Selic, IPCA e dólar | Banco Central (SGS) |
| | IPCA: inflação mensal · INPC: inflação mensal · PIB trimestral do Brasil · Vendas do comércio varejista · Produção industrial | IBGE (SIDRA) |
| Trabalho e renda | Taxa de desemprego por UF · Rendimento médio do trabalho | IBGE (SIDRA) |
| Municípios | Municípios do Brasil · População por município · Censo 2022: população, área e densidade · PIB dos municípios · Taxa de alfabetização por município | IBGE |
| Agronegócio | Produção agrícola por UF · Rebanhos por UF | IBGE (SIDRA) |
| Calendário e clima | Feriados nacionais · Clima histórico | BrasilAPI · Open-Meteo |
| Política | Deputados federais | Câmara dos Deputados |
| Internacional | Câmbio diário · Indicadores de países · Países · Terremotos no mundo | Frankfurter · Banco Mundial · USGS |

Os kits por município usam o código IBGE do município (`municipio_id`) e se relacionam entre si por ele.

### Montador de Projeto

Junta vários kits em um projeto do Power BI (`.pbip`) pronto para abrir. A pessoa escolhe os kits e baixa um `.zip` com:

- uma consulta em Power Query por tabela;
- a tabela calendário (`dCalendario`) e as dimensões compartilhadas de municípios (`dCenso2022`) e de UFs (`dUF`), incluídas quando necessárias;
- os relacionamentos entre as chaves em comum (`data`, `municipio_id`, `uf_id`, `pais_iso3`);
- as medidas DAX de cada kit, inclusive as que só fazem sentido quando dois kits estão juntos, como PIB per capita;
- uma página de relatório por kit, com cartões, gráficos e tabelas iniciais, mais uma página de resumo;
- uma capa com o título do projeto, os números do modelo, as páginas agrupadas por tema e as fontes dos dados;
- um design por tema: cada página tem cabeçalho, cor de destaque e fundo próprios do tema do kit (economia, trabalho e renda, municípios, agronegócio, calendário e clima, internacional);
- as consultas em `.pq`, os scripts em Python e as medidas em `.dax`, para reaproveitar em outro arquivo.

Participam 20 dos 22 kits; ficam fora "Municípios do Brasil" e "Deputados federais", cujas colunas vêm direto da API, sem nomes fixos.

### Gerador Python

Para as demais APIs do catálogo: cole a URL de um endpoint que devolve JSON e receba o script em `requests` + `pandas`, com opção de chave de API no cabeçalho ou na URL.

## Idiomas

A interface está em português e em inglês, com seletor no topo. O idioma inicial é escolhido nesta ordem:

1. `?lang=pt` ou `?lang=en` na URL, útil para compartilhar o link já no idioma certo;
2. idioma do navegador;
3. país de acesso, pelo cabeçalho `CF-IPCountry` da Cloudflare (só existe se o app estiver atrás da Cloudflare);
4. inglês.

O que é traduzido:

- **Interface:** todos os textos ficam em `i18n.py`.
- **Catálogo:** categorias e descrições das APIs são traduzidas pelo `catalog_pt.json`, que usa o texto original como chave. APIs novas, ou com a descrição alterada na origem, aparecem em inglês até entrarem nesse arquivo. O `catalog_en.json` faz o caminho inverso para a fonte que vem em português.
- **Kits:** o original fica em português (`kits.py` e `kits_ibge.py`) e a versão em inglês em `kits_i18n.py` e `kits_ibge.py`.

O código gerado pelos kits usa nomes de tabelas e colunas em português nos dois idiomas.

## Fontes do catálogo

O catálogo é montado ao vivo a partir de sete repositórios do GitHub, com cache de 30 minutos.

| Fonte | Papel |
|---|---|
| [public-apis/public-apis](https://github.com/public-apis/public-apis) | Fonte principal |
| [marcelscruz/public-apis](https://github.com/marcelscruz/public-apis) | APIs que a principal não tem |
| [public-api-lists/public-api-lists](https://github.com/public-api-lists/public-api-lists) | APIs que as anteriores não têm |
| [IF-TI/APIs-PublicasBrasil](https://github.com/IF-TI/APIs-PublicasBrasil) | APIs brasileiras |
| [n0shake/Public-APIs](https://github.com/n0shake/Public-APIs) | APIs de grandes empresas |
| [APIs-guru/graphql-apis](https://github.com/APIs-guru/graphql-apis) | APIs em GraphQL |
| [jdorfman/awesome-json-datasets](https://github.com/jdorfman/awesome-json-datasets) | Endereços que devolvem JSON sem autenticação |

Como as fontes são unidas (`catalog.py`):

- A fonte principal entra inteira. As demais só acrescentam o que é novo, na ordem da tabela.
- É duplicata o item com o mesmo nome, o mesmo endereço ou o mesmo domínio de outro já listado. Domínios que hospedam muitas APIs, como github.com, não contam para a última regra.
- As categorias de cada fonte são convertidas para as do site.
- Itens de conteúdo adulto são descartados.
- Se uma fonte extra ficar fora do ar, o site continua com as demais e mostra um aviso.

Algumas fontes não informam autenticação, HTTPS ou CORS; nesses cartões o campo aparece como "Não informado". Essas informações podem mudar e devem ser confirmadas na documentação de cada API.

## Estrutura do projeto

```text
├── app.py              Página: topo, abas, busca, categorias e cartões
├── catalog.py          Leitura e união das fontes do catálogo
├── catalog_pt.json     Tradução de categorias e descrições para o português
├── catalog_en.json     Tradução para o inglês das descrições que vêm em português
├── kits.py             Kits Power BI, Gerador Python e as telas dessas abas
├── kits_ibge.py        Kits do IBGE, gerados a partir da descrição de cada tabela do SIDRA
├── kits_i18n.py        Tradução dos kits para o inglês
├── montador.py         Montador de Projeto: gera o projeto Power BI (.pbip) a partir dos kits
├── i18n.py             Textos da interface, seletor e detecção de idioma
├── style.css           Visual do site
├── requirements.txt    Dependências
└── .streamlit/
    └── config.toml     Tema do Streamlit
```

## Executar localmente

Requer Python 3.10 ou mais novo.

Windows:

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

macOS ou Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

O app precisa de internet para baixar o catálogo do GitHub e para a prévia dos kits.

## Publicar no Streamlit Community Cloud

1. Acesse https://share.streamlit.io/ e conecte sua conta do GitHub.
2. Escolha este repositório e defina `app.py` como arquivo principal.
3. Publique. A cada merge na `main`, o site se atualiza sozinho.

## Como ampliar

**Novo kit do IBGE.** Acrescente uma chamada a `_kit(...)` em `kits_ibge.py` com o caminho da consulta no SIDRA, o nível territorial (`municipio`, `uf` ou `brasil`), o tipo de período (`ano`, `mes` ou `trimestre`) e as medidas. O Power Query e o Python são gerados a partir disso. Inclua a tradução em `KITS_EN`, no mesmo arquivo.

**Novo kit de outra API.** Acrescente um item à lista `KITS` em `kits.py`, com os modelos de código em M e em Python. Os parâmetros entram como marcadores no formato `«NOME»`.

**Nova fonte do catálogo.** Acrescente um item a `EXTRAS` em `catalog.py`. Se o formato for diferente dos existentes, escreva um leitor e registre-o em `PARSERS`.

**Novo idioma.** Inclua o código em `SUPPORTED` e as traduções em `STRINGS`, no `i18n.py`; crie o `catalog_<idioma>.json`; e acrescente os textos dos kits em `kits_i18n.py`.

## Créditos

O catálogo existe graças ao trabalho das comunidades que mantêm os sete repositórios listados em "Fontes do catálogo". Os dados dos kits vêm de IBGE, Banco Central do Brasil, Câmara dos Deputados, BrasilAPI, Open-Meteo, Frankfurter, Banco Mundial e USGS.
