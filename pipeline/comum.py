"""Funções de apoio da coleta: download com novas tentativas e gravação segura."""
import json, os, time, urllib.request, urllib.error

RAW = os.path.join(os.path.dirname(__file__), '..', 'raw')
UA = 'Mozilla/5.0 (painel-orcamento-federal; atualizacao diaria)'


def baixar(url, tentativas=4, espera=10, cabecalhos=None, timeout=180):
    """Baixa a URL e devolve (bytes, cabeçalhos). Repete em caso de falha de rede."""
    h = {'User-Agent': UA, 'Accept': '*/*'}
    h.update(cabecalhos or {})
    erro = None
    for i in range(tentativas):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout) as r:
                return r.read(), dict(r.headers)
        except urllib.error.HTTPError as e:
            erro = e
            if e.code == 404:
                raise
        except Exception as e:  # rede instável
            erro = e
        time.sleep(espera * (i + 1))
    raise erro


def baixar_json(url, **kw):
    b, _ = baixar(url, cabecalhos={'Accept': 'application/json'}, **kw)
    return json.loads(b.decode('utf-8'))


def gravar(caminho, obj):
    """Grava JSON compacto sem quebrar o arquivo anterior se algo falhar no meio."""
    caminho = os.path.join(RAW, caminho)
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    tmp = caminho + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, separators=(',', ':'))
    os.replace(tmp, caminho)


def ler(caminho, padrao=None):
    caminho = os.path.join(RAW, caminho)
    if not os.path.exists(caminho):
        return padrao
    with open(caminho, encoding='utf-8') as f:
        return json.load(f)
