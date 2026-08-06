const STORAGE_KEY = 'gsa-web-state-v3';
const PREF_KEY = 'gsa-web-preferences-v1';
const state = { data:null, workflowIndex:0, batch:[], batchIndex:-1, completed:new Set(), skipped:new Set(), standaloneCompleted:0, lastFinish:null };
const prefs = { autoCopy:false, compact:false, theme:'light' };
const $ = (id) => document.getElementById(id);
const escapeHtml = (value='') => String(value).replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));

function saveState() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify({
    data:state.data, workflowIndex:state.workflowIndex, batch:state.batch,
    batchIndex:state.batchIndex, completed:[...state.completed], skipped:[...state.skipped], standaloneCompleted:state.standaloneCompleted, lastFinish:state.lastFinish,
  }));
}
function savePrefs() { localStorage.setItem(PREF_KEY, JSON.stringify(prefs)); }
function restorePrefs() {
  try { Object.assign(prefs, JSON.parse(localStorage.getItem(PREF_KEY) || '{}')); } catch {}
  $('autoCopyToggle').checked=!!prefs.autoCopy;
  $('compactModeToggle').checked=!!prefs.compact;
  document.documentElement.dataset.theme=prefs.theme==='dark'?'dark':'light';
  document.body.classList.toggle('compact-workflow',!!prefs.compact);
}
function restoreState() {
  try {
    const saved=JSON.parse(localStorage.getItem(STORAGE_KEY)||'null'); if(!saved)return;
    state.data=saved.data||null; state.workflowIndex=Number(saved.workflowIndex||0);
    state.batch=Array.isArray(saved.batch)?saved.batch:[];
    state.batchIndex=Number.isInteger(saved.batchIndex)?saved.batchIndex:-1;
    state.completed=new Set(saved.completed||[]); state.skipped=new Set(saved.skipped||[]); state.standaloneCompleted=Number(saved.standaloneCompleted||0); state.lastFinish=saved.lastFinish||null;
    $('batchInput').value=state.batch.join('\n');
    if(state.data){$('emptyState').classList.add('hidden');$('gameWorkspace').classList.remove('hidden');renderAll();}
    updateBatchStatus(); updateSessionMetrics();
  } catch { localStorage.removeItem(STORAGE_KEY); }
}
function hideToast(){const toast=$('toast');toast.classList.add('hidden');clearTimeout(showToast.timer);}
function showToast(message,{actionLabel='',onAction=null,duration=1500}={}){
  const toast=$('toast');
  $('toastMessage').textContent=message;
  const action=$('toastAction');
  action.textContent=actionLabel;
  action.classList.toggle('hidden',!actionLabel||!onAction);
  action.onclick=onAction?async()=>{await onAction();hideToast();}:null;
  toast.classList.remove('hidden');
  clearTimeout(showToast.timer);
  showToast.timer=setTimeout(hideToast,duration);
}
async function copyCurrentStep(){if(!state.data)return;const s=state.data.workflow[state.workflowIndex];await navigator.clipboard.writeText(`${s.title}\n\n${s.body}`);showToast('Step copied to clipboard');}

