"""Monta o site em site/: index.html (com o logo embutido) e data/AAAA.json + data/meta.json.
Entradas em raw/: y/YAAAA.json (LOA do SIOP), y/EAAAA.json (emendas do Portal da Transparência),
parlamentares.json (leg. 57 + atuais), parl56.json (senado 56/57), dep56.json (câmara 56),
br_s2.json (mapa), pop_ibge.json (população por UF), coleta_portal.json (data da última coleta).
"""
import json, re, unicodedata, collections, os, base64, datetime

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
R = os.path.join(RAIZ, 'raw') + '/'
SITE = os.path.join(RAIZ, 'site') + '/'
OUT = SITE + 'data/'
os.makedirs(OUT, exist_ok=True)
ANOS = sorted(int(f[1:5]) for f in os.listdir(R + 'y') if re.match(r'^Y\d{4}\.json$', f) and os.path.exists(R + f'y/E{f[1:5]}.json'))
geo = json.load(open(encoding='utf-8', file=R + 'br_s2.json'))
UFNOME = {f['properties']['name']: f['properties']['nome'] for f in geo['features']}
UFS = sorted(UFNOME)
UFX = {'NA': 'Nacional', 'RG': 'Multirregional', 'EX': 'Exterior', 'OU': 'Outros localizadores'}
N = lambda x: re.sub(r'[^A-Z ]', '', unicodedata.normalize('NFKD', x or '').encode('ascii', 'ignore').decode().upper()).strip()

# ---------- partidos por legislatura ----------
P57 = json.load(open(encoding='utf-8', file=R + 'parlamentares.json'))
P56 = json.load(open(encoding='utf-8', file=R + 'parl56.json'))
D56 = json.load(open(encoding='utf-8', file=R + 'dep56.json'))

def last_party(entries):
    m = {}
    for nome, p, uf, *_ in entries:  # a API lista as filiações em ordem cronológica: fica a última
        if p and uf:
            m[(N(nome), uf)] = p
    return m

party57 = last_party(P57['dep'])
party57.update(last_party([[n, p, u] for n, p, u, i in P57['depAtual']]))
party57.update(last_party([[n, p, u] for n, p, u, f in P57['sen']]))
party57.update({('RODRIGO PACHECO', 'MG'): 'PSD', ('LEILA BARROS', 'DF'): 'PDT', ('MECIAS DE JESUS', 'RR'): 'REPUBLICANOS',
                ('FERNANDO FARIAS', 'AL'): 'MDB', ('AUGUSTA BRITO', 'CE'): 'PT', ('EDUARDO GIRAO', 'CE'): 'NOVO'})
party56 = last_party(D56)
# senadores sem UF na lista da legislatura: casar só pelo nome
sen_nome56 = {N(n): p for n, p, u in P56['sen56'] if p}
sen_nome57 = {N(n): p for n, p, u in P56['sen57'] if p}
sen_nome57.update({N(n): p for n, p, u, f in P57['sen'] if p})

def partido(ano, autor, uf, tautor):
    if tautor.startswith('Bancada'): return 'Bancada estadual'
    if tautor.startswith('Comiss'): return 'Comissão'
    if tautor.startswith('Relator'): return 'Relator-geral'
    if tautor in ('SEM INFORMAÇÃO', '', None): return 'Sem informação'
    nome = autor.split(' - ', 1)[1] if ' - ' in autor else autor
    nome = N(re.sub(r'^DEP\.\s*', '', re.sub(r'\s*\(EX-PARLAMENTAR.*$', '', nome)))
    leg56 = ano <= 2023  # LOA 2020–2023: emendas apresentadas na 56ª legislatura
    order = [party56, party57] if leg56 else [party57, party56]
    sen = [sen_nome56, sen_nome57] if leg56 else [sen_nome57, sen_nome56]
    for m in order:
        if (nome, uf) in m: return m[(nome, uf)]
    if tautor == 'Senador':
        for m in sen:
            if nome in m: return m[nome]
    return 'Não identificado'

UFNOME_N = {N(v): k for k, v in UFNOME.items()}
def uf_destino(loc):
    m = re.match(r'^(.+) \(UF\)$', loc or '')
    if m and N(m.group(1)) in UFNOME_N: return UFNOME_N[N(m.group(1))]
    m = re.search(r' - ([A-Z]{2})$', loc or '')
    if m and m.group(1) in UFS: return m.group(1)
    if loc == 'Nacional': return 'NA'
    if (loc or '').upper().startswith('MÚLTIPLO'): return 'MU'
    return 'RG'

TIPOC = {'Emenda Individual - Transferências com Finalidade Definida': 'Individual – finalidade definida',
         'Emenda Individual - Transferências Especiais': 'Individual – transferência especial',
         'Emenda de Bancada': 'Bancada estadual', 'Emenda de Comissão': 'Comissão', 'Emenda de Relator': 'Relator-geral'}

