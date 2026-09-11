# Metodo di calcolo — Report Fantacalcio

Documento di riferimento letto a ogni esecuzione. Modificando i pesi qui cambi il
comportamento del report senza toccare il task schedulato.

---

## 0. Regola generale sulle fonti — browser come fallback

Se una fonte **non è leggibile con WebFetch** (403, paywall, contenuto vuoto), non si scarta:
si riprova con il **browser** (`mcp__Claude_Browser__*`), che supera i gate JS, i cookie
wall e le protezioni anti-bot. Vale per ogni fonte, presente e futura.

Accorgimenti imparati:
- Il pannello browser è spesso **nascosto**: `computer` (scroll, click per coordinate) fallisce
  con *"not compositing frames"*. Usare `javascript_tool` per scorrere, cliccare ed estrarre.
- Sui banner cookie scegliere sempre l'opzione **più conservativa** ("Strettamente necessari",
  "Rifiuta"), mai "Accetta tutti".
- Mai fare login, registrazioni o giocate: solo lettura di quote e contenuti pubblici.

Stato delle fonti al 11/09/2026:

| Fonte | WebFetch | Browser |
|---|---|---|
| fantacalcio.it, sosfanta.com, sky, sportmediaset | ✅ | — |
| **gazzetta.it** | ❌ bloccato | ✅ **e dà più dati di tutti** |
| bwin.it | ❌ | ✅ |
| snai.it | ❌ | ✅ |
| bet365.it | ❌ | ❌ "Contenuto non disponibile" |

Gazzetta via browser è la fonte più ricca: undici con numeri di maglia, **panchina completa**,
**ballottaggi con percentuali**, squalificati, **diffidati**, indisponibili con giornata di
rientro, e un **timestamp per singola partita**.

---

## 1. Probabilità di giocare — `P_gioca`

Media **pesata** delle indicazioni di titolarità delle fonti raggiungibili.
Se una fonte non è raggiungibile, si rinormalizzano i pesi sulle restanti.

| Fonte | Peso | Tipo di dato |
|---|---|---|
| **gazzetta.it** (browser) | 0.30 | undici + panchina + ballottaggi in % + diffidati + timestamp |
| fantacalcio.it | 0.28 | % titolarità esplicita |
| sosfanta.com | 0.22 | % titolarità esplicita |
| sport.sky.it | 0.20 | formazione + ballottaggi |
| sportmediaset.it | — | riserva, se le altre mancano |

**Decadimento per freschezza.** Gazzetta data ogni partita. Se il dato di una partita è più
vecchio di **48 ore**, il peso di quella fonte per quella partita va **dimezzato**: il venerdì
mattina le gare del lunedì sono spesso ferme a inizio settimana.

**Conversione per le fonti senza percentuale** (Sky, Sportmediaset, Gazzetta):

| Situazione | P |
|---|---|
| Titolare indicato, nessun ballottaggio | 0.90 |
| Favorito nel ballottaggio (indicato per primo) | 0.62 |
| Sfavorito nel ballottaggio | 0.38 |
| In rosa ma non tra gli 11 né nei ballottaggi | 0.12 |
| Infortunato / squalificato / indisponibile | 0.00 |

**Override assoluti** (battono qualsiasi media): squalificato, infortunato
conclamato, non convocato, squadra che non gioca nel turno → `P_gioca = 0`.

**Segnale di controllo dai bookmaker**: se un giocatore NON compare nella lista
"Marcatori · In qualsiasi momento" del suo match mentre i compagni di reparto ci
sono, è un forte indizio di indisponibilità → abbassare `P_gioca` e segnalarlo.

---

## 2. Da quota a probabilità — rimozione del margine (de-vig)

Una quota **non** è una probabilità: contiene il margine del bookmaker
(*overround*). Va sempre rimosso, altrimenti tutte le probabilità risultano
gonfiate del 5–20%.

**Passo 1 — margine del match.** Dal mercato 1X2 dello stesso incontro:

```
M = 1/q1 + 1/qX + 1/q2          (tipicamente 1.05 – 1.08)
```

**Passo 2 — probabilità 1X2 pulite:**

```
P(1) = (1/q1) / M      P(X) = (1/qX) / M      P(2) = (1/q2) / M
```

**Passo 3 — mercati giocatore.** I mercati "sì/no" per giocatore (marcatore,
assist, cartellino) hanno margine più alto del 1X2. Si applica:

```
p_grezza = 1 / quota
p        = p_grezza / M_giocatori      con   M_giocatori = M ^ 1.8
```

L'esponente 1.8 approssima il margine maggiore dei mercati player-prop.
(Es.: M = 1.06 → M_giocatori ≈ 1.11, cioè ~11% di gonfiaggio rimosso.)

