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
# Aggiornato 16/10 16:35 (passata locale, giornata 7: Frosinone-Sassuolo ven 16/10 - Parma-Torino lun 19/10).
# GAZZETTA (aggiornata 16/10 08:53 - 11:33) e FANTACALCIO.IT ricopiate da gz.json/fc.json, TRANNE
# Martinez Jo. e Provedel: i parser agganciano Martinez a "Lautaro Martinez" (indisponibile) e lo
# danno a 0. Valori veri letti sulle pagine: Gazzetta ballottaggio Martinez-Provedel 70-30,
# fantacalcio.it Martinez Jo. 75% / Provedel 5%. Bug omonimi nei parser da correggere.
# SKY: giornata 7, aggiornata 16/10 16:29 (titolare 0.90, non nell'undici 0.12, indisponibile 0):
# per i 25 nessun cambio rispetto alle 13:30.
# SOSFANTA: lista-formazioni, giornata 7 (16-19/10), invariata rispetto alle 09:44.
# QUOTE: bwin letto il 16/10 alle 16:40 via API della pagina (cds-api fixture-view, fixture
# 2:7872375-7872384), tutte e 10 le partite. Snai letto il 16/10 16:42-16:48 (lista + 8 schede
# evento). Rispetto alle 15:40: Woltemade 2.87->2.85 bwin, Kolo Muani 2.50->2.75 Snai,
# ritoccate le 1X2 di Frosinone-Sassuolo su entrambi i book.
# Kone M.: indisponibile per Gazzetta, fantacalcio.it e SosFanta; Sky lo mette fra i dubbi. bwin lo quota
# ancora ("Kouadio Kone" 6.75), Snai NO: override assoluto P_gioca = 0, quote non caricate.
# Omonimi scartati: "Lautaro Martinez"/"MARTINEZ LAUTARO" (attaccante Inter). Alajbegovic e' "Kerim" su
# entrambi i book. Provedel, Jones C., Gudmundsson A., Colombo assenti da tutti i mercati dei due book.
P = [
("Martinez Jo.","P","Inter","Bologna-Inter",.75,.51,.70,.90,None,None,None,10.5,0,"Titolare per Sky; favorito su Provedel per Gazzetta (70-30, 16/10 11:33) e fantacalcio.it (75%), SosFanta 51%. Cartellino bwin 10.50."),
("Provedel","P","Inter","Bologna-Inter",.05,.49,.30,.12,None,None,None,None,0,"In panchina per fantacalcio.it (5%) e Sky; Gazzetta 30%, SosFanta 49% (ballottaggio con Martinez Jo.). Assente dai mercati bwin."),
("Skorupski","P","Bologna","Bologna-Inter",.40,.49,.45,.12,None,None,None,8.75,0,"⚠️ Ballottaggio con Pessina: Gazzetta 45% (55-45 per Pessina), fantacalcio.it 40%, SosFanta 49%; Sky titolare Pessina. Cartellino bwin 8.75."),
("Lulli","D","Roma","Roma-Genoa",.60,.51,.60,.90,14.0,25.0,5.75,5.5,0,"Titolare per Sky (Molina in panchina); Gazzetta 60% (Lulli-Rensch 60-40), fantacalcio.it 60%, SosFanta 51%. Marcatore 14.00 bwin / 25.00 Snai."),
("Comuzzo","D","Torino","Parma-Torino",.90,.95,.90,.90,15.0,33.0,15.5,4.0,0,"Titolare per tutte e quattro le fonti."),
("Doekhi","D","Lazio","Juventus-Lazio",.55,.49,.40,.12,14.5,16.0,None,4.33,0,"⚠️ Ballottaggio con Sutalo: fantacalcio.it 55%, SosFanta 49%, Gazzetta 40%; Sky titolare Sutalo. Uscito di nuovo dal mercato assist bwin (16/10 15:40). Cartellino 4.33."),
("Pavlovic","D","Milan","Milan-Atalanta",.90,.95,.90,.90,11.5,25.0,12.5,4.5,0,"Titolare per tutte e quattro le fonti."),
("Vojvoda","D","Udinese","Udinese-Lecce",.90,.95,.90,.90,7.75,7.5,5.5,5.25,0,"Titolare per tutte e quattro le fonti. Marcatore 7.75 bwin / 7.50 Snai."),
("Kalulu","D","Juventus","Juventus-Lazio",.90,.95,.90,.90,14.5,25.0,7.25,4.8,0,"Titolare per tutte e quattro le fonti."),
("Chalobah","D","Como","Fiorentina-Como",.55,.51,.90,.90,10.5,9.0,15.0,5.5,0,"Titolare per Gazzetta e Sky; ballottaggio con Kempf per fantacalcio.it (55%) e SosFanta (51%). Marcatore 10.50 bwin / 9.00 Snai."),
("Gallo","D","Lecce","Udinese-Lecce",.90,.95,.90,.90,18.5,25.0,7.75,5.75,0,"Titolare per tutte e quattro le fonti."),
("Alajbegovic","C","Juventus","Juventus-Lazio",.12,.51,.12,.12,3.6,3.25,4.1,4.75,0,"⚠️ Scivolato in panchina: Gazzetta (16/10 09:38), Sky (13:30) e fantacalcio.it lo danno fuori, solo SosFanta 51%. Marcatore 3.60 bwin / 3.25 Snai: quota ancora da titolare."),
("Gudmundsson A.","C","Lazio","Juventus-Lazio",0.0,0.0,0.0,0.0,None,None,None,None,0,"🔴 Infortunato (lussazione alla spalla) per tutte le fonti; assente dai mercati di bwin e Snai."),
("Kone M.","C","Roma","Roma-Genoa",0.0,0.0,0.0,0.0,None,None,None,None,0,"🔴 Indisponibile per Gazzetta, fantacalcio.it e SosFanta (\"in dubbio almeno per l'8a\"); Sky lo mette fra i dubbi. bwin lo quota ancora (Kouadio Kone 6.75), Snai no: override P_gioca = 0."),
("Jones C.","C","Inter","Bologna-Inter",0.0,None,0.0,0.0,None,None,None,None,0,"🔴 Indisponibile per Gazzetta, fantacalcio.it, Sky e SosFanta (adduttori). Assente da tutti i mercati di bwin e Snai."),
("Gonzalez N.","C","Juventus","Juventus-Lazio",.90,.49,.90,.90,3.8,3.25,5.25,3.5,0,"Titolare per Gazzetta, Sky e fantacalcio.it; SosFanta 49% (ballottaggio con Alajbegovic). Marcatore 3.80 bwin / 3.25 Snai."),
("Pulisic","C","Milan","Milan-Atalanta",.90,.95,.90,.90,2.75,2.5,4.1,6.5,0,"Titolare per tutte e quattro le fonti. Marcatore 2.75 bwin / 2.50 Snai."),
("Politano","C","Napoli","Venezia-Napoli",.90,.49,.12,.12,4.2,3.25,4.33,5.25,0,"⚠️ Titolare per fantacalcio.it; in panchina per Gazzetta (16/10 08:53) e Sky (gioca Giovane); SosFanta 49%. Marcatore 4.20 bwin / 3.25 Snai."),
("Bernardeschi","C","Bologna","Bologna-Inter",.90,.95,.90,.90,5.25,6.0,6.5,4.8,0,"Titolare per tutte e quattro le fonti."),
("Pellegrino M.","A","Fiorentina","Fiorentina-Como",.45,.55,.90,.12,3.3,3.25,7.75,4.8,0,"⚠️ Titolare per Gazzetta; SosFanta 55%, fantacalcio.it 45% (Beto 55%); Sky (13:30) lo mette in panchina con Beto e Njie davanti. Marcatore 3.30 bwin / 3.25 Snai: quota da titolare."),
("Woltemade","A","Juventus","Juventus-Lazio",.40,.05,.12,.90,2.85,2.75,6.0,4.8,0,"⚠️ Titolare per Sky (16:29, con Gonzalez e Kolo Muani); panchina per Gazzetta e SosFanta (5%), 40% per fantacalcio.it. La quota marcatore resta corta (2.85 bwin, 2.75 Snai)."),
("Ramos G.","A","Milan","Milan-Atalanta",.90,.95,.90,.90,2.35,2.4,6.5,5.75,0,"Titolare per tutte e quattro le fonti. Marcatore 2.35 bwin / 2.40 Snai."),
("Kolo Muani","A","Juventus","Juventus-Lazio",.90,.95,.90,.90,3.1,2.75,6.25,4.4,0,"Titolare per tutte e quattro le fonti. Marcatore 3.10 bwin / 2.75 Snai."),
("Colombo","A","Genoa","Roma-Genoa",0.0,0.0,0.0,0.0,None,None,None,None,0,"🔴 Infortunato alla caviglia per tutte le fonti; assente dai marcatori di Roma-Genoa su bwin e Snai."),
("Thuram","A","Inter","Bologna-Inter",.60,.95,.90,.90,2.1,2.25,5.0,5.5,0,"Titolare per Gazzetta, Sky e SosFanta (95%); ballottaggio per fantacalcio.it (60%). Marcatore 2.10 bwin / 2.25 Snai."),
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
