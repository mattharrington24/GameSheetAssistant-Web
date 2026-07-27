const $ = (id) => document.getElementById(id);
const escapeHtml = (value='') => String(value).replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
let result = null;

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
