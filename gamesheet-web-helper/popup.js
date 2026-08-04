const input=document.getElementById('payload'),summary=document.getElementById('summary'),error=document.getElementById('error');
document.getElementById('helperVersion').textContent=`v${chrome.runtime.getManifest().version}`;
function parse(){
  error.textContent='';
  const data=JSON.parse(input.value.trim());
  if(data.format!=='gamesheet-assistant-web-fill'||data.version!==1)throw new Error('This is not supported GameSheet Assistant web-fill data.');
  return data;
}
async function send(action){
  try{
    const data=parse();
    summary.innerHTML=`<p><b>${data.game.away_team} ${data.game.away_score} – ${data.game.home_score} ${data.game.home_team}</b><br>${data.goals.length} goals · ${data.penalties.length} penalties</p>${data.warnings.length?`<ul>${data.warnings.map(w=>`<li>${w}</li>`).join('')}</ul>`:''}`;
    const [tab]=await chrome.tabs.query({active:true,currentWindow:true});
    let response;
    try{response=await chrome.tabs.sendMessage(tab.id,{action,data});}
    catch(messageError){
      if(!String(messageError.message||messageError).includes('Receiving end does not exist'))throw messageError;
      await chrome.scripting.executeScript({target:{tabId:tab.id},files:['content.js']});
      response=await chrome.tabs.sendMessage(tab.id,{action,data});
    }
    if(!response?.ok)throw new Error(response?.error||'The GameSheet page did not respond.');
    if(action==='analyze'&&response.diagnostic){await navigator.clipboard.writeText(JSON.stringify(response.diagnostic,null,2));summary.insertAdjacentHTML('beforeend','<p><b>Form report copied.</b> Paste it into the ChatGPT conversation.</p>');return;}
    summary.insertAdjacentHTML('beforeend',`<p>${response.message}</p>`);
  }catch(e){error.textContent=e.message;}
}
document.getElementById('inspect').onclick=()=>send('inspect');
document.getElementById('analyze').onclick=()=>send('analyze');
document.getElementById('fill').onclick=()=>{if(confirm('Fill the open GameSheet form? You must review it and click Save Changes yourself.'))send('fill');};
navigator.clipboard.readText().then(text=>{if(text.includes('gamesheet-assistant-web-fill'))input.value=text;}).catch(()=>{});
