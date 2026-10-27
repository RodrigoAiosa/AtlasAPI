"""Roda o site no computador, do mesmo jeito que na Vercel.

    python servidor_local.py          # abre em http://localhost:8000
    python servidor_local.py 8080     # outra porta

/ serve o index.html e /api/<nome> chama a classe `handler` de api/<nome>.py.
Precisa de internet para o catálogo e para a prévia dos kits.
"""
import importlib.util
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)


def _carregar_funcoes() -> dict:
    funcoes = {}
    pasta = os.path.join(RAIZ, "api")
    for nome in sorted(os.listdir(pasta)):
        if nome.endswith(".py"):
            spec = importlib.util.spec_from_file_location(f"api_{nome[:-3]}", os.path.join(pasta, nome))
            modulo = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(modulo)
            funcoes[f"/api/{nome[:-3]}"] = modulo.handler
    return funcoes


FUNCOES = _carregar_funcoes()


class Roteador(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=RAIZ, **kwargs)

    def _funcao(self, metodo: str) -> bool:
        classe = FUNCOES.get(self.path.split("?")[0])
        if not classe:
            return False
        self.__class__ = type("Funcao", (classe,), {})
        getattr(self, metodo)()
        return True

    def do_GET(self):
        if not self._funcao("do_GET"):
            super().do_GET()

    def do_POST(self):
        if not self._funcao("do_POST"):
            self.send_error(404)


if __name__ == "__main__":
    porta = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(f"API Atlas em http://localhost:{porta}  (Ctrl+C para parar)")
    ThreadingHTTPServer(("127.0.0.1", porta), Roteador).serve_forever()
