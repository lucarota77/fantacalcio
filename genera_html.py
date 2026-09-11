#!/usr/bin/env python3
import json, sys, html
_d = json.load(open('/tmp/rows.json')); rows = _d['rows']
S = json.load(open('/tmp/mstate.json'))
G = sys.argv[1] if len(sys.argv) > 1 else '4'
TS = sys.argv[2] if len(sys.argv) > 2 else '11/09/2026 09:40'
OUT = sys.argv[3]
GG = ['lun','mar','mer','gio','ven','sab','dom']
def quando(v):
    """Le date arrivano in ISO da BetExplorer e leggibili dalla passata locale: uniforma."""
    if not v: return ''
    m = __import__('re').match(r'(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})', str(v))
    if not m: return str(v)
    import datetime
    a, ms, g, h, mi = m.groups()
    d = datetime.date(int(a), int(ms), int(g))
    return f"{GG[d.weekday()]} {g}/{ms} {h}:{mi}"
RN = {'P':'Portieri','D':'Difensori','C':'Centrocampisti','A':'Attaccanti'}
# Consiglio e rischio sono due dimensioni distinte: il consiglio deriva dall'unico
# ordinamento (fanta atteso), il rischio dalla sola probabilita di scendere in campo.
SLOT = {'titolare': ('titolare','Titolare'), 'riserva': ('riserva','1ª riserva'),
        'alternativa': ('alt','Alternativa'), 'fuori': ('fuori','Fuori')}
RISK = {'sicuro': ('','—'), 'ballottaggio': ('rk-b','Ballottaggio'), 'panchina': ('rk-p','Non gioca')}
def lab(x): return SLOT[x['slot']]
def risk(x):
    c, t = RISK[x['rischio']]
    return f'<td class="rk-c"><span class="risk {c}">{t}</span></td>' if c else \
           '<td class="rk-c"><span class="risk">—</span></td>'
e = html.escape
def cell(p, q):
    if p is None: return '<td class="num"><span class="nd">n.d.</span></td>'
    w = max(2, min(100, round(p*100)))
    od = f'<span class="q">{q:.2f}</span>' if q else ''
    return (f'<td class="num"><div class="bar" style="--w:{w}%"></div>'
            f'<span class="v">{round(p*100)}%</span>{od}</td>')
def plain(v):
    return ('<td class="num s"><span class="v">%.2f</span></td>' % v) if v else \
           '<td class="num s"><span class="nd">—</span></td>'
def fantac(v):
    w = max(1, min(100, round(v/9*100)))
    return (f'<td class="num fx"><div class="bar fx-bar" style="--w:{w}%"></div>'
            f'<span class="v">{v:.2f}</span></td>')
def cellq(p, q):
    if p is None: return '<td class="num"><span class="nd">n.d.</span></td>'
    w = max(2, min(100, round(p*100)))
    return (f'<td class="num"><div class="bar" style="--w:{w}%"></div>'
            f'<span class="v">{round(p*100)}%</span>'
            + (f'<span class="q">{e(q)}</span>' if q else '') + '</td>')
nq = sum(1 for x in rows if x['r'] != 'P' and x['pg'] is None)
tot = sum(1 for x in rows if x['r'] != 'P')
BANNER = ('<div class="banner"><b>Report parziale.</b> Per '
          f'{nq} giocatori su {tot} mancano le quote di gol, assist e ammonizione: questa '
          'esecuzione non ha avuto accesso ai mercati per giocatore, che richiedono il browser. '
          'Probabilita di giocare, clean sheet, contesto partita e ranking squadre sono completi. '
          'La pagina viene aggiornata con i dati mancanti alla prima esecuzione locale.</div>'
          ) if nq > tot/2 else ''
irmax = max(x['ir'] for x in rows)
def irc(v, _=None):
    w = max(1, min(100, round(v/irmax*100))) if v > 0 else 1
    return (f'<td class="num ir"><div class="bar ir-bar" style="--w:{w}%"></div>'
            f'<span class="v">{v:.2f}</span></td>')