function numericPeriodShots(values, count){
  return (values||[]).slice(0,count).map(value=>Number.isFinite(Number(value))?Number(value):null);
}
function playedGoaliesFor(team){
  return (state.data.goalies||[]).filter(g=>g.team===team&&g.minutes!=='0:00');
}
function clockSeconds(value){const [m,s]=String(value||'').split(':').map(Number);return Number.isFinite(m)&&Number.isFinite(s)?m*60+s:null;}
function clockText(seconds){const safe=Math.max(0,seconds);return `${Math.floor(safe/60)}:${String(safe%60).padStart(2,'0')}`;}
function periodKey(value){const text=String(value||'').toUpperCase();if(text.startsWith('OT')){const match=text.match(/\d+/);return 3+Number(match?.[0]||1);}const match=text.match(/\d+/);return match?Number(match[0]):null;}
function emptyNetPullTime(value){const seconds=clockSeconds(value);return seconds===null?'':clockText(Math.ceil(seconds/60)*60);}
function permutations(items){
  if(items.length<2)return [items.slice()];
  return items.flatMap((item,index)=>permutations(items.filter((_,i)=>i!==index)).map(rest=>[item,...rest]));
}
function goalieShotsFaced(goalie){
  const saves=Number(goalie.saves),ga=Number(goalie.goals_against);
  if(Number.isFinite(saves)&&Number.isFinite(ga))return saves+ga;
  const shots=Number(goalie.shots_against);return Number.isFinite(shots)?shots:null;
}
function inferGoaliePlan(team,game,shots,goals,goalies,periods){
  const played=goalies.filter(g=>g.team===team&&clockSeconds(g.minutes)>0);
  if(played.length<2||played.length>periods.length)return null;
  const opponentShots=numericPeriodShots(team===game.away_team?shots.home:shots.away,periods.length);
  if(opponentShots.some(value=>value===null))return null;
  const lengths=periods.map(period=>String(period).toUpperCase().startsWith('OT')?8*60:17*60);
  const valid=[];
  for(const ordering of permutations(played)){
    let cursor=0;const stints=[];let fits=true;
    for(const goalie of ordering){
      const duration=clockSeconds(goalie.minutes);let covered=0,start=cursor;
      while(cursor<periods.length&&covered<duration){covered+=lengths[cursor];cursor++;}
      const expectedShots=opponentShots.slice(start,cursor).reduce((sum,value)=>sum+value,0);
      if(covered!==duration||goalieShotsFaced(goalie)!==expectedShots){fits=false;break;}
      stints.push({goalie,start,end:cursor});
    }
    if(fits&&cursor===periods.length)valid.push(stints);
  }
  if(valid.length===1)return {team,stints:valid[0],basis:'unique minutes and shots match'};
  const listed=valid.find(stints=>stints.every((stint,i)=>stint.goalie===played[i]));
  if(listed)return {team,stints:listed,basis:'validated SportsEngine goalie order'};

  if(played.length===2){
    const ordered=played.slice().sort((a,b)=>clockSeconds(b.minutes)-clockSeconds(a.minutes));
    const durations=ordered.map(goalie=>clockSeconds(goalie.minutes));
    const totalLength=lengths.reduce((sum,value)=>sum+value,0);
    if(durations[0]!==durations[1]&&durations[0]+durations[1]===totalLength){
      let changePeriod=0,elapsedInPeriod=durations[0];
      while(changePeriod<lengths.length&&elapsedInPeriod>=lengths[changePeriod]){elapsedInPeriod-=lengths[changePeriod];changePeriod++;}
      if(changePeriod<lengths.length&&elapsedInPeriod>0){
        const changeRemaining=lengths[changePeriod]-elapsedInPeriod;
        const starterShots=opponentShots.slice(0,changePeriod+1).reduce((sum,value)=>sum+value,0);
        const replacementShots=opponentShots.slice(changePeriod+1).reduce((sum,value)=>sum+value,0);
        if(goalieShotsFaced(ordered[0])===starterShots&&goalieShotsFaced(ordered[1])===replacementShots){
          return {team,basis:'partial-period minutes and shots identify the starter and exact change clock',stints:[
            {goalie:ordered[0],start:0,end:changePeriod+1,start_time:clockText(lengths[0]),end_time:clockText(changeRemaining),change_period:changePeriod,partial_end:true},
            {goalie:ordered[1],start:changePeriod,end:periods.length,start_time:clockText(changeRemaining),end_time:'0:00',change_period:changePeriod,partial_start:true}
          ]};
        }
      }
    }
  }
  return null;
}
function penaltyRelease(penalty,goals,length,periods=[]){
  if(/penalty shot/i.test(penalty.penalty))return {time:penalty.remaining,period:penalty.period,crosses_period:false};
  const off=clockSeconds(penalty.remaining);if(off===null)return {time:'',period:penalty.period,crosses_period:false};
  const duration=(Number(length)||2)*60;
  const startIndex=periods.findIndex(period=>periodKey(period)===periodKey(penalty.period));
  let releaseSeconds=off-duration;
  let releasePeriod=penalty.period;
  let crossesPeriod=false;
  if(releaseSeconds<0&&startIndex>=0){
    let remaining=-releaseSeconds;
    for(let index=startIndex+1;index<periods.length;index++){
      const periodLength=String(periods[index]).toUpperCase().startsWith('OT')?8*60:17*60;
      crossesPeriod=true;
      releasePeriod=periods[index];
      if(remaining<=periodLength){releaseSeconds=periodLength-remaining;break;}
      remaining-=periodLength;
      releaseSeconds=0;
    }
  }
  releaseSeconds=Math.max(0,releaseSeconds);
  const mustServeFull=/\b(?:major|misconduct)\b/i.test(penalty.penalty)||duration>2*60;
  const earlyGoal=!mustServeFull&&!crossesPeriod?goals.find(goal=>periodKey(goal.period)===periodKey(penalty.period)&&goal.team!==penalty.team&&/power play/i.test(goal.strength||'')&&clockSeconds(goal.remaining)<off&&clockSeconds(goal.remaining)>releaseSeconds):null;
  return {time:earlyGoal?earlyGoal.remaining:clockText(releaseSeconds),period:earlyGoal?penalty.period:releasePeriod,crosses_period:crossesPeriod};
}
const UNSPECIFIED_MINOR_TYPES=['Interference - Minor','Hooking - Minor','Tripping - Minor','Body Checking - Minor','Slashing - Minor','Holding - Minor'];
function isUnspecifiedMinorPenalty(value){return /^minor(?:\s*\([^)]*\))?\s*$/i.test(String(value||'').trim());}
function unspecifiedMinorFallback(penalty){
  const key=[penalty.team,penalty.period,penalty.remaining,penalty.player].join('|');
  let hash=0;for(const character of key)hash=(hash*31+character.charCodeAt(0))>>>0;
  return UNSPECIFIED_MINOR_TYPES[hash%UNSPECIFIED_MINOR_TYPES.length];
}
function penaltyLength(value){
  const text=String(value||'');
  if(/\bmisconduct\b/i.test(text))return '10';
  if(/\bmajor\b/i.test(text))return '5';
  const minutes=(text.match(/\b(\d+)\s*(?:min|minute)/i)||[])[1];
  if(minutes)return minutes;
  const clock=(text.match(/\((\d+):\d{1,2}\)/)||[])[1];
  return clock&&Number(clock)>0?clock:'2';
}
function penaltyClassCode(value,kind){
  const text=String(value||'').trim();
  const type=(text.split(/\s+-\s+/,1)[0]||text).replace(/\s+(?:major|misconduct)\b.*$/i,'').trim();
  return `${type||'Body Checking'} - ${kind}`;
}
function expandPenaltiesForWebFill(items){
  const expanded=[];
  for(const penalty of items){
    const text=String(penalty.penalty||'');
    if(/\bmajor\b/i.test(text)&&/\bmisconduct\b/i.test(text)){
      expanded.push({...penalty,penalty:penaltyClassCode(text,'Major'),paired_major_misconduct:true});
      expanded.push({...penalty,penalty:penaltyClassCode(text,'Misconduct'),paired_major_misconduct:true});
    }else expanded.push({...penalty});
  }
  const groups=new Map();
  for(const penalty of expanded){
    const key=[penalty.team,periodKey(penalty.period),penalty.remaining,penalty.player].join('|');
    if(!groups.has(key))groups.set(key,[]);groups.get(key).push(penalty);
  }
  for(const group of groups.values()){
    const major=group.find(item=>/\bmajor\b/i.test(item.penalty));
    const misconduct=group.find(item=>/\bmisconduct\b/i.test(item.penalty));
    if(major&&misconduct){
      for(const item of group)item.paired_major_misconduct=true;
      if(/^\s*misconduct\b/i.test(misconduct.penalty))misconduct.penalty=penaltyClassCode(major.penalty,'Misconduct');
    }
  }
  return expanded;
}
function buildWebFillPayload(){
  const {game,shots,goals,penalties,goalies,source_url}=state.data;
  const periodCount=(shots.periods||[]).length;
  const awayPlayed=playedGoaliesFor(game.away_team);
  const homePlayed=playedGoaliesFor(game.home_team);
  const plans=[inferGoaliePlan(game.away_team,game,shots,goals,goalies,shots.periods||[]),inferGoaliePlan(game.home_team,game,shots,goals,goalies,shots.periods||[])].filter(Boolean);
  const goalieShotRows=[];
  if(awayPlayed.length===1)goalieShotRows.push({team:game.away_team,goalie:`#${awayPlayed[0].number} ${awayPlayed[0].name}`,periods:numericPeriodShots(shots.home,periodCount)});
  if(homePlayed.length===1)goalieShotRows.push({team:game.home_team,goalie:`#${homePlayed[0].number} ${homePlayed[0].name}`,periods:numericPeriodShots(shots.away,periodCount)});
  for(const plan of plans){
    const opponentShots=numericPeriodShots(plan.team===game.away_team?shots.home:shots.away,periodCount);
    for(const stint of plan.stints)goalieShotRows.push({team:plan.team,goalie:`#${stint.goalie.number} ${stint.goalie.name}`,periods:opponentShots.map((value,i)=>{
      if(stint.partial_start)return i>stint.start&&i<stint.end?value:0;
      return i>=stint.start&&i<stint.end?value:0;
    })});
  }
  const goalieShifts=plans.flatMap(plan=>plan.stints.map(stint=>({team:plan.team,period:shots.periods[stint.start],time:stint.start_time||(String(shots.periods[stint.start]).toUpperCase().startsWith('OT')?'8:00':'17:00'),goalie:`#${stint.goalie.number} ${stint.goalie.name}`,basis:plan.basis})));
  for(const [team,played] of [[game.away_team,awayPlayed],[game.home_team,homePlayed]]){
    if(played.length===1&&!plans.some(plan=>plan.team===team))goalieShifts.push({team,period:shots.periods[0]||'1',time:'17:00',goalie:`#${played[0].number} ${played[0].name}`,basis:'only goalie who played'});
  }
  for(const goal of goals.filter(item=>/empty\s+net/i.test(item.strength||''))){
    const defending=goal.team===game.away_team?game.home_team:game.away_team;
    const periodIndex=(shots.periods||[]).findIndex(period=>periodKey(period)===periodKey(goal.period));
    const plan=plans.find(item=>item.team===defending);
    const goalClock=clockSeconds(goal.remaining);
    const stint=plan?.stints.find(item=>periodIndex>=item.start&&periodIndex<item.end&&(!item.partial_end||periodIndex!==item.change_period||goalClock>clockSeconds(item.end_time))&&(!item.partial_start||periodIndex!==item.change_period||goalClock<=clockSeconds(item.start_time)));
    const played=defending===game.away_team?awayPlayed:homePlayed;
    const goalie=stint?.goalie||(played.length===1?played[0]:null);
    if(!goalie)continue;
    goalieShifts.push(
      {team:defending,period:goal.period,time:emptyNetPullTime(goal.remaining),goalie:'Empty net',basis:'empty-net goal'},
      {team:defending,period:goal.period,time:goal.remaining,goalie:`#${goalie.number} ${goalie.name}`,basis:'goalie returns at empty-net goal time'}
    );
  }
  goalieShifts.sort((a,b)=>{
    if(a.team!==b.team)return a.team===game.away_team?-1:1;
    const periodDifference=(periodKey(a.period)||0)-(periodKey(b.period)||0);
    if(periodDifference)return periodDifference;
    return (clockSeconds(b.time)||0)-(clockSeconds(a.time)||0);
  });
  const startingGoalies=[game.away_team,game.home_team].flatMap(team=>{
    const plan=plans.find(item=>item.team===team);
    if(plan?.stints?.[0]){
      const goalie=plan.stints[0].goalie;
      return [{team,goalie:`#${goalie.number} ${goalie.name}`,basis:plan.basis}];
    }
    const workflowStep=(state.data.workflow||[]).find(step=>step.kind==='goalie-start'&&step.team===team&&/inferred starter/i.test(`${step.title} ${step.body}`));
    const match=workflowStep?.body?.match(/#([^\n]+)/);
    if(match)return [{team,goalie:`#${match[1].trim()}`,basis:'GameSheet Assistant workflow inference'}];
    const played=playedGoaliesFor(team);
    return played.length===1?[{team,goalie:`#${played[0].number} ${played[0].name}`,basis:'only goalie who played'}]:[];
  });
  const warnings=[];
  for(const goal of goals.filter(item=>item.scorer_inferred))warnings.push(`${goal.team} ${goal.period} ${goal.remaining}: SportsEngine did not provide a valid goal scorer; ${goal.scorer} was assigned as a placeholder. Review if another source becomes available.`);
  if(awayPlayed.length!==1&&!plans.some(plan=>plan.team===game.away_team))warnings.push(`${game.away_team}: ${awayPlayed.length} goalies played; goalie order is ambiguous and must be reviewed manually.`);
  if(homePlayed.length!==1&&!plans.some(plan=>plan.team===game.home_team))warnings.push(`${game.home_team}: ${homePlayed.length} goalies played; goalie order is ambiguous and must be reviewed manually.`);
  for(const plan of plans)warnings.push(`${plan.team}: inferred ${plan.stints.map(stint=>`#${stint.goalie.number} ${stint.goalie.name} starts ${shots.periods[stint.start]}`).join('; ')} (${plan.basis}). Review before saving.`);
  const hasOvertime=(shots.periods||[]).some(period=>String(period).toUpperCase().startsWith('OT'));
  const isOvertimeTie=hasOvertime&&Number(game.away_score)===Number(game.home_score);
  if(isOvertimeTie)warnings.push('This game ended in a scoreless overtime tie. GameSheet Assistant corrected full-game goalie totals to 59:00, but GameSheet’s web editor still calculates goalie shifts through 0:00 of the 3rd period. Do not add a duplicate OT goalie shift; GameSheet may continue to display 51:00.');
  for(const penalty of penalties.filter(item=>isUnspecifiedMinorPenalty(item.penalty))){
    warnings.push(`${penalty.team} ${penalty.period} ${penalty.remaining}: SportsEngine lists only “Minor”; ${unspecifiedMinorFallback(penalty).replace(/\s*-\s*Minor$/i,'')} was selected as a placeholder. Review before saving.`);
  }
  if((shots.periods||[]).some((_,i)=>numericPeriodShots(shots.away,periodCount)[i]===null||numericPeriodShots(shots.home,periodCount)[i]===null))warnings.push('At least one period shot total is missing; review shots manually.');
  const webPenalties=expandPenaltiesForWebFill(penalties);
  for(const penalty of webPenalties.filter(item=>item.paired_major_misconduct&&/\bmajor\b/i.test(item.penalty))){
    warnings.push(`${penalty.team} ${penalty.period} ${penalty.remaining}: paired major/misconduct exported as separate 5- and 10-minute penalties; the helper will select a teammate to serve the major.`);
  }
  const webPenaltyRows=webPenalties.map(p=>{
    const length=penaltyLength(p.penalty);
    const release=penaltyRelease(p,goals,length,shots.periods||[]);
    const isPairedMajor=p.paired_major_misconduct&&/\bmajor\b/i.test(p.penalty);
    return {team:p.team,period:p.period,offender:p.player,served_by:p.player,served_by_strategy:isPairedMajor?'deterministic_teammate':'offender',length,code:isUnspecifiedMinorPenalty(p.penalty)?unspecifiedMinorFallback(p):p.penalty,time_off:p.remaining,time_start:p.remaining,time_on:release.time,time_on_period:release.period,crosses_period:release.crosses_period,type_inferred:isUnspecifiedMinorPenalty(p.penalty)};
  });
  for(const penalty of webPenaltyRows.filter(item=>item.crosses_period)){
    warnings.push(`${penalty.team} ${penalty.period} ${penalty.time_off}: ${penalty.length}-minute penalty releases at ${penalty.time_on} of ${penalty.time_on_period}. GameSheet uses one penalty row for the rollover; verify the saved result.`);
  }
  return {
    format:'gamesheet-assistant-web-fill',version:1,source_url,
    game:{away_team:game.away_team,home_team:game.home_team,away_score:Number(game.away_score),home_score:Number(game.home_score),date:game.date},
    periods:shots.periods,
    goals:goals.map(g=>{const defending=g.team===game.away_team?game.home_team:game.away_team;const plan=plans.find(item=>item.team===defending);const periodIndex=(shots.periods||[]).findIndex(period=>periodKey(period)===periodKey(g.period));const goalClock=clockSeconds(g.remaining);const stint=plan?.stints.find(item=>periodIndex>=item.start&&periodIndex<item.end&&(!item.partial_end||periodIndex!==item.change_period||goalClock>clockSeconds(item.end_time))&&(!item.partial_start||periodIndex!==item.change_period||goalClock<=clockSeconds(item.start_time)));return {team:g.team,period:g.period,time:g.remaining,player:g.scorer,assists:g.assists||[],strength:g.strength,goalie:stint?`#${stint.goalie.number} ${stint.goalie.name}`:''};}),
    penalties:webPenaltyRows,
    goalie_shots:goalieShotRows,
    goalie_shifts:goalieShifts,
    starting_goalies:startingGoalies,
    goalies:goalies.map(g=>({team:g.team,number:g.number,name:g.name,minutes:g.minutes,shots_against:g.shots_against,goals_against:g.goals_against,saves:g.saves})),
    warnings
  };
}
async function copyWebFillData(){
  if(!state.data)return;
  const payload=buildWebFillPayload();
  await navigator.clipboard.writeText(JSON.stringify(payload));
  showToast(payload.warnings.length?'Web data copied — review warnings in the Chrome helper':'Web fill data copied',{duration:3500});
}

async function importGame(rawValue,{fromBatch=false}={}){
  const value=rawValue.trim(); if(!value)return showError('Enter a SportsEngine URL or game ID.');
  setLoading(true);showError('');
  try{
    const response=await fetch('/api/import',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:value})});
    if(response.status===401){window.location.href='/login';return;}
    const payload=await response.json(); if(!response.ok||!payload.ok)throw new Error(payload.error||'Import failed');
    state.data=payload.data;state.workflowIndex=0;renderAll();
    $('emptyState').classList.add('hidden');$('gameWorkspace').classList.remove('hidden');selectTab('workflow');
    if(fromBatch)updateBatchStatus();saveState();showToast('Game imported');
  }catch(error){showError(error.message);}finally{setLoading(false);}
}
function renderAll(){
  const {game,shots,goals,penalties,goalies,validation}=state.data;
  $('awayTeam').textContent=game.away_team;$('awayScore').textContent=game.away_score;
  $('homeTeam').textContent=game.home_team;$('homeScore').textContent=game.home_score;
  $('gameDate').textContent=game.date;$('venue').textContent=game.venue;renderWorkflow();
  const shotComparison=(label,awayValue,homeValue)=>{
    const awayShots=Number(awayValue);const homeShots=Number(homeValue);
    let leader='Tie';let awayClass='';let homeClass='';
    if(awayShots>homeShots){leader=`${shots.away_team} (+${awayShots-homeShots})`;awayClass=' leader';}
    else if(homeShots>awayShots){leader=`${shots.home_team} (+${homeShots-awayShots})`;homeClass=' leader';}
    return `<section class="shot-period"><h4>${escapeHtml(label)}</h4><div class="shot-team${awayClass}"><span>${escapeHtml(shots.away_team)}</span><strong>${awayShots}</strong></div><div class="shot-team${homeClass}"><span>${escapeHtml(shots.home_team)}</span><strong>${homeShots}</strong></div><p class="shot-leader">${leader==='Tie'?'Tie':`Leader: ${escapeHtml(leader)}`}</p></section>`;
  };
  const shotRows=shots.periods.map((p,i)=>shotComparison(`${p} Period`,shots.away[i],shots.home[i])).join('');
  const shotTotal=shotComparison('Game Total',shots.away.at(-1),shots.home.at(-1));
  $('summary').innerHTML=`<div class="panel-head"><div><p class="eyebrow">GAME OVERVIEW</p><h2>Summary</h2></div></div><div class="data-grid summary-grid"><div class="data-card shots-card"><h3>Shots on Goal</h3><div class="shots-grid">${shotRows}${shotTotal}</div></div><div class="data-card"><h3>Parsed Events</h3><p>${goals.length} goals</p><p>${penalties.length} penalties</p><p>${goalies.length} goalie records</p></div></div>`;
  $('goals').innerHTML=panelCards('Goals',goals.map((g,i)=>({title:`Goal ${i+1}`,lines:[`${g.period} — ${g.remaining} remaining`,g.team,`Scorer: ${g.scorer}`,`Assists: ${g.assists.join(', ')||'None'}`,`<span class="strength">${escapeHtml(g.strength)}</span>`]})));
  $('penalties').innerHTML=panelCards('Penalties',penalties.map((p,i)=>({title:`Penalty ${i+1}`,lines:[`${p.period} — ${p.remaining} remaining`,p.team,`Player: ${p.player}`,p.penalty]})));
  $('goalies').innerHTML=panelCards('Goalies',goalies.map(g=>({title:`#${g.number} ${g.name}`,lines:[g.team,`${g.minutes} played`,`${g.shots_against} SA · ${g.goals_against} GA · ${g.saves} saves`,`Save %: ${g.save_percentage}`]})));
  $('validation').innerHTML=`<div class="panel-head"><div><p class="eyebrow">DATA QUALITY</p><h2>Validation</h2></div></div>${validation.map(c=>`<div class="check ${c.ok?'':'bad'}"><strong>${c.ok?'✓':'!'}</strong><div><b>${escapeHtml(c.label)}</b><br>${escapeHtml(c.detail)}</div></div>`).join('')}`;
}
function panelCards(title,cards){return `<div class="panel-head"><div><p class="eyebrow">PARSED DATA</p><h2>${title}</h2></div><span class="percent">${cards.length}</span></div><div class="data-grid">${cards.map(c=>`<article class="data-card"><h3>${escapeHtml(c.title)}</h3>${c.lines.map(line=>`<p>${line.startsWith('<span')?line:escapeHtml(line)}</p>`).join('')}</article>`).join('')}</div>`;}
function renderWorkflow(){
  const steps=state.data?.workflow||[];if(!steps.length)return;
  const i=Math.max(0,Math.min(state.workflowIndex,steps.length-1));state.workflowIndex=i;const step=steps[i];const pct=Math.round(((i+1)/steps.length)*100);
  $('workflowCounter').textContent=`STEP ${i+1} OF ${steps.length}`;$('workflowTitle').textContent=step.title;
  const team=step.team?`<strong class="workflow-team">${escapeHtml(step.team)}</strong>`:'';
  const warning=step.warning?' workflow-warning':'';
  $('workflowCard').className=`workflow-card kind-${escapeHtml(step.kind||'standard')}${warning}`;
  $('workflowBody').innerHTML=`${team}${team?'\n\n':''}${escapeHtml(step.body)}`;
  const isFinal=i===steps.length-1; const currentBatchDone=state.batchIndex>=0&&state.completed.has(state.batchIndex);
  $('workflowPercent').textContent=`${pct}%`;$('workflowProgress').style.width=`${pct}%`;$('previousStep').disabled=i===0;
  $('nextStep').classList.toggle('hidden',isFinal); $('finishGame').classList.toggle('hidden',!isFinal||currentBatchDone); saveState();
}
async function changeWorkflow(delta){
  if(!state.data)return;const next=Math.max(0,Math.min(state.workflowIndex+delta,state.data.workflow.length-1));
  if(next===state.workflowIndex)return;state.workflowIndex=next;renderWorkflow();if(delta>0&&prefs.autoCopy)await copyCurrentStep();
}

