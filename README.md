# API Atlas — Diretório de APIs públicas

Aplicação em Python + Streamlit que lê o catálogo do repositório [public-apis](https://github.com/public-apis/public-apis), organiza as APIs por categoria e oferece busca global.

## Executar localmente

```bash
python -m venv .venv
```

Windows:
```bat
.venv\Scripts\activate
```

macOS/Linux:
```bash
source .venv/bin/activate
```

Instale as dependências e inicie:

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Funcionalidades

- Catálogo carregado do README do GitHub.
- Navegação por categoria.
- Busca global por nome, descrição, categoria e metadados.
- Informações de autenticação, HTTPS e CORS.
- Links para a API quando encontrados no README.
- Cache de dados por 30 minutos.

## Observações

A aplicação depende do formato Markdown do README upstream. Se o repositório alterar sua estrutura, o parser poderá precisar de ajustes. As informações sobre autenticação, HTTPS e CORS devem ser confirmadas na documentação oficial de cada API.
