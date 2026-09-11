# Report Fantacalcio

Ogni **venerdì alle 14:00** (e on demand) raccoglie probabilità di giocare, segnare,
fare assist ed essere ammonito per i 25 giocatori della rosa, ordina le squadre del
turno per probabilità di vittoria e propone la **formazione 3-4-3** (1 portiere,
3 difensori, 4 centrocampisti, 3 attaccanti) con le prime riserve per ruolo.

La probabilità di vittoria della partita pesa nell'indice di rilevanza, **molto su portiere
e difensori** (dove gol e assist sono rari e conta il clean sheet) e **poco su centrocampisti
e attaccanti** (dove la forza della squadra è già dentro le quote di gol e assist).

## Dove si vede

**https://lucarota77.github.io/fantacalcio/** — pubblica, senza login, URL stabile fra le giornate.
La pagina ha `noindex` per restare fuori dai motori di ricerca, ma il repo è pubblico: chi
conosce il link vede la rosa.

## Come funziona: due esecuzioni, ogni ora dalle 14 alle 20 del venerdì

| | Quando | Dove | Cosa raccoglie |
|---|---|---|---|
| **Automatica** | ven, ogni ora :00 dalle 14 alle 20 | GitHub Actions | Probabili formazioni da **Gazzetta + fantacalcio.it** (entrambe con percentuali di ballottaggio), **MV e fantamedia** stagionali, **quote 1X2** da BetExplorer per le gare già quotate. Mancano solo i mercati per giocatore. |
| **Completa** | ven, ogni ora :20 dalle 14 alle 20, se il Mac è acceso | task locale di Claude Code | Aggiunge **marcatore, assist e ammonizione** da bwin e Snai — l'unica cosa che richiede una rete residenziale — e ripubblica il sito senza avviso. |

La seconda sovrascrive la prima: il risultato è lo stesso URL, aggiornato. Il locale gira alle
:20, venti minuti dopo l'automatica, così arriva sempre per ultimo.

### Le quote del Mac sopravvivono al Mac spento

Ogni passata locale salva i mercati per giocatore in **`quote_cache.json`** dentro il repo. Le
esecuzioni cloud successive li riusano, se sono della stessa giornata, invece di lasciare i
campi vuoti: la pagina dichiara in testata da quante ore vengono. Più spesso il Mac è acceso
nella finestra, più fresche restano le quote per le ore successive.

### Cosa raggiunge il runner GitHub (diagnostica dell'11/09/2026)

Il workflow `diagnostica.yml` misura empiricamente cosa è raggiungibile. Esito:

| Fonte | curl dal runner | Browser (Playwright) sul runner |
|---|---|---|
| gazzetta.it | ✅ 200, completa | — |
| fantacalcio.it probabili formazioni | ✅ 200 | — |
| fantacalcio.it statistiche (MV/FM) | ✅ 200 | — |
| sosfanta.com, sport.sky.it | ✅ 200 | — |
| betexplorer.com | ✅ 200 | — |
| **bwin** | ❌ SPA vuota | ❌ pagina da 7 KB (challenge) |
| **snai** | ❌ timeout | ❌ `ERR_HTTP2_PROTOCOL_ERROR` |

I bookmaker bloccano gli IP dei datacenter **anche con un browser vero**: è l'unica cosa che
resta legata al Mac. Rilancia la diagnostica quando una fonte smette di funzionare:
`gh workflow run "Diagnostica fonti" --repo lucarota77/fantacalcio`

### Perché non una routine cloud di Claude
Provata e scartata: l'ambiente cloud ha un **proxy di egress** che blocca gazzetta.it,
betexplorer.com, fantacalcio.it, sosfanta.com e sport.sky.it (`EGRESS_BLOCKED`), non ha il
browser, ed Exa restituisce contenuto in cache di settimane prima. GitHub Actions ha rete
libera, gira senza PC e può committare da solo.

## Lanciarlo a mano

### Da iPhone — Shortcut, un tap dalla schermata home

Serve una volta sola un token: GitHub → *Settings* → *Developer settings* →
*Personal access tokens* → **Fine-grained tokens** → *Generate new token*, con
**Repository access: Only select repositories → fantacalcio** e
**Permissions → Actions: Read and write**. Copialo subito, non è più visibile.

Poi nell'app **Comandi** (Shortcuts): nuovo comando → azione **Ottieni contenuti di URL**:

| Campo | Valore |
|---|---|
| URL | `https://api.github.com/repos/lucarota77/fantacalcio/actions/workflows/report.yml/dispatches` |
| Metodo | `POST` |
| Intestazioni | `Authorization` = `Bearer <IL_TUO_TOKEN>` · `Accept` = `application/vnd.github+json` |
| Corpo richiesta | JSON, campo `ref` (testo) = `main` |

Aggiungilo alla schermata home: un tap lancia il report, che compare sul sito in un paio di
minuti. Funziona anche dal Mac e da qualunque cosa sappia fare una POST (IFTTT, automazioni).

> Il token dà accesso in scrittura alle Actions di questo solo repo: se lo perdi, revocalo da
> GitHub e rigenerane uno. Non metterlo mai nel repo.

