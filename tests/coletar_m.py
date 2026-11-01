"""Gera o código M de todos os kits (com os parâmetros padrão) e das tabelas automáticas, em JSON."""
import datetime
import json
import sys

sys.path.insert(0, ".")  # roda a partir da raiz do repositório
import kits, montador, i18n
i18n.set_lang('pt')
def vals(k):
    v = {}
    for p in k['parametros']:
        d = p.get('padrao'); tp = p['tipo']
        d = 0 if tp == 'opcoes' else datetime.date.fromisoformat(d) if tp == 'data' else d
        v.update(kits.validar(p, d, p['rotulo'], ''))
    return v
saida = {k['id']: kits.preencher(k['m'], vals(k)) for k in kits.KITS}
saida['dCalendario'] = montador.M_CALENDARIO; saida['dUF'] = montador.DIM_UF['m']
json.dump(saida, sys.stdout)
