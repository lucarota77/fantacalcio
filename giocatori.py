#!/usr/bin/env python3
"""P(gioca) da 4 fonti editoriali + floor di mercato; P(gol) media bwin+snai; indice di rilevanza."""
import json, sys
from statistics import mean
S = json.load(open('/tmp/mstate.json'))
W = {'fc': .28, 'sf': .22, 'gz': .30, 'sky': .20}   # pesi fonti editoriali
STALE = .5                                           # moltiplicatore per dato piu vecchio di 48h
CAP = {'A': [(.35,.92),(.25,.80),(.18,.65),(.12,.50)],
       'C': [(.20,.90),(.14,.75),(.10,.60),(.06,.45)],
       'D': [(.09,.90),(.06,.75),(.04,.60),(.025,.45)]}
MODULO = {'P': 1, 'D': 3, 'C': 4, 'A': 3}            # 3-4-3
# Se esiste giocatori_input.json (prodotto da componi.py nel workflow automatico) la lista
# viene letta da li; altrimenti si usa quella qui sotto, compilata a mano nella passata locale.
import os
# `python3 giocatori.py locale` ignora il JSON prodotto dal workflow e usa la lista qui sotto,
# che nella passata locale contiene anche le quote di bwin e Snai.
P_AUTO = None
if 'locale' not in sys.argv and os.path.exists('giocatori_input.json'):
    P_AUTO = [tuple(r) for r in json.load(open('giocatori_input.json'))['giocatori']]
# nome, ruolo, squadra, match, fc, sf, gz, sky, q_gol_bwin, q_gol_snai, q_ass_bwin, q_amm_bwin, gz_vecchia, nota
P = [
("Martinez Jo.","P","Inter","Inter-Udinese",None,.95,.90,.90,None,None,None,13.0,0,""),
("Provedel","P","Inter","Inter-Udinese",None,None,.05,.12,None,None,None,13.0,0,"Secondo portiere dell'Inter dopo il trasferimento dalla Lazio: in panchina per Gazzetta, nessuna fonte lo da titolare."),
("Skorupski","P","Bologna","Napoli-Bologna",.90,.95,.90,.90,None,None,None,8.5,0,""),
("Lulli","D","Roma","Torino-Roma",None,.51,.90,.12,14.5,16.0,5.5,6.25,1,"Gazzetta lo da titolare ma la sua formazione Roma e ferma al 7/9; Sky lo lascia fuori."),
("Comuzzo","D","Torino","Torino-Roma",None,.95,.90,.90,19.5,33.0,21.0,3.9,1,"Quota ammonizione fra le piu basse del turno (3.90): alto rischio malus."),
("Doekhi","D","Lazio","Lazio-Milan",.90,.95,.90,.90,14.0,16.0,13.0,4.4,0,""),
("Pavlovic","D","Milan","Lazio-Milan",.90,.95,.90,.90,12.0,12.0,13.0,4.33,0,""),
("Vojvoda","D","Udinese","Inter-Udinese",None,.95,.90,.90,15.0,16.0,11.0,4.2,0,"Titolare sicuro ma l'Udinese e la squadra con la probabilita di vittoria piu bassa del turno."),
("Kalulu","D","Juventus","Sassuolo-Juventus",None,.95,.90,.90,13.5,12.0,6.5,5.75,0,""),
("Miranda J.","D","Bologna","Napoli-Bologna",.55,.51,.90,.90,18.0,25.0,8.0,4.0,0,"Gazzetta e Sky lo danno titolare, fantacalcio.it e SosFanta in ballottaggio."),
("Gallo","D","Lecce","Lecce-Monza",.90,None,.90,.90,16.5,25.0,7.5,5.25,0,""),
("Alajbegovic","C","Juventus","Sassuolo-Juventus",None,.95,.90,.90,3.6,3.5,4.6,5.75,0,""),
("Gudmundsson A.","C","Lazio","Lazio-Milan",.35,.30,.12,.12,5.25,4.5,9.25,5.0,0,"Tutte e quattro le fonti lo danno fuori dagli undici, ma i book lo prezzano da titolare (4.50 Snai)."),
("Kone M.","C","Roma","Torino-Roma",None,.00,None,.90,8.25,9.0,7.0,4.2,1,"SosFanta lo segnalava infortunato: smentito, entrambi i book lo quotano regolarmente (8.25 / 9.00)."),
("Jones C.","C","Inter","Inter-Udinese",None,.51,.45,.12,5.25,4.0,5.0,5.75,0,"Ballottaggio Sucic-Jones 55-45% secondo Gazzetta."),
("Gonzalez N.","C","Juventus","Sassuolo-Juventus",None,.95,.60,.90,2.95,3.5,4.8,4.75,0,"Ballottaggio Nico-Woltemade 60-40% per il posto da rifinitore."),
("Pulisic","C","Milan","Lazio-Milan",.45,None,.12,.12,None,3.25,None,None,0,"bwin non lo lista in alcun mercato, ma Snai lo quota 3.25 marcatore: NON e indisponibile, e un ballottaggio. Assist e ammonizione non quotati da nessuno dei due."),
("Politano","C","Napoli","Napoli-Bologna",.70,None,.90,.90,4.75,4.0,4.8,4.8,0,""),
("Bernardeschi","C","Bologna","Napoli-Bologna",.90,.95,.90,.90,5.75,6.0,6.5,4.8,0,""),
("Pellegrino M.","A","Fiorentina","Venezia-Fiorentina",.60,None,.45,.12,3.0,2.5,7.0,4.4,0,"Ballottaggio Beto-Pellegrino 55-45% (Gazzetta), ma Snai lo quota 2.50: il mercato lo vede in campo. Si gioca stasera."),
("Woltemade","A","Juventus","Sassuolo-Juventus",None,.51,.40,.12,3.0,2.5,5.0,6.25,0,"Dato in panchina da Gazzetta e Sky, ma quotato 2.50 da Snai come Kolo Muani."),
("Ramos G.","A","Milan","Lazio-Milan",.90,.95,.90,.90,2.95,3.0,7.75,5.75,0,""),
("Kolo Muani","A","Juventus","Sassuolo-Juventus",None,.51,.90,.90,2.75,2.5,6.0,5.75,0,""),
("Colombo","A","Genoa","Genoa-Frosinone",.90,None,.90,.90,2.70,3.0,7.0,6.5,0,""),
("Thuram","A","Inter","Inter-Udinese",None,.51,.55,.12,1.93,2.0,4.4,6.75,0,"Ballottaggio Thuram-Esposito 55-45%, ma e il secondo marcatore piu quotato del match (1.93/2.00)."),
]
def devig(q, Mp): return None if not q else (1/q)/Mp
def floor_mkt(pg, r):
    if pg is None or r not in CAP: return None
    for t, f in CAP[r]:
        if pg >= t: return f
    return .30

