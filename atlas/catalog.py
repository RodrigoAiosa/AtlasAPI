"""Download e leitura do catálogo de APIs do repositório public-apis."""
from __future__ import annotations

import re

import requests

README_URLS = [
    "https://raw.githubusercontent.com/public-apis/public-apis/master/README.md",
    "https://raw.githubusercontent.com/public-apis/public-apis/main/README.md",
]
IGNORED_HEADINGS = {"table of contents", "contents", "index", "contributing", "license"}
SEARCH_FIELDS = ("name", "description", "category", "auth")


def clean_cell(value: str) -> str:
    value = re.sub(r"<br\s*/?>", " ", value.strip(), flags=re.I)
    value = re.sub(r"`([^`]*)`", r"\1", value)
    value = re.sub(r"\*\*(.*?)\*\*", r"\1", value)
    value = re.sub(r"\*(.*?)\*", r"\1", value)
    return re.sub(r"\s+", " ", value).strip()


def markdown_link(value: str) -> tuple[str, str]:
    """Devolve o texto e a primeira URL de um link Markdown, se houver."""
    match = re.search(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", value)
    if match:
        return clean_cell(match.group(1)), match.group(2).strip()
    return clean_cell(value), ""


def split_row(line: str) -> list[str]:
    # No README, a linha de cabeçalho das tabelas não começa com "|".
    return [part.strip() for part in line.strip().strip("|").split("|")]


def fetch_readme(timeout: int = 20) -> str:
    last_error: Exception | None = None
    for url in README_URLS:
        try:
            response = requests.get(url, timeout=timeout, headers={"User-Agent": "API-Atlas"})
            response.raise_for_status()
            return response.text
        except requests.RequestException as exc:
            last_error = exc
    raise RuntimeError(f"Não foi possível carregar o catálogo do GitHub. Detalhe: {last_error}")


def parse_readme(content: str) -> list[dict]:
    """Transforma as tabelas Markdown do README em uma lista de APIs."""
    records: list[dict] = []
    seen: set[tuple[str, str]] = set()
    category = "Outros"
    lines = content.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        heading = re.match(r"^#{2,3}\s+(.+?)\s*#*\s*$", line)
        if heading:
            title = clean_cell(heading.group(1))
            if title.lower() not in IGNORED_HEADINGS:
                category = title

        headers = [clean_cell(x).lower() for x in split_row(line)]
        is_table = ("api" in headers or "name" in headers) and "description" in headers
        if not is_table:
            i += 1
            continue

        i += 1
        if i < len(lines) and re.match(r"^\s*\|?[\s:|-]+\|?\s*$", lines[i]):
            i += 1
        while i < len(lines) and lines[i].strip().startswith("|"):
            cells = split_row(lines[i])
            i += 1
            if len(cells) < len(headers):
                continue
            row = dict(zip(headers, cells))
            name, url = markdown_link(row.get("api", row.get("name", "")))
            if not url:
                url = markdown_link(row.get("link", ""))[1]
            key = (name.casefold(), category.casefold())
            if not name or key in seen:
                continue
            seen.add(key)
            records.append({
                "name": name,
                "description": clean_cell(row.get("description", "")),
                "auth": clean_cell(row.get("auth", "")),
                "https": clean_cell(row.get("https", "")).casefold() == "yes",
                "cors": clean_cell(row.get("cors", "")).casefold() == "yes",
                "url": url,
                "category": category,
            })
    if not records:
        raise RuntimeError("O catálogo foi carregado, mas nenhuma tabela de APIs foi identificada.")
    return records


def search(apis: list[dict], query: str) -> list[dict]:
    """Todas as palavras da busca precisam aparecer em nome, descrição, categoria ou auth."""
    words = query.casefold().split()
    if not words:
        return apis
    result = []
    for api in apis:
        haystack = " ".join(str(api[f]) for f in SEARCH_FIELDS).casefold()
        if all(word in haystack for word in words):
            result.append(api)
    return result
