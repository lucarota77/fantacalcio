#!/usr/bin/env python3
"""Salva nel repo le quote per giocatore raccolte dalla passata locale, cosi le esecuzioni
cloud successive possono riusarle invece di lasciare i campi vuoti.
Uso: python3 salva_quote.py <giornata>   (dopo `giocatori.py locale`)

I mercati per giocatore si possono leggere solo con un browser da rete residenziale: quando
il Mac e spento restano irraggiungibili. Le quote invecchiano, ma una quota di due ore fa vale
molto piu di nessuna quota: il report dichiara sempre l'eta del dato.
"""
import json, sys
from datetime import datetime
G = sys.argv[1] if len(sys.argv) > 1 else '?'
rows = json.load(open('/tmp/rows.json'))['rows']
q = {x['n']: {'qg': x.get('qg'), 'qgs': x.get('qgs'), 'qa': x.get('qa'), 'qc': x.get('qc')}
     for x in rows if any(x.get(k) for k in ('qg', 'qgs', 'qa', 'qc'))}
partite = {x['mt']: x.get('when') for x in rows}
out = {'giornata': str(G), 'rilevate': datetime.now().astimezone().isoformat(timespec='minutes'),
       'fonte': 'bwin + Snai (browser, passata locale)', 'partite': partite, 'quote': q}
json.dump(out, open('quote_cache.json', 'w'), ensure_ascii=False, indent=1)
print(f"quote_cache.json: {len(q)} giocatori, giornata {G}, rilevate {out['rilevate']}")
