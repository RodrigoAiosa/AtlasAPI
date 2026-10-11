"""Leitura e união das fontes do catálogo de APIs.

A fonte principal é obrigatória; as extras só acrescentam APIs que ainda
não estão no catálogo e, se falharem, o site continua com o que carregou.
"""
from __future__ import annotations

import json
import re
from urllib.parse import urlsplit

import requests

COLUMNS = ["name", "description", "auth", "https", "cors", "url", "category", "source"]

PRIMARY = {
    "name": "public-apis",
    "urls": (
        "https://raw.githubusercontent.com/public-apis/public-apis/master/README.md",
        "https://raw.githubusercontent.com/public-apis/public-apis/main/README.md",
    ),
}
def _readme(repo: str) -> tuple[str, str]:
    return (
        f"https://raw.githubusercontent.com/{repo}/master/README.md",
        f"https://raw.githubusercontent.com/{repo}/main/README.md",
    )


# Fontes extras, na ordem de prioridade. "format" escolhe o leitor em PARSERS;
# "dedupe_host": False vale para listas de conjuntos de dados, em que vários
# itens diferentes ficam no mesmo domínio.
EXTRAS = (
    {
        "name": "marcelscruz/public-apis",
        "format": "json",
        "urls": (
            "https://raw.githubusercontent.com/marcelscruz/public-apis/main/db/resources.json",
            "https://raw.githubusercontent.com/marcelscruz/public-apis/master/db/resources.json",
        ),
    },
    {"name": "public-api-lists", "format": "readme", "urls": _readme("public-api-lists/public-api-lists")},
    {"name": "IF-TI/APIs-PublicasBrasil", "format": "brasil", "urls": _readme("IF-TI/APIs-PublicasBrasil")},
    {"name": "n0shake/Public-APIs", "format": "n0shake", "urls": _readme("n0shake/Public-APIs")},
    {"name": "APIs-guru/graphql-apis", "format": "graphql", "urls": _readme("APIs-guru/graphql-apis")},
    {
        "name": "jdorfman/awesome-json-datasets",
        "format": "json_datasets",
        "urls": _readme("jdorfman/awesome-json-datasets"),
        "dedupe_host": False,
    },
)

# Seções dos READMEs que não são categorias de APIs.
IGNORED_HEADINGS = {
    "index", "mcp servers", "apilayer apis", "learn more about public apis",
    "table of contents", "contents", "contributing", "license",
}
# Nomes de categoria das fontes extras -> nome usado no catálogo.
CATEGORY_ALIASES = {"ai": "Machine Learning"}
# Conteúdo adulto não entra no catálogo, venha de onde vier.
BLOCKED = re.compile(r"\b(porn\w*|hentai|doujin\w*|xxx|rule34|redtube|pornhub)\b", re.I)
# Domínios que hospedam muitas APIs diferentes: o domínio sozinho não indica duplicata.
SHARED_HOSTS = {
    "github.com", "rapidapi.com", "developers.google.com", "cloud.google.com", "docs.microsoft.com",
    "learn.microsoft.com", "developer.apple.com", "aws.amazon.com", "docs.aws.amazon.com",
    "developer.yahoo.com", "apilayer.com", "npmjs.com", "gitlab.com", "docs.github.com",
}


class CatalogError(RuntimeError):
    """Falha no catálogo; `key` é a chave da mensagem traduzida."""

    def __init__(self, key: str, detail: str = "") -> None:
        super().__init__(key)
        self.key, self.detail = key, detail


def clean_cell(value: str) -> str:
    value = re.sub(r"<br\s*/?>", " ", str(value), flags=re.I)
    value = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r"\1", value)
    value = re.sub(r"`([^`]*)`", r"\1", value)
    value = re.sub(r"\*\*(.*?)\*\*", r"\1", value)
    value = re.sub(r"\*(.*?)\*", r"\1", value)
    return re.sub(r"\s+", " ", value).strip()


def split_row(line: str) -> list[str]:
    return [part.strip() for part in line.strip().strip("|").split("|")]


def markdown_link(value: str) -> tuple[str, str]:
    match = re.search(r"\[([^\]]+)\]\((https?://[^)]+)\)", value)
    if match:
        return clean_cell(match.group(1)), match.group(2).strip()
    return clean_cell(value), ""


