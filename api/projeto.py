"""POST /api/projeto {kits: [{id, valores}], titulo, lang, baixar}.

Sem "baixar", devolve o resumo do projeto (tabelas, relacionamentos, medidas e páginas).
Com "baixar": true, devolve o .zip do projeto Power BI.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import web_api  # noqa: E402


class handler(web_api.Base):
    def do_POST(self):
        dados = self.corpo()
        escolhas = [e for e in (dados.get("kits") or []) if isinstance(e, dict)][:30]
        titulo, idioma = str(dados.get("titulo") or ""), dados.get("lang")
        if dados.get("baixar"):
            pacote, erro = web_api.zip_projeto(escolhas, titulo, idioma)
            if erro:
                self.json({"erro": erro}, status=400)
            else:
                self.binario(pacote, "application/zip", f"{web_api.montador.PROJETO}.zip")
        else:
            self.json(web_api.resumo_projeto(escolhas, titulo, idioma))
