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
# Aggiornato 11/09 18:27 (seconda passata locale): rifatti gazzetta/fantacalcio.it/statistiche,
# aggiunti sosfanta e sky (browser, articolo delle 13:45), quote bwin/Snai marcatore/assist/
# ammonizione riscrapate su tutti gli 8 match con almeno uno dei 25.
P = [
("Martinez Jo.","P","Inter","Inter-Udinese",.90,.95,.90,.90,None,None,None,11.5,0,""),
("Provedel","P","Inter","Inter-Udinese",.12,None,.12,None,None,None,None,11.5,0,"Secondo portiere dell'Inter dopo il trasferimento dalla Lazio: mai favorito da alcuna fonte."),
("Skorupski","P","Bologna","Napoli-Bologna",.90,.95,.90,.90,None,None,None,7.75,0,""),
("Lulli","D","Roma","Torino-Roma",.45,.51,.60,.12,15.0,16.0,5.5,4.4,0,"Gazzetta e' passata da titolare (16:57) a ballottaggio 60% nell'ultimo aggiornamento; SosFanta lo da 51% favorito su Molina N.; Sky lo lascia fuori dalla probabile Roma pubblicata alle 13:45. Divergenza sulla fascia sinistra della difesa a tre."),
("Comuzzo","D","Torino","Torino-Roma",.90,.95,.90,.90,18.5,33.0,21.0,3.8,0,"Quota ammonizione fra le piu basse del turno: alto rischio malus."),
("Doekhi","D","Lazio","Lazio-Milan",.90,.95,.90,.90,14.0,16.0,13.5,4.75,0,""),
("Pavlovic","D","Milan","Lazio-Milan",.90,.95,.90,.90,12.0,12.0,13.0,4.0,0,""),
("Vojvoda","D","Udinese","Inter-Udinese",.90,.95,.90,.90,14.5,16.0,10.0,3.3,0,"Titolare sicuro ma l'Udinese e la squadra con la probabilita di vittoria piu bassa del turno."),
("Kalulu","D","Juventus","Sassuolo-Juventus",.90,.95,.90,.90,13.5,12.0,6.5,5.75,0,""),
("Miranda J.","D","Bologna","Napoli-Bologna",.55,.51,.90,.62,17.5,25.0,7.5,4.1,0,"Gazzetta lo da titolare; fantacalcio.it e SosFanta lo lasciano in ballottaggio stretto (51-55%) con Alhassane; Sky descrive il ballottaggio come 'vivo' ma lo schiera comunque nella probabile Bologna."),
("Gallo","D","Lecce","Lecce-Monza",.90,.95,.90,.90,16.5,25.0,7.5,6.25,0,""),
("Alajbegovic","C","Juventus","Sassuolo-Juventus",.45,.95,.90,.90,3.6,3.25,4.6,5.0,0,"fantacalcio.it lo da in ballottaggio (45%) mentre le altre tre fonti e le quote lo confermano titolare: probabile margine di cautela editoriale, non un vero dubbio. Nota: sia bwin che Snai lo etichettano 'Alajbegovic K.' invece di Benjamin: refuso del book su entrambe le piattaforme, stesso e unico Alajbegovic della Juventus in rosa.json."),
("Gudmundsson A.","C","Lazio","Lazio-Milan",.35,.30,.12,.12,5.25,4.5,9.5,4.33,0,"Tutte e quattro le fonti editoriali concordano: parte in panchina, pronto a entrare a gara in corso (Sky: 'un altro ingresso a gara in corso'; SosFanta lo da 30% nel ballottaggio con Pinamonti). I book lo quotano regolarmente da subentrante."),
("Kone M.","C","Roma","Torino-Roma",.50,None,.12,.12,8.0,9.0,7.0,4.0,0,"⚠️ CONFLITTO: Gazzetta lo segna in panchina, SosFanta lo mette 'in dubbio' per un fastidio al ginocchio (senza %) e la probabile Roma di Sky (13:45) non lo include neppure fra i titolari o i ballottaggi (schiera Pisilli). Solo fantacalcio.it lo da 'in dubbio' al 50%. Entrambi i book lo quotano pero regolarmente da titolare (8.00 bwin come 'Kouadio Kone', 9.00 Snai come 'KONE MANU'): il mercato non lo considera fuori. Da verificare a ridosso della gara."),
("Jones C.","C","Inter","Inter-Udinese",.45,.49,.45,.62,5.0,4.0,4.6,5.75,0,"Fonti divise: Sky lo schiera titolare pur descrivendo un ballottaggio con Sucic a suo favore; Gazzetta e SosFanta lo danno sfavorito (45-49%) rispettivamente con Sucic e Calhanoglu. Le quote marcatore (5.00/4.00) sono coerenti con un titolare."),
("Gonzalez N.","C","Juventus","Sassuolo-Juventus",.90,.95,.90,.90,2.95,3.25,4.75,4.6,0,"Il vecchio ballottaggio con Woltemade e superato: tutte le fonti lo confermano titolare; Woltemade ora e in ballottaggio con Kolo Muani per la punta centrale."),
("Pulisic","C","Milan","Lazio-Milan",.45,None,.12,.12,None,3.25,None,None,0,"bwin non lo lista in alcun mercato e non compare ne' nella probabile Milan di Sky ne' nei ballottaggi (titolo Sky: 'Che fine ha fatto Pulisic? Zero minuti nel Milan di Amorim'), ma Snai lo quota regolarmente 3.25 marcatore: non risulta indisponibile, resta un'opzione dalla panchina. Assist e ammonizione non quotati da nessuno dei due book."),
("Politano","C","Napoli","Napoli-Bologna",.90,.95,.90,.90,4.4,4.0,4.75,4.8,0,""),
("Bernardeschi","C","Bologna","Napoli-Bologna",.90,.95,.90,.90,5.25,5.0,6.5,4.2,0,""),
("Pellegrino M.","A","Fiorentina","Venezia-Fiorentina",.40,.49,.45,.12,2.87,2.4,7.0,4.6,0,"Sky non lo cita fra i candidati Fiorentina (parla solo del ballottaggio Goncalves-Njie e da Beto titolare), ma le altre tre fonti (fc 40%, sf 49%, gz 45%) e le quote (2.87/2.40 marcatore, fra le piu basse del turno per un ballottaggio) lo danno in lotta equilibrata con Beto per la maglia da centravanti. Si gioca stasera."),
("Woltemade","A","Juventus","Sassuolo-Juventus",.55,.49,.40,.38,3.1,2.75,5.0,5.5,0,"Sky lo da sfavorito ('tutti gli indizi portano a Kolo Muani' per la punta centrale); SosFanta conferma il ballottaggio 49% con Kolo Muani; i book lo quotano comunque da titolare credibile (3.10/2.75 marcatore)."),
("Ramos G.","A","Milan","Lazio-Milan",.90,.95,.90,.90,2.95,3.0,7.75,5.0,0,""),
("Kolo Muani","A","Juventus","Sassuolo-Juventus",.90,.51,.90,.90,2.75,2.5,6.0,5.25,0,"SosFanta e Sky lo danno lievemente favorito su Woltemade per la punta centrale ('tutti gli indizi'); le quote marcatore restano vicinissime."),
("Colombo","A","Genoa","Genoa-Frosinone",.90,.95,.90,.90,2.70,3.0,7.0,5.5,0,"Attenzione omonimo: un 'Colombo L.' (Leonardo, Monza) compare nei mercati di Lecce-Monza a quote diverse (12.0 anytime) — scartato, non e' il nostro Lorenzo Colombo del Genoa."),
("Thuram","A","Inter","Inter-Udinese",.40,.49,.55,.12,1.85,2.0,4.33,5.5,0,"⚠️ CONFLITTO NETTO: l'articolo Sky delle 13:45 e esplicito — 'Thuram parte dalla panchina. Pio e Lautaro saranno i titolari' (probabile Inter pubblicata senza Thuram in formazione) — mentre Gazzetta (55%) e SosFanta (49% in due ballottaggi separati con Martinez L. ed Esposito F.P.) lo danno vicino alla titolarita. Il mercato marcatore e ancora piu netto in senso opposto a Sky: 1.85 su bwin e 2.00 su Snai sono fra le quote piu basse del turno, un segnale di titolarita fortissimo che scatta il floor di mercato (attaccante, P_gol devig alta) e porta P_gioca sopra la media editoriale nonostante Sky. Verificare le formazioni ufficiali prima del fischio d'inizio: possibile turnover last minute o formazione Sky non aggiornata."),
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
