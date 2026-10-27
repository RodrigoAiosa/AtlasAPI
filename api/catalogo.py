"""GET /api/catalogo?lang=pt|en: catálogo local deduplicado das fontes públicas configuradas."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import web_api  # noqa: E402


class handler(web_api.Base):
    def do_GET(self):
        dados = web_api.catalogo(self.consulta().get("lang"))
        # 30 minutos na borda, o mesmo tempo do cache do catálogo.
        self.json(dados, status=503 if dados.get("erro") else 200, cache=0 if dados.get("erro") else 1800)
