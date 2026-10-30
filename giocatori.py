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
# Aggiornato 30/10 09:19 (passata locale, giornata 10: Bologna-Monza sab 31/10 - Atalanta-Parma lun 02/11).
# GAZZETTA e FANTACALCIO.IT copiate da gz.json/fc.json (25/25; Gazzetta 28/10 19:53 - 30/10 09:04), TRANNE
#   Martinez Jo.: i parser lo agganciano a Lautaro (indisponibile). Pagine: Gazzetta "1 Martinez" in panchina
#   (0.12), fantacalcio.it panchina 5%.
# SKY: pagina ancora sulla giornata 9 (aggiornata 29/10 20:44) -> None per tutti, pesi rinormalizzati.
# SOSFANTA: lista-formazioni, partite 31/10-02/11, letta il 30/10 mattina.
# QUOTE: bwin 30/10 mattina via cds-api fixture-view (10 partite; mercati giocatore aperti su 7, mancano
#   Como-Venezia, Lazio-Cagliari, Atalanta-Parma). Snai 30/10 mattina: lista + 8 schede evento.
# Omonimi scartati: Leonardo Colombo / "COLOMBO L." di Bologna-Monza (Monza).
# --- Note della giornata 9 (storiche) ---
# Alle 17:22 gz.json/fc.json/statistiche.json identici alla passata delle 16:10. NOVITA:
# - SKY aggiornata alle 17:09: Juventus 3-5-1-1 con Alajbegovic nell'undici e Kolo Muani fuori, con
#   ballottaggio esplicito "Kolo Muani e in ballottaggio con Alajbegovic" -> Alajbegovic 0.62, Kolo Muani 0.38.
# - SOSFANTA riletta alle 17:24: ballottaggi nuovi Kolo Muani-Alajbegovic 51-49 (erano 95/5) e
#   Cisse-Pulisic 51-49 (Pulisic era 95). Ramos G. resta 51%, il resto invariato.
# GAZZETTA e FANTACALCIO.IT ricopiate da gz.json/fc.json (25/25 risolti; Gazzetta aggiornata 26/10 18:47 -
#   27/10 13:10, nessuna partita oltre le 48h; fantacalcio.it fino alle 15:00). Rispetto alla P precedente
#   fantacalcio.it vale Pulisic 55% (era 40), Ramos G. 65% (era 90), Kolo Muani 60% (era 90). TRANNE:
# - Martinez Jo. e Provedel: i parser agganciano Martinez a "Lautaro Martinez" (indisponibile) e lo
#   danno a 0. Valori veri letti sulle pagine: Gazzetta "1 Martinez" in panchina (0.12), Provedel titolare;
#   fantacalcio.it (27/10 09:51) Provedel 70% / Martinez Jo. 30% ("Provedel preferito a Martinez").
# - Ramos G.: Gazzetta lo mette in panchina con ballottaggio a tre "Hutchinson-Camarda-Ramos 40-35-25%"
#   ("Cisse in vantaggio su Ramos"); il parser legge 35%, il valore di Ramos e 25% -> 0.25.
# SKY: giornata 9 (aggiornata 27/10 17:09). Unico ballottaggio in pagina Kolo Muani-Alajbegovic (0.38/0.62);
#   per gli altri titolare 0.90, fuori dall'undici 0.12, indisponibili per tutte le altre fonti 0.0.
# SOSFANTA: lista-formazioni, partite 27-29/10 (giornata 9), riletta 27/10 17:24
#   (Lulli 95%, Doekhi 45%, Politano 95%, Ramos 51%, Pulisic 49%, Provedel 51/Martinez 49, Thuram 45%).
# QUOTE: bwin letto il 27/10 alle 17:25 via API della pagina (cds-api fixture-view, fixture
#   2:7896045-7896994; 1X2 = "Risultato della partita", anytime = "Segna in qualsiasi momento",
#   assist = "1 o più assist", cartellino = "Riceve un cartellino"), tutte e 10 le partite.
# Snai letto il 27/10 17:26-17:28 (lista + 10 schede evento): marcatori presenti su tutte e 10 le partite.
# COLOMBO: sparito dai mercati bwin di Genoa-Juventus (era 4.00), ancora quotato da Snai 5.00; in panchina
#   per Gazzetta e Sky. Il "COLOMBO L." 12.00 Snai di Monza-Napoli e l'omonimo del Monza, scartato.
# ALAJBEGOVIC: Gazzetta ora 40% (ballottaggio con Gatti); panchina per fantacalcio.it, SosFanta (5%) e Sky,
#   ma bwin 3.50 / Snai 3.25 come marcatore (quota da titolare): conflitto gestito dal floor di METODO §2-bis.
# Kone M., Chalobah, Gudmundsson A., Jones C., Gonzalez N.: indisponibili per Gazzetta, fantacalcio.it e
#   SosFanta, fuori dall'undici Sky; nessuno dei due book li quota.
# Omonimi scartati: "Lautaro Martinez" (attaccante Inter), "Thuram K." (Juventus, infortunato).
# Alajbegovic e' "Kerim" su entrambi i book. Provedel ora quotato da bwin solo come cartellino (12.00).
P = [
("Martinez Jo.","P","Inter","Milan-Inter",.05,.05,.12,None,None,None,None,9.0,0,"⚠️ Panchina per Gazzetta (\"1 Martinez\"), fantacalcio.it (5%) e SosFanta (5%): Provedel titolare. Cartellino bwin 9.00."),
("Provedel","P","Inter","Milan-Inter",.90,.95,.90,None,None,None,None,8.5,0,"Titolare per Gazzetta, fantacalcio.it e SosFanta (95%). Cartellino bwin 8.50."),
("Skorupski","P","Bologna","Bologna-Monza",.90,.95,.90,None,None,None,None,11.5,0,"Titolare per Gazzetta, fantacalcio.it e SosFanta. Cartellino bwin 11.50."),
("Lulli","D","Roma","Udinese-Roma",.40,.51,.90,None,9.0,9.0,4.75,5.75,0,"⚠️ Titolare per Gazzetta; fantacalcio.it 40% e SosFanta 51% (ballottaggio con Molina). Marcatore 9.00 bwin / 9.00 Snai, assist 4.75."),
("Comuzzo","D","Torino","Frosinone-Torino",.90,.95,.90,None,13.5,25.0,15.0,4.1,0,"Titolare per Gazzetta, fantacalcio.it e SosFanta. Marcatore 13.50 bwin / 25.00 Snai, cartellino 4.10."),
("Doekhi","D","Lazio","Lazio-Cagliari",.12,.51,.12,None,None,9.0,None,None,0,"⚠️ In panchina per Gazzetta e fantacalcio.it; SosFanta 51% (ballottaggio con Sutalo). bwin non ha ancora aperto i mercati giocatore di Lazio-Cagliari; Snai marcatore 9.00."),
("Pavlovic","D","Milan","Milan-Inter",.90,.95,.90,None,13.5,9.0,19.0,3.1,0,"Titolare per Gazzetta, fantacalcio.it e SosFanta. Marcatore 13.50 bwin / 9.00 Snai, cartellino 3.10."),
("Vojvoda","D","Udinese","Udinese-Roma",.90,.95,.90,None,10.5,9.0,8.0,4.8,0,"Titolare per Gazzetta, fantacalcio.it e SosFanta. Marcatore 10.50 bwin / 9.00 Snai, assist 8.00."),
("Kalulu","D","Juventus","Juventus-Napoli",.90,.95,.90,None,15.5,25.0,7.5,4.6,0,"Titolare per Gazzetta, fantacalcio.it e SosFanta. Marcatore 15.50 bwin / 25.00 Snai, assist 7.50."),
("Chalobah","D","Como","Como-Venezia",0.0,0.0,0.0,None,None,None,None,None,0,"🔴 Infortunato: indisponibile per Gazzetta, fantacalcio.it e SosFanta (in dubbio per l'11a). bwin non ha ancora aperto i mercati giocatore di Como-Venezia."),
("Gallo","D","Lecce","Lecce-Genoa",.90,.95,.90,None,16.0,25.0,8.5,5.5,0,"Titolare per Gazzetta, fantacalcio.it e SosFanta. Marcatore 16.00 bwin / 25.00 Snai, assist 8.50."),
("Alajbegovic","C","Juventus","Juventus-Napoli",.90,.49,.12,None,4.2,4.0,5.25,4.6,0,"⚠️ Titolare per fantacalcio.it; SosFanta 49% (ballottaggio Woltemade-Alajbegovic 51-49); in panchina per Gazzetta. Marcatore 4.20 bwin / 4.00 Snai, assist 5.25: quota da titolare."),
("Gudmundsson A.","C","Lazio","Lazio-Cagliari",0.0,0.0,0.0,None,None,None,None,None,0,"🔴 Lussazione alla spalla: indisponibile per Gazzetta, fantacalcio.it e SosFanta (in dubbio per la 12a). Assente dai mercati Snai."),
("Kone M.","C","Roma","Udinese-Roma",0.0,0.0,0.0,None,None,None,None,None,0,"🔴 Lesione alla coscia: indisponibile per Gazzetta (da valutare), fantacalcio.it e SosFanta (in dubbio per l'11a). Assente dai mercati di bwin e Snai."),
("Jones C.","C","Inter","Milan-Inter",0.0,0.0,0.0,None,None,None,None,None,0,"🔴 Adduttori: indisponibile per Gazzetta, fantacalcio.it e SosFanta (in dubbio per l'11a). Assente dai mercati di bwin e Snai."),
("Gonzalez N.","C","Juventus","Juventus-Napoli",0.0,0.0,0.0,None,None,None,None,None,0,"🔴 Lesione al soleo destro: indisponibile per Gazzetta, fantacalcio.it e SosFanta (in dubbio per la 12a). Assente dai mercati di bwin e Snai."),
("Pulisic","C","Milan","Milan-Inter",.12,.60,.90,None,3.7,3.25,5.25,4.4,0,"⚠️ Titolare per Gazzetta (\"certezza\" il ritorno dal primo minuto); SosFanta 60% (ballottaggio con Cisse); in panchina per fantacalcio.it. Marcatore 3.70 bwin / 3.25 Snai: quota da titolare."),
("Politano","C","Napoli","Juventus-Napoli",.90,.95,.90,None,5.75,5.0,5.75,4.6,0,"Titolare per Gazzetta, fantacalcio.it e SosFanta. Marcatore 5.75 bwin / 5.00 Snai."),
("Bernardeschi","C","Bologna","Bologna-Monza",.90,.55,.90,None,3.2,2.75,4.1,4.4,0,"Titolare per Gazzetta e fantacalcio.it; SosFanta 55% (ballottaggio con Orsolini). Marcatore 3.20 bwin / 2.75 Snai, assist 4.10."),
("Pellegrino M.","A","Fiorentina","Sassuolo-Fiorentina",.60,.60,.90,None,2.75,2.75,6.5,4.75,0,"Titolare per Gazzetta; fantacalcio.it e SosFanta 60% (ballottaggio con Beto). Marcatore 2.75 bwin / 2.75 Snai: il mercato lo dà titolare."),
("Woltemade","A","Juventus","Juventus-Napoli",.12,.51,.90,None,3.3,3.25,7.0,5.0,0,"⚠️ Titolare per Gazzetta; SosFanta 51% (ballottaggio con Alajbegovic); in panchina per fantacalcio.it. Marcatore 3.30 bwin / 3.25 Snai: quota da titolare."),
("Ramos G.","A","Milan","Milan-Inter",.90,.95,.90,None,3.2,3.0,9.0,3.75,0,"Titolare per Gazzetta, fantacalcio.it e SosFanta (95%). Marcatore 3.20 bwin / 3.00 Snai."),
("Kolo Muani","A","Juventus","Juventus-Napoli",.90,.95,.90,None,3.6,3.25,7.25,4.5,0,"Titolare per Gazzetta, fantacalcio.it e SosFanta (95%). Marcatore 3.60 bwin / 3.25 Snai."),
("Colombo","A","Genoa","Lecce-Genoa",.12,.49,.60,None,3.0,3.0,6.75,5.0,0,"⚠️ Gazzetta 60% (Colombo-Vitinha 60-40); SosFanta 49% (ballottaggio con Vitinha); in panchina per fantacalcio.it. Marcatore 3.00 bwin / 3.00 Snai: quota da titolare (il Colombo di Bologna-Monza è Leonardo, del Monza)."),
("Thuram","A","Inter","Milan-Inter",.90,.95,.90,None,2.3,2.4,5.5,3.5,0,"Titolare per Gazzetta, fantacalcio.it e SosFanta (95%). Marcatore 2.30 bwin / 2.40 Snai."),
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
