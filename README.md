# API Atlas

Diretório de APIs públicas e gratuitas, com consultas prontas para Power BI. Feito em Python com Streamlit.

**Acesse:** https://atlasapi-delta.vercel.app/

Em outubro de 2026 o catálogo reúne mais de 3.100 APIs em 56 categorias. Os números aparecem no topo do site e mudam sozinhos conforme as fontes são atualizadas.

## O que o site oferece

O site tem cinco abas.

### Catálogo de APIs

- Busca global por nome, descrição, categoria e autenticação, em português e em inglês.
- Navegação por categoria, com a quantidade de APIs em cada uma.
- Cartões em grade com descrição, autenticação, HTTPS, CORS e link para a documentação.
- Resultados paginados de 24 em 24.
- Script Python pronto, recolhido no próprio cartão, para os endereços que devolvem JSON direto e sem autenticação (fonte awesome-json-datasets).

### Pergunta → Projeto

A pessoa escreve uma pergunta de negócio, como "Os estados com mais desemprego são os de menor renda? Como isso mudou desde 2020?", e recebe o projeto do Power BI montado para respondê-la:

- os kits que respondem à pergunta, escolhidos por palavras-chave (desemprego, renda, inflação, PIB, safra, rebanho, clima, câmbio, países…);
- as opções citadas, como produto agrícola, rebanho, cidade, moedas e países;
- o período citado ("desde 2020", "entre 2018 e 2023", "últimos 5 anos", "em 2024") aplicado aos kits que têm período;
- uma página "Sua pergunta", com a pergunta no título, os cartões principais e os gráficos dos kits escolhidos, além das páginas do Montador.

A tela mostra o que foi entendido e por quê, e deixa incluir ou retirar kits antes de baixar. Esta versão não usa IA: as regras ficam em `pergunta.py`.

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
- as medidas DAX de cada kit, inclusive as que só fazem sentido quando dois kits estão juntos, como PIB per capita, reunidas na tabela `Medidas` em pastas por tema e, dentro delas, subpastas por kit;
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
├── pergunta.py         Pergunta → Projeto: lê a pergunta e escolhe kits, opções e período
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


## API HTTP (Vercel)

Além do app Streamlit, este repositório contém uma API HTTP serverless na pasta `api/`, publicada pela Vercel. Ela expõe o catálogo, a configuração dos kits Power BI, a geração de consultas e scripts, a prévia dos dados e a montagem de projetos. Os endpoints não exigem autenticação.

Defina `BASE_URL` como o domínio atribuído ao deployment da Vercel, sem a barra final. Por exemplo:

```bash
export BASE_URL="https://seu-deployment.vercel.app"
```

Os exemplos abaixo usam `curl` e pressupõem que o deployment está ativo. Para chamadas `POST`, envie JSON com `Content-Type: application/json`. Os campos `lang` aceitam `pt` ou `en`; quando omitidos, é usada a configuração padrão da aplicação. O corpo das requisições tem limite de 200 KB.

### `GET /api/config`

Retorna os idiomas disponíveis, textos da interface, APIs em destaque, definição completa dos kits e seus parâmetros. Use `lang=pt` ou `lang=en`. Com `lang=auto` (padrão), o idioma é detectado pelos cabeçalhos da requisição.

```bash
curl "$BASE_URL/api/config?lang=pt"
```

A resposta inclui `lang`, `idiomas`, `textos`, `destaques`, `kits`, `bdg` e `padrao_montador`. Cada kit contém seu `id`, descrição, fonte, colunas, parâmetros e a indicação `montavel`. Consulte esta resposta para descobrir os IDs de kit e os parâmetros aceitos em `valores` — por exemplo, os parâmetros do kit `bcb` incluem `SERIE`, `DATA_INICIAL` e `DATA_FINAL`.

### `GET /api/catalogo`

Retorna o catálogo unificado de APIs. O parâmetro opcional `lang` aceita `pt` ou `en`.

```bash
curl "$BASE_URL/api/catalogo?lang=pt"
```

A resposta tem a forma `{"apis": [...], "aviso": "..."}`. Cada item pode incluir `n` (nome), `u` (URL), `c` (categoria), `d` (descrição), `a` (autenticação), `h` (HTTPS), `o` (CORS) e, quando disponível, `s` (script Python). Os campos `d0` e `c0` preservam a descrição e categoria originais quando foram traduzidas. Se uma fonte adicional estiver indisponível, `aviso` informa a falha parcial; uma falha ao carregar a fonte principal retorna status HTTP 503 e um objeto com `erro`, `dica` e `apis`.

### `POST /api/codigo`

