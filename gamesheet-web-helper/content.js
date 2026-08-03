const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const norm=value=>String(value||'').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();
const visible=el=>!!(el&&el.getClientRects().length);
const textIs=(el,text)=>norm(el.textContent)===norm(text);
const all=(selector)=>[...document.querySelectorAll(selector)].filter(visible);
function heading(text){return all('h1,h2,h3,h4,h5,h6').find(el=>textIs(el,text));}
function y(el){if(!el)throw new Error('A required GameSheet page element disappeared while the page was updating.');return el.getBoundingClientRect().top+scrollY;}
function controlsBetween(start,end){const low=y(start),high=end?y(end):Infinity;return all('input,select').filter(el=>{const top=y(el);return top>low&&top<high;});}
function buttonsBetween(start,end,label){const low=y(start),high=end?y(end):Infinity;return all('button').filter(el=>{const top=y(el);return top>low&&top<high&&textIs(el,label);});}
function liveSection(start,end){
  const liveStart=heading(start?.textContent||''),liveEnd=heading(end?.textContent||'');
  if(!liveStart||!liveEnd)throw new Error('GameSheet replaced a section and it could not be reacquired.');
  return {start:liveStart,end:liveEnd};
}
async function waitForButtons(start,end,label,count=2){
  for(let attempt=0;attempt<20;attempt++){
    const buttons=buttonsBetween(start,end,label);if(buttons.length>=count)return buttons;
    await pause(150);
  }
  return buttonsBetween(start,end,label);
}
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
  const a=norm(option.textContent),b=norm(wanted);if(!a||!b)return 0;if(a===b)return 100;if(a.includes(b)||b.includes(a))return 80;
  const number=(b.match(/\b\d+\b/)||[])[0],name=b.replace(/\b\d+\b/,'').trim();let score=0;
  if(number&&new RegExp(`\\b${number}\\b`).test(a))score+=35;if(name&&a.includes(name))score+=55;
  const last=name.split(' ').at(-1);if(last&&a.includes(last))score+=20;
  const words=name.split(' ').filter(word=>word.length>3&&!['minor','major','minutes','penalty'].includes(word));if(words.some(word=>a.includes(word)))score+=45;return score;
}
function selectedMatches(el,wanted){
  const option=el?.options?.[el.selectedIndex];return !!option&&optionScore(option,wanted)>=55;
}
function reacquireSelected(sectionStart,sectionEnd,side,label,anchorName,wanted,timeName){
  const matches=namedRows(sectionStart,sectionEnd,side,label,anchorName).filter(el=>selectedMatches(el,wanted));
  return matches.find(el=>!timeName||!rowField(el,timeName).value)||matches.at(-1);
}
function setSelect(el,wanted,{optional=false}={}){
  if(!wanted&&optional){el.selectedIndex=0;el.dispatchEvent(new Event('change',{bubbles:true}));return;}
  const ranked=[...el.options].map(o=>({o,score:optionScore(o,wanted)})).sort((a,b)=>b.score-a.score);
  if(!ranked[0]||ranked[0].score<35)throw new Error(`Could not match “${wanted}” in a GameSheet dropdown.`);
  el.value=ranked[0].o.value;el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));
}
function periodValue(period){const match=String(period).match(/\d+/);return match?match[0]:String(period).toUpperCase().startsWith('OT')?'OT1':period;}
function gameSheetTime(value){const match=String(value||'').match(/^(\d{1,2}):(\d{2})$/);return match?`${match[1].padStart(2,'0')}:${match[2]}`:value;}
function splitTeams(items,game){return [items.filter(i=>i.team===game.away_team),items.filter(i=>i.team===game.home_team)];}
function teamRows(sectionStart,sectionEnd,_game,side,label){
  const buttons=buttonsBetween(sectionStart,sectionEnd,label).sort((a,b)=>y(a)-y(b));
  let low=y(sectionStart),high=y(sectionEnd);
  if(buttons.length>=2){if(side===0)high=y(buttons[0]);else low=y(buttons[0]);}
  else if(buttons.length===1){if(side===0)high=y(buttons[0]);else low=y(buttons[0]);}
  return groupsByRow(controlsBetween(sectionStart,sectionEnd).filter(c=>y(c)>low&&y(c)<high));
}
function sideLimits(sectionStart,sectionEnd,side,label){
  ({start:sectionStart,end:sectionEnd}=liveSection(sectionStart,sectionEnd));
  const buttons=buttonsBetween(sectionStart,sectionEnd,label).sort((a,b)=>y(a)-y(b));
  let low=y(sectionStart),high=y(sectionEnd);
  if(buttons.length>=2){if(side===0)high=y(buttons[0]);else low=y(buttons[0]);}
  else if(buttons.length===1){if(side===0)high=y(buttons[0]);else low=y(buttons[0]);}
  return {low,high};
}
function namedRows(sectionStart,sectionEnd,side,label,anchorName){
  ({start:sectionStart,end:sectionEnd}=liveSection(sectionStart,sectionEnd));
  const {low,high}=sideLimits(sectionStart,sectionEnd,side,label);
  return all(`select[name="${anchorName}"],input[name="${anchorName}"]`).filter(el=>y(el)>low&&y(el)<high).sort((a,b)=>y(a)-y(b));
}
function rowField(anchor,name){
  const row=anchor.closest('.row')||anchor.parentElement?.parentElement;
  const field=row?.querySelector(`[name="${name}"]`);if(!field)throw new Error(`The new row is missing its ${name} field.`);return field;
}
async function addRow(sectionStart,sectionEnd,game,side,label,index){
  const anchorName=label==='ADD GOAL'?'scorerId':'servedById';
  if(namedRows(sectionStart,sectionEnd,side,label,anchorName).length>index)return;
  let buttons=[];
  for(let attempt=0;attempt<20&&buttons.length<2;attempt++){({start:sectionStart,end:sectionEnd}=liveSection(sectionStart,sectionEnd));buttons=buttonsBetween(sectionStart,sectionEnd,label).sort((a,b)=>y(a)-y(b));if(buttons.length<2)await pause(150);}
  if(buttons.length<2)throw new Error(`Could not find both ${label} buttons before adding a row.`);
  buttons[side].click();
  for(let attempt=0;attempt<20;attempt++){await pause(150);if(namedRows(sectionStart,sectionEnd,side,label,anchorName).length>index){await pause(500);return;}}
  throw new Error(`GameSheet did not create the requested row for ${side===0?game.away_team:game.home_team}.`);
}
async function fillGoals(data){
  const start=heading('Scoring'),end=heading('Penalties');if(!start||!end)throw new Error('Scoring section was not found.');
  const byTeam=splitTeams(data.goals,data.game);
  for(let side=0;side<2;side++){
    for(let i=0;i<byTeam[side].length;i++){
      const goal=byTeam[side][i];await addRow(start,end,data.game,side,'ADD GOAL',i);
      let anchor=namedRows(start,end,side,'ADD GOAL','scorerId').find(el=>!el.value)||namedRows(start,end,side,'ADD GOAL','scorerId')[i];if(!anchor)throw new Error('The newly created goal row could not be found.');
      const opponents=(data.goalies||[]).filter(g=>g.team!==goal.team&&g.minutes!=='0:00');
      setSelect(anchor,goal.player);await pause(300);anchor=reacquireSelected(start,end,side,'ADD GOAL','scorerId',goal.player,'time');if(!anchor)throw new Error(`Could not reacquire the goal row for ${goal.player}.`);
      setSelect(rowField(anchor,'assistAId'),goal.assists[0]||'',{optional:true});setSelect(rowField(anchor,'assistBId'),goal.assists[1]||'',{optional:true});
      if(goal.goalie)setSelect(rowField(anchor,'goalieId'),goal.goalie);
      else if(opponents.length===1)setSelect(rowField(anchor,'goalieId'),`#${opponents[0].number} ${opponents[0].name}`);
      setInput(rowField(anchor,'time'),gameSheetTime(goal.time));setSelect(rowField(anchor,'period'),periodValue(goal.period));await pause(500);
    }
  }
}
async function fillPenalties(data){
  const start=heading('Penalties'),end=heading('Shootouts');if(!start||!end)throw new Error('Penalties section was not found.');
  const byTeam=splitTeams(data.penalties,data.game);
  for(let side=0;side<2;side++){
    for(let i=0;i<byTeam[side].length;i++){
      const p=byTeam[side][i];await addRow(start,end,data.game,side,'ADD PENALTY',i);
      let anchor=namedRows(start,end,side,'ADD PENALTY','servedById').find(el=>!el.value)||namedRows(start,end,side,'ADD PENALTY','servedById')[i];if(!anchor)throw new Error('The newly created penalty row could not be found.');
      let row=anchor.closest('.row')||anchor.parentElement?.parentElement;let selects=[...(row?.querySelectorAll('select')||[])];if(selects.length<5)throw new Error('A penalty row did not contain its five dropdowns.');
      setSelect(selects[1],p.offender);setSelect(anchor,p.served_by);await pause(300);anchor=reacquireSelected(start,end,side,'ADD PENALTY','servedById',p.served_by,'offTime');if(!anchor)throw new Error(`Could not reacquire the penalty row for ${p.served_by}.`);
      setSelect(rowField(anchor,'length'),p.length);await pause(300);
      anchor=reacquireSelected(start,end,side,'ADD PENALTY','servedById',p.served_by,'offTime');row=anchor.closest('.row')||anchor.parentElement?.parentElement;selects=[...(row?.querySelectorAll('select')||[])];
      setSelect(rowField(anchor,'code'),p.code);setInput(rowField(anchor,'offTime'),gameSheetTime(p.time_off));setInput(rowField(anchor,'startTime'),gameSheetTime(p.time_start));setInput(rowField(anchor,'onTime'),gameSheetTime(p.time_on||p.time_off));setSelect(selects[0],periodValue(p.period));await pause(500);
    }
  }
}
async function addGoalieShiftRow(start,end,side,index){
  if(teamRows(start,end,null,side,'ADD GOALIE SHIFT').length>index)return;
  let buttons=[];
  for(let attempt=0;attempt<20&&buttons.length<2;attempt++){({start,end}=liveSection(start,end));buttons=buttonsBetween(start,end,'ADD GOALIE SHIFT').sort((a,b)=>y(a)-y(b));if(buttons.length<2)await pause(150);}
  if(buttons.length<2)throw new Error('Could not find both ADD GOALIE SHIFT buttons.');
  buttons[side].click();
  for(let attempt=0;attempt<20;attempt++){await pause(150);if(teamRows(start,end,null,side,'ADD GOALIE SHIFT').length>index){await pause(500);return;}}
  throw new Error('GameSheet did not create the requested goalie-shift row.');
}
async function fillGoalieShifts(data){
  if(!data.goalie_shifts?.length)return;
  const start=heading('Goalie shifts'),end=heading('Shots');if(!start||!end)throw new Error('Goalie shifts section was not found.');
  const byTeam=splitTeams(data.goalie_shifts,data.game);
  for(let side=0;side<2;side++)for(let i=0;i<byTeam[side].length;i++){
    const shift=byTeam[side][i];await addGoalieShiftRow(start,end,side,i);
    let row=teamRows(start,end,null,side,'ADD GOALIE SHIFT')[i];let selects=row?.controls.filter(el=>el.tagName==='SELECT')||[];let inputs=row?.controls.filter(el=>el.tagName==='INPUT')||[];
    if(selects.length<2||!inputs.length)throw new Error(`The goalie-shift row for ${shift.team} is missing fields.`);
    setSelect(selects[1],shift.goalie);await pause(300);
    row=teamRows(start,end,null,side,'ADD GOALIE SHIFT').find(candidate=>candidate.controls.some(el=>el.tagName==='SELECT'&&selectedMatches(el,shift.goalie)))||teamRows(start,end,null,side,'ADD GOALIE SHIFT')[i];
    selects=row.controls.filter(el=>el.tagName==='SELECT');inputs=row.controls.filter(el=>el.tagName==='INPUT');
    setInput(inputs[0],gameSheetTime(shift.time));setSelect(selects[0],periodValue(shift.period));await pause(500);
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
  const teamOnPage=team=>{
    const full=norm(team);if(body.includes(full))return true;
    const meaningful=full.split(' ').filter(word=>word.length>=5);
    return meaningful.some(word=>new RegExp(`\\b${word}\\b`).test(body));
  };
  if(!teamOnPage(data.game.away_team)||!teamOnPage(data.game.home_team))throw new Error('The teams on this GameSheet page do not match the copied game.');
  return `Page matched. Ready for ${data.goals.length} goals and ${data.penalties.length} penalties.`;
}
function analyzeForm(){
  const scoring=heading('Scoring'),penalties=heading('Penalties'),shootouts=heading('Shootouts');if(!scoring||!penalties||!shootouts)throw new Error('Scoring or Penalties section was not found.');
  const report=(start,end,buttonLabel)=>{
    const addButtons=buttonsBetween(start,end,buttonLabel).sort((a,b)=>y(a)-y(b));if(!addButtons.length)return [];
    const low=y(start),high=y(addButtons[0]);
    return all('body *').filter(el=>{const rect=el.getBoundingClientRect();return y(el)>low&&y(el)<high&&rect.width>0&&rect.width<600&&rect.height>0&&rect.height<120;}).slice(0,160).map(el=>({tag:el.tagName.toLowerCase(),type:el.getAttribute('type'),role:el.getAttribute('role'),name:el.getAttribute('name'),class:String(el.className||'').slice(0,160),text:norm(el.textContent).slice(0,80),width:Math.round(el.getBoundingClientRect().width),height:Math.round(el.getBoundingClientRect().height)}));
  };
  return {scoring:report(scoring,penalties,'ADD GOAL'),penalties:report(penalties,shootouts,'ADD PENALTY')};
}
chrome.runtime.onMessage.addListener((request,_sender,respond)=>{
  (async()=>{try{
    const message=inspect(request.data);
    if(request.action==='analyze'){respond({ok:true,message:'Form report copied.',diagnostic:analyzeForm()});return;}
    if(request.action!=='fill'){respond({ok:true,message});return;}
    try{await fillGoals(request.data);}catch(e){throw new Error(`Goals: ${e.message}`);}
    try{await fillPenalties(request.data);}catch(e){throw new Error(`Penalties: ${e.message}`);}
    try{await fillGoalieShifts(request.data);}catch(e){throw new Error(`Goalie shifts: ${e.message}`);}
    try{fillShots(request.data);}catch(e){throw new Error(`Shots: ${e.message}`);}
    const scoring=heading('Scoring');if(scoring)scoring.scrollIntoView({behavior:'smooth',block:'start'});
    respond({ok:true,message:'Form filled. Review goals, penalties, shots, goalie shifts, and lineups. Save Changes was not clicked.'});
  }catch(e){respond({ok:false,error:e.message});}})();return true;
});
