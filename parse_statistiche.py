#!/usr/bin/env python3
"""Estrae media voto (MV) e fantamedia (FM) stagionali da fantacalcio.it/statistiche-serie-a.
La pagina e leggibile con curl: i dati sono nell'HTML, non caricati via JS.
L'export Excel (/api/v1/Excel/stats/21/1) richiede invece autenticazione: non usarlo.
"""
import html as _html
import json, re, subprocess, sys, unicodedata
URL = 'https://www.fantacalcio.it/statistiche-serie-a'
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/140.0 Safari/537.36')
# Chiavi reali della tabella: pg=partite, mv=media voto, mfv=fantamedia, rig="segnati / tirati"
COLS = ['sq', 'pg', 'mv', 'mfv', 'gol', 'gs', 'rp', 'ass', 'amm', 'esp']

def norm(s):
    s = unicodedata.normalize('NFKD', s or '')
    return ''.join(c for c in s if not unicodedata.combining(c)).lower()

def num(s):
    s = (s or '').strip().replace(',', '.')
    m = re.match(r'^-?\d+(\.\d+)?$', s)
    return float(s) if m else None

def scarica():
    r = subprocess.run(['curl', '-sL', '-A', UA, '-m', '60', URL], capture_output=True, text=True)
    if r.returncode != 0 or len(r.stdout) < 10000:
        raise SystemExit(f"fetch statistiche fallito ({r.returncode})")
    return r.stdout

def tabella(html=None):
    h = html or scarica()
    out = {}
    for row in re.findall(r'<tr class="player-row"(.*?)</tr>', h, re.S):
        nm = re.search(r'data-filter-keywords="([^"]+)"', row)
        if not nm: continue
        rec = {}
        for k in COLS:
            c = re.search(r'data-col-key="%s"[^>]*>(.*?)</t[dh]>' % k, row, re.S)
            if not c: continue
            v = re.sub(r'<[^>]+>', '', c.group(1)).strip()
            rec[k] = v if k == 'sq' else num(v)
        rec['mv'], rec['fm'] = rec.get('mv'), rec.pop('mfv', None)
        rl = re.search(r'data-filter-role-classic="(\w)"', row)
        rec['ruolo'] = (rl.group(1) or '').upper() if rl else None
        out[_html.unescape(nm.group(1)).strip()] = rec   # i nomi sono HTML-encoded: Kon&#xE8; M.
    return out

# Sigla di squadra usata nella tabella: serve a scartare gli omonimi di altri club
# (senza questo controllo "Kone" della Roma aggancia il Kone del Frosinone).
SIGLE = {'inter': 'INT', 'milan': 'MIL', 'lazio': 'LAZ', 'roma': 'ROM', 'juventus': 'JUV',
         'napoli': 'NAP', 'bologna': 'BOL', 'fiorentina': 'FIO', 'genoa': 'GEN',
         'lecce': 'LEC', 'torino': 'TOR', 'udinese': 'UDI', 'atalanta': 'ATA',
         'cagliari': 'CAG', 'como': 'COM', 'parma': 'PAR', 'monza': 'MON',
         'sassuolo': 'SAS', 'venezia': 'VEN', 'frosinone': 'FRO'}

def per_rosa(rosa, html=None):
    t = tabella(html)
    idx = {norm(k): v for k, v in t.items()}
    res = {}
    for g in rosa:
        sig = SIGLE.get(norm(g['squadra']))
        toks = [x for x in re.split(r'[\s.]+', g.get('nome_fonte') or g['nome']) if len(x) > 2]
        chiavi = [norm(g['nome'])] + ([norm(toks[-1])] if toks else []) + \
                 ([norm(' '.join(toks[-2:]))] if len(toks) > 1 else [])
        def ok(v): return not sig or not v.get('sq') or v['sq'] == sig
        hit = next((idx[c] for c in chiavi if c in idx and ok(idx[c])), None)
        if hit is None:
            cand = [v for k, v in idx.items()
                    if any(c and (c in k or k in c) for c in chiavi) and ok(v)]
            hit = cand[0] if cand else None
        if hit is None:                      # nessun riscontro nella squadra giusta
            res[g['nome']] = {'nota': 'non presente nelle statistiche di ' + g['squadra']}
        else:
            res[g['nome']] = hit
    return res

if __name__ == '__main__':
    rosa = json.load(open(sys.argv[1] if len(sys.argv) > 1 else 'rosa.json'))['rosa']
    r = per_rosa(rosa)
    print(json.dumps(r, ensure_ascii=False, indent=1))
    ok = sum(1 for v in r.values() if v.get('mv') is not None)
    print(f"\n# {ok}/{len(rosa)} giocatori con MV/FM", file=sys.stderr)
