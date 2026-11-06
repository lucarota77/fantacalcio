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
# Aggiornato 30/10 14:55 (passata locale, giornata 10: Bologna-Monza sab 31/10 - Atalanta-Parma lun 02/11).
# Alle 14:55: Gazzetta, fantacalcio.it, statistiche, SosFanta e Sky (14:16) invariati per i 25; Snai identico
#   (1X2, O/U, marcatori); bwin identico su 1X2/O/U, ritoccati cartellino Pavlovic 3.60 e Pellegrino 4.75,
#   assist Kolo Muani 7.25. bwin ha aperto i marcatori di Como-Venezia: Chalobah non quotato (coerente).
# GAZZETTA e FANTACALCIO.IT copiate da gz.json/fc.json (25/25; Gazzetta 28/10 19:53 - 30/10 13:47,
#   fantacalcio.it Milan-Inter 14:08), TRANNE Martinez Jo.: i parser lo agganciano a Lautaro (indisponibile).
#   Pagine: Gazzetta "1 Martinez" in panchina (0.12), fantacalcio.it ballottaggio Provedel 55 / Martinez 45.
# PASSATA 30/10 15:35: Gazzetta, fantacalcio.it, SosFanta e Sky (14:16) identici alle 14:55. bwin (15:40)
#   1X2/O-U invariati, cartellini Martinez 7.75, Provedel 8.25, Skorupski 9.75, Pavlovic 3.70, Pellegrino 4.80,
#   assist Pellegrino 6.25; mercati giocatore aperti ora anche su Atalanta-Parma (nessuno dei 25). Snai marcatori
#   identici; 1X2/O-U mossi su Bologna-Monza, Frosinone-Torino, Lazio-Cagliari, Juventus-Napoli, Sassuolo-Fiorentina.
# PASSATA 30/10 16:35: Gazzetta, fantacalcio.it, statistiche, SosFanta e Sky (14:16) identici. bwin (16:40) 1X2 mossi su
#   7 partite (Bologna-Monza, Udinese-Roma, Como-Venezia, Frosinone-Torino, Lazio-Cagliari, Lecce-Genoa, Sassuolo-Fiorentina),
#   Alajbegovic marcatore 4.10 e assist 5.00, Kolo Muani assist 7.00, ritoccati cartellini e assist di Bernardeschi e Pellegrino.
#   Snai (16:42) Pulisic 3.25 e Kolo Muani 3.00 marcatore, 1X2 Lazio-Cagliari 1.42/4.50/7.50.
# PASSATA 30/10 17:35: Gazzetta, fantacalcio.it, statistiche e SosFanta identici; Sky aggiornata alle 17:13 ma identica
#   per i 25. bwin (17:40) 1X2/O-U, marcatori e assist invariati; cartellini Martinez 7.50, Lulli 5.25, Comuzzo 4.33,
#   Pavlovic 3.80, Alajbegovic 5.00, Bernardeschi 4.75, Ramos 4.50, Thuram 4.10. Snai (17:42) Kolo Muani 3.25 e
#   Colombo 3.25 marcatore, O/U Lecce-Genoa 2.25/1.57.
# PASSATA 30/10 19:20: Gazzetta aggiornata 18:44-19:15 -> Martinez-Provedel 80-20 (il parser aggancia ancora
#   Lautaro: valore letto in pagina), Doekhi titolare, Vojvoda 55%, Colombo 55%. fantacalcio.it (Inter 19:03)
#   Martinez Jo. 75 / Provedel 25 (stesso omonimo nel parser), Lulli 45%. SosFanta e Sky (18:28) invariati.
#   estrai_quote.js corretto: l'etichetta "Slide 1 of 1" sfasava di una posizione assist e cartellini;
#   bwin riletto per intero (Milan-Inter, Sassuolo-Fiorentina, Atalanta-Parma solo dalla pagina Italia).
#   bwin 1X2 Udinese-Roma 5.00/4.20/1.57; Gallo 16.00, Pellegrino 2.80. Snai 1X2 Udinese-Roma e Lecce-Genoa;
#   marcatori Snai invariati.
# PASSATA 31/10 10:22: Gazzetta (fino 31/10 01:26) Lulli-Molina 60-40, Boga-Woltemade 60-40 (Juve col tridente
#   Zhegrova-Kolo Muani-Boga), Martinez-Provedel ancora 80-20. fantacalcio.it (Inter 08:27) Martinez 60 / Provedel 40
#   (parser aggancia Lautaro: valori letti in pagina), Lulli 55%. SosFanta: Martinez 95, Pulisic 95, Bernardeschi 95.
#   Sky (31/10 10:05) invariata. bwin (10:40, cds-api) e Snai (10:45): 1X2/O-U di tutte e 10, marcatori Snai
#   Bernardeschi 2.50 e Pulisic 3.50; Doekhi ancora assente da bwin (Snai 9.00).
# SKY: ora sulla giornata 10 (aggiornata 30/10 13:37, poi 14:16). Nessun ballottaggio fra i 25: titolare 0.90, fuori
#   dall'undici 0.12, indisponibile 0.0. Inter con Josep Martinez in porta (Provedel fuori).
# SOSFANTA: lista-formazioni, partite 31/10-02/11, riletta 30/10 14:15: portiere Inter ribaltato,
#   Martinez 55 / Provedel 45 (stamattina 5/95).
# QUOTE: bwin 30/10 14:20 via cds-api fixture-view (10 partite; mercati giocatore aperti su 8, mancano
#   Como-Venezia e Atalanta-Parma). Lazio-Cagliari aperta ora: Doekhi ASSENTE (ci sono Sutalo e Provstgaard).
#   Snai 30/10 14:22-14:26: lista + 9 schede evento.
# CHALOBAH: Snai lo quota 7.50 marcatore in Como-Venezia, ma e indisponibile per tutte e 4 le fonti
#   (override METODO §1): quota NON caricata, altrimenti il floor lo rimetterebbe in campo.
#   Alle 14:55 bwin ha aperto i marcatori di Como-Venezia e NON lo quota: conferma l'indisponibilita.
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
# ===== GIORNATA 11 — passata locale 05/11/2026 13:15 (Venezia-Udinese ven 06/11 - Fiorentina-Juventus dom 08/11) =====
# GAZZETTA e FANTACALCIO.IT copiate da gz.json/fc.json (25/25; Gazzetta 04/11 12:43 - 05/11 12:47).
# SOSFANTA: lista-formazioni, partite 06-08/11 (giornata 11), letta 05/11 13:05.
# SKY: NON disponibile (la pagina e ancora sulla giornata 10, aggiornata 02/11 20:48) -> None, pesi rinormalizzati.
# QUOTE: Snai 05/11 13:12-13:14 (lista + 9 schede evento; marcatori aperti su tutte). bwin NON letto:
#   col pannello browser nascosto la griglia partite non si disegna (10 segnaposto vuoti, nessun link evento)
#   e la lettura diretta dell'API cds-api e stata negata dal classificatore dei permessi -> assist e cartellini n.d.
# Kone M. (Snai 5.00), Chalobah (12.00), Jones C. (6.00): quotati da Snai ma indisponibili per Gazzetta
#   (override METODO §1) -> quote NON caricate, altrimenti il floor li rimetterebbe in campo.
# "COLOMBO L." di Genoa-Milan e Lorenzo Colombo del Genoa (l'omonimo Leonardo e del Monza, che gioca con l'Atalanta).
# ===== GIORNATA 11 — passata locale 05/11/2026 16:55 =====
# gz.json/fc.json identici alla passata delle 13:15 (git diff vuoto, Gazzetta sempre 04/11 12:43 - 05/11 12:47);
#   SosFanta riletta 05/11 16:56: invariata. Sky ancora sulla giornata 10 (02/11 20:48) -> None.
# bwin LETTO (16:57-17:00) dalle schede evento: 1X2 e O/U 2.5 dal tab Tutto, marcatori/assist/cartellini
#   con estrai_quote.js. La lista partite col pannello nascosto mostra i link ma non le quote.
#   Fiorentina-Juventus e Monza-Atalanta non ancora in palinsesto bwin -> Juventus/Fiorentina solo Snai.
# Snai: lista 1X2/O-U riletta 17:00; marcatori Fiorentina-Juventus riletti (invariati), gli altri dalle 13:12.
# Omonimi scartati su bwin: "Lautaro Martinez" (Inter), "Ismael Kone" (Roma-Sassuolo, non Manu Kone).
# Assenti dai mercati bwin coerentemente con le fonti: Jones C., Chalobah, Gudmundsson A., Kone M., Doekhi.
# COLOMBO assente da tutti i mercati bwin di Genoa-Milan (come in G10), Snai 4.50.
# ===== GIORNATA 11 — passata locale 06/11/2026 10:10 =====
# GAZZETTA aggiornata 06/11 08:47-10:00 (gz.json/fc.json ricopiati, 25/25): Lulli 40% (era titolare),
#   Colombo 55% (era titolare), Jones C. in panchina (era indisponibile). fantacalcio.it invariato.
# SOSFANTA riletta 06/11 ~10:20: Pavlovic 70 (Bartesaghi 30), Pulisic 95, Bernardeschi 70 (Orsolini 30),
#   Pellegrino 95, Kolo Muani 95. Il "Colombo L." in ballottaggio con Akinsanmiro e l'omonimo del Monza:
#   Lorenzo Colombo non e nel Genoa di SosFanta -> 0.05.
# SKY ora sulla giornata 11 (aggiornata 06/11 09:18), letta via browser pagina per pagina (WebFetch
#   restituisce solo la squadra di casa). Nessun ballottaggio fra i 25: titolare 0.90, riserva 0.12,
#   indisponibile 0.0. Lulli, Doekhi, Provedel, Colombo, Jones C. (in dubbio), Chalobah (in dubbio),
#   Kone M. (in dubbio) fra le riserve; Gudmundsson e Nico Gonzalez indisponibili.
# QUOTE bwin 06/11 10:30 su 7 partite (schede evento). Inter-Como, Monza-Atalanta e Fiorentina-Juventus
#   NON in palinsesto bwin stamattina: per Inter-Como restano le quote bwin del 05/11 17:00 (ultima
#   rilevazione reale: Thuram 2.15, assist 5.25, cartellini Thuram 4.10 e Martinez 11.00).
# Snai 06/11 10:40: lista 1X2/O-U di 9 partite (Monza-Atalanta assente: resta il dato del 05/11) e
#   8 schede evento. Lulli 9.00 (era 7.50), Pulisic 3.00 (era 2.75).
# Kone M.: ora quotato da entrambi i book (bwin "Kouadio Kone" 5.25, Snai 5.00) ma infortunato per
#   Gazzetta, fantacalcio.it e SosFanta, in dubbio per Sky -> quote NON caricate (override §1).
#   "Ismael Kone" di Roma-Sassuolo e il sassolese, scartato.
# ===== GIORNATA 11 — passata locale 06/11/2026 13:35 =====
# gz.json/fc.json rigenerati (25/25, git diff vuoto: Gazzetta fino 13:21, Lulli 40% e Kone M. fuori confermati).
#   Sincronizzato Bernardeschi fc .90 -> .65: fc.json lo da al 65% gia dalla passata delle 10:10.
# SosFanta riletta 13:37: invariata. Sky aggiornata 06/11 12:34 (articolo ultime news): nessun cambio sui 25.
# bwin 13:39 sulle stesse 7 partite (Inter-Como, Monza-Atalanta, Fiorentina-Juventus ancora assenti):
#   Venezia-Udinese 1X2 2.25/3.30/3.00, Vojvoda marcatore 10.00 e cartellino 5.75, Bernardeschi 3.30 e assist 4.60.
# Snai 13:41: lista di tutte e 10 (Monza-Atalanta di nuovo presente), 8 schede evento:
#   Pulisic 2.75, Colombo L. 4.00, Pellegrino 3.25, Alajbegovic 3.75.
# ===== GIORNATA 11 — passata locale 06/11/2026 14:35 =====
# GAZZETTA aggiornata Genoa-Milan alle 14:31: PAVLOVIC fuori dall'undici e fra gli indisponibili
#   "da valutare" (condizioni non ottimali dopo l'Europa League) -> gz 0.0. fantacalcio.it invariato (titolare).
# SOSFANTA riletta 14:40: Pavlovic 51 / Bartesaghi 49 (era 70). Il resto invariato.
# SKY aggiornata 06/11 14:23: Pavlovic ancora titolare, nessun cambio sui 25.
# bwin 14:40 sulle stesse 7 partite: Pavlovic sempre quotato (11.50, cartellino 3.25); Ramos 2.65,
#   Pulisic 3.10, Politano 4.60, Gallo 18.50; cartellini ritoccati. Snai 14:45: Pulisic 3.00, Colombo L. 4.50.
# PASSATA 15:35: Gazzetta, fantacalcio.it e SosFanta invariati; Sky aggiornata 15:18 senza cambi sui 25
#   (Pavlovic sempre titolare). bwin: Gallo 16.50, cartellino Comuzzo 5.75, assist Politano 4.33 e Ramos 8.50.
#   Snai: Pulisic 2.75; 1X2 Genoa-Milan 4.75 e Inter-Como 3.50 in trasferta; O/U ritoccati.
P = [
("Martinez Jo.","P","Inter","Inter-Como",.90,.95,.90,.90,None,None,None,11.0,0,"Titolare per tutte e quattro le fonti (SosFanta 95%). Cartellino bwin 11.00 (05/11: Inter-Como non in palinsesto bwin il 06/11)."),
("Provedel","P","Inter","Inter-Como",.12,.05,.12,.12,None,None,None,None,0,"🔴 Panchina per tutte e quattro le fonti: gioca Martinez. Assente dai mercati bwin."),
("Skorupski","P","Bologna","Parma-Bologna",.90,.95,.90,.90,None,None,None,10.0,0,"Titolare per tutte e quattro le fonti. Cartellino bwin 10.00."),
("Lulli","D","Roma","Roma-Sassuolo",.45,.49,.40,.12,7.0,9.0,3.7,6.75,0,"⚠️ Ballottaggio: Gazzetta 40% (06/11 09:27, era titolare), fantacalcio.it 45%, SosFanta 49% (Molina 51), riserva per Sky. Marcatore bwin 7.00 / Snai 9.00, assist bwin 3.70."),
("Comuzzo","D","Torino","Torino-Lecce",.90,.95,.90,.90,13.0,25.0,13.0,5.75,0,"Titolare per tutte e quattro le fonti. Marcatore bwin 13.00 / Snai 25.00, cartellino bwin 5.75."),
("Doekhi","D","Lazio","Napoli-Lazio",.12,.05,.12,.12,None,12.0,None,None,0,"🔴 Panchina per tutte e quattro le fonti. Assente dai mercati bwin; Snai lo quota 12.00 marcatore."),
("Pavlovic","D","Milan","Genoa-Milan",.90,.51,0.0,.90,11.5,7.5,21.0,3.25,0,"⚠️ In dubbio: Gazzetta (06/11 14:31) lo toglie dall'undici, condizioni non ottimali, da valutare; SosFanta 51% (Bartesaghi 49); titolare per fantacalcio.it e Sky (15:18). Ancora quotato da entrambi i book: marcatore bwin 11.50 / Snai 7.50, cartellino bwin 3.25."),
("Vojvoda","D","Udinese","Venezia-Udinese",.90,.95,.90,.90,10.0,9.0,6.75,5.75,0,"Titolare per tutte e quattro le fonti. Si gioca stasera, venerdì 06/11 alle 20:45. Marcatore bwin 10.00 / Snai 9.00."),
("Kalulu","D","Juventus","Fiorentina-Juventus",.90,.95,.90,.90,None,25.0,None,None,0,"Titolare per tutte e quattro le fonti. Marcatore Snai 25.00; Fiorentina-Juventus non ancora su bwin."),
("Chalobah","D","Como","Inter-Como",0.0,0.0,0.0,.12,None,None,None,None,0,"🔴 Affaticamento muscolare: indisponibile per Gazzetta, fantacalcio.it e SosFanta, in dubbio per Sky. Snai lo quota 12.00 marcatore (non usata: override indisponibile)."),
("Gallo","D","Lecce","Torino-Lecce",.90,.95,.90,.90,16.5,25.0,8.5,6.0,0,"Titolare per tutte e quattro le fonti. Marcatore bwin 16.50 / Snai 25.00."),
("Alajbegovic","C","Juventus","Fiorentina-Juventus",.60,.95,.90,.90,None,3.75,None,None,0,"Titolare per Gazzetta, SosFanta (95%) e Sky; fantacalcio.it 60%. Marcatore Snai 3.75."),
("Gudmundsson A.","C","Lazio","Napoli-Lazio",0.0,0.0,0.0,0.0,None,None,None,None,0,"🔴 Lussazione alla spalla: indisponibile per tutte e quattro le fonti (in dubbio per la 12a). Assente dai marcatori."),
("Kone M.","C","Roma","Roma-Sassuolo",0.0,0.0,0.0,.12,None,None,None,None,0,"🔴 Lesione alla coscia: indisponibile per Gazzetta, fantacalcio.it e SosFanta, in dubbio per Sky. Quotato bwin 5.25 / Snai 5.00 (non usate: override indisponibile)."),
("Jones C.","C","Inter","Inter-Como",.12,.05,.12,.12,None,None,None,None,0,"🔴 Panchina per tutte e quattro le fonti (in dubbio per Sky, rientra parzialmente in gruppo). Snai lo quota 6.00 marcatore (non usata: altrimenti il floor lo rimetterebbe in campo)."),
("Gonzalez N.","C","Juventus","Fiorentina-Juventus",0.0,0.0,0.0,0.0,None,None,None,None,0,"🔴 Lesione al soleo: indisponibile per tutte e quattro le fonti (in dubbio per la 12a). Assente dai marcatori Snai."),
("Pulisic","C","Milan","Genoa-Milan",.90,.95,.90,.90,3.1,2.75,4.6,5.75,0,"Titolare per tutte e quattro le fonti (SosFanta 95%). Marcatore bwin 3.10 / Snai 2.75."),
("Politano","C","Napoli","Napoli-Lazio",.90,.95,.90,.90,4.6,4.0,4.33,4.6,0,"Titolare per tutte e quattro le fonti. Marcatore bwin 4.60 / Snai 4.00."),
("Bernardeschi","C","Bologna","Parma-Bologna",.65,.70,.90,.90,3.3,3.0,4.6,4.33,0,"⚠️ Titolare per Gazzetta e Sky; fantacalcio.it 65%, SosFanta 70% (Orsolini 30). Marcatore bwin 3.30 / Snai 3.00."),
("Pellegrino M.","A","Fiorentina","Fiorentina-Juventus",.65,.95,.90,.90,None,3.25,None,None,0,"Titolare per Gazzetta, SosFanta (95%) e Sky; fantacalcio.it 65%. Marcatore Snai 3.25."),
("Woltemade","A","Juventus","Fiorentina-Juventus",.90,.95,.90,.90,None,3.0,None,None,0,"Titolare per tutte e quattro le fonti. Marcatore Snai 3.00."),
("Ramos G.","A","Milan","Genoa-Milan",.90,.95,.90,.90,2.65,2.5,8.5,4.6,0,"Titolare per tutte e quattro le fonti. Marcatore bwin 2.65 / Snai 2.50."),
("Kolo Muani","A","Juventus","Fiorentina-Juventus",.90,.95,.90,.90,None,2.75,None,None,0,"Titolare per tutte e quattro le fonti (SosFanta 95%, era 51). Marcatore Snai 2.75."),
("Colombo","A","Genoa","Genoa-Milan",.12,.05,.55,.12,None,4.5,None,None,0,"⚠️ Gazzetta 55% (06/11 09:37, era titolare); panchina per fantacalcio.it, SosFanta e Sky. Marcatore Snai 4.50 (Lorenzo, Genoa); assente da tutti i mercati bwin."),
("Thuram","A","Inter","Inter-Como",.90,.95,.90,.90,2.15,2.25,5.25,4.1,0,"Titolare per tutte e quattro le fonti. Marcatore Snai 2.25 / bwin 2.15 (05/11: Inter-Como non in palinsesto bwin il 06/11)."),
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