def fetch(urls) -> str:
    last_error: Exception | None = None
    for url in urls:
        try:
            response = requests.get(url, timeout=25, headers={"User-Agent": "API-Atlas-Streamlit"})
            response.raise_for_status()
            return response.text
        except requests.RequestException as exc:
            last_error = exc
    raise CatalogError("err_load", str(last_error))


def parse_readme(content: str) -> list[dict]:
    """Lê as tabelas de categorias (API | Description | Auth | HTTPS | CORS) de um README."""
    rows: list[dict] = []
    category = ""
    lines = content.splitlines()
    i = 0
    while i < len(lines):
        raw_line = lines[i].strip()

        heading = re.match(r"^#{2,4}\s+(.+?)\s*#*\s*$", raw_line)
        if heading:
            heading_text = clean_cell(heading.group(1))
            if heading_text.casefold() in IGNORED_HEADINGS or "sponsor" in heading_text.casefold():
                category = ""
            else:
                category = heading_text

        # O cabeçalho da tabela pode ou não começar com "|".
        header_cells = [clean_cell(cell).lower() for cell in raw_line.strip("|").strip().split("|")]
        is_api_header = (
            len(header_cells) >= 5
            and header_cells[0] == "api"
            and all(column in header_cells for column in ("description", "auth", "https", "cors"))
        )
        if not (is_api_header and category):
            i += 1
            continue

        i += 1
        if i < len(lines) and re.match(r"^\s*\|?\s*:?-{2,}", lines[i]):
            i += 1
        while i < len(lines) and lines[i].strip().startswith("|"):
            cells = split_row(lines[i])
            i += 1
            if len(cells) < len(header_cells):
                continue
            row = dict(zip(header_cells, cells))
            name, url = markdown_link(row.get("api", ""))
            if not name or name.casefold() in {"api", "name"}:
                continue
            rows.append({
                "name": name,
                "description": clean_cell(row.get("description", "")),
                "auth": clean_cell(row.get("auth", "")) or "Unknown",
                "https": clean_cell(row.get("https", "")) or "Unknown",
                "cors": clean_cell(row.get("cors", "")) or "Unknown",
                "url": url,
                "category": category,
            })
    return rows


def parse_json(content: str) -> list[dict]:
    """Lê o resources.json do marcelscruz/public-apis.

    O arquivo não informa HTTPS, então esse campo fica como "Unknown".
    """
    rows = []
    for entry in json.loads(content).get("entries", []):
        name = clean_cell(entry.get("API", ""))
        if not name:
            continue
        cors = clean_cell(entry.get("Cors", "")).capitalize()
        rows.append({
            "name": name,
            "description": clean_cell(entry.get("Description", "")),
            "auth": clean_cell(entry.get("Auth", "")) or "No",
            "https": "Unknown",
            "cors": cors if cors in {"Yes", "No"} else "Unknown",
            "url": str(entry.get("Link", "")).strip(),
            "category": clean_cell(entry.get("Category", "")) or "Other",
        })
    return rows


def _tables(content: str, required: tuple[str, ...]):
    """Percorre as tabelas Markdown de um README.

    Devolve (título da seção, linha como dicionário de células brutas) para
    cada linha das tabelas cujo cabeçalho contém as colunas de `required`.
    """
    heading = ""
    headers: list[str] | None = None
    for raw_line in content.splitlines():
        line = raw_line.strip()
        title = re.match(r"^#{1,4}\s+(.+?)\s*#*\s*$", line)
        if title:
            heading, headers = clean_cell(title.group(1)), None
            continue
        if "|" not in line:
            headers = None
            continue
        cells = split_row(line)
        if re.fullmatch(r"[\s:|-]+", line):
            continue
        names = [clean_cell(cell).casefold() for cell in cells]
        if all(column in names for column in required):
            headers = names
            continue
        if headers and len(cells) >= len(required):
            yield heading, dict(zip(headers, cells))


def _row(name: str, description: str, url: str, category: str, auth: str = "Unknown") -> dict:
    # Tira marcas de versão ("_v1_"), etiquetas ("#Limited") e o "N/A" usado como descrição vazia.
    description = re.sub(r"\s*(_v\w+_|#\w+)\s*$", "", description).strip()
    if description.upper() == "N/A":
        description = ""
    return {
        "name": name, "description": description, "auth": auth,
        "https": "Unknown", "cors": "Unknown", "url": url, "category": category,
    }


