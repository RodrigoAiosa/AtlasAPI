"""GET /api/busca?q=...: resultados federados, sem espelhar o roster APIs.io."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import catalog  # noqa: E402
import web_api  # noqa: E402


class handler(web_api.Base):
    def do_GET(self):
        query = (self.consulta().get("q") or "").strip()
        if len(query) < 3:
            self.json({"apis": [], "total": 0})
            return
        try:
            rows, total = catalog.search_apisio(query, limit=24)
        except Exception:
            self.json({"apis": [], "total": 0, "erro": "apisio_unavailable"}, status=502)
            return
        apis = [{
            "n": row["name"],
            "d": row["description"],
            "a": row["auth"],
            "h": row["https"],
            "o": row["cors"],
            "u": row["url"],
            "c": row["category"],
            "fonte": row["source"],
        } for row in rows]
        # Cache por consulta para evitar gastar a cota Explore a cada visita.
        self.json({"apis": apis, "total": total}, cache=21600)
