import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from atlas import catalog, ui

README = """
## Index
* [Animals](#animals)

### Animals
API | Description | Auth | HTTPS | CORS |
|:---|:---|:---|:---|:---|
| [Cat Facts](https://catfact.ninja/) | Daily cat facts | No | Yes | No |
| [Dogs](https://dog.ceo/dog-api/) | Based on the `Stanford` Dogs Dataset | `apiKey` | Yes | Yes |
| [Cat Facts](https://dup.example/) | Duplicate | No | Yes | No |

### Weather
API | Description | Auth | HTTPS | CORS |
|---|---|---|---|---|
| [Yr](https://api.met.no/) | Weather & climate <data> | No | No | Unknown |
"""


def test_parse_readme():
    apis = catalog.parse_readme(README)
    assert [a["name"] for a in apis] == ["Cat Facts", "Dogs", "Yr"]
    dogs = apis[1]
    assert dogs == {
        "name": "Dogs",
        "description": "Based on the Stanford Dogs Dataset",
        "auth": "apiKey",
        "https": True,
        "cors": True,
        "url": "https://dog.ceo/dog-api/",
        "category": "Animals",
    }
    assert apis[2]["category"] == "Weather" and not apis[2]["https"]


def test_search_matches_all_words_in_any_field():
    apis = catalog.parse_readme(README)
    assert [a["name"] for a in catalog.search(apis, "animals cat")] == ["Cat Facts"]
    assert [a["name"] for a in catalog.search(apis, "APIKEY")] == ["Dogs"]
    assert catalog.search(apis, "  ") == apis
    assert catalog.search(apis, "nada") == []


def test_card_escapes_html():
    html = ui.card(catalog.parse_readme(README)[2])
    assert "&lt;data&gt;" in html and "<data>" not in html
    assert 'href="https://api.met.no/"' in html
    assert "\n" not in html
