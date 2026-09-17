// Estrae da una scheda partita bwin i mercati marcatore/assist/cartellino dei 25 giocatori.
// Uso: javascript_tool sulla pagina /it/sports/eventi/<slug>-2:<id> (attendere ~5s dopo il navigate).
// Ritorna: {match, anytime:{nome:quota}, assist:{...}, card:{...}}
// I nomi in TG vanno tenuti allineati a rosa.json (cognomi o frammenti univoci).
const T=e=>(e.textContent||'').trim(),
      L=s=>[...document.querySelectorAll('*')].filter(e=>T(e)===s&&!e.children.length);
const b=L('Giocatori'); if(b.length) b[0].click();
await new Promise(r=>setTimeout(r,4000));
for(let i=0;i<3;i++){ L('Mostra di più').forEach(e=>{try{e.click()}catch(_){}});
                      await new Promise(r=>setTimeout(r,1200)); }
const t=document.querySelector('main').innerText,
      tm=document.title.replace(/^Quote scommesse /,'').replace(/ \| bwin.*$/,'').split(' - ').map(s=>s.trim());
const TG=["Martinez","Martínez","Jones","Thuram","Provedel","Doekhi","Gudmundsson","Skorupski",
          "Chalobah","Bernardeschi","Lulli","Kone","Koné","Comuzzo","Pavlovic","Pulisic","Ramos",
          "Vojvoda","Kalulu","Alajbegovic","Gonzalez","González","Woltemade","Kolo","Gallo",
          "Politano","Pellegrino","Colombo"];
// I nomi di squadra vanno scartati o disallineano l'accoppiamento nome <-> quota.
const SK=new Set(['Tutti','1+','2+','3+','4+','5+','Mostra di più','Mostra di meno','Gol singolo',
  'Gol multipli','In qualsiasi momento','Nessun marcatore','Tempi regolamentari','1° tempo',
  '2° tempo','Over','Under','Sì','No'].concat(tm));
const ST=['Ultimo Marcatore','1° marcatore','1º marcatore','Totale tiri','Fuorigioco',
          'Riceve un cartellino','Totale assist','Mostra di meno','Marcatori'];
const sec=(a,s)=>{const i=t.indexOf(a); if(i<0) return null; let j=t.length;
  for(const x of s){const k=t.indexOf(x,i+a.length); if(k>0&&k<j) j=k;}
  return t.slice(i+a.length,j).split('\n').map(x=>x.trim()).filter(Boolean);};
// Nelle sezioni assist/cartellino i nomi vengono tutti prima e le quote tutte dopo:
// si separa per tipo e si accoppia per indice. Nella sezione marcatori sono alternati: stesso esito.
const pr=l=>{ if(!l) return null; const n=[],o=[];
  for(const x of l){ if(SK.has(x)) continue;
    /^\d+([.,]\d+)?$/.test(x) ? o.push(parseFloat(x.replace(',','.'))) : n.push(x); }
  const r={}; n.forEach((x,i)=>{ if(o[i]!=null) r[x]=o[i]; }); return r; };
const mn=o=>{ if(!o) return null; const r={};
  for(const k in o) if(TG.some(x=>k.includes(x))) r[k]=o[k]; return r; };
JSON.stringify({ match:tm.join('-'),
  anytime: mn(pr(sec('In qualsiasi momento', ST.filter(s=>s!=='Marcatori')))),
  assist:  mn(pr(sec('Totale assist giocatore', ST))),
  card:    mn(pr(sec('Riceve un cartellino', ST))) });
