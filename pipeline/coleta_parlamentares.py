"""Atualiza a filiação partidária de deputados (Câmara, legislaturas 56 e 57) e senadores
(Senado, legislaturas 56 e 57 e em exercício). Usado para dar partido ao autor de cada emenda.

Saídas: raw/parlamentares.json {dep, depAtual, sen}, raw/parl56.json {dep56, sen56, sen57}, raw/dep56.json
Cada lista falha de forma independente: se uma API estiver fora, o arquivo anterior é mantido.
"""
import sys
from comum import baixar_json, gravar, ler

CAM = 'https://dadosabertos.camara.leg.br/api/v2/deputados?itens=1000&ordem=ASC&ordenarPor=nome'
SEN = 'https://legis.senado.leg.br/dadosabertos/senador/lista/'


def deputados(leg=None):
    out = []
    for pag in range(1, 6):
        url = CAM + (f'&idLegislatura={leg}' if leg else '') + f'&pagina={pag}'
        dados = baixar_json(url)['dados']
        out += [[d['nome'], d['siglaPartido'], d['siglaUf'], d['id']] for d in dados]
        if len(dados) < 1000:
            break
    return out


def senado_leg(leg):
    j = baixar_json(SEN + f'legislatura/{leg}.json')
    P = j['ListaParlamentarLegislatura']['Parlamentares']['Parlamentar']
    return [[p['IdentificacaoParlamentar'].get('NomeParlamentar'), p['IdentificacaoParlamentar'].get('SiglaPartidoParlamentar'),
             p['IdentificacaoParlamentar'].get('UfParlamentar')] for p in P]


def senado_atual():
    j = baixar_json(SEN + 'atual.json')
    P = j['ListaParlamentarEmExercicio']['Parlamentares']['Parlamentar']
    return [[p['IdentificacaoParlamentar']['NomeParlamentar'], p['IdentificacaoParlamentar'].get('SiglaPartidoParlamentar'),
             p['IdentificacaoParlamentar'].get('UfParlamentar'), p['IdentificacaoParlamentar'].get('NomeCompletoParlamentar')] for p in P]


def tenta(nome, f, anterior):
    try:
        v = f()
        if not v:
            raise RuntimeError('lista vazia')
        print(f'{nome}: {len(v)} registros')
        return v
    except Exception as e:
        print(f'{nome}: falhou ({e}); mantida a lista anterior', file=sys.stderr)
        return anterior


def main():
    p57 = ler('parlamentares.json', {'dep': [], 'depAtual': [], 'sen': []})
    p56 = ler('parl56.json', {'dep56': [], 'sen56': [], 'sen57': []})
    d56 = ler('dep56.json', [])
    p57['dep'] = tenta('Câmara leg. 57', lambda: deputados(57), p57['dep'])
    p57['depAtual'] = tenta('Câmara em exercício', lambda: deputados(), p57['depAtual'])
    p57['sen'] = tenta('Senado em exercício', senado_atual, p57['sen'])
    d56 = tenta('Câmara leg. 56', lambda: deputados(56), d56)
    p56['sen56'] = tenta('Senado leg. 56', lambda: senado_leg(56), p56['sen56'])
    p56['sen57'] = tenta('Senado leg. 57', lambda: senado_leg(57), p56['sen57'])
    p56['dep56'] = d56[:1000]
    gravar('parlamentares.json', p57)
    gravar('parl56.json', p56)
    gravar('dep56.json', d56)


if __name__ == '__main__':
    main()
