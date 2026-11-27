"""Baixa a LOA de cada exercício nos dados abertos do SIOP e agrega por
resultado primário, órgão, função, ação, GND, modalidade de aplicação e UF.

Saída: raw/y/YAAAA.json  {ano, lm, dims, dic, rows}
  rows = [i_rp, i_orgao, i_funcao, i_acao, i_gnd, i_mod, i_uf,
          projeto_lei, dotacao_inicial, lei_mais_creditos, empenhado, liquidado, pago]

A UF vem do texto do localizador (subtitulo_descricao), já que o arquivo não traz a UF
em coluna própria: "No Estado de X", "... - UF", Distrito Federal/Brasília, Nacional,
Exterior e regiões (multirregional). O que não se encaixa fica como "OU" (outros).

Uso: python coleta_siop.py [anos...]   (sem argumentos: exercício corrente e anteriores ausentes)
"""
import csv, gzip, io, re, sys, datetime
from comum import baixar, gravar, ler

URL = 'https://www1.siop.planejamento.gov.br/downloads/rdf/loa{ano}.csv.gz'
ANO0 = 2020
UFN = {'Acre': 'AC', 'Alagoas': 'AL', 'Amapá': 'AP', 'Amazonas': 'AM', 'Bahia': 'BA', 'Ceará': 'CE',
       'Distrito Federal': 'DF', 'Espírito Santo': 'ES', 'Goiás': 'GO', 'Maranhão': 'MA', 'Mato Grosso': 'MT',
       'Mato Grosso do Sul': 'MS', 'Minas Gerais': 'MG', 'Pará': 'PA', 'Paraíba': 'PB', 'Paraná': 'PR',
       'Pernambuco': 'PE', 'Piauí': 'PI', 'Rio de Janeiro': 'RJ', 'Rio Grande do Norte': 'RN',
       'Rio Grande do Sul': 'RS', 'Rondônia': 'RO', 'Roraima': 'RR', 'Santa Catarina': 'SC', 'São Paulo': 'SP',
       'Sergipe': 'SE', 'Tocantins': 'TO'}
SIGLAS = set(UFN.values())
R_ESTADO = re.compile(r'^N[oa] Estado d[eoa]s? (.+?)(\s*\(.*\))?$')
R_SIGLA = re.compile(r' - ([A-Z]{2})(\s*\(.*\))?$')
R_REGIAO = re.compile(r'Regi[ãa]o (Norte|Nordeste|Sul|Sudeste|Centro-Oeste)|Amazônia Legal|Semiárido|Semi-árido', re.I)
DIMS = ['resultado_primario', 'orgao', 'funcao', 'acao', 'grupo_natureza_despesa', 'modalidade_aplicacao']
VALS = ['valor_projeto_lei', 'valor_dotacao_inicial', 'valor_lei_mais_creditos', 'valor_empenhado', 'valor_liquidado', 'valor_pago']


def uf(s):
    m = R_ESTADO.match(s)
    if m and m.group(1).strip() in UFN:
        return UFN[m.group(1).strip()]
    if s.startswith('No Distrito Federal') or s.startswith('Em Brasília'):
        return 'DF'
    m = R_SIGLA.search(s)
    if m and m.group(1) in SIGLAS:
        return m.group(1)
    for k, v in UFN.items():
        if s.endswith('Estado de ' + k) or s.endswith('Estado do ' + k) or s.endswith('Estado da ' + k):
            return v
    if s.startswith('Nacional'):
        return 'NA'
    if s.startswith('Exterior'):
        return 'EX'
    if R_REGIAO.search(s):
        return 'RG'
    return 'OU'


def num(x):
    try:
        return float(x or 0)
    except ValueError:
        return float(x.replace('.', '').replace(',', '.'))


def coletar(ano):
    b, h = baixar(URL.format(ano=ano))
    lm = h.get('Last-Modified') or h.get('last-modified') or ''
    texto = gzip.decompress(b).decode('utf-8-sig')
    rd = csv.reader(io.StringIO(texto))
    H = next(rd)
    ix = {n: i for i, n in enumerate(H)}
    di = [(ix[d + '_codigo'], ix[d + '_descricao']) for d in DIMS]
    vi = [ix[v] for v in VALS]
    si = ix['subtitulo_descricao']
    dic = [dict() for _ in DIMS]
    ufm = {}
    g = {}
    n = 0
    for p in rd:
        if not p:
            continue
        n += 1
        k = []
        for j, (c, d) in enumerate(di):
            m = dic[j]
            if p[c] not in m:
                m[p[c]] = (len(m), p[d])
            k.append(m[p[c]][0])
        u = uf(p[si])
        if u not in ufm:
            ufm[u] = len(ufm)
        k.append(ufm[u])
        k = tuple(k)
        a = g.get(k)
        if a is None:
            a = g[k] = [0.0] * 6
        for j in range(6):
            a[j] += num(p[vi[j]])
    rows = [list(k) + [round(x) for x in a] for k, a in g.items() if any(abs(x) >= .5 for x in a)]
    out = {'ano': ano, 'lm': lm, 'dims': DIMS + ['uf'],
           'dic': [[[c, d] for c, (i, d) in m.items()] for m in dic] + [[[u, ''] for u in ufm]],
           'rows': rows}
    gravar(f'y/Y{ano}.json', out)
    tot = sum(r[9] for r in rows)
    print(f'SIOP {ano}: {n} linhas, {len(rows)} agregadas, dotação atual R$ {tot / 1e12:.2f} tri, base {lm}')


def main():
    hoje = datetime.date.today()
    if len(sys.argv) > 1:
        anos = [int(a) for a in sys.argv[1:]]
    else:
        # exercício corrente sempre; anteriores só se ainda não existirem; em janeiro, também o anterior
        anos = [a for a in range(ANO0, hoje.year) if ler(f'y/Y{a}.json') is None]
        if hoje.month <= 2:
            anos.append(hoje.year - 1)
        anos.append(hoje.year)
    falhas = []
    for a in sorted(set(anos)):
        try:
            coletar(a)
        except Exception as e:  # mantém o arquivo anterior
            falhas.append(a)
            print(f'SIOP {a}: falhou ({e}); mantido o arquivo anterior', file=sys.stderr)
    if falhas and len(falhas) == len(set(anos)):
        sys.exit(1)


if __name__ == '__main__':
    main()
