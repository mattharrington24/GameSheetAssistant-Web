const $ = (id) => document.getElementById(id);
const escapeHtml = (value='') => String(value).replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
let result = null;
let transferResult = null;

function showError(message) {
  $('rosterError').textContent = message;
  $('rosterError').classList.toggle('hidden', !message);
}

function detail(player) {
  return [
    player.number ? `#${player.number}` : '',
    player.position,
    player.grade ? `Grade ${player.grade}` : '',
  ].filter(Boolean).join(' · ');
}

function playerRow(player, previous=null) {
  const currentDetail = detail(player);
  const oldDetail = previous ? detail(previous) : '';
  let meta = currentDetail;
  if (previous && oldDetail && oldDetail !== currentDetail) meta = `${oldDetail} → ${currentDetail || 'No details'}`;
  return `<article class="player-row"><strong>${escapeHtml(player.name)}</strong>${meta ? `<span>${escapeHtml(meta)}</span>` : ''}</article>`;
}

function renderPlayers(id, players, returning=false) {
  $(id).innerHTML = players.length
    ? players.map(item => returning ? playerRow(item.current, item.previous) : playerRow(item)).join('')
    : '<p class="empty-list">None</p>';
}

async function compare() {
  const previousUrl = $('previousRoster').value.trim();
  const currentUrl = $('currentRoster').value.trim();
  if (!previousUrl || !currentUrl) return showError('Enter both SportsEngine roster URLs.');
  const button = $('compareRosters');
  button.disabled = true;
  button.textContent = 'Comparing…';
  showError('');
  try {
    const response = await fetch('/api/rosters/compare', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({previous_url:previousUrl, current_url:currentUrl}),
    });
    if (response.status === 401) { window.location.href='/login'; return; }
    const payload = await response.json();
    if (!response.ok || !payload.ok) throw new Error(payload.error || 'Comparison failed.');
    result = payload.data;
    $('comparisonTitle').textContent = `${result.previous.title} → ${result.current.title}`;
    $('returningCount').textContent = result.counts.returning;
    $('newCount').textContent = result.counts.new;
    $('departedCount').textContent = result.counts.departed;
    renderPlayers('returningPlayers', result.returning, true);
    renderPlayers('newPlayers', result.new);
    renderPlayers('departedPlayers', result.departed);
    $('rosterResults').classList.remove('hidden');
    $('rosterResults').scrollIntoView({behavior:'smooth', block:'start'});
  } catch (error) {
    showError(error.message);
    $('rosterResults').classList.add('hidden');
  } finally {
    button.disabled = false;
    button.textContent = 'Compare Rosters';
  }
}

function copyGroup(group) {
  if (!result) return;
  let names;
  if (group === 'returning') names = result.returning.map(item => item.current.name);
  else names = result[group].map(player => player.name);
  navigator.clipboard.writeText(names.join('\n'));
  $('toastMessage').textContent = `${names.length} names copied`;
  $('toast').classList.remove('hidden');
  clearTimeout(copyGroup.timer);
  copyGroup.timer = setTimeout(() => $('toast').classList.add('hidden'), 1500);
}

$('compareRosters').addEventListener('click', compare);
document.querySelectorAll('[data-copy]').forEach(button => button.addEventListener('click', () => copyGroup(button.dataset.copy)));
[$('previousRoster'), $('currentRoster')].forEach(input => input.addEventListener('keydown', event => {
  if (event.key === 'Enter') compare();
}));

document.querySelectorAll('.mode-tab').forEach(button => button.addEventListener('click', () => {
  document.querySelectorAll('.mode-tab').forEach(item => item.classList.toggle('active', item === button));
  document.querySelectorAll('.mode-panel').forEach(panel => panel.classList.toggle('active', panel.id === button.dataset.mode));
}));

function showTransferError(message) {
  $('transferError').textContent = message;
  $('transferError').classList.toggle('hidden', !message);
}

async function jsonResponse(response) {
  const text = await response.text();
  try {
    return JSON.parse(text);
  } catch {
    if (response.status >= 500) {
      throw new Error('The server restarted during the scan. Please wait a moment and try again.');
    }
    throw new Error('The server returned an unexpected response. Please refresh and try again.');
  }
}

function transferRow(item) {
  const confidence = item.confidence === 'Likely' ? '' : ' · Review name duplicates';
  return `<article class="player-row transfer-row"><strong>${escapeHtml(item.name)}</strong><span>${escapeHtml(item.previous_team)} → ${escapeHtml(item.current_team)}${confidence}</span></article>`;
}

