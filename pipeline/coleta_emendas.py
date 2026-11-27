"""Baixa as emendas parlamentares de cada exercício na consulta do Portal da Transparência
(autor, tipo, UF do autor, localidade do gasto, função, ação, empenhado, liquidado, pago e
restos a pagar). Os restos a pagar das emendas antigas mudam todo dia, por isso todos os
exercícios são coletados de novo.

Saída: raw/y/EAAAA.json  {D, rows}; textos repetidos ficam no dicionário D.
  rows = [codigo, tipo, autor, tipoAutor, ufAutor, numero, localidade, codFuncao, funcao, 0, 0, acao,
          empenhado, liquidado, pago, resto_inscrito, resto_pago, 0]

Uso: python coleta_emendas.py [anos...]
"""
import sys, datetime
from urllib.parse import urlencode
from comum import baixar_json, gravar

BASE = 'https://portaldatransparencia.gov.br/emendas/consulta/resultado?'
COLS = ('linkDetalhamento,ano,tipoEmenda,autor,numeroEmenda,localidadeDoGasto,funcao,subfuncao,programa,acao,'
        'planoOrcamentario,valorEmpenhado,valorLiquidado,valorPago,valorRestoInscrito,valorRestoCancelado,'
        'valorRestoPago,codigoEmenda,ufAutor,tipoAutor')
ANO0 = 2020
PAGINA = 1000


def n(s):
    return float((s or '0').replace('.', '').replace(',', '.'))


def limpo(s):
    return ''.join(c for c in (s or '') if ord(c) >= 32 and ord(c) not in (0x2028, 0x2029))


def coletar(ano):
    todos = []
    for off in range(0, 100000, PAGINA):
        q = urlencode({'paginacaoSimples': 'true', 'tamanhoPagina': PAGINA, 'offset': off,
                       'direcaoOrdenacao': 'desc', 'colunaOrdenacao': 'valorEmpenhado',
                       'de': ano, 'ate': ano, 'colunasSelecionadas': COLS})
        j = baixar_json(BASE + q)
        todos += j['data']
        if len(j['data']) < PAGINA:
            break
    d, D = {}, []

    def i(s):
        s = limpo(s)
        if s not in d:
            d[s] = len(D)
            D.append(s)
        return d[s]
    rows = [[e.get('codigoEmenda'), i(e.get('tipoEmenda')), i(e.get('autor')), i(e.get('tipoAutor')),
             i(e.get('ufAutor')), e.get('numeroEmenda'), i(e.get('localidadeDoGasto')), e.get('codigoFuncao'),
             i(e.get('funcao')), 0, 0, i(e.get('acao')), n(e.get('valorEmpenhado')), n(e.get('valorLiquidado')),
             n(e.get('valorPago')), n(e.get('valorRestoInscrito')), n(e.get('valorRestoPago')), 0] for e in todos]
    if not rows:
        raise RuntimeError('consulta sem registros')
    gravar(f'y/E{ano}.json', {'D': D, 'rows': rows})
    print(f'Portal {ano}: {len(rows)} emendas, empenhado R$ {sum(r[12] for r in rows) / 1e9:.2f} bi, '
          f'RP pagos R$ {sum(r[16] for r in rows) / 1e9:.2f} bi')


def main():
    anos = [int(a) for a in sys.argv[1:]] or list(range(ANO0, datetime.date.today().year + 1))
    ok = 0
    for a in anos:
        try:
            coletar(a)
            ok += 1
        except Exception as e:
            print(f'Portal {a}: falhou ({e}); mantido o arquivo anterior', file=sys.stderr)
    if ok:
        gravar('coleta_portal.json', {'data': (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=3)).strftime('%d/%m/%Y')})
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
