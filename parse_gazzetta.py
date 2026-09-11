#!/usr/bin/env python3
"""Parser deterministico delle probabili formazioni di Gazzetta (testo da raccolta_cloud.py).
Per ogni giocatore di rosa.json restituisce la stima P(gioca) secondo METODO.md:
titolare 0.90 | percentuale del ballottaggio se indicata | panchina 0.12 | indisponibile 0.00.
Serve al workflow GitHub Actions, che non ha un modello a disposizione per leggere le pagine.
"""
import json, re, sys, unicodedata
from datetime import datetime

MESI = {m: i+1 for i, m in enumerate(
    'gennaio febbraio marzo aprile maggio giugno luglio agosto settembre ottobre novembre dicembre'.split())}

def norm(s):
    s = unicodedata.normalize('NFKD', s)
    return ''.join(c for c in s if not unicodedata.combining(c)).lower()

def chiavi(nome_fonte, nome):
    """Chiavi di ricerca in ordine di preferenza: Gazzetta usa il cognome, che e l'ultimo
    token. Attenzione: max(toks, key=len) sceglierebbe il nome proprio a parita di lunghezza
    ("Marcus" invece di "Thuram")."""
    toks = [t for t in re.split(r'[\s.]+', (nome_fonte or nome)) if len(t) > 2]
    if not toks: return [norm(nome)]
    out = [norm(toks[-1])]
    if len(toks) > 1: out.append(norm(' '.join(toks[-2:])))   # cognomi doppi: "kolo muani"
    return out

def blocchi(testo):
    idx = [m.start() for m in re.finditer(r'^Ultimo aggiornamento:', testo, re.M)]
    for i, a in enumerate(idx):
        b = idx[i+1] if i+1 < len(idx) else len(testo)
        yield testo[a:b]

def ts_blocco(b):
    m = re.search(r'Ultimo aggiornamento:\s*(\d{1,2})\s+(\w+)\s+(\d{4}),\s*ore\s*(\d{1,2}):(\d{2})', b)
    if not m: return None
    g, mese, a, h, mi = m.groups()
    if norm(mese) not in MESI: return None
    return datetime(int(a), MESI[norm(mese)], int(g), int(h), int(mi))

def squadre(b):
    righe = [l.strip() for l in b.split('\n') if l.strip()]
    out = []
    for l in righe[1:12]:
        if l.startswith(('Modulo:', 'Allenatore:', 'Ore:')): break
        if re.match(r'^[A-ZÀ-Ü][\w\'. ]{2,22}$', l) and not re.match(r'^(Luned|Marted|Mercoled|Gioved|Venerd|Sabato|Domenica)', l):
            out.append(l)
    return out[:2]

def analizza(testo, rosa, adesso=None):
    adesso = adesso or datetime.now()
    res = {}
    for b in blocchi(testo):
        sq = squadre(b); ts = ts_blocco(b)
        if len(sq) < 2: continue
        stale = bool(ts and (adesso - ts).total_seconds() > 48*3600)
        nsq = [norm(s) for s in sq]
        panchina = ' ;; '.join(re.findall(r'^Panchina:.*$', b, re.M))
        ballo = ' ;; '.join(re.findall(r'^Ballottaggio:.*$', b, re.M))
        fuori = ' ;; '.join(re.findall(r'^(?:Indisponibili|Squalificati):.*$', b, re.M))
        # le righe successive a "Indisponibili:" quando l'etichetta e su riga propria
        fuori += ' ;; ' + ' '.join(re.findall(r'^(?:Indisponibili|Squalificati):\s*\n(.+)$', b, re.M))
        # Nel testo estratto da curl nome e numero di maglia stanno su righe SEPARATE:
        # i titolari sono le righe non numeriche fra l'intestazione e la panchina.
        corpo = b.split('Panchina:')[0].split('DISPOSIZIONE')[0]
        righe = [l.strip() for l in corpo.split('\n')]
        start = max((i for i, l in enumerate(righe) if l.startswith('Allenatore:')), default=0)
        undici = '\n'.join(l for l in righe[start+1:]
                           if l and not l.isdigit() and len(l) < 28
                           and not l.startswith(('Modulo:', 'Ore:', 'Allenatore:'))
                           and not re.match(r'^(Luned|Marted|Mercoled|Gioved|Venerd|Sabato|Domenica)', l))
        for g in rosa:
            if norm(g['squadra']) not in nsq and not any(norm(g['squadra'])[:5] in s for s in nsq):
                continue
            ks = chiavi(g.get('nome_fonte'), g['nome'])
            c = ks[0]
            info = {'gz': None, 'stale': stale, 'nota': '',
                    'ts': ts.isoformat() if ts else None, 'match': ' - '.join(sq)}
            hit = lambda testo: any(k in norm(testo) for k in ks)
            if hit(fuori):
                info['gz'], info['nota'] = 0.0, 'indisponibile o squalificato (Gazzetta)'
            else:
                perc = None
                for m in re.finditer(r'([\w\'à-ÿ-]+)\s*[-–]\s*([\w\'à-ÿ-]+)\s*(\d{2})\s*%?\s*[-–]\s*(\d{2})', norm(ballo)):
                    if m.group(1) == c: perc = int(m.group(3))/100
                    elif m.group(2) == c: perc = int(m.group(4))/100
                if perc is not None:
                    info['gz'], info['nota'] = perc, f'ballottaggio {round(perc*100)}% (Gazzetta)'
                elif hit(panchina):
                    info['gz'], info['nota'] = 0.12, 'in panchina (Gazzetta)'
                elif hit(undici):
                    info['gz'], info['nota'] = 0.90, 'titolare (Gazzetta)'
            if stale and info['gz'] is not None:
                info['nota'] += ' — dato piu vecchio di 48h, peso dimezzato'
            res[g['nome']] = info
    return res

if __name__ == '__main__':
    testo = open(sys.argv[1]).read()
    rosa = json.load(open(sys.argv[2] if len(sys.argv) > 2 else 'rosa.json'))['rosa']
    r = analizza(testo, rosa)
    print(json.dumps(r, ensure_ascii=False, indent=1))
    ok = sum(1 for v in r.values() if v['gz'] is not None)
    print(f"\n# {ok}/{len(rosa)} giocatori risolti da Gazzetta", file=sys.stderr)