N0SHAKE_CATEGORIES = {
    "advertising": "Business", "analytics": "Business", "augmented reality": "Development",
    "barcode": "Development", "big data and analytics": "Development",
    "cryptocurrency/crypto wallets": "Cryptocurrency", "calendar": "Calendar", "captcha": "Security",
    "check-in": "Social", "commerce": "Shopping", "communication": "Social", "content": "News",
    "currency": "Currency Exchange", "design": "Art & Design", "dictionary": "Dictionaries",
    "entertainment": "Entertainment", "events": "Events", "face recognition": "Machine Learning",
    "file storage and manipulation": "Cloud Storage & File Sharing", "finance": "Finance",
    "fitness": "Sports & Fitness", "google": "Development",
    "identity verification": "Authentication & Authorization", "image moderation": "Machine Learning",
    "iot": "Development", "legal": "Government", "open licenses": "Open Source Projects",
    "login authentication": "Authentication & Authorization", "machine learning": "Machine Learning",
    "maps": "Geocoding", "math": "Science & Math", "medical": "Health", "miscellaneous": "Development",
    "movies": "Video", "music": "Music", "music discovery": "Music", "music identification": "Music",
    "music lyrics": "Music", "music stores": "Music", "news services": "News",
    "natural language processing": "Text Analysis", "placeholder images": "Photography",
    "places": "Geocoding", "product": "Shopping", "quotes": "Personality", "retail": "Shopping",
    "science": "Science & Math", "screenshots": "Development", "social media": "Social",
    "source control": "Development", "sport": "Sports & Fitness", "test data": "Test Data",
    "transportation": "Transportation", "url shorteners": "URL Shorteners",
    "videogames": "Games & Comics", "weather": "Weather",
}


def parse_n0shake(content: str) -> list[dict]:
    """n0shake/Public-APIs: tabelas API | Description | Open/Trial, com categorias próprias."""
    rows = []
    for heading, cells in _tables(content, ("api", "description")):
        category = N0SHAKE_CATEGORIES.get(heading.casefold())
        name, url = markdown_link(cells.get("api", ""))
        if category and name and url:
            rows.append(_row(name, clean_cell(cells.get("description", "")), url, category))
    return rows


def parse_graphql(content: str) -> list[dict]:
    """APIs-guru/graphql-apis: APIs GraphQL oficiais e proxies não oficiais (as de demonstração ficam fora)."""
    rows = []
    for heading, cells in _tables(content, ("api", "description")):
        if "demonstration" in heading.casefold():
            continue
        name = clean_cell(cells.get("api", ""))
        url = ""
        for column, value in cells.items():
            if column not in {"api", "description"} and "docs" in column:
                url = markdown_link(value)[1]
        url = url or next((markdown_link(v)[1] for c, v in cells.items() if c not in {"api", "description"} and markdown_link(v)[1]), "")
        if name and url:
            rows.append(_row(name, clean_cell(cells.get("description", "")).strip('"'), url, "GraphQL"))
    return rows


BRASIL_CATEGORIES = {
    "cep, cnpj e dados comerciais": "Business", "dados geográficos e estatísticos": "Open Data",
    "governo e política": "Government", "economia e finanças": "Finance",
    "clima e meteorologia": "Weather", "transporte e mobilidade": "Transportation",
    "feriados e datas comemorativas": "Calendar", "educação e cultura": "Education",
}


def parse_brasil(content: str) -> list[dict]:
    """IF-TI/APIs-PublicasBrasil: tabelas Nome | URL | Descrição, com descrições em português."""
    rows = []
    for heading, cells in _tables(content, ("nome", "url")):
        category = BRASIL_CATEGORIES.get(re.sub(r"^[^\w]+", "", heading).strip().casefold())
        name = clean_cell(cells.get("nome", ""))
        url = clean_cell(cells.get("url", ""))
        if category and name and url.startswith(("http://", "https://")):
            rows.append(_row(name, clean_cell(cells.get("descrição", "")), url, category))
    return rows


JSON_DATASET_CATEGORIES = {
    "bitcoin": "Cryptocurrency", "climate": "Environment", "crime": "Open Data",
    "currency": "Currency Exchange", "food": "Food & Drink", "gaming": "Games & Comics",
    "github api": "Development", "government": "Government", "historical events": "Open Data",
    "http": "Development", "nasa": "Science & Math", "natural disasters": "Disasters",
    "nobel prize": "Science & Math", "open source licenses": "Open Source Projects",
    "population": "Open Data", "gdp": "Finance", "reddit": "Social", "travel": "Transportation",
    "tv shows": "Video", "movies": "Video",
}


