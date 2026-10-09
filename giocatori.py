#!/usr/bin/env python3
"""P(gioca) da 4 fonti editoriali + floor di mercato; P(gol) media bwin+snai; indice di rilevanza."""
import json, os, sys
from statistics import mean
S = json.load(open('/tmp/mstate.json'))
# Statistiche stagionali (media voto e fantamedia) da parse_statistiche.py, se disponibili.
ST = {}
if os.path.exists('statistiche.json'):
    ST = json.load(open('statistiche.json'))
# --- Tabella bonus/malus della lega di Luca ------------------------------------------
# Presa dal regolamento della sua lega, non dai valori standard: qui gol subito vale -1
# (non -0.5) e la porta inviolata +1 (non 3, che era un peso arbitrario).
B_GOL        =  3.0    # gol segnato, rigore segnato incluso (le quote "marcatore" li contano gia)
B_ASSIST     =  1.0    # assist, gold e soft valgono tutti 1
B_CLEANSHEET =  1.0    # porta inviolata
B_GOLSUBITO  = -1.0    # per ogni gol subito (portiere)
B_RIGPARATO  =  3.0    # rigore parato
B_AMMONIZ    = -0.5
B_ESPULS     = -1.0
B_GOLVITT    =  0.5    # gol della vittoria (quello del pareggio vale 0)
P_RIG_PARATO = 0.035   # probabilita che un portiere pari un rigore in una partita
R_ROSSO      = 0.06    # espulsioni per ogni ammonizione attesa (rapporto storico)
Q_DECISIVO   = 0.30    # quota dei gol che risultano "della vittoria"
# Non modellati, perche non prevedibili dalle quote: player of the match (+1),
# autogol (-2), rigore sbagliato (-3). Sono eventi rari o non quotati.

# --- Pesi del punteggio finale (vedi METODO.md par. 5-ter) --------------------------
# Fanta atteso = P_gioca * (6.0 + W_MV * (MV_attesa - 6.0)) + W_Q * IR
# Il 6.0 e comune a tutti e non ordina nulla: a ordinare sono P_gioca, lo scarto di MV
# rispetto a 6 e l'IR. Misurato sulla 4a giornata: lo scarto medio della MV da 6.00 e 0.13,
# quello dell'IR da 0 e 0.82 — le quote sono ~6 volte piu informative dello storico.
# W_Q deve restare 1.0: l'IR e gia espresso in punti fanta secondo la tabella della lega,
# quindi moltiplicarlo gonfia la scala e il numero smette di significare "punti attesi".
# Con W_Q=2.5 la media dei 25 saliva a 7.50 contro una fantamedia reale di 6.30, e difensori
# e centrocampisti arrivavano a 9, valori che nessuno di loro fa.
# Per dare piu peso alla prospettiva si abbassa W_MV, non si alza W_Q.
W_MV = 0.5          # peso dello scarto di media voto: dimezzato perche su 2-3 presenze e rumoroso
W_Q  = 1.0          # peso delle quote: 1.0 mantiene la scala in punti fanta reali
R_PANCHINA = 5.5    # rendimento atteso di chi subentra col cambio automatico
K_SHRINK = 3.0      # con poche presenze la MV e rumorosa: si tira verso 6.0 (k = presenze equivalenti)
MV_BASE = 6.0
W = {'fc': .28, 'sf': .22, 'gz': .30, 'sky': .20}   # pesi fonti editoriali
STALE = .5                                           # moltiplicatore per dato piu vecchio di 48h
CAP = {'A': [(.35,.92),(.25,.80),(.18,.65),(.12,.50)],
       'C': [(.20,.90),(.14,.75),(.10,.60),(.06,.45)],
       'D': [(.09,.90),(.06,.75),(.04,.60),(.025,.45)]}