function resetForNextImport(message='Game completed. Ready for the next game.') {
  state.data=null; state.workflowIndex=0;
  $('gameWorkspace').classList.add('hidden'); $('emptyState').classList.remove('hidden');
  $('gameInput').value=''; $('gameInput').focus(); saveState(); updateSessionMetrics(); showToast(message);
}

async function undoLastFinish(){
  const action=state.lastFinish;
  if(!action)return;

  if(action.mode==='batch'){
    state.completed.delete(action.batchIndex);
    state.skipped.delete(action.batchIndex);
    state.batchIndex=action.batchIndex;
    state.data=action.data;
    state.workflowIndex=Math.max(0,(action.data?.workflow?.length||1)-1);
    $('emptyState').classList.add('hidden');
    $('gameWorkspace').classList.remove('hidden');
    renderAll();
    updateBatchStatus();
    selectTab('workflow');
  }else{
    state.standaloneCompleted=Math.max(0,state.standaloneCompleted-1);
    state.data=action.data;
    state.workflowIndex=Math.max(0,(action.data?.workflow?.length||1)-1);
    $('emptyState').classList.add('hidden');
    $('gameWorkspace').classList.remove('hidden');
    renderAll();
    selectTab('workflow');
  }

  state.lastFinish=null;
  saveState();
  updateSessionMetrics();
  showToast('Completion undone');
}

