# API Atlas

Diretório de APIs públicas e gratuitas, com consultas prontas para Power BI. Feito em Python e publicado na Vercel.

**Acesse:** https://atlasapi-delta.vercel.app/

O catálogo combina fontes públicas de APIs e especificações OpenAPI, com meta de até 10.000 registros únicos após deduplicação. O total real aparece no topo do site e varia conforme a disponibilidade e a atualização das fontes.

## Duas versões, o mesmo código

| Versão | Onde roda | Abas |
|---|---|---|
| **Site publicado** (`index.html` + funções em `api/`) | Vercel, em https://atlasapi-delta.vercel.app/ | Catálogo de APIs · Kits Power BI · Montador de Projeto · Gerador Python |
| **App Streamlit** (`app.py`) | Na sua máquina, com `streamlit run app.py` | As quatro acima e mais **Pergunta → Projeto** |

As duas usam os mesmos módulos de lógica (`catalog.py`, `kits.py`, `kits_extra.py`, `kits_ibge.py`, `montador.py`, `i18n.py`); uma mudança nesses arquivos vale para as duas.

## O que o site oferece

### Catálogo de APIs

- Busca global por nome, descrição, categoria e autenticação, em português e em inglês.
- Navegação por categoria, com a quantidade de APIs em cada uma.
- Cartões em grade com descrição, autenticação, HTTPS, CORS e link para a documentação.
- Resultados paginados de 24 em 24.
- Script Python pronto, recolhido no próprio cartão, para os endereços que devolvem JSON direto e sem autenticação (fonte awesome-json-datasets).

### Pergunta → Projeto (só no app Streamlit)

A pessoa escreve uma pergunta de negócio, como "Os estados com mais desemprego são os de menor renda? Como isso mudou desde 2020?", e recebe o projeto do Power BI montado para respondê-la:

- os kits que respondem à pergunta, escolhidos por palavras-chave (desemprego, renda, inflação, PIB, safra, rebanho, clima, câmbio, países…);
- as opções citadas, como produto agrícola, rebanho, cidade, moedas e países;
- o período citado ("desde 2020", "entre 2018 e 2023", "últimos 5 anos", "em 2024") aplicado aos kits que têm período;
- uma página "Sua pergunta", com a pergunta no título, os cartões principais e os gráficos dos kits escolhidos, além das páginas do Montador.

A tela mostra o que foi entendido e por quê, e deixa incluir ou retirar kits antes de baixar. Esta versão não usa IA: as regras ficam em `pergunta.py`.

### Kits Power BI

33 kits de APIs que não exigem cadastro nem chave. Em cada kit a pessoa ajusta os parâmetros (período, cidade, moeda, produto, assunto) e recebe:

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
| Calendário e clima | Feriados nacionais · Clima histórico · Previsão do tempo para até 16 dias · Qualidade do ar | BrasilAPI · Open-Meteo |
| Política | Deputados federais | Câmara dos Deputados |
| Internacional | Câmbio diário · Indicadores de países · Países · Terremotos no mundo · Indicadores globais por país | Frankfurter · Banco Mundial · USGS |
| Mercado financeiro | Expectativas de mercado (Focus) · Séries do Ipeadata · Criptomoedas em reais | Banco Central (Olinda) · Ipea · Mercado Bitcoin |
| Mundo | Feriados no mundo · Our World in Data | Nager.Date · Our World in Data |
| Conhecimento e pesquisa | Livros por assunto · Publicações científicas por assunto · Visualizações de artigos da Wikipédia | Open Library · Crossref · Wikimedia |

Os kits por município usam o código IBGE do município (`municipio_id`) e se relacionam entre si por ele.

As consultas ao Banco Central (kits Selic, IPCA e dólar e Expectativas de mercado) enviam um cabeçalho `User-Agent` de navegador. Sem ele, o Banco Central redireciona o Power Query para `http://www.bcb.gov.br/` e a consulta falha com erro 404.

### Montador de Projeto

