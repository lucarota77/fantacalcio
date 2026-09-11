#!/usr/bin/env python3
"""Raccolta dati SENZA browser: pensata per la routine cloud, usa solo curl.

  python3 raccolta_cloud.py calendario -> le 10 partite del turno con data/ora (BetExplorer JSON-LD)
  python3 raccolta_cloud.py quote      -> quote 1X2 medie di mercato, per le partite gia quotate
  python3 raccolta_cloud.py gazzetta   -> testo delle probabili formazioni di Gazzetta
  python3 raccolta_cloud.py dati       -> scrive dati.json con quello che riesce a ottenere

COSA FUNZIONA E COSA NO (verificato il 11/09/2026)
  gazzetta.it      curl con user-agent -> 200, pagina completa. WebFetch invece e bloccato.
  betexplorer.com  curl -> 1X2 medie di mercato dalla lista, e il calendario completo dal JSON-LD.
                   Le quote compaiono solo per le partite piu imminenti: a meta settimana
                   alcune gare non sono ancora quotate.
  bwin             l'API widget ha un rate limit: dopo poche richieste serve la SPA HTML al posto
                   del JSON. NON affidabile per uso automatico. Il cds-api risponde 403.
  snai             curl va in timeout. Exa in crawl timeout.
  Marcatore/assist/ammonizione: nessuna fonte senza browser. Restano alla passata locale.

OPZIONALE — the-odds-api.com: se la variabile d'ambiente ODDS_API_KEY e impostata, le quote 1X2
e Over/Under di tutte e 10 le partite arrivano da li (piano gratuito: 500 richieste al mese,
ne serve una a settimana). Senza chiave si usa BetExplorer e si accetta la copertura parziale.
"""
import json, os, re, subprocess, sys

UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/140.0 Safari/537.36')
BE = 'https://www.betexplorer.com/football/italy/serie-a/'
GAZZETTA = 'https://www.gazzetta.it/Calcio/prob_form/'
ODDS_API = ('https://api.the-odds-api.com/v4/sports/soccer_italy_serie_a/odds'
            '?regions=eu&markets=h2h,totals&oddsFormat=decimal&apiKey=')

def fetch(url, timeout=40, follow=True):
    cmd = ['curl', '-s'] + (['-L'] if follow else []) + ['-A', UA, '-m', str(timeout), url]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout:
        raise SystemExit(f"fetch fallito ({r.returncode}): {url}")
    return r.stdout

def calendario(html=None):
    """Tutte le partite del campionato dal JSON-LD, con data/ora ISO."""
    h = html or fetch(BE)
    ev = re.findall(r'"name":\s*"([^"]+)",\s*"startDate":\s*"([^"]+)",\s*"url":\s*"([^"]+)"', h)
    return [{'name': n, 'start': d, 'url': u} for n, d, u in ev]

def quote_betexplorer(html=None):
    """1X2 medie di mercato. I nomi si prendono dal JSON-LD via URL, non dal testo della riga:
    il testo contiene anche orari e punteggi e si presta a falsi match."""
    h = html or fetch(BE)
    byurl = {e['url'].rstrip('/').split('/')[-1]: e for e in calendario(h)}
    out = []
    for r in re.findall(r'<tr[^>]*>(.*?)</tr>', h, re.S):
        # Dal runner GitHub (IP non italiano) i link sono /football/... senza il prefisso /it/
        link = re.search(r'href="(?:/it)?/football/italy/serie-a/[^"]*?/([A-Za-z0-9]{6,10})/"', r)
        od = re.findall(r'data-odd="([\d.]+)"', r)
        if not link or len(od) < 3: continue
        ev = byurl.get(link.group(1))
        if not ev: continue                       # gara passata: non e nel JSON-LD dei prossimi
        n = ev['name'].split(' - ')
        if len(n) != 2: continue
        out.append({'home': n[0].strip(), 'away': n[1].strip(), 'start': ev['start'],
                    'odds': [float(od[0]), float(od[1]), float(od[2])], 'ou': None,
                    'fonte': 'betexplorer (media di mercato)'})
    return out