def trow(i, x, show_role=True):
    cls, txt = lab(x)
    role = f'<td><span class="role r-{x["r"]}">{x["r"]}</span></td>' if show_role else ''
    wr = ' <span class="warn-i" title="fonti in conflitto">&#9888;</span>' if x['flag'] else ''
    st = ' <span class="star" title="titolare nel 3-4-3">&#9733;</span>' if x['titolare'] else ''
    qg2 = f"{x['qg']:.2f}/{x['qgs']:.2f}" if (x['qg'] and x['qgs']) else (
          f"{x['qgs']:.2f} (solo Snai)" if x['qgs'] else (f"{x['qg']:.2f}" if x['qg'] else None))
    return (f'<tr><td class="rk">{i}</td>'
            f'<td class="nm"><b>{e(x["n"])}</b>{wr}{st}<span class="sq">{e(x["sq"])}</span></td>'
            f'{role}<td class="mt">{e(x["mt"])}<span class="wh">{e(quando(x["when"]))}</span></td>'
            f'{cell(x["pgio"],None)}{risk(x)}{plain(x["mv"])}{plain(x["fm"])}{cellq(x["pg"],qg2)}'
            f'{cell(x["pa"],x["qa"])}{cell(x["pc"],x["qc"])}'
            f'{irc(x["ir"], x["ir"])}{fantac(x["fanta"])}'
            f'<td><span class="pill {cls}">{txt}</span></td></tr>')
HEAD = ('<tr><th>#</th><th>Giocatore</th>{R}<th>Partita</th>'
        '<th class="num">Gioca</th><th>Rischio</th><th class="num">MV</th><th class="num">FM</th>'
        '<th class="num">Gol</th><th class="num">Assist</th><th class="num">Ammonito</th>'
        '<th class="num">IR</th><th class="num">Fanta atteso</th><th>Consiglio</th></tr>')
# squadre
teams = []
for k, v in S.items():
    teams.append((v['home'], v['p1'], 'vs '+v['away'], v['when']))
    teams.append((v['away'], v['p2'], 'a '+v['home'], v['when']))
teams.sort(key=lambda t: -t[1])
tmax = teams[0][1]
team_rows = ''.join(
    f'<tr><td class="rk">{i}</td><td class="nm"><b>{e(n)}</b></td><td class="mt">{e(o)}'
    f'<span class="wh">{e(quando(w))}</span></td><td class="num wide">'
    f'<div class="bar team-bar" style="--w:{round(p/tmax*100)}%"></div>'
    f'<span class="v">{p*100:.1f}%</span></td></tr>'
    for i,(n,p,o,w) in enumerate(teams,1))
match_rows = ''.join(
    f'<tr><td class="nm"><b>{e(k)}</b><span class="sq">{e(quando(v["when"]))}</span></td>'
    f'<td class="num s"><span class="v">{v["p1"]*100:.0f}%</span></td>'
    f'<td class="num s"><span class="v">{v["px"]*100:.0f}%</span></td>'
    f'<td class="num s"><span class="v">{v["p2"]*100:.0f}%</span></td>'
    f'<td class="num s"><span class="v">{v["lam"]:.2f}</span></td>'
    f'<td class="num s"><span class="v">{v["cs_home"]*100:.0f}%</span></td>'
    f'<td class="num s"><span class="v">{v["cs_away"]*100:.0f}%</span></td></tr>'
    for k,v in S.items())
# formazione consigliata
best = ''
for r in 'PDCA':
    tt = [x for x in rows if x['titolare'] and x['r']==r]
    rs = [x for x in rows if not x['titolare'] and x['r']==r and x['pgio'] >= .40][:2]
    items = ''.join(
        f'<li><span class="bn">{e(x["n"])}'
        + (' <span class="warn-i">&#9888;</span>' if x['flag'] else '')
        + f'</span><span class="bi">{x["fanta"]:.2f}</span>'
        f'<span class="bp">{round(x["pgio"]*100)}% in campo &middot; MV {x["mv"]:.2f}</span></li>'
        if x['mv'] else
        f'<span class="bp">{round(x["pgio"]*100)}% in campo &middot; {e(x["sq"])}</span></li>' for x in tt)
    res = ('<div class="bres"><span class="brl">Prime riserve</span>' + ''.join(
        f'<span class="brn">{e(x["n"])} <em>{x["fanta"]:.2f}</em></span>' for x in rs) + '</div>') if rs else ''
    best += (f'<div class="bcard b-{r}"><h3><span class="role r-{r}">{r}</span>{RN[r]}'
             f'<span class="bcount">{len(tt)}</span></h3>'
             f'<ol class="blist">{items}</ol>{res}</div>')
