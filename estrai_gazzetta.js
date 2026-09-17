// gazzetta.it/Calcio/prob_form/ — da eseguire con javascript_tool DOPO il browser (WebFetch e bloccato).
// Ritorna, per ogni partita che contiene almeno uno dei 25: intestazione (con il timestamp della
// partita), le righe Ballottaggio/Squalificati/Indisponibili/Diffidati, e per ciascun giocatore
// se e in panchina e in quali righe compare.
// Conversione in P(gioca): titolare senza ballottaggio 0.90 | % del ballottaggio se indicata |
// in panchina 0.12 | indisponibile o squalificato 0.00.
// ATTENZIONE: usare il timestamp "Ultimo aggiornamento" di ogni partita — se supera le 48h,
// dimezzare il peso di questa fonte per quella partita (gz_vecchia=1 in giocatori.py).
const TG=["Martinez","Martínez","Jones","Thuram","Provedel","Doekhi","Gudmundsson","Skorupski",
          "Chalobah","Bernardeschi","Lulli","Kone","Koné","Comuzzo","Pavlovic","Pulisic","Ramos",
          "Vojvoda","Kalulu","Alajbegovic","Gonzalez","González","Woltemade","Kolo","Gallo",
          "Politano","Pellegrino","Colombo"];
const t=document.querySelector('main').innerText;
const blocks=t.split('Torna su').filter(b=>b.indexOf('Modulo:')>0);
const out=blocks.map(b=>{
  const lines=b.split('\n').map(x=>x.trim()).filter(Boolean);
  const head=lines.slice(0,12).filter(x=>!/^\d+$/.test(x)).slice(0,8).join(' | ');
  const key=lines.filter(x=>/^(Ballottaggio|Squalificati|Indisponibili|Diffidati):/.test(x));
  const bench=lines.filter(x=>x.startsWith('Panchina:')).join(' ;; ');
  const found={};
  TG.forEach(n=>{ if(!b.includes(n)) return;
    found[n]={ panchina: bench.includes(n),
               righe: lines.filter(x=>x.includes(n)&&!x.startsWith('Panchina:')).slice(0,3) }; });
  return Object.keys(found).length ? {head, key, miei:found} : null;
}).filter(Boolean);
JSON.stringify(out,null,1);
