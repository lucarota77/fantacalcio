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
# Aggiornato 18/09 14:44 (sesta passata locale, giornata 5). Gazzetta/fantacalcio.it/statistiche
# 25/25, nessun dato stale, invariati rispetto alla passata delle 14:10. SosFanta riverificato a
# browser (non solo WebFetch): Martinez Jo. ora titolare 95% (prima assente dalla lista, sf n.d.),
# Provedel sceso a 5% (prima sf n.d.), Gudmundsson A. salito da 12% a 15%. Quote bwin: movimenti
# minimi su Kone M., Pellegrino M. (assist), Kalulu, Woltemade, Kolo Muani (marcatore+cartellino) e
# sul 1X2 Bologna-Torino; tutto il resto (Snai, mercati bwin degli altri 20) confermato invariato.
# RIMOSSI I DUE OVERRIDE HARDCODED su Provedel (.05) e Doekhi (.03): erano valori legati alla
# situazione di inizio settimana e ora i dati li contraddicono — Gazzetta apre un ballottaggio fra
# i portieri dell'Inter (Martinez Jo. 70% / Provedel 30%) e sposta Doekhi da indisponibile a
# panchina. Il P_gioca ora esce dalla media pesata delle fonti, come per tutti gli altri.
# DOEKHI rientrato: bwin lo ha rimesso nei mercati (10.5 marcatore, 16 assist, 4.6 cartellino) dopo
# averlo escluso nelle passate precedenti; SosFanta lo da "in dubbio" (senza percentuale, quindi
# sf=None per non inventare numeri), Gazzetta in panchina al 12%.
# WOLTEMADE rientrato nei mercati bwin (2.95, addirittura piu' corto di Kolo Muani a 3.00) benche'
# Gazzetta e sky lo diano in panchina: divergenza fra mercato e fonti editoriali, segnalata in nota.
# ALAJBEGOVIC: le fonti sono spaccate (Gazzetta panchina 12%, fantacalcio.it 55%, SosFanta 49%,
# sky titolare) e il mercato lo tiene corto (3.40): caso piu' incerto del turno.
# PULISIC: bwin lo tiene ancora fuori dai mercati giocatore per il secondo giorno; Snai lo quota
# 2.00 come suo top marcatore del Milan, quindi non e' un segnale di indisponibilita' (solo le
# colonne bwin a None). Gazzetta lo ha riportato a ballottaggio 60%.
# Omonimi: su Roma-Inter entrambi i book elencano "Martinez Lautaro"/"MARTINEZ LAUTARO" (attaccante
# Inter), scartato: non e' il nostro Martinez Jo. (portiere). Alajbegovic resta "Kerim"/"K." su
# entrambi i book, non "Benjamin" come in rosa.json: refuso probabile, rosa non toccata.
# Provedel: sky lo elenca ancora fra le riserve della LAZIO (club sbagliato dopo la cessione
# all'Inter) e SosFanta non trova Martinez Jo.: entrambe le caselle lasciate None invece di usare
# un dato riferito alla squadra sbagliata.
P = [
("Martinez Jo.","P","Inter","Roma-Inter",.90,.95,.70,.90,None,None,None,7.0,0,"⚠️ Gazzetta apre un ballottaggio fra i pali dell'Inter e lo da al 70% su Provedel (30%); fantacalcio.it e sky lo confermano titolare. SosFanta lo ha ripescato titolare 95% (verificato a browser alle 14:43, prima era assente dalla lista): sf non e' piu' n.d."),
("Provedel","P","Inter","Roma-Inter",.12,.05,.30,None,None,None,None,None,0,"⚠️ Gazzetta lo porta al 30% nel ballottaggio coi pali dell'Inter (era una riserva fissa): non e' piu' una comparsa, ma resta sfavorito su Martinez Jo. SosFanta lo elenca ora in panchina al 5% (verificato a browser): sf aggiornato da n.d. a .05. sky lo elenca ancora fra le riserve della Lazio (club sbagliato dopo la cessione): sky lasciata n.d."),
("Skorupski","P","Bologna","Bologna-Torino",.90,.60,.90,.90,None,None,None,9.25,0,"SosFanta lo mette in ballottaggio al 60% col secondo portiere; le altre tre fonti lo confermano titolare."),
("Lulli","D","Roma","Roma-Inter",.40,.51,.60,.90,17.5,25.0,7.5,4.75,0,"Ballottaggio sulla fascia destra della difesa a tre: fantacalcio.it 40%, SosFanta 51%, Gazzetta 60%; sky lo da titolare pieno."),
("Comuzzo","D","Torino","Bologna-Torino",.90,.95,.90,.90,18.5,33.0,18.5,5.0,0,""),
("Doekhi","D","Lazio","Venezia-Lazio",.40,None,.12,None,10.5,9.0,16.0,4.6,0,"RIENTRO: non e' piu' dato indisponibile. Gazzetta lo sposta da 'indisponibile' a panchina (12%) e bwin lo ha rimesso nei mercati giocatore (10.5 marcatore) dopo averlo escluso. SosFanta lo segna 'in dubbio' e sky 'in ballottaggio', entrambe senza percentuale: caselle lasciate n.d. per non inventare numeri. Rimosso l'override manuale che forzava il P_gioca a .03."),
("Pavlovic","D","Milan","Milan-Lecce",.90,.95,.90,.90,8.0,7.5,10.0,5.0,0,""),
("Vojvoda","D","Udinese","Udinese-Cagliari",.90,.95,.90,.90,8.75,9.0,6.5,4.4,0,"Gazzetta finalmente riaggiornata per Udinese-Cagliari: il dato non e' piu' stale, gz_vecchia torna a 0."),
("Kalulu","D","Juventus","Juventus-Atalanta",.90,.95,.90,.90,13.0,16.0,6.5,5.25,0,""),
("Chalobah","D","Como","Frosinone-Como",.90,.95,.90,.90,9.5,9.0,12.5,5.75,0,"Sostituisce Miranda J. (ceduto) in rosa dal 17/09/2026. Tutte e quattro le fonti lo danno titolare."),
("Gallo","D","Lecce","Milan-Lecce",.90,.95,.90,.90,23.0,33.0,10.5,5.25,0,""),
("Alajbegovic","C","Juventus","Juventus-Atalanta",.55,.49,.12,.90,3.4,3.5,4.5,5.5,0,"⚠️ CASO PIU' INCERTO DEL TURNO: le quattro fonti sono spaccate — Gazzetta lo mette in panchina (12%), SosFanta lo da sfavorito nel ballottaggio (49%), fantacalcio.it favorito (55%), sky titolare pieno. Il mercato lo tiene corto (3.40 marcatore), segno che i book lo aspettano in campo. Sia bwin ('Kerim Alajbegovic') che Snai ('ALAJBEGOVIC K.') usano il nome Kerim, non Benjamin come in rosa.json: probabile refuso da verificare."),
("Gudmundsson A.","C","Lazio","Venezia-Lazio",.12,.15,.12,.12,None,3.0,None,None,0,"Tutte e quattro le fonti concordano: parte in panchina, pronto a subentrare (SosFanta lo aggiorna a 15%, verificato a browser). Assente dal mercato marcatore bwin, quotato 3.00 su Snai."),
("Kone M.","C","Roma","Roma-Inter",.90,.95,.90,.90,10.0,12.0,8.75,3.8,0,"Tutte e quattro le fonti lo danno titolare (bwin lo elenca come 'Kouadio Kone', suo nome di nascita). Cartellino a 3.80 su bwin: e' il piu' 'a rischio ammonizione' della rosa."),
("Jones C.","C","Inter","Roma-Inter",.60,.51,.70,.90,7.5,6.0,8.25,5.0,0,"Ballottaggio con Mkhitaryan che si sta sciogliendo a suo favore: Gazzetta lo alza al 70% (era 55%) e sky lo da titolare; fantacalcio.it 60%, SosFanta 51%."),
("Gonzalez N.","C","Juventus","Juventus-Atalanta",.65,.51,.90,.90,3.7,3.5,5.5,4.4,0,"fantacalcio.it lo abbassa a 65% e SosFanta a 51%, mentre Gazzetta e sky lo confermano titolare."),
("Pulisic","C","Milan","Milan-Lecce",.55,.55,.60,.90,None,2.0,None,None,0,"Ballottaggio con Loftus-Cheek: fantacalcio.it e SosFanta 55%, Gazzetta 60%, sky titolare. ⚠️ bwin lo tiene fuori dai mercati giocatore per il secondo giorno di fila; Snai lo quota 2.00 ed e' il suo top marcatore del Milan, quindi non e' un segnale di indisponibilita': solo le colonne bwin restano n.d."),
("Politano","C","Napoli","Fiorentina-Napoli",.90,.95,.90,.90,4.75,4.0,5.25,5.75,0,"Tutte e quattro le fonti lo danno titolare (SosFanta lo ha promosso da ballottaggio 55% a titolare)."),
("Bernardeschi","C","Bologna","Bologna-Torino",.60,.55,.90,.90,3.8,3.5,4.75,5.0,0,"Si e' aperto un ballottaggio: fantacalcio.it 60% e SosFanta 55% (ieri lo davano titolare), mentre Gazzetta e sky lo confermano in campo."),
("Pellegrino M.","A","Fiorentina","Fiorentina-Napoli",.40,.51,.55,.12,3.25,3.0,8.0,4.75,0,"Ballottaggio con Beto per la maglia da centravanti, ora girato a suo favore: Gazzetta lo porta da panchina a 55% e SosFanta a 51%; fantacalcio.it resta al 40% e sky lo mette in panchina."),
("Woltemade","A","Juventus","Juventus-Atalanta",.45,.49,.12,.12,2.9,2.75,6.0,5.75,0,"⚠️ Mercato contro fonti editoriali: bwin lo ha rimesso fra i marcatori a 2.95, piu' corto di Kolo Muani (3.00), mentre Gazzetta e sky lo danno in panchina e fantacalcio.it/SosFanta lo tengono in ballottaggio quasi alla pari (45-49%)."),
("Ramos G.","A","Milan","Milan-Lecce",.90,.95,.90,.90,1.85,2.0,5.25,6.75,0,"Gazzetta lo riporta a titolare pieno (ieri 80%): tutte e quattro le fonti concordi. Quota marcatore 1.85, la piu' corta della rosa."),
("Kolo Muani","A","Juventus","Juventus-Atalanta",.90,.51,.90,.90,3.1,2.5,6.25,5.75,0,"Gazzetta, fantacalcio.it e sky lo confermano titolare; SosFanta lo tiene in ballottaggio risicato (51-49%) con Woltemade, che il mercato bwin quota addirittura piu' corto di lui."),
("Colombo","A","Genoa","Parma-Genoa",.90,.60,.90,.90,3.0,3.5,7.0,5.0,0,"Gazzetta, fantacalcio.it e sky lo confermano titolare; SosFanta lo mette in ballottaggio al 60% con Vitinha O."),
("Thuram","A","Inter","Roma-Inter",.55,.95,.90,.90,2.75,3.0,6.0,5.25,0,"SosFanta lo promuove titolare pieno (era 60%), con Gazzetta e sky d'accordo; solo fantacalcio.it lo tiene in ballottaggio al 55% con Esposito F.P."),
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
