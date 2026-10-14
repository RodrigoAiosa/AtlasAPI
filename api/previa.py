"""POST /api/previa {kit, valores, lang}: roda o script do kit e devolve as primeiras linhas."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import web_api  # noqa: E402


class handler(web_api.Base):
    def do_POST(self):
        dados = self.corpo()
        try:
            self.json(web_api.previa(str(dados.get("kit")), dados.get("valores"), dados.get("lang")))
        except ValueError as erro:
            self.json({"erro": str(erro)}, status=400)
