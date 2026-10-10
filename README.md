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

## Estrutura

```text
api_atlas_streamlit/
├── app.py
├── kits.py
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
