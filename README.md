# API Atlas — Public API Directory

Diretório de APIs públicas construído com Python e Streamlit, inspirado no layout de referência enviado.

## Recursos

- Pesquisa global fixa no topo da página.
- Catálogo obtido do README do repositório `public-apis/public-apis` no GitHub.
- Busca por nome, descrição, categoria e metadados.
- Navegação por categorias com contagem de APIs.
- Cards com nome, descrição, autenticação, HTTPS e CORS.
- Links para documentação quando disponíveis.
- Cache por 30 minutos para reduzir chamadas ao GitHub.
- **Kits Power BI:** 9 APIs sem autenticação com consulta pronta em Power Query (M) e em Python, parâmetros ajustáveis, prévia dos dados, ideias de visuais, medidas DAX e a ponte com o [BI Data Generator](https://ai-bidatagenerator.streamlit.app/).
- **Gerador Python:** cole a URL de qualquer endpoint JSON e receba o script em `requests` + `pandas`, com opção de chave de API.
- CSS separado, configuração do tema Streamlit e estrutura pronta para GitHub/Streamlit Community Cloud.

## Idiomas (i18n)

A interface está em português e inglês. O idioma inicial é escolhido nesta ordem:

1. `?lang=pt` ou `?lang=en` na URL (útil para compartilhar o link já no idioma certo);
2. idioma do navegador;
3. país de acesso, pelo cabeçalho `CF-IPCountry` da Cloudflare (só existe se o app estiver atrás da Cloudflare);
4. inglês.

O visitante pode trocar o idioma no seletor do topo. Para adicionar um idioma, inclua o código em `SUPPORTED` e as traduções em `STRINGS` no `i18n.py`, e os textos dos kits em `kits_i18n.py`. O que não for traduzido aparece em inglês (interface) ou em português (kits).

Descrições e categorias do catálogo vêm do repositório de origem e ficam em inglês. O código gerado pelos kits usa nomes de tabelas e colunas em português nos dois idiomas.

## Estrutura

```text
api_atlas_streamlit/
├── app.py
├── kits.py
├── kits_i18n.py
├── i18n.py
├── style.css
├── requirements.txt
├── README.md
├── .gitignore
└── .streamlit/
    └── config.toml
```

## Executar no Windows

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Executar no macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Publicar no Streamlit Community Cloud

1. Crie um repositório no GitHub e envie todos os arquivos desta pasta.
2. Acesse https://share.streamlit.io/ e conecte sua conta GitHub.
3. Escolha o repositório e defina `app.py` como arquivo principal.
4. Publique o app.

## Fonte e observações

Fonte: https://github.com/public-apis/public-apis

A aplicação percorre as tabelas de todas as categorias no README upstream e carrega todas as entradas encontradas. A lista de APIs em destaque na página inicial é uma seleção editorial; o catálogo completo, a busca global e os resultados por categoria vêm do repositório upstream. Autenticação, HTTPS e CORS podem mudar e devem ser confirmados na documentação oficial de cada API.
