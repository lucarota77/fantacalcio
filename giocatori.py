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
# Aggiornato 15/09 11:15 (passata locale, giornata 5): gazzetta/fantacalcio.it/statistiche/sosfanta
# rifatti da capo con browser. Sky non disponibile: la pagina probabili-formazioni non ha ancora
# pubblicato la scheda squadra-per-squadra della 5a giornata (link ancora sulla 4a, datato 11/09).
# Quote bwin e Snai 1X2/Over-Under raccolte su tutti gli 8 match con almeno uno dei 25, ma i mercati
# per giocatore (marcatore/assist/cartellino) NON sono ancora aperti su nessuno dei due book a 4-5
# giorni dal turno: verificato su Bologna-Torino e Roma-Inter su bwin (solo "Ultimo Marcatore" con
# "Nessun marcatore", nessun altro mercato Giocatori) e su Roma-Inter su Snai (nessun mercato
# marcatore per giocatore in nessuna tab). Fanta atteso quindi guidato da P_gioca editoriale, MV/FM
# storiche e clean sheet/contesto (questi ultimi due gia disponibili da 1X2/O-U); gol, assist e
# ammonizione restano n.d. per tutti. Da riprovare in una passata locale piu vicina al weekend.
P = [
("Martinez Jo.","P","Inter","Roma-Inter",.90,.95,.90,None,None,None,None,None,0,""),
("Provedel","P","Inter","Roma-Inter",.12,.05,.12,None,None,None,None,None,0,"Secondo portiere dell'Inter: mai favorito da alcuna fonte."),
("Skorupski","P","Bologna","Bologna-Torino",.90,.95,.90,None,None,None,None,None,0,""),
("Lulli","D","Roma","Roma-Inter",.40,.49,.90,None,None,None,None,None,0,"Gazzetta lo da titolare; fantacalcio.it (40%) e SosFanta (49%, sfavorito 51-49 su Molina N.) lo mettono invece in ballottaggio sulla fascia destra della difesa a tre giallorossa. Nessuna quota di mercato disponibile per arbitrare (vedi nota di testata sui mercati giocatore non ancora aperti)."),
("Comuzzo","D","Torino","Bologna-Torino",.90,.95,.90,None,None,None,None,None,0,""),
("Doekhi","D","Lazio","Venezia-Lazio",.40,.05,.0,None,None,None,None,None,0,"⚠️ INFORTUNIO: Gazzetta lo da indisponibile e SosFanta lo elenca fra gli indisponibili della Lazio ('operazione alla mano destra, in dubbio per la 6a', quindi fuori per questo turno); fantacalcio.it non ha ancora aggiornato la scheda e lo mostra ancora in ballottaggio al 40%. P_gioca forzato quasi a zero (override manuale, vedi codice)."),
("Pavlovic","D","Milan","Milan-Lecce",.90,.95,.90,None,None,None,None,None,0,""),
("Vojvoda","D","Udinese","Udinese-Cagliari",.90,.95,.90,None,None,None,None,None,0,""),
("Kalulu","D","Juventus","Juventus-Atalanta",.90,.95,.90,None,None,None,None,None,0,""),
("Miranda J.","D","Bologna","Bologna-Torino",.60,.60,.90,None,None,None,None,None,0,"Gazzetta lo da titolare; fantacalcio.it e SosFanta lo mettono entrambi in ballottaggio al 60% con Alhassane."),
("Gallo","D","Lecce","Milan-Lecce",.90,.95,.90,None,None,None,None,None,0,""),
("Alajbegovic","C","Juventus","Juventus-Atalanta",.60,.95,.90,None,None,None,None,None,0,"fantacalcio.it lo mette in ballottaggio (60%) mentre Gazzetta e SosFanta lo confermano titolare: come gia notato la giornata scorsa, sembra cautela editoriale piu che un vero dubbio."),
("Gudmundsson A.","C","Lazio","Venezia-Lazio",.12,.15,.12,None,None,None,None,None,0,"Tutte le fonti concordano: parte in panchina, pronto a subentrare."),
("Kone M.","C","Roma","Roma-Inter",.90,.60,.90,None,None,None,None,None,0,"Gazzetta e fantacalcio.it lo confermano titolare; SosFanta lo mette invece in ballottaggio (60%) con Pisilli."),
("Jones C.","C","Inter","Roma-Inter",.60,.49,.12,None,None,None,None,None,0,"Fonti divise: Gazzetta lo da in panchina, fantacalcio.it e SosFanta lo mettono invece in ballottaggio (49-60%) con Mkhitaryan."),
("Gonzalez N.","C","Juventus","Juventus-Atalanta",.90,.95,.90,None,None,None,None,None,0,""),
("Pulisic","C","Milan","Milan-Lecce",.55,.60,.12,None,None,None,None,None,0,"Gazzetta lo da ancora in panchina; fantacalcio.it e SosFanta lo mettono invece favorito nel ballottaggio (55-60%) con Loftus-Cheek."),
("Politano","C","Napoli","Fiorentina-Napoli",.90,.55,.90,None,None,None,None,None,0,"Gazzetta e fantacalcio.it lo confermano titolare; SosFanta lo mette in ballottaggio piu stretto (55%) con Favasuli."),
("Bernardeschi","C","Bologna","Bologna-Torino",.90,.95,.90,None,None,None,None,None,0,""),
("Pellegrino M.","A","Fiorentina","Fiorentina-Napoli",.40,.49,.12,None,None,None,None,None,0,"Ballottaggio stretto con Beto per la maglia da centravanti: fantacalcio.it (40%) e SosFanta (49%, sfavorito 51-49) lo danno in lotta aperta; Gazzetta lo mette invece in panchina."),
("Woltemade","A","Juventus","Juventus-Atalanta",.40,.49,.12,None,None,None,None,None,0,"In ballottaggio equilibrato con Kolo Muani per la punta centrale: SosFanta lo da quasi alla pari (49-51%); Gazzetta lo mette in panchina."),
("Ramos G.","A","Milan","Milan-Lecce",.90,.95,.90,None,None,None,None,None,0,""),
("Kolo Muani","A","Juventus","Juventus-Atalanta",.90,.51,.90,None,None,None,None,None,0,"Gazzetta e fantacalcio.it lo confermano titolare; SosFanta conferma il vantaggio ma con margine risicato (51-49%) su Woltemade."),
("Colombo","A","Genoa","Parma-Genoa",.90,.55,.90,None,None,None,None,None,0,"Gazzetta e fantacalcio.it lo confermano titolare; SosFanta lo mette in ballottaggio piu stretto (55%) con Vitinha O."),
("Thuram","A","Inter","Roma-Inter",.55,.60,.90,None,None,None,None,None,0,"Gazzetta lo conferma titolare; fantacalcio.it e SosFanta lo mettono invece in ballottaggio (55-60%) con Esposito F.P."),
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
    if n == "Provedel": pgio, flag = .05, ''
    if n == "Doekhi": pgio, flag = .03, ''  # override: infortunio confermato da Gazzetta+SosFanta
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
