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
$('previousStep').addEventListener('click',()=>changeWorkflow(-1));$('nextStep').addEventListener('click',()=>changeWorkflow(1));$('copyStep').addEventListener('click',copyCurrentStep);$('finishGame').addEventListener('click',finishCurrentGame);
$('loadBatch').addEventListener('click',loadBatch);$('previousGame').addEventListener('click',()=>moveGame(-1));$('skipGame').addEventListener('click',()=>moveGame(1,{skip:true}));$('nextGame').addEventListener('click',()=>moveGame(1));$('clearBatch').addEventListener('click',clearBatch);
$('autoCopyToggle').addEventListener('change',e=>{prefs.autoCopy=e.target.checked;savePrefs();showToast(prefs.autoCopy?'Auto-copy enabled':'Auto-copy disabled');});
$('compactModeToggle').addEventListener('change',e=>{prefs.compact=e.target.checked;document.body.classList.toggle('compact-workflow',prefs.compact);savePrefs();});
$('themeToggle').addEventListener('click',()=>{prefs.theme=prefs.theme==='dark'?'light':'dark';document.documentElement.dataset.theme=prefs.theme;savePrefs();});
document.addEventListener('keydown',e=>{if(!state.data||['INPUT','TEXTAREA'].includes(document.activeElement.tagName))return;if(e.key==='ArrowLeft')changeWorkflow(-1);if(e.key==='ArrowRight')changeWorkflow(1);});
restorePrefs();restoreState();