### Dall'app GitHub, senza token
App GitHub ufficiale → repo *fantacalcio* → tab **Actions** → *Report fantacalcio* →
**Run workflow**. Più clic, zero configurazione.

### Dal Mac
```bash
gh workflow run "Report fantacalcio" --repo lucarota77/fantacalcio
```
Questo lancia però solo la parte automatica. Per la **passata completa con le quote** serve il
task locale: pannello **Scheduled** della sidebar → *Run now* su ⚽ *Fantacalcio — passata
completa*, oppure in chat «lancia la passata completa del fantacalcio». È l'unica che può
leggere bwin e Snai.

## Ora legale

Il workflow fira **ogni ora fra le 11:00 e le 19:00 UTC** e uno step tiene solo le esecuzioni
in cui a Roma l'ora è fra le 14 e le 20. La finestra copre sia l'ora legale (UTC+2) sia quella
solare (UTC+1), quindi vale tutto l'anno senza correggere il cron ai cambi d'ora — a differenza
delle routine cloud, dove il cron è in UTC fisso.

## File

| File | Cosa fa |
|---|---|
| `rosa.json` | I 25 giocatori: ruolo, squadra, alias usato dai bookmaker. **Da aggiornare a ogni mercato.** |
| `METODO.md` | Formule e regole: de-vig, pesi delle fonti, segnale di mercato, indice di rilevanza. È il documento da modificare per cambiare il comportamento del report. |
| `dati.json` | Le 10 partite del turno con quote 1X2 e Over/Under. Riscritto a ogni esecuzione. |
| `estrai_quote.js` | Da iniettare in una scheda partita **bwin**: marcatore, assist e cartellino dei soli 25. |
| `estrai_gazzetta.js` | Da iniettare su **gazzetta.it** (browser): undici, panchina, ballottaggi in %, diffidati, timestamp per partita. |
| `estrai_snai.js` | Due usi: 1X2+U/O dalla lista **Snai**, e marcatori dalla scheda evento. |
| `calcola.py` | De-vig 1X2, gol attesi (Poisson), split casa/trasferta, clean sheet. |
| `giocatori.py` | Contiene la tabella dei 25 con fonti e quote del turno; calcola P(gioca) e l'indice di rilevanza. |
| `report.py` | Produce il markdown in `report/`. |
| `genera_html.py` | Produce la pagina HTML da pubblicare come artifact. |
| `report/` | Storico dei report, un file per giornata. |

## Catena di esecuzione

```bash
cd ~/fantacalcio
python3 calcola.py dati.json                    # controlla a vista i numeri stampati
python3 giocatori.py
python3 report.py 4 "11/09/2026 14:00" report/2026-09-11-giornata4.md
python3 genera_html.py 4 "11/09/2026 14:00" /tmp/fantacalcio-g4.html
```

## Regola sulle fonti

**Se WebFetch non legge una fonte, si riprova col browser.** Vale per tutte, anche nuove.
Il pannello browser è spesso nascosto: usare `javascript_tool`, non click e scroll da mouse.

| Fonte | WebFetch | Browser | Cosa dà |
|---|---|---|---|
| fantacalcio.it | ✅ | — | % titolarità esplicite |
| sosfanta.com | ✅ | — | % titolarità esplicite |
| sport.sky.it | ✅ | — | undici + ballottaggi |
| **gazzetta.it** | ❌ | ✅ | **la più ricca**: undici, panchina, ballottaggi in %, diffidati, rientri, timestamp per partita |
| bwin.it | ❌ | ✅ | 1X2, U/O, marcatore, assist, ammonizione |
| snai.it | ❌ | ✅ | 1X2, U/O, marcatore |
| bet365.it | ❌ | ❌ | blocca l'automazione |

**Non aggiungere Sisal né Eurobet**: Sisal replica il feed Snai, bwin è la piattaforma di Eurobet.
Sarebbe un falso consenso. Le famiglie indipendenti sono due.

Il venerdì mattina le gare di domenica e lunedì sono le meno affidabili: per quelle il mercato
pesa più del dato editoriale, e il peso di Gazzetta si dimezza se il suo timestamp supera le 48h.

## Limiti noti

- **Assist e ammonizioni sono single-source** (solo bwin): Snai non li espone per giocatore.
- **L'esecuzione automatica ha le quote 1X2 solo per le gare già quotate** da BetExplorer
  (tipicamente quelle entro 48 ore): per le altre il contesto partita resta neutro e viene
  dichiarato. Con una chiave gratuita di
  [the-odds-api.com](https://the-odds-api.com) (500 richieste al mese, ne serve una a settimana)
  anche il report automatico avrebbe 1X2 e Over/Under di tutte e 10 le partite: il codice è già
  pronto, basta aggiungere il secret `ODDS_API_KEY` nelle impostazioni del repo.
- Il clean sheet è modellato (Poisson sui gol attesi), non letto da un mercato dedicato.
- Le quote si muovono di ora in ora: ogni report vale per l'istante indicato in testata.