async function finishCurrentGame(){
  if(!state.data)return;
  const steps=state.data.workflow||[];
  if(!steps.length||state.workflowIndex!==steps.length-1)return;
  if(!confirm('Finish this game? You can undo immediately afterward.'))return;

  const finishedData=state.data;

  if(state.batch.length&&state.batchIndex>=0){
    const current=state.batchIndex;
    state.lastFinish={mode:'batch',batchIndex:current,data:finishedData};
    state.skipped.delete(current);
    state.completed.add(current);
    const next=current+1;
    updateBatchStatus(); saveState();
    if(next<state.batch.length){
      state.batchIndex=next; updateBatchStatus(); saveState();
      await importGame(state.batch[next],{fromBatch:true});
      selectTab('workflow');
      showToast('Game completed. Next game loaded.',{actionLabel:'Undo',onAction:undoLastFinish,duration:30000});
    }else{
      renderWorkflow();
      $('workflowCounter').textContent='BATCH COMPLETE';
      $('workflowTitle').textContent='All games completed';
      $('workflowBody').textContent=`${state.completed.size} game${state.completed.size===1?'':'s'} completed. You can start a new batch whenever you are ready.`;
      $('finishGame').classList.add('hidden'); $('nextStep').classList.add('hidden');
      showToast('Batch complete!',{actionLabel:'Undo',onAction:undoLastFinish,duration:30000});
    }
    return;
  }

  state.lastFinish={mode:'standalone',data:finishedData};
  state.standaloneCompleted+=1;
  resetForNextImport();
  showToast('Game completed. Ready for the next game.',{actionLabel:'Undo',onAction:undoLastFinish,duration:30000});
}