if P_AUTO: P = P_AUTO
rows = []
for (n, r, sq, mt, fc, sf, gz, sky, qgb, qgs, qab, qcb, stale, nota) in P:
    m = S[mt]; casa = (m['home'] == sq)
    # P(gol): media delle stime devig dei due bookmaker
    est = [devig(q, m['Mp'][b]) for q, b in ((qgb,'bwin'), (qgs,'snai')) if q]
    pg = mean(est) if est else None
    spread_g = (max(est)-min(est)) if len(est) > 1 else 0.
    pa = devig(qab, m['Mp']['bwin']); pc = devig(qcb, m['Mp']['bwin'])
    # media pesata delle fonti editoriali
    src = {'fc': fc, 'sf': sf, 'gz': gz, 'sky': sky}
    wts = {k: (W[k]*STALE if (k == 'gz' and stale) else W[k]) for k in src if src[k] is not None}
    media = (sum(wts[k]*src[k] for k in wts)/sum(wts.values())) if wts else None
    fl = floor_mkt(pg, r); flag = ''
    if fl is None:   pgio = media if media is not None else .50
    elif media is None: pgio = fl
    elif fl <= media:   pgio = media                       # il mercato e solo un floor
    elif fl - media > .32: pgio = .6*fl + .4*media; flag = ' ⚠️'
    else: pgio = fl
    if n == "Provedel": pgio, flag = .05, ''
    pgio = min(pgio, .97)
    cs = m['cs_home'] if casa else m['cs_away']
    pvit = m['p1'] if casa else m['p2']
    sub = m['lam_away'] if casa else m['lam_home']
    ctx = pvit - .33                                       # contesto: quanto e favorita la squadra
    if r == 'P':
        ir = pgio*(3.0*cs - sub*.5 + .5 + 2.2*ctx)
    elif r == 'D':
        ir = 3*(pg or 0) + (pa or 0) - .5*(pc or 0) + pgio*(1.5*cs + 1.8*ctx)
    else:
        k = .9 if r == 'C' else .7
        ir = 3*(pg or 0) + (pa or 0) - .5*(pc or 0) + pgio*k*ctx
    rows.append(dict(n=n, r=r, sq=sq, mt=mt, when=m['when'], pgio=pgio, pg=pg, pa=pa, pc=pc,
                     cs=cs, pvit=pvit, ir=ir, flag=flag, nota=nota, qg=qgb, qgs=qgs, qa=qab, qc=qcb,
                     spread_g=spread_g, books=len(est)))
rows.sort(key=lambda x: -x['ir'])
# formazione 3-4-3: i migliori per IR in ogni ruolo, con P(gioca) >= 0.40
titolari, panchina = [], []
for r, k in MODULO.items():
    cand = [x for x in rows if x['r'] == r]
    ok = [x for x in cand if x['pgio'] >= .40]
    sel = (ok + [x for x in cand if x not in ok])[:k]
    for x in sel: x['titolare'] = True
    titolari += sel
    panchina += [x for x in cand if x not in sel]
for x in rows: x.setdefault('titolare', False)
json.dump({'rows': rows, 'titolari': [x['n'] for x in titolari]}, open('/tmp/rows.json','w'))
f = lambda v: '  n.d.' if v is None else f'{v*100:5.1f}%'
print(f"{'#':<3}{'GIOCATORE':<17}{'R':<2}{'SQUADRA':<11}{'P.VITT':>7}{'GIOCA':>7}{'GOL':>7}{'ASS':>7}{'AMM':>7}{'CS':>6}{'IR':>7}  ")
print('-'*96)
for i, x in enumerate(rows, 1):
    star = '★' if x['titolare'] else ' '
    print(f"{i:<3}{x['n']+x['flag']:<17}{x['r']:<2}{x['sq']:<11}{f(x['pvit'])}{f(x['pgio'])}"
          f"{f(x['pg'])}{f(x['pa'])}{f(x['pc'])}{x['cs']*100:>5.0f}%{x['ir']:>7.2f} {star}")
print('\nFORMAZIONE 3-4-3:')
for r in 'PDCA':
    print(f"  {r}: " + ', '.join(x['n'] for x in titolari if x['r'] == r))