serie_loa = collections.defaultdict(lambda: [0]*6)
serie_em = collections.defaultdict(lambda: [0, 0, 0, 0, 0])
meta_anos = {}
nao_id = collections.Counter()
for ano in ANOS:
    y = json.load(open(encoding='utf-8', file=R + f'y/Y{ano}.json'))
    dims = y['dims']; dic = y['dic']
    # descrições e códigos de UF
    ufcodes = [c for c, _ in dic[-1]]
    dic[-1] = [[c, UFNOME.get(c, UFX.get(c, c))] for c in ufcodes]
    for r in y['rows']:
        rp = dic[0][r[0]][0]; uf = dic[6][r[6]][0]
        a = serie_loa[(ano, rp, uf)]
        for i in range(6): a[i] += r[7 + i]
    e = json.load(open(encoding='utf-8', file=R + f'y/E{ano}.json')); D = e['D']
    autores, aidx, rows = [], {}, []
    acao_desc = {}
    for r in e['rows']:
        cod, tipo, autor, tautor, ufa, num, loc, cfun = r[0], D[r[1]], D[r[2]], D[r[3]], D[r[4]], r[5], D[r[6]], r[7]
        acao = D[r[11]]
        emp, liq, pag, rpi, rpp = r[12:17]
        ac = acao.split(' - ', 1)[0] if acao else ''
        if ac and ' - ' in acao: acao_desc[ac] = acao.split(' - ', 1)[1].capitalize()
        pt = partido(ano, autor, ufa, tautor)
        if pt == 'Não identificado': nao_id[(ano, autor, ufa)] += 1
        nome = autor.split(' - ', 1)[1] if ' - ' in autor else autor
        nome = re.sub(r'\s*\(EX-PARLAMENTAR.*$', '', nome).title() or 'Sem informação'
        k = (nome, tautor or 'Sem informação', ufa or 'N/A', pt)
        if k not in aidx: aidx[k] = len(autores); autores.append(list(k))
        ufd = uf_destino(loc)
        tc = TIPOC.get(tipo, tipo)
        rows.append([aidx[k], tc, ufd, loc, cfun, ac, round(emp), round(liq), round(pag), round(rpi), round(rpp), cod])
        s = serie_em[(ano, tc, pt, ufd, ufa if ufa not in ('N/A', '', None) else 'NA')]
        for i, v in enumerate((emp, liq, pag, rpi, rpp)): s[i] += v
    tipos = sorted(set(x[1] for x in rows)); tix = {t: i for i, t in enumerate(tipos)}
    locs = sorted(set(x[3] for x in rows)); lix = {t: i for i, t in enumerate(locs)}
    for x in rows: x[1] = tix[x[1]]; x[3] = lix[x[3]]
    funcao = {c: d for c, d in dic[2]}
    for r in e['rows']: funcao.setdefault(r[7], D[r[8]])
    acoes = {c: d for c, d in dic[3]}
    for c, d in acao_desc.items(): acoes.setdefault(c, d)
    out = {'ano': ano, 'base': y['lm'],
           'loa': {'dims': ['rp', 'orgao', 'funcao', 'acao', 'gnd', 'mod', 'uf'], 'dic': dic, 'rows': y['rows']},
           'em': {'autores': autores, 'tipos': tipos, 'locs': locs, 'rows': rows, 'funcao': funcao, 'acao': acoes}}
    s = json.dumps(out, ensure_ascii=False, separators=(',', ':'))
    open(OUT + f'{ano}.json', 'w').write(s)
    meta_anos[ano] = {'base': y['lm'], 'bytes': len(s)}
    print(ano, 'loa', len(y['rows']), 'em', len(rows), 'KB', len(s) // 1024)

pop = json.load(open(encoding='utf-8', file=R + 'pop_ibge.json'))
for a in ANOS:  # exercício sem estimativa do IBGE: usa a mais recente
    if str(a) not in pop:
        pop[str(a)] = pop[max(pop, key=int)]
coleta = json.load(open(encoding='utf-8', file=R + 'coleta_portal.json')) if os.path.exists(R + 'coleta_portal.json') else {'data': '27/11/2026'}
meta = {'pop': pop, 'anos': ANOS, 'atual': max(ANOS), 'portal': coleta['data'], 'anosInfo': meta_anos, 'geo': geo,
        'serieLoa': [[k[0], k[1], k[2]] + [round(x) for x in v] for k, v in serie_loa.items()],
        'serieEm': [list(k) + [round(x) for x in v] for k, v in serie_em.items()]}
s = json.dumps(meta, ensure_ascii=False, separators=(',', ':'))
open(OUT + 'meta.json', 'w').write(s)
print('meta KB', len(s) // 1024, 'serieLoa', len(meta['serieLoa']), 'serieEm', len(meta['serieEm']))
print('não identificados', sum(nao_id.values()), nao_id.most_common(15))

logo = base64.b64encode(open(os.path.join(RAIZ, 'web', 'logo.png'), 'rb').read()).decode()
html = open(os.path.join(RAIZ, 'web', 'index.html'), encoding='utf-8').read().replace('__LOGO__', logo)
open(SITE + 'index.html', 'w', encoding='utf-8').write(html)
open(SITE + '.nojekyll', 'w').write('')
print('site montado em', SITE, datetime.datetime.now(datetime.timezone.utc).isoformat())