function selectTab(name){document.querySelectorAll('.tab').forEach(b=>b.classList.toggle('active',b.dataset.tab===name));document.querySelectorAll('.tab-panel').forEach(p=>p.classList.toggle('active',p.id===name));}
function showError(message){$('errorBox').textContent=message;$('errorBox').classList.toggle('hidden',!message);}
function setLoading(loading){$('importButton').disabled=loading;$('importButton').textContent=loading?'Importing…':'Import Game';$('connectionBadge').lastChild.textContent=loading?'Working…':'Ready';}

function loadBatch(){
  const values=$('batchInput').value.split(/\n/).map(v=>v.trim()).filter(Boolean);if(!values.length)return showError('Paste at least one batch URL or game ID.');
  state.batch=values;state.batchIndex=0;state.completed.clear();state.skipped.clear();updateBatchStatus();saveState();importGame(values[0],{fromBatch:true});
}
function moveGame(delta,{skip=false}={}){
  if(!state.batch.length)return;const current=state.batchIndex;const next=current+delta;if(next<0||next>=state.batch.length)return;
  if(delta>0){if(skip)state.skipped.add(current);else state.completed.add(current);}state.batchIndex=next;updateBatchStatus();saveState();importGame(state.batch[next],{fromBatch:true});
}
function clearBatch(){if(!confirm('Clear the current batch and its progress?'))return;state.batch=[];state.batchIndex=-1;state.completed.clear();state.skipped.clear();$('batchInput').value='';updateBatchStatus();saveState();showToast('Batch cleared');}
function updateSessionMetrics(){
  $('sessionCompleted').textContent=state.completed.size+state.standaloneCompleted;
  $('sessionRemaining').textContent=Math.max(0,state.batch.length-state.completed.size-state.skipped.size);
}
function updateBatchStatus(){
  const total=state.batch.length,completed=state.completed.size,skipped=state.skipped.size,remaining=Math.max(0,total-completed-skipped-(state.batchIndex>=0?1:0));
  $('batchStatus').textContent=total?`Game ${state.batchIndex+1} of ${total}`:'0 games';
  $('batchCompletedCount').textContent=completed;$('batchCurrentCount').textContent=total&&state.batchIndex>=0?1:0;$('batchRemainingCount').textContent=remaining;$('batchSkippedCount').textContent=skipped;
  $('batchLog').innerHTML=state.batch.map((v,i)=>`<div class="batch-item ${i===state.batchIndex?'current':''}">${state.completed.has(i)?'✓':state.skipped.has(i)?'↷':i===state.batchIndex?'▶':'○'} ${i+1}. ${escapeHtml(v)}</div>`).join('');
  $('previousGame').disabled=state.batchIndex<=0;$('nextGame').disabled=!total||state.batchIndex>=total-1;$('skipGame').disabled=!total||state.batchIndex>=total-1;updateSessionMetrics();
}

