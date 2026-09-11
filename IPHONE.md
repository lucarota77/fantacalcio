# Lanciare il report dall'iPhone

Obiettivo: un tap (o "Ehi Siri") e il report si rigenera, senza Mac acceso.
Si usa l'app **Comandi** (Shortcuts), già installata su ogni iPhone: nessun servizio
intermedio, nessun ritardo, funziona anche offline dal Mac.

---

## Passo 1 — Crea il token (una volta sola, ~2 minuti)

Più comodo dal Mac. Apri **https://github.com/settings/personal-access-tokens/new**

| Campo | Cosa mettere |
|---|---|
| Token name | `Shortcut fantacalcio iPhone` |
| Expiration | 1 anno (o *No expiration* se preferisci non rifarlo) |
| Repository access | **Only select repositories** → `lucarota77/fantacalcio` |
| Permissions → Repository permissions → **Actions** | **Read and write** |

Lascia tutto il resto com'è, poi **Generate token**. Copia subito la stringa che inizia con
`github_pat_…`: **non sarà più visibile**. Mandatela su iPhone come preferisci (iMessage a te
stesso, Note, password manager).

> Il token può solo far partire le Actions di questo repo. Se lo perdi, revocalo dalla stessa
> pagina e generane un altro.

---

## Passo 2 — Crea il comando

App **Comandi** → **+** in alto a destra → **Aggiungi azione** → cerca
**"Ottieni contenuti di URL"**.

Tocca il campo URL e incolla:

```
https://api.github.com/repos/lucarota77/fantacalcio/actions/workflows/report.yml/dispatches
```

Tocca **Mostra altro** per aprire le opzioni, poi:

| Opzione | Valore |
|---|---|
| **Metodo** | `POST` |
| **Intestazioni** → Aggiungi nuova intestazione | chiave `Authorization` · valore `Bearer github_pat_…` |
| **Intestazioni** → Aggiungi nuova intestazione | chiave `Accept` · valore `application/vnd.github+json` |
| **Corpo richiesta** | `JSON` |
| **Corpo richiesta** → Aggiungi nuovo campo → **Testo** | chiave `ref` · valore `main` |

Attenzione a `Bearer`: va scritto prima del token, con uno spazio in mezzo.

---

## Passo 3 — Aggiungi il ritorno visivo (consigliato)

Sotto l'azione precedente aggiungi **Mostra notifica** con testo
`Report fantacalcio avviato — pronto fra un paio di minuti`.

Se preferisci vedere subito il risultato, invece della notifica metti
**Attendi** `150` secondi e poi **Apri URL** `https://lucarota77.github.io/fantacalcio/`.

---

## Passo 4 — Nome, icona, home, Siri

In alto tocca il nome del comando → chiamalo **Report fantacalcio** e scegli l'icona ⚽
(il nome è anche la frase per Siri: *"Ehi Siri, Report fantacalcio"*).

Poi menu **⋯** → **Aggiungi alla schermata Home**.

---

## Verificare che funzioni

Dopo il tap, il run compare qui: **https://github.com/lucarota77/fantacalcio/actions**
La pagina si aggiorna entro un paio di minuti su **https://lucarota77.github.io/fantacalcio/**

Se il comando dà errore:

| Sintomo | Causa |
|---|---|
| Nessuna risposta, comando OK | è normale: l'API risponde `204 No Content` |
| `401 Bad credentials` | token sbagliato, o manca `Bearer ` davanti |
| `403` | al token manca il permesso **Actions: Read and write** |
| `404` | URL sbagliato, oppure il token non vede questo repository |

---

## Cosa lancia, esattamente

La **parte automatica**: probabili formazioni (Gazzetta + fantacalcio.it), MV e fantamedia,
quote 1X2. I mercati per giocatore (gol, assist, ammonizione) vengono dall'ultima passata
fatta col Mac, e la pagina dichiara in testata da quante ore. Per rilevarli di nuovo serve il
Mac acceso: bwin e Snai bloccano gli IP dei datacenter anche con un browser vero.

## Perché non IFTTT

Servirebbe comunque **lo stesso token** dentro una sua azione webhook, ma con un intermediario
in più, qualche secondo di latenza e il limite di applet del piano gratuito. Comandi è nativo,
immediato e integrato con Siri. Se preferisci comunque IFTTT: applet con trigger *Button
widget* e azione *Webhooks → Make a web request*, stessi URL, metodo, header e body del Passo 2.

## Alternativa senza token

App **GitHub** ufficiale → repo `fantacalcio` → tab **Actions** → *Report fantacalcio* →
**Run workflow**. Più tap, ma niente da configurare.
