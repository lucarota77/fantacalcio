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
# Aggiornato 27/10 14:16 (passata locale, giornata 9 infrasettimanale: Sassuolo-Lazio mar 27/10 -
#   Fiorentina-Atalanta gio 29/10).
# GAZZETTA e FANTACALCIO.IT ricopiate da gz.json/fc.json (25/25 risolti, invariati rispetto alle 10:42;
#   Gazzetta aggiornata 26/10 18:13 - 27/10 10:19, nessuna partita oltre le 48h), TRANNE:
# - Martinez Jo. e Provedel: i parser agganciano Martinez a "Lautaro Martinez" (indisponibile) e lo
#   danno a 0. Valori veri letti sulle pagine: Gazzetta "1 Martinez" in panchina (0.12), Provedel titolare;
#   fantacalcio.it (27/10 09:51) Provedel 70% / Martinez Jo. 30% ("Provedel preferito a Martinez").
# - Ramos G.: Gazzetta lo mette in panchina con ballottaggio a tre "Hutchinson-Camarda-Ramos 40-35-25%"
#   ("Cisse in vantaggio su Ramos"); il parser legge 35%, il valore di Ramos e 25% -> 0.25.
# SKY: giornata 9 (aggiornata 27/10 13:16, undici invariati). Nessun ballottaggio in pagina: titolare 0.90,
#   fuori dall'undici 0.12, indisponibili per tutte le altre fonti 0.0.
# SOSFANTA: lista-formazioni, partite 27-29/10 (giornata 9), riletta 27/10 14:20: percentuali invariate
#   (Lulli 95%, Doekhi 45%, Politano 95%, Ramos 51%, Provedel 51/Martinez 49, Thuram 45%).
# QUOTE: bwin letto il 27/10 alle 14:22 via API della pagina (cds-api fixture-view, fixture
#   2:7896045-7896994; 1X2 = "Risultato della partita", anytime = "Segna in qualsiasi momento",
#   assist = "1 o più assist", cartellino = "Riceve un cartellino"), tutte e 10 le partite.
# Snai letto il 27/10 14:25-14:30 (lista + 10 schede evento): marcatori presenti su tutte e 10 le partite.
# COLOMBO: sparito dai mercati bwin di Genoa-Juventus (era 4.00), ancora quotato da Snai 5.00; in panchina
#   per Gazzetta e Sky. Il "COLOMBO L." 12.00 Snai di Monza-Napoli e l'omonimo del Monza, scartato.
# ALAJBEGOVIC: Gazzetta ora 40% (ballottaggio con Gatti); panchina per fantacalcio.it, SosFanta (5%) e Sky,
#   ma bwin 3.50 / Snai 3.25 come marcatore (quota da titolare): conflitto gestito dal floor di METODO §2-bis.
# Kone M., Chalobah, Gudmundsson A., Jones C., Gonzalez N.: indisponibili per Gazzetta, fantacalcio.it e
#   SosFanta, fuori dall'undici Sky; nessuno dei due book li quota.
# Omonimi scartati: "Lautaro Martinez" (attaccante Inter), "Thuram K." (Juventus, infortunato).
# Alajbegovic e' "Kerim" su entrambi i book. Provedel ora quotato da bwin solo come cartellino (12.00).
P = [
("Martinez Jo.","P","Inter","Venezia-Inter",.30,.49,.12,.12,None,None,None,9.75,0,"⚠️ Panchina per Gazzetta e Sky (Provedel titolare); fantacalcio.it 30% (Provedel 70%, \"preferito a Martinez\"); SosFanta 49% (ballottaggio con Provedel). Cartellino bwin 9.75."),
("Provedel","P","Inter","Venezia-Inter",.70,.51,.90,.90,None,None,None,12.0,0,"Titolare per Gazzetta e Sky; fantacalcio.it 70%; SosFanta 51% (ballottaggio con Martinez Jo.). Cartellino bwin 12.00."),
("Skorupski","P","Bologna","Milan-Bologna",.90,.95,.90,.90,None,None,None,8.0,0,"Titolare per Gazzetta, fantacalcio.it, SosFanta e Sky. Cartellino bwin 8.00."),
("Lulli","D","Roma","Roma-Cagliari",.90,.95,.60,.90,8.75,9.0,4.6,7.0,0,"Titolare per fantacalcio.it, SosFanta (95%) e Sky; Gazzetta 60% (ballottaggio con Wesley). Marcatore 8.75 bwin / 9.00 Snai, assist 4.60."),
("Comuzzo","D","Torino","Torino-Como",.90,.95,.90,.90,17.0,33.0,17.0,4.75,0,"Titolare per Gazzetta, fantacalcio.it, SosFanta e Sky. Marcatore 17.00 bwin / 33.00 Snai, cartellino 4.75."),
("Doekhi","D","Lazio","Sassuolo-Lazio",.40,.45,.12,.12,9.75,9.0,14.5,5.0,0,"⚠️ In panchina per Gazzetta e Sky; fantacalcio.it 40%; SosFanta 45% (ballottaggio con Sutalo). Marcatore 9.75 bwin / 9.00 Snai: quota da titolare, conflitto fra fonti e mercato."),
("Pavlovic","D","Milan","Milan-Bologna",.90,.95,.90,.90,9.75,7.5,13.0,4.4,0,"Titolare per Gazzetta, fantacalcio.it, SosFanta e Sky. Marcatore 9.75 bwin / 7.50 Snai, cartellino 4.40."),
("Vojvoda","D","Udinese","Parma-Udinese",.90,.95,.90,.90,10.0,9.0,6.5,4.8,0,"Titolare per Gazzetta, fantacalcio.it, SosFanta e Sky. Marcatore 10.00 bwin / 9.00 Snai, assist 6.50."),
("Kalulu","D","Juventus","Genoa-Juventus",.90,.95,.90,.90,12.0,12.0,7.25,5.5,0,"Titolare per Gazzetta, fantacalcio.it, SosFanta e Sky. Marcatore 12.00 bwin / 12.00 Snai."),
("Chalobah","D","Como","Torino-Como",0.0,0.0,0.0,0.0,None,None,None,None,0,"🔴 Infortunato: indisponibile per Gazzetta, fantacalcio.it e SosFanta (in dubbio per la 10a), fuori dall'undici Sky. Assente dai mercati di bwin e Snai."),
("Gallo","D","Lecce","Frosinone-Lecce",.90,.95,.90,.90,16.0,25.0,7.5,5.0,0,"Titolare per Gazzetta, fantacalcio.it, SosFanta e Sky. Marcatore 16.00 bwin / 25.00 Snai."),
("Alajbegovic","C","Juventus","Genoa-Juventus",.12,.05,.40,.12,3.5,3.5,4.1,5.5,0,"⚠️ Gazzetta 40% (ballottaggio con Gatti); panchina per fantacalcio.it, SosFanta (5%) e Sky. Marcatore 3.50 bwin / 3.50 Snai e assist 4.10: quota da titolare, conflitto fra fonti e mercato."),
("Gudmundsson A.","C","Lazio","Sassuolo-Lazio",0.0,0.0,0.0,0.0,None,None,None,None,0,"🔴 Lussazione alla spalla: indisponibile per Gazzetta, fantacalcio.it e SosFanta (in dubbio per la 10a), fuori dall'undici Sky. Assente dai mercati di bwin e Snai."),
("Kone M.","C","Roma","Roma-Cagliari",0.0,0.0,0.0,0.0,None,None,None,None,0,"🔴 Lesione alla coscia: indisponibile per Gazzetta, fantacalcio.it e SosFanta (in dubbio per l'11a), fuori dall'undici Sky. Assente dai mercati di bwin e Snai."),
("Jones C.","C","Inter","Venezia-Inter",0.0,0.0,0.0,0.0,None,None,None,None,0,"🔴 Adduttori: indisponibile per Gazzetta, fantacalcio.it e SosFanta (in dubbio per l'11a), fuori dall'undici Sky. Assente dai mercati bwin."),
("Gonzalez N.","C","Juventus","Genoa-Juventus",0.0,0.0,0.0,0.0,None,None,None,None,0,"🔴 Lesione di basso grado al soleo destro: indisponibile per Gazzetta, fantacalcio.it e SosFanta (in dubbio fino alla 12a), fuori dall'undici Sky. Assente dai mercati di bwin e Snai."),
("Pulisic","C","Milan","Milan-Bologna",.40,.95,.90,.90,2.95,2.5,3.7,6.75,0,"Titolare per Gazzetta, SosFanta (95%) e Sky; fantacalcio.it 40%. Marcatore 2.95 bwin / 2.50 Snai: quota da titolare."),
("Politano","C","Napoli","Monza-Napoli",.90,.95,.90,.90,4.1,3.5,4.1,5.0,0,"Titolare per Gazzetta, fantacalcio.it, SosFanta (95%) e Sky. Marcatore 4.10 bwin / 3.50 Snai."),
("Bernardeschi","C","Bologna","Milan-Bologna",.60,.95,.90,.90,5.0,6.0,6.5,4.1,0,"Titolare per Gazzetta, SosFanta (95%) e Sky; fantacalcio.it 60%. Marcatore 5.00 bwin / 6.00 Snai."),
("Pellegrino M.","A","Fiorentina","Fiorentina-Atalanta",.45,.55,.90,.90,2.8,2.75,6.5,6.25,0,"Titolare per Gazzetta e Sky (Beto in panchina); fantacalcio.it 45%, SosFanta 55% (ballottaggio con Beto). Marcatore 2.80 bwin / 2.75 Snai: il mercato lo dà titolare."),
("Woltemade","A","Juventus","Genoa-Juventus",.90,.95,.90,.90,2.95,2.75,6.0,5.75,0,"Titolare per Gazzetta, fantacalcio.it, SosFanta e Sky. Marcatore 2.95 bwin / 2.75 Snai."),
("Ramos G.","A","Milan","Milan-Bologna",.90,.51,.25,.90,2.3,2.4,6.25,5.75,0,"⚠️ Fonti divise: titolare per fantacalcio.it e Sky; SosFanta 51% (ballottaggio con Cisse); Gazzetta in panchina (\"Cisse in vantaggio su Ramos\", Hutchinson-Camarda-Ramos 40-35-25%). Marcatore 2.30 bwin / 2.40 Snai: il mercato lo dà titolare."),
("Kolo Muani","A","Juventus","Genoa-Juventus",.90,.95,.90,.90,3.0,2.75,5.75,5.75,0,"Titolare per Gazzetta, fantacalcio.it, SosFanta e Sky. Marcatore 3.00 bwin / 2.75 Snai."),
("Colombo","A","Genoa","Genoa-Juventus",.55,.49,.12,.12,None,5.0,None,None,0,"⚠️ In panchina per Gazzetta e Sky; fantacalcio.it 55%, SosFanta 49%. Sparito dai mercati bwin (era 4.00), Snai lo quota ancora 5.00 in Genoa-Juventus (il COLOMBO L. di Monza-Napoli è l'omonimo del Monza)."),
("Thuram","A","Inter","Venezia-Inter",.40,.45,.30,.12,1.77,1.8,4.0,6.0,0,"⚠️ Panchina per Sky (Bonny-Esposito); Gazzetta 30% (Bonny-Thuram 70-30); fantacalcio.it 40%; SosFanta 45%. Marcatore 1.77 bwin / 1.80 Snai: quota da titolare, conflitto fra fonti e mercato."),
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
