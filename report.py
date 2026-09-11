#!/usr/bin/env python3
"""Genera il report markdown da /tmp/rows.json e /tmp/mstate.json"""
import json, sys
from datetime import datetime
_d = json.load(open('/tmp/rows.json')); rows = _d['rows']; TIT = _d['titolari']
S = json.load(open('/tmp/mstate.json'))
GIORNATA = sys.argv[1] if len(sys.argv) > 1 else '4'
TS = sys.argv[2] if len(sys.argv) > 2 else datetime.now().strftime('%d/%m/%Y %H:%M')
RUOLO = {'P':'Portieri','D':'Difensori','C':'Centrocampisti','A':'Attaccanti'}
med = {}
for r in 'PDCA':
    v = sorted([x['ir'] for x in rows if x['r']==r], reverse=True)
    med[r] = v[max(0,len(v)//3-1)] if v else 0
def lab(x):
    if x['pgio'] < .40: return '🔴 PANCHINA'
    if x['pgio'] < .75: return '🟠 BALLOTTAGGIO'
    return '🟢 SCHIERA' if x['ir'] >= med[x['r']] else '🟡 OK'
pc = lambda v: 'n.d.' if v is None else f'{round(v*100)}%'
L = []
L.append(f"# Report Fantacalcio — Serie A, giornata {GIORNATA}\n")
L.append(f"**Rilevazione:** {TS} · **Turno:** ven 11 – lun 14 settembre 2026\n")
L.append("**Probabili formazioni:** gazzetta.it (via browser), fantacalcio.it, sosfanta.com, sport.sky.it.  \n"
         "**Quote:** bwin (1X2, marcatore, assist, ammonizione) e Snai (1X2, marcatore) — due famiglie "
         "indipendenti. Sisal replica il feed Snai e bwin è la piattaforma di Eurobet: non aggiungono "
         "informazione. bet365 blocca l'automazione.  \n"
         "**Single-source:** assist e ammonizioni vengono dal solo bwin.\n")

L.append("\n## 0. Formazione consigliata — 3-4-3\n")
for _r in 'PDCA':
    _t = [x for x in rows if x['titolare'] and x['r'] == _r]
    _p = [x for x in rows if not x['titolare'] and x['r'] == _r and x['pgio'] >= .40][:2]
    L.append(f"- **{RUOLO[_r]}:** " + ', '.join(f"{x['n']}{x['flag']} ({x['ir']:.2f})" for x in _t)
             + ("  \n  _prime riserve:_ " + ', '.join(f"{x['n']} ({x['ir']:.2f})" for x in _p) if _p else ""))
L.append("> Le quote sono usate come **stima di probabilità**, non come invito al gioco. "
         "Tutte le probabilità sono al netto del margine del bookmaker (de-vig).\n")
# squadre
teams = []
for k, v in S.items():
    teams.append((v['home'], v['p1'], f"vs {v['away']}", v['when'], 'casa'))
    teams.append((v['away'], v['p2'], f"a {v['home']}", v['when'], 'trasferta'))
teams.sort(key=lambda t: -t[1])
L.append("\n## 1. Squadre per probabilità di vittoria\n")
L.append("| # | Squadra | Avversario | Quando | P(vittoria) |")
L.append("|---|---|---|---|---|")
for i,(n,p,opp,w,_) in enumerate(teams,1):
    L.append(f"| {i} | **{n}** | {opp} | {w} | {p*100:.1f}% |")
L.append("\n### Dettaglio partite\n")
L.append("| Partita | 1 | X | 2 | Gol attesi | Clean sheet casa | Clean sheet trasferta |")
L.append("|---|---|---|---|---|---|---|")
for k,v in S.items():
    L.append(f"| {k} | {v['p1']*100:.1f}% | {v['px']*100:.1f}% | {v['p2']*100:.1f}% | "
             f"{v['lam']:.2f} | {v['cs_home']*100:.0f}% | {v['cs_away']*100:.0f}% |")
# classifica generale
L.append(f"\n## 2. I tuoi 25 in ordine di rilevanza\n")
L.append("`IR` = punti fanta attesi dai bonus/malus (gol +3, assist +1, ammonizione −0,5, clean sheet +1 "
         "per i difensori), pesati per la probabilità di giocare e per il contesto della partita. "
         "Il contesto pesa molto sui portieri (2,2) e sui difensori (1,8), poco su centrocampisti (0,9) "
         "e attaccanti (0,7), perché per questi ultimi la forza della squadra è già dentro le quote di "
         "gol e assist. ★ = titolare nel 3-4-3 consigliato.\n")
L.append("| # | Giocatore | R | Squadra | Partita | P(vitt) | Gioca | Gol | Assist | Amm. | CS | IR | Consiglio |")
L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for i,x in enumerate(rows,1):
    st = " ★" if x['titolare'] else ""
    L.append(f"| {i} | **{x['n']}**{x['flag']}{st} | {x['r']} | {x['sq']} | {x['mt']} | {pc(x['pvit'])} | {pc(x['pgio'])} | "
             f"{pc(x['pg'])} | {pc(x['pa'])} | {pc(x['pc'])} | {pc(x['cs'])} | {x['ir']:.2f} | {lab(x)} |")
# per ruolo
L.append("\n## 3. Per ruolo — come schierare\n")
for r in 'PDCA':
    rr = [x for x in rows if x['r']==r]
    L.append(f"\n### {RUOLO[r]}\n")
    L.append("| # | Giocatore | Squadra | Partita | P(vitt) | Gioca | Gol | Assist | Amm. | CS | IR | Consiglio |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for i,x in enumerate(rr,1):
        st = " ★" if x['titolare'] else ""
        L.append(f"| {i} | **{x['n']}**{x['flag']}{st} | {x['sq']} | {x['mt']} | {pc(x['pvit'])} | {pc(x['pgio'])} | "
                 f"{pc(x['pg'])} | {pc(x['pa'])} | {pc(x['pc'])} | {pc(x['cs'])} | {x['ir']:.2f} | {lab(x)} |")
# note
L.append("\n## 4. Note e alert\n")
for x in rows:
    if x['nota']:
        L.append(f"- **{x['n']}** ({x['sq']}) — {x['nota']}")
L.append("\n### Conflitti fonti ⚠️\n")
L.append("Il simbolo ⚠️ segnala uno scarto superiore a 32 punti fra ciò che dicono le probabili "
         "formazioni e ciò che prezzano i bookmaker. In questi casi la stima pesa il mercato al 60% "
         "perché è più aggiornato, ma il giocatore va **riverificato poco prima della partita**.\n")
L.append("\n## 5. Limiti di questo report\n")
L.append("- Quote rilevate in un istante preciso: si muovono, soprattutto per le gare di domenica e lunedì.\n"
         "- Assist e ammonizioni vengono dal solo bwin: non sono verificate da un secondo book.\n"
         "- Le probabili formazioni del venerdì mattina sono incomplete per le gare di lunedì; la formazione "
         "della Roma su Gazzetta è ferma al 7 settembre e il suo peso è stato dimezzato.\n"
         "- Il clean sheet è derivato da un modello di Poisson sui gol attesi, non da un mercato dedicato.\n"
         "- bet365 blocca l'automazione: le famiglie di book realmente indipendenti sono due.\n")
open(sys.argv[3] if len(sys.argv)>3 else '/tmp/report.md','w').write('\n'.join(L))
print('\n'.join(L[:4]))