**Passo 4 — controllo di coerenza sui marcatori.** La somma delle `p` di tutti i
marcatori "in qualsiasi momento" di un match deve avvicinarsi ai **gol attesi**
del match. I gol attesi si stimano dalla linea Over/Under 2.5:

```
gol_attesi ≈ 2.5 + 1.15 * (P(Over 2.5) - 0.5) * 4
```

Se la somma dei marcatori devig si discosta di oltre il 15%, riscalare
proporzionalmente tutte le `p` marcatore del match su `gol_attesi * 0.78`
(il fattore 0.78 tiene conto di autogol e delle marcature multiple dello stesso
giocatore, che il mercato "anytime" non distingue).

> **ATTENZIONE — errore da non fare:** la quota "anytime goalscorer" **incorpora
> già** la probabilità che il giocatore scenda in campo. NON moltiplicarla di
> nuovo per `P_gioca`. Per ottenere la probabilità *condizionata a giocare* si
> divide: `P_gol|gioca = P_gol / P_gioca`.

---

## 2-bis. Il mercato come segnale di titolarità (regola aggiunta l'11/09/2026)

Le probabili formazioni dei siti invecchiano: il venerdì mattina molte redazioni
non hanno ancora pubblicato le squadre che giocano la domenica o il lunedì. Le
quote dei bookmaker, invece, sono già allineate. Quando un giocatore è quotato
**basso** nel mercato marcatori, il book lo sta dando in campo.

Si ricava un **floor** su `P_gioca` dalla probabilità di gol devig:

| P_gol devig | Attaccante | Centrocampista | Difensore |
|---|---|---|---|
| ≥ 0.35 / 0.20 / 0.09 | 0.92 | 0.90 | 0.90 |
| ≥ 0.25 / 0.14 / 0.06 | 0.80 | 0.75 | 0.75 |
| ≥ 0.18 / 0.10 / 0.04 | 0.65 | 0.60 | 0.60 |
| ≥ 0.12 / 0.06 / 0.025 | 0.50 | 0.45 | 0.45 |

**Combinazione con la media editoriale `media`:**

```
se floor <= media            ->  P_gioca = media        (mai al ribasso: è un floor)
se floor - media  > 0.32     ->  P_gioca = 0.6*floor + 0.4*media   e marca ⚠️ CONFLITTO
altrimenti                   ->  P_gioca = floor
```

> Il floor può solo **alzare** la stima, mai abbassarla. Un terzino con quota gol
> a 20.00 non è un indizio di panchina: è semplicemente un terzino.

**Segnale opposto — assenza dai mercati.** Se un giocatore non compare in *nessun*
mercato (marcatore, assist, cartellino) mentre i compagni ci sono, è quasi
certamente indisponibile: `P_gioca = 0.10` e alert nel report, anche se le
probabili formazioni lo danno in campo.

**Segnale di trasferimento.** Se un giocatore compare nei mercati di una partita
diversa da quella della squadra registrata in `rosa.json`, è stato ceduto:
aggiornare `rosa.json` e segnalarlo.

---

## 3. Mercati bwin da leggere (tab **Giocatori** della scheda match)

| Dato richiesto | Mercato bwin |
|---|---|
| Probabilità di segnare | `Marcatori` → colonna **In qualsiasi momento** |
| Probabilità di assist | `Totale assist giocatore` → colonna **1+** |
| Probabilità di ammonizione | `Riceve un cartellino` |
| *(bonus)* tiri in porta | `Totale tiri in porta giocatore` → **1+** |

Dal tab **Gol / Principali** della stessa scheda:

| Dato | Mercato |
|---|---|
| Clean sheet squadra X | `<avversario> - Over/Under` linea **0,5** → quota **Under** |
| Gol attesi match | `Over/Under` linea **2,5** |

`P_cleansheet(X) = devig( 1 / quota_Under_0.5_avversario )`

---

## 4. Fallback quando il giocatore non è quotato

Capita per riserve e giovani. Stima da baseline di ruolo, corretta per la forza
offensiva della squadra (`F = P(vittoria squadra) / 0.33`, limitata a [0.5, 1.8]):

| Ruolo | P_gol base | P_assist base | P_amm base |
|---|---|---|---|
| P | 0.00 | 0.01 | 0.06 |
| D centrale | 0.04 | 0.02 | 0.22 |
| D esterno | 0.03 | 0.07 | 0.18 |
| C | 0.07 | 0.09 | 0.20 |
| C offensivo / trequartista | 0.13 | 0.13 | 0.15 |
| A | 0.24 | 0.10 | 0.13 |

`P_stimata = base * F * P_gioca` — e va **marcata come stima** nel report.

---

## 5. Indice di Rilevanza (IR) — ordinamento dei 25