def parse_json_datasets(content: str) -> list[dict]:
    """jdorfman/awesome-json-datasets: endereços que devolvem JSON sem autenticação.

    A lista não traz descrições; o nome recebe o tema da seção ("Bitcoin: Latest Block")
    e a descrição é montada a partir dele.
    """
    rows = []
    heading = ""
    for line in content.splitlines():
        title = re.match(r"^##\s+(.+?)\s*$", line.strip())
        if title:
            heading = clean_cell(title.group(1))
            continue
        item = re.match(r"^\s*[-*]\s+\[([^\]]+)\]\((https?://[^)\s]+)\)", line)
        category = JSON_DATASET_CATEGORIES.get(heading.casefold())
        if item and category:
            rows.append(_row(
                f"{heading}: {clean_cell(item.group(1))}",
                f"JSON dataset, no authentication required ({heading})",
                item.group(2), category, auth="No",
            ))
    return rows


def _name_key(name: str) -> str:
    key = re.sub(r"\(.*?\)", "", name.casefold())
    key = re.sub(r"\b(api|apis|the)\b", "", key)
    return re.sub(r"[^a-z0-9]+", "", key)


def _host(url: str) -> str:
    return urlsplit(url).netloc.lower().removeprefix("www.")


def _url_key(url: str) -> str:
    parts = urlsplit(url)
    return _host(url) + parts.path.rstrip("/").lower()


def merge(primary: list[dict], extras: list[tuple], primary_name: str = "public-apis") -> list[dict]:
    """Une as fontes, mantendo a principal e acrescentando só o que é novo.

    Uma entrada extra é duplicata quando já existe alguma com o mesmo nome
    (sem "API", parênteses e pontuação), o mesmo endereço ou o mesmo domínio.
    Domínios compartilhados, como github.com, não contam para a última regra.
    Cada extra é (fonte, linhas) ou (fonte, linhas, comparar_dominio).
    """
    merged: list[dict] = []
    names: set[str] = set()
    urls: set[str] = set()
    hosts: set[str] = set()
    exact: set[tuple] = set()

    def remember(row: dict) -> None:
        names.add(_name_key(row["name"]))
        if row["url"]:
            urls.add(_url_key(row["url"]))
            hosts.add(_host(row["url"]))

    for row in primary:
        identity = (row["name"], row["category"], row["url"])
        if identity in exact or BLOCKED.search(f'{row["name"]} {row["description"]}'):
            continue
        exact.add(identity)
        merged.append({**row, "source": primary_name})
    for row in merged:
        remember(row)

    categories = {row["category"].casefold(): row["category"] for row in merged}
    for source, rows, *options in extras:
        by_host = options[0] if options else True
        for row in rows:
            host = _host(row["url"]) if row["url"] else ""
            if (
                BLOCKED.search(f'{row["name"]} {row["description"]}')
                or not _name_key(row["name"])
                or _name_key(row["name"]) in names
                or (row["url"] and _url_key(row["url"]) in urls)
                or (by_host and host and host not in SHARED_HOSTS and host in hosts)
            ):
                continue
            category = CATEGORY_ALIASES.get(row["category"].casefold(), row["category"])
            category = categories.setdefault(category.casefold(), category)
            merged.append({**row, "category": category, "source": source})
            remember(row)
    return merged


PARSERS = {
    "readme": parse_readme,
    "json": parse_json,
    "brasil": parse_brasil,
    "n0shake": parse_n0shake,
    "graphql": parse_graphql,
    "json_datasets": parse_json_datasets,
}


def load() -> tuple[list[dict], list[str]]:
    """Devolve as APIs e a lista de fontes extras que não puderam ser lidas."""
    primary = parse_readme(fetch(PRIMARY["urls"]))
    if not primary:
        raise CatalogError("err_parse")
    extras: list[tuple[str, list[dict]]] = []
    failed: list[str] = []
    for source in EXTRAS:
        try:
            content = fetch(source["urls"])
            rows = PARSERS[source["format"]](content)
        except (CatalogError, ValueError, KeyError, AttributeError, IndexError):
            rows = []
        if rows:
            extras.append((source["name"], rows, source.get("dedupe_host", True)))
        else:
            failed.append(source["name"])
    return merge(primary, extras, PRIMARY["name"]), failed