$('importButton').addEventListener('click',()=>importGame($('gameInput').value));
$('gameInput').addEventListener('keydown',e=>{if(e.key==='Enter')importGame(e.target.value)});
document.querySelectorAll('.tab').forEach(b=>b.addEventListener('click',()=>selectTab(b.dataset.tab)));
$('previousStep').addEventListener('click',()=>changeWorkflow(-1));$('nextStep').addEventListener('click',()=>changeWorkflow(1));$('copyStep').addEventListener('click',copyCurrentStep);$('copyWebFill').addEventListener('click',copyWebFillData);$('finishGame').addEventListener('click',finishCurrentGame);
$('loadBatch').addEventListener('click',loadBatch);$('previousGame').addEventListener('click',()=>moveGame(-1));$('skipGame').addEventListener('click',()=>moveGame(1,{skip:true}));$('nextGame').addEventListener('click',()=>moveGame(1));$('clearBatch').addEventListener('click',clearBatch);
$('autoCopyToggle').addEventListener('change',e=>{prefs.autoCopy=e.target.checked;savePrefs();showToast(prefs.autoCopy?'Auto-copy enabled':'Auto-copy disabled');});
$('compactModeToggle').addEventListener('change',e=>{prefs.compact=e.target.checked;document.body.classList.toggle('compact-workflow',prefs.compact);savePrefs();});
$('themeToggle').addEventListener('click',()=>{prefs.theme=prefs.theme==='dark'?'light':'dark';document.documentElement.dataset.theme=prefs.theme;savePrefs();});
document.addEventListener('keydown',e=>{if(!state.data||['INPUT','TEXTAREA'].includes(document.activeElement.tagName))return;if(e.key==='ArrowLeft')changeWorkflow(-1);if(e.key==='ArrowRight')changeWorkflow(1);});
restorePrefs();restoreState();