Junta vários kits em um projeto do Power BI (`.pbip`) pronto para abrir. A pessoa escolhe os kits e baixa um `.zip` com:

- uma consulta em Power Query por tabela;
- a tabela calendário (`dCalendario`) e as dimensões compartilhadas de municípios (`dCenso2022`) e de UFs (`dUF`), incluídas quando necessárias;
- os relacionamentos entre as chaves em comum (`data`, `municipio_id`, `uf_id`, `pais_iso3`, `pais_iso2`); os indicadores de países, o Our World in Data e os feriados no mundo se ligam à dimensão `dPais` quando o kit Países está no projeto;
- as medidas DAX de cada kit, inclusive as que só fazem sentido quando dois kits estão juntos, como PIB per capita, reunidas na tabela `Medidas` em pastas por tema e, dentro delas, subpastas por kit;
- uma página de relatório por kit, com cartões, gráficos e tabelas iniciais, mais uma página de resumo;
- uma capa com o título do projeto, os números do modelo, as páginas agrupadas por tema e as fontes dos dados;
- um design por tema: cada página tem cabeçalho, cor de destaque e fundo próprios do tema do kit (economia, trabalho e renda, municípios, agronegócio, calendário e clima, internacional, conhecimento e pesquisa); com mais de seis temas, a capa organiza os blocos em quatro por linha;
- as consultas em `.pq`, os scripts em Python e as medidas em `.dax`, para reaproveitar em outro arquivo.

Participam 28 dos 30 kits; ficam fora "Municípios do Brasil" e "Deputados federais", cujas colunas vêm direto da API, sem nomes fixos.

### Gerador Python

Para as demais APIs do catálogo: cole a URL de um endpoint que devolve JSON e receba o script em `requests` + `pandas`, com opção de chave de API no cabeçalho ou na URL.

### Experiência de uso no site

O site da Vercel segue sete leis de usabilidade:

- **Jakob** (o que as pessoas já conhecem): abas fixas no topo ao rolar, `/` leva à busca e `Esc` limpa, filtros com botão "✕".
- **Fitts** (alvos grandes e perto): fora do catálogo o topo encolhe; botão grande "Copiar código"; barra fixa com o botão de baixar no Montador.
- **Hick** (menos opções de cada vez): 12 categorias mais populares primeiro, com a lista completa a um clique; kits agrupados por tema na lista e no Montador.
- **Miller** (blocos menores): grupos por tema com contagem de kits marcados e total selecionado sempre à vista.
- **Postel** (tolerante com a entrada): busca por várias palavras em qualquer ordem e sem acentos; o Gerador Python completa o `https://`; o kit vai para o Montador com os mesmos parâmetros.
- **Pico-final** (bom fim de tarefa): ao copiar, um aviso diz onde colar; ao baixar o projeto, aparecem os próximos passos.
- **Estética-usabilidade**: atualização sem piscar a tela, foco visível no teclado e rodapé com links úteis.

## Idiomas

A interface está em português e em inglês, com seletor no topo. O idioma inicial é escolhido nesta ordem:

1. `?lang=pt` ou `?lang=en` na URL, útil para compartilhar o link já no idioma certo;
2. idioma do navegador;
3. país de acesso, pelo cabeçalho de país do provedor (`X-Vercel-IP-Country` na Vercel, `CF-IPCountry` na Cloudflare);
4. inglês.

O que é traduzido:

- **Interface:** todos os textos ficam em `i18n.py`.
- **Catálogo:** categorias e descrições das APIs são traduzidas pelo `catalog_pt.json`, que usa o texto original como chave. APIs novas, ou com a descrição alterada na origem, aparecem em inglês até entrarem nesse arquivo. O `catalog_en.json` faz o caminho inverso para a fonte que vem em português.
- **Kits:** o original fica em português (`kits.py`, `kits_extra.py` e `kits_ibge.py`) e a versão em inglês em `kits_i18n.py` e `kits_ibge.py`.

O código gerado pelos kits usa nomes de tabelas e colunas em português nos dois idiomas.

