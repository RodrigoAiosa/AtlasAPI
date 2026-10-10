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
EXTRAS = (
    {
        "name": "marcelscruz/public-apis",
        "format": "json",
        "urls": (
            "https://raw.githubusercontent.com/marcelscruz/public-apis/main/db/resources.json",
            "https://raw.githubusercontent.com/marcelscruz/public-apis/master/db/resources.json",
        ),
    },
    {
        "name": "public-api-lists",
        "format": "readme",
        "urls": (
            "https://raw.githubusercontent.com/public-api-lists/public-api-lists/master/README.md",
            "https://raw.githubusercontent.com/public-api-lists/public-api-lists/main/README.md",
        ),
    },
)

# Seções dos READMEs que não são categorias de APIs.
IGNORED_HEADINGS = {
    "index", "mcp servers", "apilayer apis", "learn more about public apis",
    "table of contents", "contents", "contributing", "license",
}
# Nomes de categoria das fontes extras -> nome usado no catálogo.
CATEGORY_ALIASES = {"ai": "Machine Learning"}
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


def _name_key(name: str) -> str:
    key = re.sub(r"\(.*?\)", "", name.casefold())
    key = re.sub(r"\b(api|apis|the)\b", "", key)
    return re.sub(r"[^a-z0-9]+", "", key)


def _host(url: str) -> str:
    return urlsplit(url).netloc.lower().removeprefix("www.")


def _url_key(url: str) -> str:
    parts = urlsplit(url)
    return _host(url) + parts.path.rstrip("/").lower()


def merge(primary: list[dict], extras: list[tuple[str, list[dict]]], primary_name: str = "public-apis") -> list[dict]:
    """Une as fontes, mantendo a principal e acrescentando só o que é novo.

    Uma entrada extra é duplicata quando já existe alguma com o mesmo nome
    (sem "API", parênteses e pontuação), o mesmo endereço ou o mesmo domínio.
    Domínios compartilhados, como github.com, não contam para a última regra.
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
        if identity in exact:
            continue
        exact.add(identity)
        merged.append({**row, "source": primary_name})
    for row in merged:
        remember(row)

    categories = {row["category"].casefold(): row["category"] for row in merged}
    for source, rows in extras:
        for row in rows:
            host = _host(row["url"]) if row["url"] else ""
            if (
                not _name_key(row["name"])
                or _name_key(row["name"]) in names
                or (row["url"] and _url_key(row["url"]) in urls)
                or (host and host not in SHARED_HOSTS and host in hosts)
            ):
                continue
            category = CATEGORY_ALIASES.get(row["category"].casefold(), row["category"])
            category = categories.setdefault(category.casefold(), category)
            merged.append({**row, "category": category, "source": source})
            remember(row)
    return merged


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
            rows = parse_json(content) if source["format"] == "json" else parse_readme(content)
        except (CatalogError, ValueError, KeyError, AttributeError):
            rows = []
        if rows:
            extras.append((source["name"], rows))
        else:
            failed.append(source["name"])
    return merge(primary, extras, PRIMARY["name"]), failed
