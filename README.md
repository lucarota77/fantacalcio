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

## Come funziona: due esecuzioni

| | Quando | Dove | Cosa raccoglie |
|---|---|---|---|
| **Automatica** | venerdì 14:00, sempre | GitHub Actions | Probabili formazioni complete (Gazzetta, parsing deterministico). **Niente quote**: i runner GitHub non hanno browser e BetExplorer blocca i loro IP. La pagina mostra un avviso di report parziale. |
| **Completa** | venerdì 14:15, se il Mac è acceso | task locale di Claude Code | Aggiunge marcatore, assist e ammonizione da bwin e Snai, che richiedono il browser, e ripubblica il sito senza avviso. |

La seconda sovrascrive la prima: il risultato è lo stesso URL, aggiornato.

### Perché non una routine cloud di Claude
Provata e scartata: l'ambiente cloud ha un **proxy di egress** che blocca gazzetta.it,
betexplorer.com, fantacalcio.it, sosfanta.com e sport.sky.it (`EGRESS_BLOCKED`), non ha il
browser, ed Exa restituisce contenuto in cache di settimane prima. GitHub Actions ha rete
libera, gira senza PC e può committare da solo.

## Lanciarlo a mano

Dal terminale:
```bash
gh workflow run "Report fantacalcio" --repo lucarota77/fantacalcio
```
Da web: la tab **Actions** del repo → *Report fantacalcio* → *Run workflow*.

Da un servizio esterno (IFTTT, Shortcut iOS, automazione domestica) — serve un token
fine-grained sul solo repo `fantacalcio` con permesso **Actions: write**:
```
POST https://api.github.com/repos/lucarota77/fantacalcio/actions/workflows/report.yml/dispatches
Authorization: Bearer <TOKEN>
Accept: application/vnd.github+json
Body: {"ref":"main"}
```

Per la passata completa con le quote serve il Mac: pannello **Scheduled** → "Run now" sul task
⚽ *Fantacalcio — passata completa*, oppure in chat «lancia la passata completa del fantacalcio».

## Ora legale

Il workflow fira alle **12:00 e 13:00 UTC** e tiene solo l'esecuzione in cui a Roma sono le 14.
Così il venerdì alle 14:00 italiane vale tutto l'anno e non serve correggere il cron ai cambi
d'ora — a differenza delle routine cloud, dove il cron è in UTC fisso.

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
- **L'esecuzione automatica non ha quote.** Con una chiave gratuita di
  [the-odds-api.com](https://the-odds-api.com) (500 richieste al mese, ne serve una a settimana)
  anche il report automatico avrebbe 1X2 e Over/Under di tutte e 10 le partite: il codice è già
  pronto, basta aggiungere il secret `ODDS_API_KEY` nelle impostazioni del repo.
- Il clean sheet è modellato (Poisson sui gol attesi), non letto da un mercato dedicato.
- Le quote si muovono di ora in ora: ogni report vale per l'istante indicato in testata.
