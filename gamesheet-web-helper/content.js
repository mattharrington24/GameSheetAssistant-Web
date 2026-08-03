const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const norm=value=>String(value||'').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();
const visible=el=>!!(el&&el.getClientRects().length);
const textIs=(el,text)=>norm(el.textContent)===norm(text);
const all=(selector)=>[...document.querySelectorAll(selector)].filter(visible);
function heading(text){return all('h1,h2,h3,h4,h5,h6').find(el=>textIs(el,text));}
function y(el){return el.getBoundingClientRect().top+scrollY;}
function controlsBetween(start,end){const low=y(start),high=end?y(end):Infinity;return all('input,select').filter(el=>{const top=y(el);return top>low&&top<high;});}
function buttonsBetween(start,end,label){const low=y(start),high=end?y(end):Infinity;return all('button').filter(el=>{const top=y(el);return top>low&&top<high&&textIs(el,label);});}
function groupsByRow(controls){
  const rows=[];
  controls.sort((a,b)=>y(a)-y(b)||a.getBoundingClientRect().left-b.getBoundingClientRect().left).forEach(el=>{
    const top=y(el);let row=rows.find(r=>Math.abs(r.top-top)<12);if(!row){row={top,controls:[]};rows.push(row);}row.controls.push(el);
  });
  return rows.filter(r=>r.controls.length>=2).sort((a,b)=>a.top-b.top);
}
function setInput(el,value){
  const setter=Object.getOwnPropertyDescriptor(el instanceof HTMLInputElement?HTMLInputElement.prototype:HTMLTextAreaElement.prototype,'value')?.set;
  if(setter)setter.call(el,String(value));else el.value=String(value);
  el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));
}
function optionScore(option,wanted){
  const a=norm(option.textContent),b=norm(wanted);if(a===b)return 100;if(a.includes(b)||b.includes(a))return 80;
  const number=(b.match(/\b\d+\b/)||[])[0],name=b.replace(/\b\d+\b/,'').trim();let score=0;
  if(number&&new RegExp(`\\b${number}\\b`).test(a))score+=35;if(name&&a.includes(name))score+=55;
  const last=name.split(' ').at(-1);if(last&&a.includes(last))score+=20;return score;
}
function setSelect(el,wanted,{optional=false}={}){
  if(!wanted&&optional){el.selectedIndex=0;el.dispatchEvent(new Event('change',{bubbles:true}));return;}
  const ranked=[...el.options].map(o=>({o,score:optionScore(o,wanted)})).sort((a,b)=>b.score-a.score);
  if(!ranked[0]||ranked[0].score<35)throw new Error(`Could not match “${wanted}” in a GameSheet dropdown.`);
  el.value=ranked[0].o.value;el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));
}
function periodValue(period){const match=String(period).match(/\d+/);return match?match[0]:String(period).toUpperCase().startsWith('OT')?'OT1':period;}
function splitTeams(items,game){return [items.filter(i=>i.team===game.away_team),items.filter(i=>i.team===game.home_team)];}
async function ensureRows(sectionStart,sectionEnd,buttonLabel,teamItems){
  const buttons=buttonsBetween(sectionStart,sectionEnd,buttonLabel);
  if(buttons.length<2)throw new Error(`Could not find both ${buttonLabel} buttons.`);
  for(let side=0;side<2;side++){
    for(let guard=0;guard<teamItems[side].length+2;guard++){
      const boundaries=[sectionStart,...buttons,sectionEnd].filter(Boolean).sort((a,b)=>y(a)-y(b));
      const low=side===0?y(sectionStart):y(buttons[0]);const high=side===0?y(buttons[0]):y(sectionEnd);
      const rows=groupsByRow(controlsBetween(sectionStart,sectionEnd).filter(c=>y(c)>low&&y(c)<high));
      if(rows.length>=teamItems[side].length)break;
      buttons[side].click();await pause(120);
    }
  }
}
function rowsForTeam(sectionStart,sectionEnd,buttonLabel,side){
  const buttons=buttonsBetween(sectionStart,sectionEnd,buttonLabel);
  const low=side===0?y(sectionStart):y(buttons[0]),high=side===0?y(buttons[0]):y(sectionEnd);
  return groupsByRow(controlsBetween(sectionStart,sectionEnd).filter(c=>y(c)>low&&y(c)<high));
}
async function fillGoals(data){
  const start=heading('Scoring'),end=heading('Penalties');if(!start||!end)throw new Error('Scoring section was not found.');
  const byTeam=splitTeams(data.goals,data.game);await ensureRows(start,end,'ADD GOAL',byTeam);
  for(let side=0;side<2;side++){
    const rows=rowsForTeam(start,end,'ADD GOAL',side);
    byTeam[side].forEach((goal,i)=>{const c=rows[i]?.controls;if(!c||c.length<6)throw new Error('A goal row did not have the expected fields.');setSelect(c[0],periodValue(goal.period));setInput(c[1],goal.time);setSelect(c[2],goal.player);setSelect(c[3],goal.assists[0]||'',{optional:true});setSelect(c[4],goal.assists[1]||'',{optional:true});});
  }
}
async function fillPenalties(data){
  const start=heading('Penalties'),end=heading('Shootouts');if(!start||!end)throw new Error('Penalties section was not found.');
  const byTeam=splitTeams(data.penalties,data.game);await ensureRows(start,end,'ADD PENALTY',byTeam);
  for(let side=0;side<2;side++){
    const rows=rowsForTeam(start,end,'ADD PENALTY',side);
    byTeam[side].forEach((p,i)=>{const c=rows[i]?.controls;if(!c||c.length<8)throw new Error('A penalty row did not have the expected fields.');setSelect(c[0],periodValue(p.period));setSelect(c[1],p.offender);setSelect(c[2],p.served_by);setSelect(c[3],p.length);setSelect(c[4],p.code);setInput(c[5],p.time_off);setInput(c[6],p.time_start);setInput(c[7],p.time_on||p.time_off);});
  }
}
function nearbyText(el){const row=el.closest('tr')||el.parentElement?.parentElement||el.parentElement;return norm(row?.textContent);}
function fillShots(data){
  const start=heading('Shots'),end=heading('Scoring');if(!start||!end)throw new Error('Shots section was not found.');
  const rows=groupsByRow(controlsBetween(start,end));
  for(const target of data.goalie_shots){
    const wanted=norm(target.goalie),number=(wanted.match(/\b\d+\b/)||[])[0],last=wanted.split(' ').at(-1);
    const row=rows.find(r=>{const t=nearbyText(r.controls[0]);return (!number||new RegExp(`\\b${number}\\b`).test(t))&&(!last||t.includes(last));});
    if(!row)throw new Error(`Could not find the shots row for ${target.goalie}.`);
    target.periods.forEach((value,i)=>{if(value!==null&&row.controls[i])setInput(row.controls[i],value);});
  }
}
function inspect(data){
  if(!heading('Edit Game'))throw new Error('Open a GameSheet Edit Game page first.');
  const body=norm(document.body.textContent);
  if(!body.includes(norm(data.game.away_team))||!body.includes(norm(data.game.home_team)))throw new Error('The teams on this GameSheet page do not match the copied game.');
  return `Page matched. Ready for ${data.goals.length} goals and ${data.penalties.length} penalties.`;
}
chrome.runtime.onMessage.addListener((request,_sender,respond)=>{
  (async()=>{try{const message=inspect(request.data);if(request.action==='fill'){await fillGoals(request.data);await fillPenalties(request.data);fillShots(request.data);window.scrollTo({top:y(heading('Scoring'))-80,behavior:'smooth'});respond({ok:true,message:'Form filled. Review goals, penalties, shots, goalie shifts, and lineups. Save Changes was not clicked.'});}else respond({ok:true,message});}catch(e){respond({ok:false,error:e.message});}})();return true;
});
