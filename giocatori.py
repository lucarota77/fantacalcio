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
# Aggiornato 26/10 10:58 (passata locale, giornata 9 infrasettimanale: Sassuolo-Lazio mar 27/10 -
#   Fiorentina-Atalanta gio 29/10).
# GAZZETTA e FANTACALCIO.IT ricopiate da gz.json/fc.json (25/25 risolti, Gazzetta aggiornata 24/10 21:18 -
#   26/10 10:39, nessuna partita oltre le 48h), TRANNE:
# - Martinez Jo. e Provedel: i parser agganciano Martinez a "Lautaro Martinez" (indisponibile) e lo
#   danno a 0. Valori veri letti sulle pagine: Gazzetta Provedel titolare ("verso la conferma dal 1'") /
#   "1 Martinez" in panchina (0.12); fantacalcio.it (26/10) Provedel 70% / Martinez Jo. 30%.
# SKY: la pagina (aggiornata 25/10 22:17) e ancora sulla giornata 8 -> fonte NON disponibile, None
#   (pesi rinormalizzati su Gazzetta, fantacalcio.it e SosFanta, METODO §1).
# SOSFANTA: lista-formazioni, partite 27-29/10 (giornata 9), letta 26/10 10:55.
# QUOTE: bwin letto il 26/10 alle 10:55 via API della pagina (cds-api fixture-view, fixture
#   2:7896045-7896994; anytime = "Segna in qualsiasi momento", assist = "1 o più assist",
#   cartellino = "Riceve un cartellino"), tutte e 10 le partite: i mercati giocatore sono gia aperti.
# Snai letto il 26/10 10:56-11:00 (lista + 10 schede evento): marcatori presenti su 9 partite;
#   Venezia-Inter non ha ancora la tab GIOCATORI (riprovato due volte) -> Thuram solo bwin.
# COLOMBO: quotato nei marcatori di Genoa-Juventus (bwin 4.00, Snai 5.00) e quindi rientrato; Gazzetta lo
#   mette in panchina, fantacalcio.it 55%, SosFanta 49%. Il "COLOMBO L." 12.00 Snai di Monza-Napoli e
#   l'omonimo del Monza, scartato.
# ALAJBEGOVIC: in panchina per Gazzetta, fantacalcio.it e SosFanta (5%), ma bwin e Snai lo quotano 3.50 come
#   marcatore (quota da titolare): conflitto fra fonti e mercato, gestito dal floor di METODO §2-bis.
# Kone M., Chalobah, Gudmundsson A., Jones C., Gonzalez N.: indisponibili per Gazzetta, fantacalcio.it e
#   SosFanta; nessuno dei due book li quota.
# Omonimi scartati: "Lautaro Martinez" (attaccante Inter), "Thuram K." (Juventus, infortunato).
# Alajbegovic e' "Kerim" su entrambi i book. Provedel assente dai mercati bwin.
P = [
("Martinez Jo.","P","Inter","Venezia-Inter",.30,.51,.12,None,None,None,None,14.0,0,"⚠️ Fonti divise: Gazzetta lo mette in panchina e dà Provedel \"verso la conferma\"; fantacalcio.it 30% (Provedel 70%); SosFanta 51% (ballottaggio con Provedel). Cartellino bwin 14.00. Sky ancora sulla giornata 8 (n.d.)."),
("Provedel","P","Inter","Venezia-Inter",.70,.49,.90,None,None,None,None,None,0,"⚠️ Titolare per Gazzetta (\"verso la conferma dal 1'\") e fantacalcio.it (70%); SosFanta 49%. Assente dai mercati bwin."),
("Skorupski","P","Bologna","Milan-Bologna",.90,.95,.90,None,None,None,None,7.75,0,"Titolare per Gazzetta, fantacalcio.it e SosFanta. Cartellino bwin 7.75."),
("Lulli","D","Roma","Roma-Cagliari",.12,.45,.90,None,9.0,9.0,4.6,6.0,0,"⚠️ Titolare per Gazzetta; in panchina per fantacalcio.it; SosFanta 45% (ballottaggio con Molina). Marcatore 9.00 bwin / 9.00 Snai, assist 4.60."),
("Comuzzo","D","Torino","Torino-Como",.90,.95,.90,None,16.5,33.0,17.0,3.8,0,"Titolare per Gazzetta, fantacalcio.it e SosFanta. Marcatore 16.50 bwin / 33.00 Snai, cartellino 3.80."),
("Doekhi","D","Lazio","Sassuolo-Lazio",.40,.05,.12,None,9.75,9.0,14.5,4.1,0,"⚠️ In panchina per Gazzetta e SosFanta (5%); fantacalcio.it 40%. Marcatore 9.75 bwin / 9.00 Snai: quota da titolare, conflitto fra fonti e mercato."),
("Pavlovic","D","Milan","Milan-Bologna",.90,.95,.90,None,10.5,7.5,13.5,4.1,0,"Titolare per Gazzetta, fantacalcio.it e SosFanta. Marcatore 10.50 bwin / 7.50 Snai, cartellino 4.10."),
("Vojvoda","D","Udinese","Parma-Udinese",.90,.95,.90,None,10.0,9.0,6.25,5.5,0,"Titolare per Gazzetta, fantacalcio.it e SosFanta. Marcatore 10.00 bwin / 9.00 Snai, assist 6.25."),
("Kalulu","D","Juventus","Genoa-Juventus",.90,.95,.90,None,12.0,12.0,7.25,4.6,0,"Titolare per Gazzetta, fantacalcio.it e SosFanta. Marcatore 12.00 bwin / 12.00 Snai."),
("Chalobah","D","Como","Torino-Como",0.0,0.0,0.0,None,None,None,None,None,0,"🔴 Infortunato: indisponibile per Gazzetta, fantacalcio.it e SosFanta (in dubbio per la 10a). Assente dai mercati di bwin e Snai."),
("Gallo","D","Lecce","Frosinone-Lecce",.90,.95,.90,None,15.5,25.0,8.25,5.25,0,"Titolare per Gazzetta, fantacalcio.it e SosFanta. Marcatore 15.50 bwin / 25.00 Snai."),
("Alajbegovic","C","Juventus","Genoa-Juventus",.12,.05,.12,None,3.5,3.5,4.2,4.33,0,"⚠️ In panchina per Gazzetta, fantacalcio.it e SosFanta (5%), ma marcatore 3.50 su bwin e Snai e assist 4.20: quota da titolare, conflitto fra fonti e mercato."),
("Gudmundsson A.","C","Lazio","Sassuolo-Lazio",0.0,0.0,0.0,None,None,None,None,None,0,"🔴 Lussazione alla spalla: indisponibile per Gazzetta, fantacalcio.it e SosFanta (in dubbio per la 10a). Assente dai mercati di bwin e Snai."),
("Kone M.","C","Roma","Roma-Cagliari",0.0,0.0,0.0,None,None,None,None,None,0,"🔴 Lesione alla coscia: indisponibile per Gazzetta, fantacalcio.it e SosFanta (in dubbio per l'11a). Assente dai mercati di bwin e Snai."),
("Jones C.","C","Inter","Venezia-Inter",0.0,0.0,0.0,None,None,None,None,None,0,"🔴 Adduttori: indisponibile per Gazzetta (\"ancora out\"), fantacalcio.it e SosFanta (in dubbio per l'11a). Assente dai mercati bwin."),
("Gonzalez N.","C","Juventus","Genoa-Juventus",0.0,0.0,0.0,None,None,None,None,None,0,"🔴 Lesione di basso grado al soleo destro: indisponibile per Gazzetta, fantacalcio.it e SosFanta (in dubbio fino alla 12a). Ora assente anche dai mercati di bwin e Snai."),
("Pulisic","C","Milan","Milan-Bologna",.40,.95,.90,None,2.95,2.5,4.0,5.25,0,"Titolare per Gazzetta e SosFanta (95%); fantacalcio.it 40%. Marcatore 2.95 bwin / 2.50 Snai: quota da titolare."),
("Politano","C","Napoli","Monza-Napoli",.90,.60,.90,None,4.6,3.5,4.2,5.0,0,"Titolare per Gazzetta e fantacalcio.it; SosFanta 60% (ballottaggio con Giovane). Marcatore 4.60 bwin / 3.50 Snai (scarto ampio fra i book)."),
("Bernardeschi","C","Bologna","Milan-Bologna",.60,.95,.90,None,5.0,6.0,6.5,4.4,0,"Titolare per Gazzetta e SosFanta (95%); fantacalcio.it 60%. Marcatore 5.00 bwin / 6.00 Snai."),
("Pellegrino M.","A","Fiorentina","Fiorentina-Atalanta",.45,.55,.40,None,2.75,2.75,6.5,4.75,0,"⚠️ Ballottaggio con Beto: Gazzetta 40%, fantacalcio.it 45%, SosFanta 55%. Marcatore 2.75 su bwin e Snai: il mercato lo dà titolare."),
("Woltemade","A","Juventus","Genoa-Juventus",.90,.95,.90,None,2.8,3.0,5.5,3.9,0,"Titolare per Gazzetta, fantacalcio.it e SosFanta. Marcatore 2.80 bwin / 3.00 Snai."),
("Ramos G.","A","Milan","Milan-Bologna",.90,.95,.90,None,2.25,2.25,6.5,4.75,0,"Titolare per Gazzetta, fantacalcio.it e SosFanta. Marcatore 2.25 su bwin e Snai."),
("Kolo Muani","A","Juventus","Genoa-Juventus",.90,.95,.90,None,3.0,2.75,5.75,4.1,0,"Titolare per Gazzetta, fantacalcio.it e SosFanta. Marcatore 3.00 bwin / 2.75 Snai."),
("Colombo","A","Genoa","Genoa-Juventus",.55,.49,.12,None,4.0,5.0,8.75,5.25,0,"⚠️ Rientrato dalla distorsione: in panchina per Gazzetta, fantacalcio.it 55%, SosFanta 49% (ballottaggio con El Shaarawy). Marcatore 4.00 bwin / 5.00 Snai in Genoa-Juventus (il COLOMBO L. di Monza-Napoli è l'omonimo del Monza)."),
("Thuram","A","Inter","Venezia-Inter",.40,.95,.55,None,1.82,None,4.5,4.33,0,"Ballottaggio: Gazzetta 55%, fantacalcio.it 40% (Esposito F.P. 60%), SosFanta 95%. Marcatore 1.82 bwin: quota da titolare. Snai non ha ancora aperto i marcatori di Venezia-Inter (n.d.)."),
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