def quote_odds_api(key):
    """Tutte e 10 le partite con 1X2 e Over/Under, se e disponibile una chiave."""
    d = json.loads(fetch(ODDS_API + key))
    out = []
    for ev in d:
        h, a = ev['home_team'], ev['away_team']
        h2h, tot = [], []
        for bk in ev.get('bookmakers', []):
            for mk in bk.get('markets', []):
                if mk['key'] == 'h2h':
                    o = {x['name']: x['price'] for x in mk['outcomes']}
                    if h in o and a in o and 'Draw' in o: h2h.append([o[h], o['Draw'], o[a]])
                elif mk['key'] == 'totals':
                    for x in mk['outcomes']:
                        if abs(x.get('point', 0) - 2.5) < .01: tot.append((x['name'], x['price']))
        if not h2h: continue
        med = [round(sum(c[i] for c in h2h)/len(h2h), 3) for i in range(3)]
        ov = [p for n, p in tot if n == 'Over']; un = [p for n, p in tot if n == 'Under']
        out.append({'home': h, 'away': a, 'odds': med,
                    'ou': [round(sum(ov)/len(ov), 3), round(sum(un)/len(un), 3), 2.5] if ov and un else None,
                    'fonte': f'the-odds-api, media di {len(h2h)} bookmaker'})
    return out

def giornata(testo=None):
    """Numero di giornata letto dai dati, non dedotto contando i file di report:
    Gazzetta lo scrive come "4° Giornata" in testa alla pagina."""
    t = testo or gazzetta_testo()
    m = re.search(r'(\d{1,2})\s*[°ºo]\s*Giornata', t)
    return m.group(1) if m else None

def gazzetta_testo():
    h = fetch(GAZZETTA, 60)
    h = re.sub(r'(?is)<(script|style|noscript)[^>]*>.*?</\1>', ' ', h)
    h = re.sub(r'(?i)<br\s*/?>|</(p|div|li|tr|h\d|section|span)>', '\n', h)
    t = re.sub(r'<[^>]+>', ' ', h)
    for a, b in [('&nbsp;', ' '), ('&amp;', '&'), ('&egrave;', 'è'), ('&agrave;', 'à'),
                 ('&ograve;', 'ò'), ('&igrave;', 'ì'), ('&ugrave;', 'ù'), ('&#039;', "'")]:
        t = t.replace(a, b)
    t = re.sub(r'[ \t]{2,}', ' ', t)
    return '\n'.join(l.strip() for l in t.split('\n') if l.strip())

if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'dati'
    key = os.environ.get('ODDS_API_KEY', '').strip()
    if cmd == 'calendario':
        for e in calendario(): print(f"  {e['name']:<26} {e['start'][:16]}")
    elif cmd == 'giornata':
        g = giornata()
        print(g or '', end='')
        if not g: print("giornata non trovata nel testo di Gazzetta", file=sys.stderr)
    elif cmd == 'gazzetta':
        t = gazzetta_testo(); print(t)
        print(f"\n# {len(t)} caratteri, 'Ballottaggio' x{t.count('Ballottaggio')}", file=sys.stderr)
    elif cmd in ('quote', 'dati'):
        q = quote_odds_api(key) if key else quote_betexplorer()
        for r in q:
            r['name'] = f"{r['home']}-{r['away']}"
            r.setdefault('start', None)
            r['when'] = r.get('start')
        if cmd == 'quote':
            print(json.dumps(q, ensure_ascii=False, indent=1))
        else:
            json.dump({'matches': q}, open('dati_cloud.json', 'w'), ensure_ascii=False, indent=1)
            print(f"dati_cloud.json: {len(q)} partite quotate"
                  f"{' (chiave the-odds-api attiva)' if key else ' — BetExplorer, copertura parziale'}")
        if not key:
            print("# Nessuna ODDS_API_KEY: copertura limitata alle gare gia quotate.", file=sys.stderr)