notes = ''.join(f'<li><b>{e(x["n"])}</b> <span class="nsq">{e(x["sq"])}</span> — {e(x["nota"])}</li>'
                for x in rows if x['nota'])
by_role = ''
for r in 'PDCA':
    rr = [x for x in rows if x['r']==r]
    body = ''.join(trow(i,x,False) for i,x in enumerate(rr,1))
    by_role += (f'<h3 class="rh"><span class="role r-{r}">{r}</span>{RN[r]}</h3>'
                f'<div class="scroll"><table class="t">'
                f'<thead>{HEAD.format(R="")}</thead><tbody>{body}</tbody></table></div>')
all_rows = ''.join(trow(i,x) for i,x in enumerate(rows,1))

TPL = r'''<title>Formazione Giornata @@G@@</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>
:root{
  --ground:#F3F6F2; --surface:#FFFFFF; --surface2:#E9EFE8; --ink:#141F17; --muted:#586A5D;
  --line:#D5DFD4; --line2:#E6EDE5; --accent:#1E5F3E; --gold:#A9700C;
  --rp:#C2802A; --rd:#358350; --rc:#2F6EA8; --ra:#B8443B;
  --ok:#2C7A4E; --warn:#A96D0B; --bad:#A93B32; --neu:#66756B;
  --bar:#CBD9CB; --bar-ir:#9CC4A9; --bar-team:#B9CEBC;
  --shadow:0 1px 2px rgba(20,31,23,.06),0 6px 18px rgba(20,31,23,.05);
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --ground:#0C120E; --surface:#141C17; --surface2:#1A241D; --ink:#E6EEE7; --muted:#8DA093;
  --line:#25322A; --line2:#1E2922; --accent:#5EC48B; --gold:#DFA93E;
  --rp:#E0A94A; --rd:#5BB87A; --rc:#5C9FD8; --ra:#E06A60;
  --ok:#4FB37A; --warn:#D69A2A; --bad:#D55F55; --neu:#8DA093;
  --bar:#26332B; --bar-ir:#2F5C41; --bar-team:#2A4735;
  --shadow:0 1px 2px rgba(0,0,0,.4),0 6px 18px rgba(0,0,0,.3);
}}
:root[data-theme="dark"]{
  --ground:#0C120E; --surface:#141C17; --surface2:#1A241D; --ink:#E6EEE7; --muted:#8DA093;
  --line:#25322A; --line2:#1E2922; --accent:#5EC48B; --gold:#DFA93E;
  --rp:#E0A94A; --rd:#5BB87A; --rc:#5C9FD8; --ra:#E06A60;
  --ok:#4FB37A; --warn:#D69A2A; --bad:#D55F55; --neu:#8DA093;
  --bar:#26332B; --bar-ir:#2F5C41; --bar-team:#2A4735;
  --shadow:0 1px 2px rgba(0,0,0,.4),0 6px 18px rgba(0,0,0,.3);
}
*{box-sizing:border-box}
body{background:var(--ground);color:var(--ink);
  font:400 15px/1.55 "IBM Plex Sans",system-ui,-apple-system,Segoe UI,sans-serif;
  -webkit-font-smoothing:antialiased;padding:0 0 72px}
.wrap{max-width:1120px;margin:0 auto;padding:0 22px}
h1,h2,h3{font-family:"Barlow Condensed","Arial Narrow",system-ui,sans-serif;
  text-wrap:balance;margin:0;letter-spacing:.01em}
/* header */
.hdr{border-bottom:1px solid var(--line);background:var(--surface);margin-bottom:30px}
.hdr .wrap{padding-top:26px;padding-bottom:22px}
.eyebrow{font:600 12px/1 "IBM Plex Sans",sans-serif;letter-spacing:.15em;text-transform:uppercase;
  color:var(--accent);margin-bottom:10px}
h1{font-size:clamp(38px,6vw,60px);font-weight:700;line-height:.95;text-transform:uppercase}
h1 em{font-style:normal;color:var(--muted)}
.meta{display:flex;flex-wrap:wrap;gap:8px 20px;margin-top:14px;
  font:400 13px/1.4 "IBM Plex Mono",ui-monospace,monospace;color:var(--muted)}
.meta b{color:var(--ink);font-weight:500}
.srcs{margin-top:14px;font-size:13px;color:var(--muted);max-width:74ch}
.srcs b{color:var(--ink);font-weight:600}
/* sezioni */
section{margin-top:42px}
h2{font-size:27px;font-weight:600;text-transform:uppercase;letter-spacing:.04em;
  padding-bottom:9px;border-bottom:2px solid var(--ink);display:flex;align-items:baseline;gap:11px}
h2 span{font:400 12px/1 "IBM Plex Mono",monospace;color:var(--muted);text-transform:none;letter-spacing:0}
.lede{color:var(--muted);font-size:14px;margin:12px 0 18px;max-width:72ch}
/* formazione consigliata */
.best{display:grid;grid-template-columns:repeat(auto-fit,minmax(218px,1fr));gap:14px;margin-top:18px}
.bcard{background:var(--surface);border:1px solid var(--line);border-radius:3px;padding:15px 16px 13px;
  box-shadow:var(--shadow)}
.bcard h3{font-size:16px;font-weight:600;text-transform:uppercase;letter-spacing:.06em;
  display:flex;align-items:center;gap:8px;margin-bottom:11px;color:var(--muted)}
.blist{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:9px}
.blist li{display:grid;grid-template-columns:1fr auto;gap:2px 10px;align-items:baseline;
  padding-bottom:9px;border-bottom:1px solid var(--line2)}
.blist li:last-child{border-bottom:0;padding-bottom:0}
.bn{font-weight:600;font-size:15px}
.bi{font:500 15px/1 "IBM Plex Mono",monospace;color:var(--accent);font-variant-numeric:tabular-nums}
.bp{grid-column:1/-1;font:400 12px/1 "IBM Plex Mono",monospace;color:var(--muted)}
.bcount{margin-left:auto;font:500 12px/1 "IBM Plex Mono",monospace;color:var(--accent)}
.bres{margin-top:11px;padding-top:10px;border-top:1px dashed var(--line);
  display:flex;flex-wrap:wrap;gap:5px 12px;align-items:baseline}
.brl{font:600 10px/1 "IBM Plex Sans",sans-serif;letter-spacing:.1em;text-transform:uppercase;
  color:var(--muted);width:100%}
.brn{font-size:13px;color:var(--muted)}
.brn em{font:500 12px/1 "IBM Plex Mono",monospace;font-style:normal;color:var(--ink)}
.star{color:var(--gold);font-size:12px;margin-left:3px}
/* ruoli */
.role{display:inline-flex;align-items:center;justify-content:center;width:20px;height:20px;
  border-radius:50%;font:600 11px/1 "IBM Plex Sans",sans-serif;color:#fff;flex:none}
.r-P{background:var(--rp)}.r-D{background:var(--rd)}.r-C{background:var(--rc)}.r-A{background:var(--ra)}
/* tabelle */
.scroll{overflow-x:auto;background:var(--surface);border:1px solid var(--line);border-radius:3px;
  box-shadow:var(--shadow)}
table.t{width:100%;border-collapse:collapse;font-size:14px;min-width:1080px}
table.t th{font:600 11px/1.2 "IBM Plex Sans",sans-serif;letter-spacing:.09em;text-transform:uppercase;
  color:var(--muted);text-align:left;padding:11px 12px;border-bottom:1px solid var(--line);
  background:var(--surface2);white-space:nowrap}
table.t td{padding:10px 12px;border-bottom:1px solid var(--line2);vertical-align:middle}
table.t tbody tr:last-child td{border-bottom:0}
table.t tbody tr:hover td{background:var(--surface2)}
.rk{font:400 12px/1 "IBM Plex Mono",monospace;color:var(--muted);width:34px;
  font-variant-numeric:tabular-nums}
.nm b{font-weight:600;white-space:nowrap}
.nm .sq,.mt .wh{display:block;font:400 11.5px/1.3 "IBM Plex Mono",monospace;color:var(--muted);margin-top:1px}
.mt{white-space:nowrap;font-size:13px}
th.num,td.num{text-align:right;position:relative;white-space:nowrap;min-width:86px}
td.num .v{position:relative;font:500 14px/1 "IBM Plex Mono",monospace;font-variant-numeric:tabular-nums}
td.num .q{position:relative;display:block;font:400 11px/1.3 "IBM Plex Mono",monospace;
  color:var(--muted);margin-top:2px}
td.num .nd{font:400 12px/1 "IBM Plex Mono",monospace;color:var(--muted)}
.bar{position:absolute;left:0;bottom:0;top:0;width:var(--w);background:var(--bar);opacity:.55;
  border-right:1px solid var(--bar)}
.ir-bar{background:var(--bar-ir);opacity:.6}
.fx-bar{background:var(--bar-ir);opacity:.85}
td.fx .v{font-weight:600;color:var(--ink)}
.team-bar{background:var(--bar-team);opacity:.65}
td.ir .v{font-weight:500;color:var(--accent)}
td.num.wide{min-width:190px}
td.num.s{min-width:60px}
/* pill */
.pill{display:inline-block;padding:3px 9px;border-radius:2px;white-space:nowrap;
  font:600 11px/1.35 "IBM Plex Sans",sans-serif;letter-spacing:.05em;text-transform:uppercase;
  border:1px solid currentColor}
.pill.titolare{color:var(--ok)}.pill.riserva{color:var(--rc)}
.pill.alt{color:var(--neu)}.pill.fuori{color:var(--bad)}
.rk-c{white-space:nowrap}
.risk{font:500 12px/1 "IBM Plex Mono",monospace;color:var(--muted)}
.risk.rk-b{color:var(--warn)}.risk.rk-p{color:var(--bad)}
.warn-i{color:var(--warn);font-size:12px;margin-left:3px}
/* filtri */
.filters{display:flex;flex-wrap:wrap;gap:7px;margin:16px 0}
.filters button{font:600 11px/1 "IBM Plex Sans",sans-serif;letter-spacing:.08em;text-transform:uppercase;
  padding:8px 13px;border:1px solid var(--line);background:var(--surface);color:var(--muted);
  border-radius:2px;cursor:pointer;transition:background .13s,color .13s,border-color .13s}
.filters button:hover{border-color:var(--muted);color:var(--ink)}
.filters button[aria-pressed="true"]{background:var(--ink);color:var(--ground);border-color:var(--ink)}
.filters button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.rh{font-size:19px;font-weight:600;text-transform:uppercase;letter-spacing:.06em;
  display:flex;align-items:center;gap:9px;margin:26px 0 10px;color:var(--muted)}
/* note */
.notes{list-style:none;margin:16px 0 0;padding:0;display:flex;flex-direction:column;gap:0}
.notes li{padding:12px 0 12px 15px;border-left:2px solid var(--warn);border-bottom:1px solid var(--line2);
  font-size:14px;color:var(--muted)}
.notes li:last-child{border-bottom:0}
.notes b{color:var(--ink);font-weight:600}
.nsq{font:400 11.5px/1 "IBM Plex Mono",monospace;color:var(--muted);margin-left:4px}
.banner{background:var(--surface);border:1px solid var(--warn);border-left:3px solid var(--warn);
  border-radius:3px;padding:13px 16px;margin:0 0 8px;font-size:13.5px;color:var(--muted)}
.banner b{color:var(--ink)}
.callout{background:var(--surface);border:1px solid var(--line);border-left:3px solid var(--accent);
  border-radius:3px;padding:15px 18px;margin-top:18px;font-size:14px;color:var(--muted)}
.callout b{color:var(--ink)}
.callout p{margin:0 0 8px}.callout p:last-child{margin:0}
.legend{display:flex;flex-wrap:wrap;gap:9px 18px;margin-top:14px;font-size:12.5px;color:var(--muted)}
.legend span{display:inline-flex;align-items:center;gap:6px}
.legend .sep{width:100%;margin-top:4px;padding-top:9px;border-top:1px solid var(--line2)}
.legend .sep b{color:var(--ink)}
footer{margin-top:48px;padding-top:18px;border-top:1px solid var(--line);
  font:400 12px/1.6 "IBM Plex Mono",monospace;color:var(--muted)}
@media (max-width:640px){.wrap{padding:0 15px}h1{font-size:36px}}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
</style>

<header class="hdr"><div class="wrap">
  <div class="eyebrow">Serie A 2026/27 &middot; Rosa di 25</div>
  <h1>Giornata <em>04</em></h1>
  <div class="meta">
    <span>Turno <b>ven 11 &ndash; lun 14 settembre</b></span>
    <span>Quote rilevate <b>@@TS@@</b></span>
    <span>Bookmaker <b>bwin + Snai</b></span>
    <span>Modulo <b>3-4-3</b></span>
  </div>
  <p class="srcs"><b>Probabili formazioni:</b> gazzetta.it (via browser), fantacalcio.it,
  sosfanta.com, sport.sky.it. &middot; <b>Quote:</b> bwin e Snai, due famiglie indipendenti
  (Sisal replica il feed Snai, bwin e la piattaforma di Eurobet; bet365 blocca l&rsquo;automazione).
  Assist e ammonizioni vengono dal solo bwin. Tutte le probabilita sono al netto del margine del
  bookmaker. Le quote servono qui come stima di probabilita, non come invito al gioco.</p>
</div></header>

<div class="wrap">
@@BANNER@@
<section>
  <h2>Formazione consigliata <span>3-4-3 &middot; il numero accanto a ogni nome e il <b>fanta atteso</b>, lo stesso che ordina le tabelle</span></h2>
  <div class="best">@@BEST@@</div>
</section>

<section>
  <h2>I 25 in ordine di rilevanza <span>IR = punti bonus/malus attesi</span></h2>
  <p class="lede"><b>Un solo numero ordina tutto: il fanta atteso.</b> Da li discende anche la
  colonna <i>Consiglio</i>, quindi non puo contraddire la formazione. Il <i>Rischio</i> e
  un'informazione separata e non entra nell'ordinamento: un titolare puo essere in ballottaggio
  e restare comunque il miglior nome del suo reparto.
  L&rsquo;indice di rilevanza somma il valore atteso dei bonus e dei malus &mdash;
  gol &times;3, assist &times;1, ammonizione &minus;0,5, clean sheet &times;1 per i difensori &mdash;
  pesati per la probabilita di giocare e per il contesto della partita.
  <b>Il contesto pesa molto su portiere (2,2) e difensori (1,8) e poco su centrocampisti (0,9) e
  attaccanti (0,7)</b>: per questi ultimi la forza della squadra e gia dentro le quote di gol e
  assist, e contarla due volte falserebbe il confronto. Sotto le percentuali trovi le quote
  decimali da cui derivano; per il gol, <b>bwin / Snai</b>.
  &#9733; = titolare nel 3-4-3 consigliato.</p>
  <div class="filters" role="group" aria-label="Filtra per ruolo">
    <button data-f="all" aria-pressed="true">Tutti</button>
    <button data-f="P" aria-pressed="false">Portieri</button>
    <button data-f="D" aria-pressed="false">Difensori</button>
    <button data-f="C" aria-pressed="false">Centrocampisti</button>
    <button data-f="A" aria-pressed="false">Attaccanti</button>
  </div>
  <div class="scroll"><table class="t" id="main">
    <thead>@@HEAD@@</thead><tbody>@@ALLROWS@@</tbody></table></div>
  <div class="legend">
    <span><span class="pill titolare">Titolare</span> schierato nel 3-4-3</span>
    <span><span class="pill riserva">1ª riserva</span> primo cambio del ruolo</span>
    <span><span class="pill alt">Alternativa</span> disponibile ma piu indietro</span>
    <span><span class="pill fuori">Fuori</span> sotto il 40% di presenza</span>
    <span class="sep">Il <b>rischio</b> e una colonna a parte: un titolare puo essere in
    ballottaggio, e resta il miglior nome del reparto.</span>
    <span>&#9888; fonti in conflitto</span>
  </div>
</section>

<section>
  <h2>Reparto per reparto</h2>
  @@BYROLE@@
</section>

<section>
  <h2>Squadre per probabilita di vittoria <span>media bwin + Snai, margine rimosso</span></h2>
  <div class="scroll"><table class="t" style="min-width:560px">
    <thead><tr><th>#</th><th>Squadra</th><th>Partita</th><th class="num wide">P(vittoria)</th></tr></thead>
    <tbody>@@TEAMS@@</tbody></table></div>
  <h3 class="rh">Dettaglio partite</h3>
  <div class="scroll"><table class="t" style="min-width:640px">
    <thead><tr><th>Partita</th><th class="num s">1</th><th class="num s">X</th><th class="num s">2</th>
    <th class="num s">Gol attesi</th><th class="num s">Clean sheet casa</th>
    <th class="num s">Clean sheet trasferta</th></tr></thead>
    <tbody>@@MATCHES@@</tbody></table></div>
  <p class="lede">I gol attesi sono ricavati dalla linea Over/Under e ripartiti fra le due squadre
  con un modello di Poisson coerente con le probabilita 1X2; da li discendono i clean sheet.</p>
</section>

<section>
  <h2>Note e alert</h2>
  <ul class="notes">@@NOTES@@</ul>
  <div class="callout">
    <p><b>Limiti di questa rilevazione.</b> Le quote si muovono: quelle qui riportate valgono per
    l&rsquo;istante indicato in testata.</p>
    <p><b>Assist e ammonizioni sono single-source</b> (solo bwin): Snai non espone l&rsquo;assist per
    giocatore e il suo tab Sanzioni contiene solo rigori, espulsioni e consulti VAR. Non sono quindi
    verificati da un secondo book.</p>
    <p>La formazione della Roma su Gazzetta e ferma al 7 settembre: per Torino-Roma il peso di quella
    fonte e stato dimezzato. Il venerdi mattina le gare di lunedi sono le meno affidabili.</p>
    <p>Il clean sheet e derivato da un modello di Poisson sui gol attesi, non da un mercato dedicato.</p>
  </div>
</section>

<footer>Generato il @@TS@@ &middot; fonti: gazzetta.it, fantacalcio.it, sosfanta.com, sport.sky.it, bwin.it, snai.it<br>
Il gioco e riservato ai maggiorenni e puo creare dipendenza patologica.</footer>
</div>

<script>
(function(){
  var btns=document.querySelectorAll('.filters button'),
      rows=document.querySelectorAll('#main tbody tr');
  btns.forEach(function(b){
    b.addEventListener('click',function(){
      btns.forEach(function(o){o.setAttribute('aria-pressed',String(o===b))});
      var f=b.dataset.f;
      rows.forEach(function(r){
        r.hidden = f!=='all' && r.querySelector('.role').textContent.trim()!==f;
      });
    });
  });
})();
</script>
'''
out = (TPL.replace('@@G@@', G).replace('@@TS@@', TS).replace('@@BEST@@', best)
       .replace('@@HEAD@@', HEAD.format(R='<th>R</th>')).replace('@@ALLROWS@@', all_rows)
       .replace('@@BYROLE@@', by_role).replace('@@TEAMS@@', team_rows)
       .replace('@@MATCHES@@', match_rows).replace('@@NOTES@@', notes)
       .replace('@@BANNER@@', BANNER))
open(OUT, 'w').write(out)
print('scritto', OUT, len(out), 'byte')