Gera os códigos Power Query (M) e Python de um kit a partir dos parâmetros informados.

```bash
curl -X POST "$BASE_URL/api/codigo" \
  -H "Content-Type: application/json" \
  -d '{
    "kit": "bcb",
    "valores": {
      "SERIE": 432,
      "DATA_INICIAL": "2024-01-01",
      "DATA_FINAL": "2024-12-31"
    },
    "lang": "pt"
  }'
```

`kit` é o ID do kit, `valores` é um objeto cujas chaves são definidas pelos parâmetros retornados em `/api/config`, e `lang` é opcional. A resposta de sucesso contém `m` (consulta Power Query) e `python` (script Python). Em caso de erro de validação, a resposta pode conter `erro`; kit desconhecido ou payload malformado pode resultar em HTTP 400.

### `POST /api/previa`

Executa o script Python gerado para um kit e retorna uma prévia dos dados. A execução consulta a API externa de origem do kit, portanto depende da disponibilidade dessa fonte.

```bash
curl -X POST "$BASE_URL/api/previa" \
  -H "Content-Type: application/json" \
  -d '{
    "kit": "bcb",
    "valores": {
      "SERIE": 432,
      "DATA_INICIAL": "2024-01-01",
      "DATA_FINAL": "2024-01-31"
    },
    "lang": "pt"
  }'
```

A resposta de sucesso contém `resumo`, `colunas`, `linhas`, `csv` e `arquivo`. A tabela é limitada a 200 linhas em `linhas`; `csv` contém o CSV completo somente quando ele não ultrapassa 8 MB, caso contrário é `null`. Se a API externa falhar, a resposta traz `falha` e `detalhe`. Erros de validação retornam `erro`; kit desconhecido pode resultar em HTTP 400.

### `POST /api/projeto`

Gera um resumo do modelo do projeto Power BI ou, com `baixar: true`, baixa o projeto compactado em ZIP. `kits` é uma lista de objetos com `id` e, opcionalmente, `valores`. No máximo 30 escolhas válidas são consideradas. `titulo` é opcional e limitado a 60 caracteres; `lang` também é opcional.

Para obter o resumo JSON:

```bash
curl -X POST "$BASE_URL/api/projeto" \
  -H "Content-Type: application/json" \
  -d '{
    "titulo": "Indicadores econômicos",
    "kits": [
      {
        "id": "bcb",
        "valores": {
          "SERIE": 433,
          "DATA_INICIAL": "2024-01-01",
          "DATA_FINAL": "2024-12-31"
        }
      }
    ],
    "lang": "pt"
  }'
```

O resumo contém `tabelas`, `relacionamentos`, `medidas`, `paginas` e `avisos`. Para baixar o ZIP, acrescente `"baixar": true` ao mesmo corpo. A resposta será `application/zip`, com o nome do projeto no header `Content-Disposition`; use `curl -o projeto.zip` para salvar o arquivo. Erros de montagem retornam HTTP 400 com `{"erro": "..."}`.

```bash
curl -X POST "$BASE_URL/api/projeto" \
  -H "Content-Type: application/json" \
  -o projeto.zip \
  -d '{"titulo":"Indicadores econômicos","kits":[{"id":"bcb","valores":{"SERIE":433,"DATA_INICIAL":"2024-01-01","DATA_FINAL":"2024-12-31"}}],"baixar":true,"lang":"pt"}'
```

### `POST /api/script`

Gera um script Python genérico para consultar um endpoint JSON. Este endpoint gera o código, mas não executa a consulta.

```bash
curl -X POST "$BASE_URL/api/script" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://api.example.com/v1/items",
    "caminho": "data.items",
    "autenticacao": "header",
    "nome_chave": "X-API-Key",
    "csv": true,
    "lang": "pt"
  }'
```

Campos: `url` (URL do endpoint), `caminho` (caminho opcional até a lista/objeto de dados no JSON), `autenticacao` (`none`, `header` ou `query`), `nome_chave` (nome do cabeçalho ou parâmetro de query da chave) e `csv` (se o script gerado deve incluir exportação CSV). A resposta de sucesso contém `codigo`; se a URL ou as opções forem inválidas, pode conter `erro`.

### Cache e implantação

`/api/config` e `/api/catalogo` usam cache na borda para respostas com idioma explícito; o catálogo tem cache de borda de 30 minutos e a configuração, de 24 horas. A configuração com `lang=auto` não é armazenada em cache compartilhado. Respostas de geração e downloads não são armazenados em cache. Para publicar ou atualizar os endpoints, conecte o repositório à Vercel e faça o deploy do projeto; a configuração de funções está em `vercel.json` e as dependências Python da API em `pyproject.toml`.