Valore atteso in punti fantacalcio dai bonus/malus (gol +3, assist +1, ammonizione −0,5,
clean sheet +1 per i difensori, portiere imbattuto +1).

Sia `ctx = P(vittoria della squadra) − 0,33` il **contesto partita**: quanto la squadra è
favorita rispetto a un esito neutro.

```
Portiere       IR = P_gioca * ( 3,0*CS − gol_subiti_attesi*0,5 + 0,5 + 2,2*ctx )
Difensore      IR = 3*P_gol + P_assist − 0,5*P_amm + P_gioca*( 1,5*CS + 1,8*ctx )
Centrocampista IR = 3*P_gol + P_assist − 0,5*P_amm + P_gioca*0,9*ctx
Attaccante     IR = 3*P_gol + P_assist − 0,5*P_amm + P_gioca*0,7*ctx
```

**Perché il peso del contesto cresce scendendo di reparto.** Per attaccanti e centrocampisti
la forza della squadra è **già dentro** le quote di gol e assist: un attaccante del Como contro
il Parma ha già una quota marcatore corta. Pesarla di nuovo sarebbe doppio conteggio, quindi il
coefficiente resta basso (0,7–0,9). Per portieri e difensori invece gol e assist sono rari e
quasi irrilevanti: il loro rendimento dipende da clean sheet e solidità, cioè dal contesto, che
perciò pesa molto di più (1,8 per i difensori, 2,2 per i portieri).

Conseguenza pratica: un difensore titolare fisso di una squadra sfavorita vale meno di un
difensore della capolista, anche a parità di probabilità di scendere in campo.

**Etichetta operativa:**

| Condizione | Consiglio |
|---|---|
| `P_gioca >= 0.75` e IR nel terzo superiore del ruolo | 🟢 **SCHIERA** |
| `P_gioca >= 0.75` e IR medio | 🟡 **OK** |
| `0.40 <= P_gioca < 0.75` | 🟠 **BALLOTTAGGIO** |
| `P_gioca < 0.40` | 🔴 **PANCHINA** |

---

## 5-bis. Formazione consigliata — modulo 3-4-3

Luca gioca **3-4-3**: si consigliano **1 portiere, 3 difensori, 4 centrocampisti, 3 attaccanti**.

Si prendono i migliori per IR in ciascun ruolo, dando la precedenza a chi ha
`P_gioca >= 0.40`; chi resta fuori diventa la panchina, ordinata per IR. Vanno sempre indicate
le **prime riserve per ruolo**, perché un titolare con ⚠️ può saltare all'ultimo.

---

## 6. Bookmaker multipli e indipendenza delle fonti

Le probabilità devig si **mediano fra i book**, e la media va rinormalizzata a 1.
Si riporta lo **scarto** fra book quando supera i 3 punti percentuali: segnala una linea
incerta o una notizia di formazione non ancora prezzata da tutti.

> **Attenzione: contare i book non basta, vanno verificati indipendenti.**
> Al 11/09/2026: **Sisal restituisce quote identiche a Snai** (stesso feed), e **bwin è la
> piattaforma di Eurobet**. Mediare Snai con Sisal, o bwin con Eurobet, produce un falso
> consenso. Le famiglie realmente indipendenti trovate sono **due**: bwin/Eurobet e Snai/Sisal.

| Book | 1X2 e Over/Under | Marcatore | Assist | Ammonizione |
|---|---|---|---|---|
| bwin | ✅ | ✅ | ✅ | ✅ |
| Snai | ✅ | ✅ | ✗ (colonna vuota) | ✗ (il tab Sanzioni ha solo rigori/espulsioni/VAR) |
| bet365 | ✗ blocca l'automazione | ✗ | ✗ | ✗ |

Assist e ammonizioni restano quindi su **bwin soltanto**: vanno dichiarati come single-source.
Un giocatore assente dai mercati di **un** book non è indisponibile — va verificato sull'altro:
l'11/09/2026 Pulisic mancava del tutto da bwin ma Snai lo quotava 3.25 marcatore.

## 6-bis. Ranking squadre

Tutte e 20 le squadre del turno, ordinate per `P(vittoria)` devig media.

---

## 7. Regole di qualità

- **Mai inventare una quota o una percentuale.** Se un dato manca, scrivere `n.d.`
  e spiegare perché in fondo al report.
- Registrare sempre **data e ora della rilevazione**: le quote si muovono.
- Indicare per ogni giocatore **quali fonti** hanno contribuito a `P_gioca`.
- Le probabilità sono arrotondate all'intero percentuale; l'IR a due decimali.
- Il gioco è riservato ai maggiorenni. Le quote sono usate qui come *stima di
  probabilità*, non come invito alla scommessa.