## Fontes do catálogo

O catálogo é montado ao vivo a partir de dez fontes públicas, com cache de 30 minutos e limite de 10.000 registros após deduplicação.

| Fonte | Papel |
|---|---|
| [public-apis/public-apis](https://github.com/public-apis/public-apis) | Fonte principal |
| [marcelscruz/public-apis](https://github.com/marcelscruz/public-apis) | APIs que a principal não tem |
| [public-api-lists/public-api-lists](https://github.com/public-api-lists/public-api-lists) | APIs que as anteriores não têm |
| [IF-TI/APIs-PublicasBrasil](https://github.com/IF-TI/APIs-PublicasBrasil) | APIs brasileiras |
| [n0shake/Public-APIs](https://github.com/n0shake/Public-APIs) | APIs de grandes empresas |
| [APIs-guru/graphql-apis](https://github.com/APIs-guru/graphql-apis) | APIs em GraphQL |
| [jdorfman/awesome-json-datasets](https://github.com/jdorfman/awesome-json-datasets) | Endereços que devolvem JSON sem autenticação |
| [dspinellis/awesome-rest-apis](https://github.com/dspinellis/awesome-rest-apis) | APIs REST abertas, sem cadastro ou pagamento, organizadas por tema |
| [APIs-guru/openapi-directory](https://github.com/APIs-guru/openapi-directory) | Diretório de definições OpenAPI; metadados lidos pela [API pública do projeto](https://apis.guru/api-doc/) |
| [API Directory](https://www.apidirectory.dev/) | Catálogo curado e índice amplo de especificações; a seleção é limitada e deduplicada para manter o site leve |

Como as fontes são unidas (`catalog.py`):

- A fonte principal entra inteira. As demais só acrescentam o que é novo, na ordem da tabela.
- É duplicata o item com o mesmo nome, o mesmo endereço ou, na maioria das fontes, o mesmo domínio de outro já listado. Fontes que reúnem vários serviços no mesmo host, como os conjuntos de dados e o diretório OpenAPI, podem manter APIs distintas do mesmo domínio.
- As categorias de cada fonte são convertidas para as do site.
- Itens de conteúdo adulto são descartados.
- Se uma fonte extra ficar fora do ar, o site continua com as demais e mostra um aviso.

Os diretórios APIs.guru e API Directory incluem APIs e especificações documentadas; algumas podem exigir cadastro ou pagamento, e uma especificação não garante que o serviço esteja ativo ou que tenha endpoint público sem autenticação. Seus links apontam para as especificações OpenAPI, não necessariamente para endpoints de dados prontos para consulta. Quando a definição não informa autenticação, o cartão mostra "Não informado". Confira a documentação e o endpoint antes de usar o Gerador Python.

Algumas fontes não informam autenticação, HTTPS ou CORS; nesses cartões o campo aparece como "Não informado". Essas informações podem mudar e devem ser confirmadas na documentação de cada API.

## Estrutura do projeto

```text
├── index.html          Site publicado na Vercel: página única que conversa com a pasta api/
├── api/                Funções da Vercel: catálogo, configuração, código, prévia, projeto e script
├── web_api.py          Ponte entre as funções da Vercel e os módulos de lógica
├── vercel.json         Configuração das funções da Vercel
├── pyproject.toml      Dependências das funções da Vercel
├── app.py              App Streamlit: topo, abas, busca, categorias e cartões
├── catalog.py          Leitura e união das fontes do catálogo
├── catalog_pt.json     Tradução de categorias e descrições para o português
├── catalog_en.json     Tradução para o inglês das descrições que vêm em português
├── kits.py             Kits Power BI, Gerador Python e as telas dessas abas
├── kits_extra.py       Kits de Focus, Ipeadata, Mercado Bitcoin, Nager.Date e Our World in Data
├── kits_ibge.py        Kits do IBGE, gerados a partir da descrição de cada tabela do SIDRA
├── kits_i18n.py        Tradução dos kits para o inglês
├── pergunta.py         Pergunta → Projeto: lê a pergunta e escolhe kits, opções e período
├── montador.py         Montador de Projeto: gera o projeto Power BI (.pbip) a partir dos kits
├── i18n.py             Textos da interface, seletor e detecção de idioma
├── esconder_selo.py    App Streamlit: esconde os controles do Streamlit Cloud
├── rolagem.py          App Streamlit: rola até a lista ao escolher uma categoria
├── style.css           Visual do app Streamlit
├── requirements.txt    Dependências do app Streamlit
└── .streamlit/
    └── config.toml     Tema do Streamlit
```

## Executar o app Streamlit localmente

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

## Publicação na Vercel

O repositório está ligado à Vercel pelo GitHub:

- **Merge na `main`:** a Vercel publica o site em produção automaticamente, em poucos minutos.
- **Pull request:** a Vercel gera uma prévia com endereço próprio, sem mexer no site publicado; o link aparece no próprio PR.
- O resultado de cada publicação aparece no GitHub, ao lado do commit (selo da Vercel).

As funções ficam na pasta `api/`, com os limites de tempo definidos em `vercel.json` e as dependências em `pyproject.toml`. A página é o `index.html`.

O workflow `.github/workflows/validate.yml` valida a sintaxe Python, os IDs dos kits, a inclusão dos novos kits no Montador, o parser da fonte API Directory e o limite de 10.000 registros.

## Como ampliar

**Novo kit do IBGE.** Acrescente uma chamada a `_kit(...)` em `kits_ibge.py` com o caminho da consulta no SIDRA, o nível territorial (`municipio`, `uf` ou `brasil`), o tipo de período (`ano`, `mes` ou `trimestre`) e as medidas. O Power Query e o Python são gerados a partir disso. Inclua a tradução em `KITS_EN`, no mesmo arquivo.

**Novo kit de outra API.** Acrescente um item à lista `KITS` em `kits_extra.py`, com os modelos de código em M e em Python. Os parâmetros entram como marcadores no formato `«NOME»`. Inclua a tradução em `kits_i18n.py`. Para o kit entrar no Montador, acrescente em `montador.py` o esquema das colunas (`ESQUEMAS`), os visuais (`VISUAIS`) e o tema (`TEMA_DO_KIT`); para a aba Pergunta → Projeto, as palavras-chave em `pergunta.py`.

**Nova fonte do catálogo.** Acrescente um item a `EXTRAS` em `catalog.py`. Se o formato for diferente dos existentes, escreva um leitor e registre-o em `PARSERS`.

**Novo idioma.** Inclua o código em `SUPPORTED` e as traduções em `STRINGS`, no `i18n.py`; crie o `catalog_<idioma>.json`; e acrescente os textos dos kits em `kits_i18n.py`.

## Créditos

O catálogo existe graças ao trabalho das comunidades que mantêm as fontes listadas em "Fontes do catálogo". Os dados dos kits vêm de IBGE, Banco Central do Brasil, Ipea, Câmara dos Deputados, BrasilAPI, Open-Meteo, Frankfurter, Banco Mundial, USGS, Mercado Bitcoin, Nager.Date, Our World in Data (licença CC BY), Open Library e Crossref.


## API HTTP (Vercel)

O site publicado usa uma API HTTP serverless na pasta `api/`, publicada pela Vercel. Ela expõe o catálogo, a configuração dos kits Power BI, a geração de consultas e scripts, a prévia dos dados e a montagem de projetos. Os endpoints não exigem autenticação.

Defina `BASE_URL` como o domínio do site, sem a barra final:

```bash
export BASE_URL="https://atlasapi-delta.vercel.app"
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

`/api/config` e `/api/catalogo` usam cache na borda para respostas com idioma explícito; o catálogo tem cache de borda de 30 minutos e a configuração, de 24 horas. A configuração com `lang=auto` não é armazenada em cache compartilhado. Respostas de geração e downloads não são armazenados em cache. Os endpoints são atualizados a cada merge na `main` (veja "Publicação na Vercel").
