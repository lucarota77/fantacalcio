// SNAI — due usi distinti.
//
// (A) LISTA: su https://www.snai.it/scommesse/quote/calcio/serie-a  ->  1X2 e Under/Over 2.5
//     di tutte e 10 le partite in una sola passata.
const t=document.querySelector('main').innerText;
const re=/(\d{2}\/\d{2})\n(\d{2}:\d{2})\n([^\n]+)\n([^\n]+)\nEsito Finale 1x2\n1\n([\d.]+)\nX\n([\d.]+)\n2\n([\d.]+)[\s\S]{0,120}?Under\/Over\n2\.5\nUNDER\n([\d.]+)\nOVER\n([\d.]+)/g;
const out=[];let m;
while((m=re.exec(t))!==null) out.push({d:m[1]+' '+m[2],h:m[3],a:m[4],
  q1:+m[5],qx:+m[6],q2:+m[7],under25:+m[8],over25:+m[9]});
JSON.stringify(out);

/* (B) SCHEDA EVENTO: su https://www.snai.it/scommesse/evento/calcio/serie-a/<casa>-<trasferta>
       -> quote "Marcatore" (anytime) dei 25. Attendere ~7s dopo il navigate.
       NON cliccare "Vedi le altre": rompe l'estrazione (il main viene sostituito).
       Snai NON espone assist per giocatore, e il tab SANZIONI contiene solo rigori,
       espulsioni e consulti VAR: ammonizioni e assist restano su bwin.
       I nomi Snai sono in MAIUSCOLO e a volte invertiti ("MARTINEZ LAUTARO"): attenzione ai
       falsi positivi fra omonimi di squadre diverse.

const leaf=s=>[...document.querySelectorAll('*')].filter(e=>(e.textContent||'').trim()===s&&!e.children.length);
const g=leaf('GIOCATORI'); if(g.length) g[0].click();
await new Promise(r=>setTimeout(r,5000));
const TG=["MARTINEZ","JONES","THURAM","PROVEDEL","DOEKHI","GUDMUNDSSON","SKORUPSKI","MIRANDA",
          "BERNARDESCHI","LULLI","KONE","COMUZZO","PAVLOVIC","PULISIC","RAMOS","VOJVODA","KALULU",
          "ALAJBEGOVIC","GONZALEZ","WOLTEMADE","KOLO","GALLO","POLITANO","PELLEGRINO","COLOMBO"];
const t=(document.querySelector('main')||document.body).innerText;
const re=/([A-ZÀ-Ü][^\n]{2,40})\n\s*Marcatore\n([\d.]+)/g;
const o={}; let m;
while((m=re.exec(t))!==null){ const n=m[1].trim(); if(TG.some(x=>n.includes(x))) o[n]=+m[2]; }
JSON.stringify(o);
*/