MODULO = {'P': 1, 'D': 3, 'C': 4, 'A': 3}            # 3-4-3
# Se esiste giocatori_input.json (prodotto da componi.py nel workflow automatico) la lista
# viene letta da li; altrimenti si usa quella qui sotto, compilata a mano nella passata locale.
# `python3 giocatori.py locale` ignora il JSON prodotto dal workflow e usa la lista qui sotto,
# che nella passata locale contiene anche le quote di bwin e Snai.
P_AUTO = None
if 'locale' not in sys.argv and os.path.exists('giocatori_input.json'):
    P_AUTO = [tuple(r) for r in json.load(open('giocatori_input.json'))['giocatori']]
# nome, ruolo, squadra, match, fc, sf, gz, sky, q_gol_bwin, q_gol_snai, q_ass_bwin, q_amm_bwin, gz_vecchia, nota
# Aggiornato 09/10 19:44 (dodicesima passata locale, giornata 6, venerdi': il giorno prima del turno).
# GAZZETTA: invariata, 25/25.
# SKY: nuovo aggiornamento 09/10 19:14 -> Martinez Jo. ora titolare in Inter-Parma (Provedel fuori).
# Resto invariato (Politano, Lulli, Doekhi, Gonzalez, Woltemade in panchina; Bernardeschi titolare).
# FANTACALCIO.IT: invariata (Martinez Jo. titolare, Provedel panchina).
# SOSFANTA: Politano 95% -> 51% (ballottaggio con Beukema); resto invariato.
# QUOTE: bwin letto il 09/10 alle 19:41 via API della pagina (cds-api fixture-view): 1X2, U/O,
# marcatori e assist invariati; cartellino Pavlovic 4.10 -> 4.80, Comuzzo 4.75 -> 4.40,
# Pulisic 5.75 -> 6.75, Ramos G. 5.00 -> 6.00.
# Snai riletto il 09/10 19:43: 1X2, U/O e marcatori tutti invariati.
# Jones C. assente da TUTTI i mercati di bwin e di Snai: conferma l'indisponibilita'.
# Omonimi scartati: "Lautaro Martinez"/"MARTINEZ LAUTARO" (attaccante Inter). Snai elenca ancora un
# "COLOMBO L." fra i marcatori di Lazio-Monza (16.00): NON agganciato (tutte le fonti danno il Colombo del
# Genoa indisponibile e bwin non lo ha in Lazio-Monza). Alajbegovic e' "Kerim" su entrambi i book.
P = [
("Martinez Jo.","P","Inter","Inter-Parma",.90,.51,.90,.90,None,None,None,12.5,0,"Titolare per Gazzetta, fantacalcio.it e Sky (novita' 09/10 19:14, prima lo dava in panchina); SosFanta 51% (con Provedel). bwin lo quota sul cartellino (12.50), Provedel no."),
("Provedel","P","Inter","Inter-Parma",.12,.49,.12,.12,None,None,None,None,0,"In panchina per Gazzetta, fantacalcio.it e ora anche Sky (09/10 19:14); SosFanta 49%. Assente dai mercati bwin."),
("Skorupski","P","Bologna","Lecce-Bologna",.90,.51,.90,.90,None,None,None,9.5,0,"Titolare per Gazzetta, Sky e fantacalcio.it (novita' pomeriggio del 09/10, era 60%); SosFanta 51% con Pessina. Cartellino bwin 9.50."),
("Lulli","D","Roma","Como-Roma",.35,.45,.12,.12,18.5,25.0,7.0,4.33,0,"In panchina per Gazzetta e Sky; fantacalcio.it 35%, SosFanta 45% (con Molina)."),
("Comuzzo","D","Torino","Torino-Udinese",.90,.95,.90,.90,15.5,25.0,13.5,4.4,0,"Titolare per tutte e quattro le fonti."),
("Doekhi","D","Lazio","Lazio-Monza",.55,.49,.12,.12,9.75,9.0,14.0,5.25,0,"Fuori per Gazzetta e Sky; fantacalcio.it 55%, SosFanta 49% (con Sutalo). Ma marcatore 9.75 bwin / 9.00 Snai: quota da difensore titolare."),
("Pavlovic","D","Milan","Sassuolo-Milan",.90,.95,.90,.90,14.5,25.0,14.0,4.8,0,"Titolare per tutte e quattro le fonti. Cartellino 4.80."),
("Vojvoda","D","Udinese","Torino-Udinese",.60,.95,.90,.90,10.5,9.0,6.75,4.6,0,"Titolare per Gazzetta, Sky e SosFanta (95%); fantacalcio.it ballottaggio 60%. Marcatore 10.50 bwin / 9.00 Snai."),
("Kalulu","D","Juventus","Cagliari-Juventus",.90,.95,.90,.90,15.5,25.0,7.25,5.25,0,"Titolare per tutte e quattro le fonti."),
("Chalobah","D","Como","Como-Roma",.90,.95,.90,.90,12.5,12.0,16.5,5.5,0,"Titolare per tutte e quattro le fonti."),
("Gallo","D","Lecce","Lecce-Bologna",.90,.95,.90,.90,19.5,25.0,9.25,5.5,0,"Titolare per tutte e quattro le fonti."),
("Alajbegovic","C","Juventus","Cagliari-Juventus",.45,.51,.45,.90,3.4,3.25,4.4,5.25,0,"Titolare per Sky; ballottaggio per fantacalcio.it (45%), SosFanta (51% con Conceicao) e Gazzetta (45%). Marcatore 3.40 bwin / 3.25 Snai."),
("Gudmundsson A.","C","Lazio","Lazio-Monza",0.0,0.0,0.0,0.0,None,None,None,None,0,"🔴 Infortunato alla spalla per tutte e quattro le fonti; assente dai mercati di bwin e Snai."),
("Kone M.","C","Roma","Como-Roma",.90,.95,.90,.90,8.0,9.0,9.25,3.4,0,"Titolare per tutte e quattro le fonti. Cartellino 3.40: il piu' esposto della rosa. bwin lo chiama Kouadio Kone, Snai Manu Kone."),
("Jones C.","C","Inter","Inter-Parma",0.0,0.0,0.0,0.0,None,None,None,None,0,"🔴 Novita' 09/10: indisponibile per Gazzetta, fantacalcio.it e SosFanta (problema all'adduttore), indisponibile anche per Sky (aggiornamento 09/10 15:18). Assente da tutti i mercati di bwin e Snai."),
("Gonzalez N.","C","Juventus","Cagliari-Juventus",.55,.40,.55,.12,3.7,3.25,5.25,3.8,0,"⚠️ Ballottaggio: fantacalcio.it 55% (novita' 09/10, era panchina), Gazzetta 55%, SosFanta 40% (con McKennie), panchina per Sky. I book lo quotano su tutti i mercati (Snai 3.25)."),
("Pulisic","C","Milan","Sassuolo-Milan",.90,.95,.90,.90,2.8,2.5,3.9,6.75,0,"Titolare per tutte e quattro le fonti. Marcatore 2.80 bwin / 2.50 Snai."),
("Politano","C","Napoli","Napoli-Frosinone",.55,.51,.90,.12,3.8,3.0,3.5,7.25,0,"⚠️ Titolare per Gazzetta; ballottaggio per fantacalcio.it (55%) e SosFanta (51% con Beukema, era 95%); in panchina per Sky. Marcatore 3.80 bwin / 3.00 Snai contro il Frosinone: il mercato lo da' in campo."),
("Bernardeschi","C","Bologna","Lecce-Bologna",.90,.49,.12,.90,3.9,4.0,4.8,5.75,0,"⚠️ Titolare per Sky e fantacalcio.it; in panchina per Gazzetta, SosFanta 49% con Orsolini e Cambiaghi."),
("Pellegrino M.","A","Fiorentina","Genoa-Fiorentina",.60,.51,.90,.90,3.1,3.0,7.0,4.2,0,"Titolare per Gazzetta e Sky; ballottaggio con Beto per fantacalcio.it (60%) e SosFanta (51%). Marcatore 3.10 bwin / 3.00 Snai."),
("Woltemade","A","Juventus","Cagliari-Juventus",.12,.05,.12,.12,2.85,2.75,5.5,4.8,0,"⚠️ Panchina per tutte e quattro le fonti (SosFanta 5%, fantacalcio.it non piu' in ballottaggio): ma la quota marcatore resta corta (2.85 bwin, 2.75 Snai). Conflitto fonti/mercato."),
("Ramos G.","A","Milan","Sassuolo-Milan",.90,.95,.90,.90,2.55,2.5,6.5,6.0,0,"Titolare per tutte e quattro le fonti. Marcatore 2.55 bwin / 2.50 Snai."),
("Kolo Muani","A","Juventus","Cagliari-Juventus",.90,.95,.90,.90,3.1,2.5,6.25,5.0,0,"Titolare per tutte e quattro le fonti (SosFanta 95%). Marcatore 3.10 bwin / 2.50 Snai."),
("Colombo","A","Genoa","Genoa-Fiorentina",0.0,0.0,0.0,0.0,None,None,None,None,0,"🔴 Infortunato alla caviglia per tutte e quattro le fonti; assente dai marcatori di Genoa-Fiorentina su bwin e Snai."),
("Thuram","A","Inter","Inter-Parma",.90,.95,.90,.90,1.55,1.8,3.4,6.5,0,"Titolare per tutte e quattro le fonti (SosFanta 95%). Marcatore 1.55 bwin / 1.80 Snai contro il Parma, la quota piu' corta della rosa."),
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
    # Il margine da usare per il de-vig e quello del book di provenienza; se quel book non
    # e fra le quote 1X2 di questa esecuzione (tipico quando le quote giocatore arrivano dalla
    # cache locale e le 1X2 da un'altra fonte) si ripiega sul primo margine disponibile.
    Mp_ = m['Mp']; Mp_def = next(iter(Mp_.values()))
    est = [devig(q, Mp_.get(b, Mp_def)) for q, b in ((qgb, 'bwin'), (qgs, 'snai')) if q]
    pg = mean(est) if est else None
    spread_g = (max(est)-min(est)) if len(est) > 1 else 0.
    pa = devig(qab, Mp_.get('bwin', Mp_def)); pc = devig(qcb, Mp_.get('bwin', Mp_def))
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
    pgio = min(pgio, .97)
    cs = m['cs_home'] if casa else m['cs_away']
    pvit = m['p1'] if casa else m['p2']
    sub = m['lam_away'] if casa else m['lam_home']
    ctx = pvit - .33                                       # contesto: quanto e favorita la squadra
    amm = pc or 0
    malus = B_AMMONIZ*amm + B_ESPULS*(amm*R_ROSSO)
    bonus_gol = B_GOL*(pg or 0) + B_GOLVITT*(pg or 0)*pvit*Q_DECISIVO
    if r == 'P':
        ir = pgio*(B_CLEANSHEET*cs + B_GOLSUBITO*sub + B_RIGPARATO*P_RIG_PARATO
                   + B_AMMONIZ*amm + 2.2*ctx)
    elif r == 'D':
        ir = bonus_gol + B_ASSIST*(pa or 0) + malus + pgio*(B_CLEANSHEET*cs + 1.8*ctx)
    else:
        k = .9 if r == 'C' else .7
        ir = bonus_gol + B_ASSIST*(pa or 0) + malus + pgio*k*ctx
    # Voto base atteso: la media voto stagionale, ritirata verso 6.0 quando le presenze
    # sono poche. La fantamedia NON si somma: contiene gia i bonus, che l'IR stima in
    # prospettiva su questa partita; sommarle sarebbe un doppio conteggio. Resta come
    # riferimento storico e come segnale quando diverge molto dalla stima.
    st = ST.get(n) or {}
    mv, fm, pgio_st = st.get('mv'), st.get('fm'), st.get('pg') or 0
    mv_att = ((mv*pgio_st + MV_BASE*K_SHRINK)/(pgio_st + K_SHRINK)) if mv else MV_BASE
    # Se il giocatore non scende in campo non prendi zero: entra la riserva col cambio
    # automatico. Il costo di una presenza incerta e quindi la DIFFERENZA rispetto alla
    # riserva, non l'intero punteggio. Senza questa correzione il termine P_gioca*6,0
    # pesava piu della differenza fra una partita facile e una difficile.
    fanta = (R_PANCHINA
             + pgio*(MV_BASE - R_PANCHINA + W_MV*(mv_att - MV_BASE))
             + W_Q*ir)
    rows.append(dict(n=n, r=r, sq=sq, mt=mt, when=m['when'], pgio=pgio, pg=pg, pa=pa, pc=pc,
                     cs=cs, pvit=pvit, ir=ir, flag=flag, nota=nota, qg=qgb, qgs=qgs, qa=qab, qc=qcb,
                     spread_g=spread_g, books=len(est), mv=mv, fm=fm, pres=pgio_st,
                     mv_att=mv_att, fanta=fanta))
rows.sort(key=lambda x: -x['fanta'])
# formazione 3-4-3: i migliori per IR in ogni ruolo, con P(gioca) >= 0.40
# Un solo ordinamento (fanta atteso) decide tutto: la selezione e le etichette.
# Il rischio di presenza e una dimensione SEPARATA, non va mescolata col consiglio.
titolari, panchina = [], []
for r, k in MODULO.items():
    cand = [x for x in rows if x['r'] == r]   # gia ordinati per fanta atteso
    ok = [x for x in cand if x['pgio'] >= .40]
    sel = (ok + [x for x in cand if x not in ok])[:k]
    resto = [x for x in cand if x not in sel]
    for x in sel: x['titolare'], x['slot'] = True, 'titolare'
    for i, x in enumerate(resto):
        x['slot'] = 'riserva' if (i == 0 and x['pgio'] >= .40) else (
                    'alternativa' if x['pgio'] >= .40 else 'fuori')
    titolari += sel; panchina += resto
for x in rows:
    x.setdefault('titolare', False); x.setdefault('slot', 'fuori')
    x['rischio'] = ('sicuro' if x['pgio'] >= .75 else
                    'ballottaggio' if x['pgio'] >= .40 else 'panchina')
json.dump({'rows': rows, 'titolari': [x['n'] for x in titolari]}, open('/tmp/rows.json','w'))
f = lambda v: '  n.d.' if v is None else f'{v*100:5.1f}%'
print(f"{'#':<3}{'GIOCATORE':<17}{'R':<2}{'SQUADRA':<11}{'GIOCA':>7}{'MV':>6}{'FM':>6}"
      f"{'GOL':>7}{'ASS':>7}{'AMM':>7}{'IR':>7}{'FANTA':>7}  ")
print('-'*99)
for i, x in enumerate(rows, 1):
    star = '★' if x['titolare'] else ' '
    mv = f"{x['mv']:.2f}" if x['mv'] else '  —'
    fm = f"{x['fm']:.2f}" if x['fm'] else '  —'
    print(f"{i:<3}{x['n']+x['flag']:<17}{x['r']:<2}{x['sq']:<11}{f(x['pgio'])}{mv:>6}{fm:>6}"
          f"{f(x['pg'])}{f(x['pa'])}{f(x['pc'])}{x['ir']:>7.2f}{x['fanta']:>7.2f} {star}")
print('\nFORMAZIONE 3-4-3:')
for r in 'PDCA':
    print(f"  {r}: " + ', '.join(x['n'] for x in titolari if x['r'] == r))
