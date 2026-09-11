#!/usr/bin/env python3
"""Unisce l'output di parse_gazzetta.py e di raccolta_cloud.py in dati.json +
giocatori_input.json, senza intervento umano. Usato dal workflow GitHub Actions."""
import json, sys, unicodedata
def norm(s):
    s = unicodedata.normalize('NFKD', s)
    return ''.join(c for c in s if not unicodedata.combining(c)).lower()
import os
from datetime import datetime
gz   = json.load(open('gz.json'))
# Quote per giocatore salvate dall'ultima passata locale: si riusano se sono della STESSA
# giornata. Il browser non e disponibile in cloud, quindi senza questa cache i campi
# resterebbero vuoti.
CACHE, cache_eta = {}, None
if os.path.exists('quote_cache.json'):
    _c = json.load(open('quote_cache.json'))
    # GIORNATA puo arrivare vuota dalle esecuzioni schedulate: in quel caso si accetta la
    # cache cosi com'e (sara scartata al cambio giornata dal confronto sulle partite).
    _g = os.environ.get('GIORNATA') or None
    if _g is None or str(_c.get('giornata')) == str(_g):
        CACHE = _c.get('quote', {})
        try:
            dt = datetime.fromisoformat(_c['rilevate'])
            cache_eta = (datetime.now().astimezone() - dt).total_seconds()/3600
        except Exception: cache_eta = None
fc   = json.load(open('fc.json')) if os.path.exists('fc.json') else {}
q    = json.load(open('dati_cloud.json'))['matches']
rosa = json.load(open('rosa.json'))['rosa']
ALIAS = {'ac milan': 'milan', 'as roma': 'roma', 'inter milan': 'inter'}
def canon(s): return ALIAS.get(norm(s), norm(s))
byteam = {}
for m in q:
    m['home_c'], m['away_c'] = canon(m['home']), canon(m['away'])
    byteam[m['home_c']] = m; byteam[m['away_c']] = m
# partite senza quote: il contesto resta neutro e viene dichiarato
matches, visti, stimate = [], set(), []
for g in rosa:
    c = canon(g['squadra'])
    info = gz.get(g['nome'], {})
    nome_match = info.get('match')
    m = byteam.get(c)
    if m:
        key = f"{m['home']}-{m['away']}"
        if key not in visti:
            visti.add(key)
            matches.append({'name': key, 'home': m['home'], 'away': m['away'],
                            'when': m.get('when') or '', 'bwin': {'odds': m['odds'],
                            'ou': m['ou'] or [1.85, 1.95, 2.5]}})
            if not m['ou']: stimate.append(key + ' (Over/Under stimato)')
    elif nome_match:
        key = nome_match.replace(' - ', '-')
        if key not in visti:
            visti.add(key)
            h, a = (nome_match.split(' - ') + [''])[:2]
            matches.append({'name': key, 'home': h, 'away': a, 'when': '',
                            'bwin': {'odds': [3.0, 3.3, 3.0], 'ou': [1.85, 1.95, 2.5]}})
            stimate.append(key + ' (nessuna quota: contesto neutro)')
json.dump({'matches': matches}, open('dati.json', 'w'), ensure_ascii=False, indent=1)
# righe per giocatori.py
out = []
for g in rosa:
    info = gz.get(g['nome'], {})
    nm = info.get('match', '')
    key = nm.replace(' - ', '-') if nm else None
    if key not in visti:
        c = canon(g['squadra']); m = byteam.get(c)
        key = f"{m['home']}-{m['away']}" if m else None
    if not key: continue
    f = fc.get(g['nome'], {})
    c = CACHE.get(g['nome'], {})
    note = ' / '.join(x for x in (f.get('nota'), info.get('nota')) if x)
    if c and cache_eta is not None:
        note = (note + ' / ' if note else '') + f'quote da rilevazione locale di {cache_eta:.0f}h fa'
    out.append([g['nome'], g['ruolo'], g['squadra'], key, f.get('fc'), None,
                info.get('gz'), None, c.get('qg'), c.get('qgs'), c.get('qa'), c.get('qc'),
                1 if info.get('stale') else 0, note])
json.dump({'giocatori': out, 'stimate': stimate}, open('giocatori_input.json', 'w'),
          ensure_ascii=False, indent=1)
print(f"dati.json: {len(matches)} partite ({len(stimate)} con quote stimate o assenti)")
print(f"giocatori_input.json: {len(out)} giocatori"
      + (f" — quote riusate dalla cache locale di {cache_eta:.0f}h fa ({len(CACHE)} giocatori)"
         if CACHE else " — nessuna quota in cache"))
for s in stimate: print("  ! " + s)
