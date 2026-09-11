#!/usr/bin/env python3
"""Parser deterministico delle probabili formazioni di fantacalcio.it.
La pagina e leggibile con curl e marca le sezioni in modo pulito:
  player-list starters / reserves, ballot-list (con percentuali esplicite),
  injured-list, doubts-list, suspendeds-list.
Restituisce per ogni giocatore di rosa.json la stima P(gioca), come parse_gazzetta.py.
"""
import html as _html, json, re, subprocess, sys, unicodedata
URL = 'https://www.fantacalcio.it/probabili-formazioni-serie-a'
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/140.0 Safari/537.36')

def norm(s):
    s = unicodedata.normalize('NFKD', _html.unescape(s or ''))
    return ''.join(c for c in s if not unicodedata.combining(c)).lower().strip()

def scarica():
    r = subprocess.run(['curl', '-sL', '-A', UA, '-m', '60', URL], capture_output=True, text=True)
    if r.returncode != 0 or len(r.stdout) < 50000:
        raise SystemExit(f"fetch fantacalcio fallito ({r.returncode})")
    return r.stdout

def nomi(frammento):
    """(squadra, nome) presi dall'href: /serie-a/squadre/<squadra>/<giocatore>/<id>.
    La squadra nell'URL evita i falsi positivi fra omonimi di club diversi
    (senza, "Thuram" dell'Inter aggancia Thuram K. della Juventus, infortunato)."""
    out = []
    for href, nome in re.findall(
            r'class="player-name player-link"\s+href="([^"]*)"[^>]*>\s*<span>(.*?)</span>',
            frammento, re.S):
        m = re.search(r'/squadre/([^/]+)/', href)
        out.append((norm(m.group(1)) if m else '', norm(nome)))
    return out

def sezioni(h, classe):
    return re.findall(r'<[uo]l class="%s"[^>]*>(.*?)</[uo]l>' % classe, h, re.S)

def chiavi(g):
    toks = [t for t in re.split(r'[\s.]+', g.get('nome_fonte') or g['nome']) if len(t) > 2]
    out = [norm(g['nome'])]
    if toks: out.append(norm(toks[-1]))
    if len(toks) > 1: out.append(norm(' '.join(toks[-2:])))
    return [k for k in out if k]

def analizza(h, rosa):
    # I blocchi squadra sono delimitati da team-lineup: dentro ci sono titolari, riserve e ballottaggi
    blocchi = re.findall(r'<ul class="team-lineup"[^>]*>(.*?)(?=<ul class="team-lineup"|\Z)', h, re.S)
    if not blocchi: blocchi = [h]
    start_all, res_all, ballo_all = [], [], {}
    for b in blocchi:
        for s in sezioni(b, 'player-list starters'): start_all += nomi(s)
        for s in sezioni(b, 'player-list reserves'): res_all += nomi(s)
    for s in sezioni(h, 'ballot-list'):
        for href, a, p in re.findall(
                r'class="player-name player-link"\s+href="([^"]*)"[^>]*>\s*<span>(.*?)</span>\s*</a>\s*'
                r'<strong class="percentage">(\d+)%', s, re.S):
            m = re.search(r'/squadre/([^/]+)/', href)
            ballo_all[((norm(m.group(1)) if m else ''), norm(a))] = int(p)/100
    fuori = []
    for cls in ('injured-list', 'suspendeds-list'): 
        for s in sezioni(h, cls): fuori += nomi(s)
    dubbi = []
    for s in sezioni(h, 'doubts-list'): dubbi += nomi(s)
    res = {}
    ALIAS = {'inter': 'inter', 'milan': 'milan', 'juventus': 'juventus'}
    for g in rosa:
        ks = chiavi(g); info = {'fc': None, 'nota': ''}
        sq = ALIAS.get(norm(g['squadra']), norm(g['squadra']))
        def match(coppia):
            s_, n_ = coppia
            if s_ and sq and sq not in s_ and s_ not in sq: return False   # squadra diversa
            return any(k == n_ or (len(k) > 4 and k in n_) for k in ks)
        hit = lambda lst: any(match(c) for c in lst)
        pb = next((v for k, v in ballo_all.items() if match(k)), None)
        if hit(fuori):
            info['fc'], info['nota'] = 0.0, 'indisponibile o squalificato (fantacalcio.it)'
        elif pb is not None:
            info['fc'], info['nota'] = pb, f'ballottaggio {round(pb*100)}% (fantacalcio.it)'
        elif hit(dubbi):
            info['fc'], info['nota'] = 0.5, 'in dubbio (fantacalcio.it)'
        elif hit(start_all):
            info['fc'], info['nota'] = 0.90, 'titolare (fantacalcio.it)'
        elif hit(res_all):
            info['fc'], info['nota'] = 0.12, 'in panchina (fantacalcio.it)'
        res[g['nome']] = info
    return res

if __name__ == '__main__':
    h = open(sys.argv[1]).read() if len(sys.argv) > 1 and sys.argv[1] != '-' else scarica()
    rosa = json.load(open(sys.argv[2] if len(sys.argv) > 2 else 'rosa.json'))['rosa']
    r = analizza(h, rosa)
    print(json.dumps(r, ensure_ascii=False, indent=1))
    print(f"\n# {sum(1 for v in r.values() if v['fc'] is not None)}/{len(rosa)} risolti da fantacalcio.it",
          file=sys.stderr)
