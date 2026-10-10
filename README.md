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
- CSS separado, configuração do tema Streamlit e estrutura pronta para GitHub/Streamlit Community Cloud.

## Estrutura

```text
api_atlas_streamlit/
├── app.py
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

A aplicação busca o README do repositório upstream. Como a estrutura desse README pode mudar, o parser pode precisar de manutenção. A lista de APIs em destaque na página inicial é apenas uma seleção editorial inicial; os resultados e categorias são carregados do catálogo upstream. Autenticação, HTTPS e CORS podem mudar e devem ser confirmados na documentação oficial de cada API.
