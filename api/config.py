"""GET /api/config?lang=pt|en|auto: textos da interface e definição dos kits."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import web_api  # noqa: E402


class handler(web_api.Base):
    def do_GET(self):
        pedido = self.consulta().get("lang", "auto")
        if pedido == "auto":
            # Idioma pelos cabeçalhos: depende de quem pede, então não vai para o cache compartilhado.
            self.json(web_api.configuracao(web_api.detectar_idioma(self.headers)))
        else:
            self.json(web_api.configuracao(pedido), cache=86400)