function renderTransfers(data) {
  transferResult = data;
  $('transferCount').textContent = data.counts.likely_transfers;
  $('reviewCount').textContent = data.counts.needs_review;
  $('teamCount').textContent = data.counts.previous_teams + data.counts.current_teams;
  $('avaCheck').textContent = data.ava_lindsay_found
    ? '✓ Test confirmed: Ava Lindsay — Breck → Minnetonka'
    : '⚠ Ava Lindsay was not found as Breck → Minnetonka. Review scan warnings.';
  $('avaCheck').classList.toggle('bad', !data.ava_lindsay_found);
  $('transferPlayers').innerHTML = data.transfers.length
    ? data.transfers.map(transferRow).join('')
    : '<p class="empty-list">No exact-name transfers found.</p>';
  $('reviewPlayers').innerHTML = data.ambiguous.map(transferRow).join('');
  $('reviewGroup').classList.toggle('hidden', !data.ambiguous.length);
  $('warningText').textContent = `${data.failures.length} pages could not be read. The rest of the comparison is shown above.`;
  $('scanWarnings').classList.toggle('hidden', !data.failures.length);
  $('transferResults').classList.remove('hidden');
  $('transferResults').scrollIntoView({behavior:'smooth', block:'start'});
}

async function pollTransferJob(jobId) {
  const response = await fetch(`/api/transfers/status/${jobId}`);
  if (response.status === 401) { window.location.href='/login'; return; }
  const payload = await jsonResponse(response);
  if (!response.ok || !payload.ok) throw new Error(payload.error || 'Could not check transfer scan.');
  const job = payload.job;
  const total = Math.max(1, Number(job.total || 1));
  const current = Math.max(0, Number(job.current || 0));
  const percent = Math.min(99, Math.round((current / total) * 100));
  $('transferProgressBar').style.width = `${job.status === 'complete' ? 100 : percent}%`;
  $('transferStage').textContent = job.stage || 'Working…';
  $('transferProgressText').textContent = total > 1 ? `${current} of ${total}` : '';
  if (job.status === 'complete') {
    renderTransfers(job.result);
    $('transferProgress').classList.add('hidden');
    $('findTransfers').disabled = false;
    $('findTransfers').textContent = 'Find Transfers';
    return;
  }
  if (job.status === 'failed') throw new Error(job.error || 'Transfer scan failed.');
  setTimeout(() => pollTransferJob(jobId).catch(failTransferScan), 1800);
}

function failTransferScan(error) {
  showTransferError(error.message);
  $('transferProgress').classList.add('hidden');
  $('findTransfers').disabled = false;
  $('findTransfers').textContent = 'Find Transfers';
}

async function findTransfers() {
  const previousUrl = $('previousSeason').value.trim();
  const currentUrl = $('currentSeason').value.trim();
  if (!previousUrl || !currentUrl) return showTransferError('Enter both season-hub URLs.');
  $('findTransfers').disabled = true;
  $('findTransfers').textContent = 'Scanning…';
  $('transferResults').classList.add('hidden');
  $('transferProgress').classList.remove('hidden');
  $('transferProgressBar').style.width = '2%';
  $('transferStage').textContent = 'Starting scan…';
  $('transferProgressText').textContent = '';
  showTransferError('');
  try {
    const response = await fetch('/api/transfers/start', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({previous_url:previousUrl, current_url:currentUrl}),
    });
    if (response.status === 401) { window.location.href='/login'; return; }
    const payload = await jsonResponse(response);
    if (!response.ok || !payload.ok) throw new Error(payload.error || 'Could not start transfer scan.');
    await pollTransferJob(payload.job_id);
  } catch (error) {
    failTransferScan(error);
  }
}

$('findTransfers').addEventListener('click', findTransfers);
$('copyTransfers').addEventListener('click', () => {
  if (!transferResult) return;
  const lines = transferResult.transfers.map(item => `${item.name}: ${item.previous_team} → ${item.current_team}`);
  navigator.clipboard.writeText(lines.join('\n'));
  $('toastMessage').textContent = `${lines.length} transfers copied`;
  $('toast').classList.remove('hidden');
  clearTimeout(copyGroup.timer);
  copyGroup.timer = setTimeout(() => $('toast').classList.add('hidden'), 1500);
});
