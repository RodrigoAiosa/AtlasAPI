# API Atlas — Diretório de APIs públicas

Aplicação em Python + Streamlit que lê o catálogo do repositório [public-apis](https://github.com/public-apis/public-apis) e o apresenta em uma grade de cartões, com busca global e filtro por categoria.

## Executar localmente

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Estrutura

```
app.py                  Página (busca, categoria, destaques, paginação)
atlas/catalog.py        Download e leitura do README do public-apis, busca
atlas/ui.py             HTML dos cartões
assets/style.css        Todo o visual do site
.streamlit/config.toml  Tema claro do Streamlit
tests/                  Testes do parser, da busca e dos cartões
requirements.txt        Dependências da aplicação
requirements-dev.txt    Dependências para rodar os testes
```

## Funcionalidades

- Destaques da semana: 9 APIs sorteadas, que mudam a cada semana.
- Busca global por nome, descrição, categoria e tipo de autenticação.
- Filtro por categoria (usado quando o campo de busca está vazio).
- Cartões com autenticação, HTTPS e CORS ao passar o mouse; o cartão inteiro abre a API.
- Layout responsivo (3, 2 ou 1 coluna) e cache dos dados por 30 minutos.

## Testes

```bash
pip install -r requirements-dev.txt
pytest
```

## Observações

A aplicação depende do formato Markdown do README upstream. Se o repositório alterar sua estrutura, o parser em `atlas/catalog.py` poderá precisar de ajustes. As informações sobre autenticação, HTTPS e CORS devem ser confirmadas na documentação oficial de cada API.
