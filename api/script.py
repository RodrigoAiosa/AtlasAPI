"""POST /api/script {url, caminho, autenticacao, nome_chave, csv, lang}: script requests + pandas."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import web_api  # noqa: E402


class handler(web_api.Base):
    def do_POST(self):
        dados = self.corpo()
        self.json(web_api.script(dados, dados.get("lang")))
