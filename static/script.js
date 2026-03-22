const state = {
  stats: {},
  users: [],
  groups: [],
  logs: [],
  password: localStorage.getItem('dashboard_pwd') || sessionStorage.getItem('hinata_pwd') || ''
};

// Sync auth keys so inline HTML scripts can make authorized requests
if (state.password) {
  localStorage.setItem('dashboard_pwd', state.password);
  sessionStorage.setItem('hinata_pwd', state.password);
}

// Global Fetch Wrapper with Auth
async function authFetch(url, options = {}) {
  const headers = options.headers || {};
  headers['X-Dashboard-Password'] = state.password;
  
  const res = await fetch(url, { ...options, headers });
  
  if (res.status === 401) {
    showLogin();
    throw new Error('Unauthorized');
  }
  return res;
}

// UI Elements
const els = {
  statUsers: document.getElementById('stat-users'),
  statGroups: document.getElementById('stat-groups'),
  statUptime: document.getElementById('stat-uptime'),
  botStatusDot: document.getElementById('bot-status-dot'),
  botStatusText: document.getElementById('bot-status-text'),
  logsContainer: document.getElementById('logs-container'),
  masterUsersBody: document.getElementById('master-users-body'),
  broadcastsBody: document.getElementById('broadcasts-body'),
  tokenInput: document.getElementById('bot-token-input'),
  maskedToken: document.getElementById('masked-token-view'),
  welcomeImgInput: document.getElementById('welcome-img-input'),
  fallbackImgInput: document.getElementById('fallback-img-input'),
  coupleBgInput: document.getElementById('couple-bg-input'),
  coupleEnabledCheckbox: document.getElementById('couple-enabled-checkbox')
};

async function init() {
  if (!state.password) {
    showLogin();
    return;
  }
  
  hideLogin();
  await refreshData();
  await refreshLogs();
  await refreshConfig();
  await refreshMood();
  // Load all additional sections
  loadBotInfo();
  loadLeaderboard();
  loadKeywords();
  loadTrackingConfig();
  
  // Polling
  setInterval(() => { if(state.password) refreshData(); }, 15000);
  setInterval(() => { if(state.password) refreshLogs(); }, 4000);
}

function showLogin() {
  const overlay = document.getElementById('login-overlay');
  if (overlay) overlay.style.display = 'flex';
}

function hideLogin() {
  const overlay = document.getElementById('login-overlay');
  if (overlay) overlay.style.display = 'none';
}

function logout() {
  localStorage.removeItem('dashboard_pwd');
  sessionStorage.removeItem('hinata_pwd');
  location.reload();
}

function downloadDB() {
  window.location.href = `/api/download_db?pwd=${state.password}`;
}

async function attemptLogin() {
  const pwdInput = document.getElementById('login-password');
  const errText = document.getElementById('login-error');
  const pwd = pwdInput.value;
  
  if (!pwd) return;
  
  state.password = pwd; // Temporary set to test
  try {
    const res = await authFetch('/api/config');
    if (res.ok) {
      localStorage.setItem('dashboard_pwd', pwd);
      sessionStorage.setItem('hinata_pwd', pwd);
      hideLogin();
      init();
    }
  } catch (e) {
    errText.style.display = 'block';
    state.password = '';
  }
}

async function refreshData() {
  try {
    const res = await authFetch('/api/data');
    const data = await res.json();
    
    // Update State
    state.stats = data.stats;
    state.users = data.users;
    state.groups = data.groups;
    
    // Update Stats UI
    if (els.statUsers) els.statUsers.innerText = data.stats.total_users;
    if (els.statGroups) els.statGroups.innerText = data.stats.total_groups;
    if (els.statUptime) els.statUptime.innerText = data.stats.uptime;
    const statMessages = document.getElementById('stat-messages');
    if (statMessages) statMessages.innerText = data.stats.total_messages || 0;
    
    // Update Status
    if (els.botStatusDot) {
      if (data.stats.status === 'online') {
        els.botStatusDot.classList.add('online');
        if (els.botStatusText) els.botStatusText.innerText = 'System Online';
      } else {
        els.botStatusDot.classList.remove('online');
        if (els.botStatusText) els.botStatusText.innerText = 'System Offline';
      }
    }
    
    renderMasterTable(data.users);
    renderMasterGroups(data.groups);
    renderRecentTables(data.users, data.groups);
    renderBroadcastHistory(data.broadcasts);
    renderBannedUsers(data.banned_users);
    refreshFiles();
    
  } catch (e) {
    console.error("Data Refresh Failed", e);
  }
}

async function refreshFiles() {
  try {
    const res = await authFetch('/api/files');
    const files = await res.json();
    renderFiles(files);
  } catch (e) {}
}

function renderFiles(files) {
  const fBody = document.getElementById('files-body');
  if (!fBody) return;
  
  if (!files || files.length === 0) {
    fBody.innerHTML = '<tr><td colspan="3">Storage segments clear.</td></tr>';
  } else {
    fBody.innerHTML = files.map(f => `
      <tr>
        <td><code>${f.name}</code></td>
        <td><span class="v-tag" style="background:var(--secondary)">${f.size}</span></td>
        <td style="font-family: monospace; font-size: 0.8rem;">${f.time}</td>
      </tr>
    `).join('');
  }
}

function renderBannedUsers(banned) {
  const bBody = document.getElementById('banned-users-body');
  if (!bBody) return;
  
  if (!banned || banned.length === 0) {
    bBody.innerHTML = '<tr><td colspan="2">No active bans in neural network.</td></tr>';
  } else {
    bBody.innerHTML = banned.map(uid => `
      <tr>
        <td><code>${uid}</code></td>
        <td><span class="v-tag" style="background:var(--danger); box-shadow:none;">BLACK-LISTED</span></td>
      </tr>
    `).join('');
  }
}

async function refreshLogs() {
  try {
    const res = await authFetch('/api/logs');
    const logs = await res.json();
    
    if (els.logsContainer) {
      const newContent = logs.map(log => {
        let type = 'info';
        const low = log.toLowerCase();
        if (low.includes('error')) type = 'error';
        if (low.includes('warn')) type = 'warn';
        if (low.includes('system') || low.includes('init')) type = 'system';
        return `<div class="log-entry ${type}">${log}</div>`;
      }).join('');
      
      if (els.logsContainer.innerHTML !== newContent) {
        els.logsContainer.innerHTML = newContent;
        els.logsContainer.scrollTop = els.logsContainer.scrollHeight;
      }
    }
  } catch (e) {}
}

async function refreshConfig() {
  try {
    const res = await authFetch('/api/config');
    const config = await res.json();
    if (els.maskedToken) els.maskedToken.innerText = config.token;
    if (els.welcomeImgInput && config.welcome_img) els.welcomeImgInput.value = config.welcome_img;
    if (els.fallbackImgInput && config.fallback_img) els.fallbackImgInput.value = config.fallback_img;
    
    // Track inputs
    const trackUserInp = document.getElementById('tracked-user-input');
    const fwdGroupInp = document.getElementById('forward-group-input');
    if (trackUserInp && config.tracked_user_id) trackUserInp.value = config.tracked_user_id;
    if (fwdGroupInp && config.forward_group_id) fwdGroupInp.value = config.forward_group_id;
    if (els.coupleBgInput && config.couple_bg) els.coupleBgInput.value = config.couple_bg;
    if (els.coupleEnabledCheckbox && typeof config.couple_enabled !== 'undefined') els.coupleEnabledCheckbox.checked = config.couple_enabled;
  
  // Update status panel
  if (config.bot_enabled !== undefined) {
    const on = config.bot_enabled;
    const dot = document.getElementById('bot-power-dot');
    const val = document.getElementById('bot-power-value');
    if (dot) dot.classList.toggle('online', on);
    if (val) val.innerText = on ? 'ON' : 'OFF';
  }
  if (config.global_access !== undefined) {
    const on = config.global_access;
    const dot = document.getElementById('global-access-dot');
    const val = document.getElementById('global-access-value');
    if (dot) dot.classList.toggle('online', on);
    if (val) val.innerText = on ? 'ENABLED' : 'DISABLED';
  }
  if (config.couple_enabled !== undefined) {
    const on = config.couple_enabled;
    const dot = document.getElementById('couple-enabled-dot');
    const val = document.getElementById('couple-enabled-value');
    if (dot) dot.classList.toggle('online', on);
    if (val) val.innerText = on ? 'ENABLED' : 'DISABLED';
  }
  } catch (e) {}
}

async function updateBotMood() {
  const moodSelect = document.getElementById('bot-mood-select');
  if (!moodSelect) return;
  const mood = moodSelect.value;
  alertBox("Updating bot mood...", "info");
  
  try {
    const res = await authFetch('/api/mood', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mood })
    });
    const data = await res.json();
    if (data.success) {
      alertBox("Bot mood updated successfully!", "success");
    } else {
      alertBox("Mood update failed: " + data.error, "danger");
    }
  } catch (e) {
    alertBox("Network error during mood update", "danger");
  }
}

async function updateAssets() {
  const welcome_img = els.welcomeImgInput.value;
  const fallback_img = els.fallbackImgInput.value;
  
  const trackUserInp = document.getElementById('tracked-user-input');
  const fwdGroupInp = document.getElementById('forward-group-input');
  const tracked_user_id = trackUserInp ? trackUserInp.value : '';
  const forward_group_id = fwdGroupInp ? fwdGroupInp.value : '';
  const couple_bg = els.coupleBgInput ? els.coupleBgInput.value : '';
  const couple_enabled = els.coupleEnabledCheckbox ? els.coupleEnabledCheckbox.checked : true;
  
  alertBox("Syncing configuration...", "info");
  try {
    const res = await authFetch('/api/config-update', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ welcome_img, fallback_img, tracked_user_id, forward_group_id, couple_enabled, couple_bg })
    });
    const data = await res.json();
    if (data.success) {
      alertBox("Neural assets updated!", "success");
      refreshData();
    } else {
      alertBox("Sync failed: " + data.error, "danger");
    }
  } catch (e) {
    alertBox("Network error during sync", "danger");
  }
}

function renderRecentTables(users, groups) {
  const uBody = document.getElementById('users-body');
  const gBody = document.getElementById('groups-body');
  
  if (uBody) {
    uBody.innerHTML = users.slice(0, 5).map(u => `
      <tr>
        <td><code>${u.id}</code></td>
        <td>${u.full_name || u.name || 'Unknown'}</td>
        <td>${u.username ? '@' + u.username : '-'}</td>
        <td>${u.joined_at || '-'}</td>
      </tr>
    `).join('') || '<tr><td colspan="4">No users.</td></tr>';
  }
  
  if (gBody) {
    gBody.innerHTML = groups.slice(0, 5).map(g => `
      <tr>
        <td><code>${g.id}</code></td>
        <td>${g.title || 'Unknown'}</td>
        <td><span class="v-tag" style="background: var(--secondary); box-shadow:none;">${g.type || 'group'}</span></td>
        <td>${g.added_at || '-'}</td>
      </tr>
    `).join('') || '<tr><td colspan="4">No groups.</td></tr>';
  }
}

function renderMasterTable(users) {
  if (els.masterUsersBody) {
    els.masterUsersBody.innerHTML = users.map(u => `
      <tr>
        <td><code>${u.id}</code></td>
        <td>${u.full_name || u.name || 'Unknown'}</td>
        <td>${u.username ? '@' + u.username : '-'}</td>
        <td>${u.joined_at || '-'}</td>
      </tr>
    `).join('') || '<tr><td colspan="4">No records.</td></tr>';
  }
}

function renderMasterGroups(groups) {
  const gBody = document.getElementById('master-groups-body');
  if (gBody) {
    gBody.innerHTML = groups.map(g => `
      <tr>
        <td><code>${g.id}</code></td>
        <td>${g.title || 'Unknown'}</td>
        <td><span class="v-tag" style="background: var(--secondary); box-shadow:none;">${g.type || 'group'}</span></td>
        <td>${g.added_at || '-'}</td>
      </tr>
    `).join('') || '<tr><td colspan="4">No records.</td></tr>';
  }
}

function renderBroadcastHistory(broadcasts) {
  if (els.broadcastsBody) {
    els.broadcastsBody.innerHTML = broadcasts.map(b => `
      <tr>
        <td><code>#${b.id}</code></td>
        <td>${b.text.substring(0, 40)}${b.text.length > 40 ? '...' : ''}</td>
        <td><span class="v-tag">${b.target}</span></td>
        <td><span style="color:var(--success)">${b.sent_count} ✅</span> / <span style="color:var(--danger)">${b.failed_count} ❌</span></td>
        <td>${b.timestamp}</td>
        <td>
          <button class="btn btn-danger" style="padding: 5px 12px; font-size: 0.75rem;" onclick="deleteBroadcast(${b.id})">
            <i class="fas fa-trash"></i>
          </button>
        </td>
      </tr>
    `).join('') || '<tr><td colspan="6">No history.</td></tr>';
  }
}

// Actions
async function controlBot(action) {
  if (!confirm(`Confirm system action: ${action}?`)) return;
  alertBox(`Executing ${action}...`, 'info');
  
  try {
    const res = await authFetch('/api/control', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action })
    });
    const data = await res.json();
    if (data.success) {
      alertBox(`Action ${action} successful!`, 'success');
      if (action === 'restart') setTimeout(() => location.reload(), 3000);
      refreshData();
      refreshConfig();
    } else {
       alertBox(`Error: ${data.error}`, 'danger');
    }
  } catch (e) {
    alertBox(`Network failed`, 'danger');
  }
}

async function executeMessageAction(action) {
  const urlParams = document.getElementById('admin-msg-url').value.trim();
  if (!urlParams) return alertBox("Please enter a valid message URL", "danger");

  if (!confirm(`Are you sure you want to ${action} this message?`)) return;
  alertBox(`Requesting ${action}...`, 'info');
  
  const endpoint = `/api/${action}_msg`;
  try {
    const res = await authFetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: urlParams })
    });
    const data = await res.json();
    if (data.success) {
      alertBox(`Message ${action} successful!`, 'success');
      if (action === 'delete') document.getElementById('admin-msg-url').value = '';
    } else {
       alertBox(`Error: ${data.error}`, 'danger');
    }
  } catch (e) {
    alertBox(`Network failed`, 'danger');
  }
}

async function executeAdmin(action) {
  const uid = document.getElementById('admin-user-id').value.trim();
  const gid = document.getElementById('admin-group-id').value.trim();
  
  if (!uid && action !== 'unban') return alertBox("User ID required", "danger");

  alertBox(`Executing ${action}...`, "info");
  
  try {
    const res = await authFetch('/api/execute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command: action, user_id: uid, chat_id: gid })
    });
    const data = await res.json();
    if (data.success) {
      alertBox(`Success: ${data.message || 'Action executed'}`, "success");
    } else {
      alertBox(`Failed: ${data.error}`, "danger");
    }
  } catch(e) {
    alertBox("Admin Action Failed", "danger");
  }
}

async function updateBotToken() {
  const token = els.tokenInput.value;
  if (!token) return alert("Please enter a new token!");
  
  if (!confirm("Update Bot Token? This will require a manual restart.")) return;
  
  try {
    const res = await authFetch('/api/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token })
    });
    const data = await res.json();
    if (data.success) {
      alertBox("Token updated! Click RESTART to apply.", "success");
      els.tokenInput.value = '';
      refreshConfig();
    } else {
      alertBox("Failed: " + data.error, "danger");
    }
  } catch (e) {
    alertBox("Update failed", "danger");
  }
}

async function sendBroadcast(target) {
    const msgInput = document.getElementById('broadcast-msg');
    const targetInput = document.getElementById('broadcast-target-id');
    const photoInput = document.getElementById('broadcast-photo-url');
    const message = msgInput.value.trim();
    const photoUrl = photoInput ? photoInput.value.trim() : '';
    
    // Require either a message or a photo URL
    if (!message && !photoUrl) return alert("Please enter a message or a photo URL!");
    if (target === 'specific') {
        target = targetInput.value.trim();
        if (!target) return alert("Please enter a Specific Target ID!");
    }
    
    const isMedia = !!photoUrl;
    alertBox(`${isMedia ? '📸 Media' : '💬 Text'} broadcast to ${target}...`, 'info');
    try {
        const payload = {
            target,
            message: isMedia ? '' : message,
            photo_url: photoUrl,
            caption: isMedia ? message : ''
        };
        const res = await authFetch('/api/broadcast', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.status === 'success') {
            alertBox(`✅ Broadcast sent! ${data.sent} delivered, ${data.failed || 0} failed.`, 'success');
            msgInput.value = '';
            if (photoInput) photoInput.value = '';
            refreshData();
        } else {
            alertBox(`❌ Broadcast failed: ${data.detail || data.error || 'Unknown error'}`, "danger");
        }
    } catch (e) {
        alertBox("Broadcast error: " + e.message, "danger");
    }
}

async function deleteBroadcast(id) {
  if (!confirm(`Delete broadcast #${id}?`)) return;
  try {
    await authFetch(`/api/broadcasts/${id}`, { method: 'DELETE' });
    refreshData();
  } catch(e) {}
}

async function trackUsers() {
  if (!confirm("Track all users metadata? This may take time.")) return;
  await controlBot('track_users');
}

function filterUsers() {
  const query = document.getElementById('user-search').value.toLowerCase();
  const rows = document.querySelectorAll('#master-users-table tbody tr');
  rows.forEach(row => {
    const text = row.innerText.toLowerCase();
    row.style.display = text.includes(query) ? '' : 'none';
  });
}

function filterGroups() {
  const query = document.getElementById('group-search').value.toLowerCase();
  const rows = document.querySelectorAll('#master-groups-table tbody tr');
  rows.forEach(row => {
    const text = row.innerText.toLowerCase();
    row.style.display = text.includes(query) ? '' : 'none';
  });
}

function alertBox(text, type) {
  // Create a toast notification instead of basic alert
  const toast = document.createElement('div');
  toast.className = `alert-toast alert-${type}`;
  toast.innerText = text;
  toast.style.position = 'fixed';
  toast.style.bottom = '20px';
  toast.style.right = '20px';
  toast.style.padding = '15px 25px';
  toast.style.borderRadius = '8px';
  toast.style.color = '#fff';
  toast.style.fontWeight = 'bold';
  toast.style.zIndex = '9999';
  toast.style.transition = 'opacity 0.3s ease';
  
  // Set color based on type
  if (type === 'success') toast.style.backgroundColor = '#28a745';
  else if (type === 'danger') toast.style.backgroundColor = '#dc3545';
  else if (type === 'info') toast.style.backgroundColor = '#17a2b8';
  else toast.style.backgroundColor = '#333';
  
  document.body.appendChild(toast);
  
  setTimeout(() => {
      toast.style.opacity = '0';
      setTimeout(() => toast.remove(), 300);
  }, 3000);
}

// Start
document.addEventListener('DOMContentLoaded', () => {
    init();
    
    // Enter key for login
    const loginPass = document.getElementById('login-password');
    if (loginPass) {
        loginPass.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') attemptLogin();
        });
    }
});

// ══════════════════════════════════════════════════════════════
//  GROUP COMMAND CENTER (GCC) – Full Implementation
// ══════════════════════════════════════════════════════════════

let gccCurrentGroupId = null;
let gccMembers = [];

function gccShow(el, show) {
  if (el) el.style.display = show ? '' : 'none';
}

function gccResult(text, type = 'info') {
  const el = document.getElementById('gcc-result-banner');
  if (!el) return;
  el.className = `gcc-result ${type}`;
  el.innerHTML = `<i class="fa-solid fa-${type === 'success' ? 'circle-check' : type === 'danger' ? 'circle-xmark' : 'circle-info'}"></i> ${text}`;
  el.style.display = 'block';
  setTimeout(() => { el.style.display = 'none'; }, 6000);
}

async function gccScanGroup() {
  const gidInput = document.getElementById('gcc-group-id');
  const gid = gidInput ? gidInput.value.trim() : '';
  if (!gid) return alertBox('Please enter a Group ID', 'danger');

  gccCurrentGroupId = gid;
  gccMembers = [];

  // Show spinner, hide results
  const loading = document.getElementById('gcc-loading');
  const infoBanner = document.getElementById('gcc-group-info');
  const membersCard = document.getElementById('gcc-members-card');
  const bulkCard = document.getElementById('gcc-bulk-card');
  gccShow(loading, true);
  gccShow(infoBanner, false);
  gccShow(membersCard, false);
  gccShow(bulkCard, false);

  try {
    const res = await authFetch(`/api/gcc/group_info?group_id=${encodeURIComponent(gid)}`);
    const data = await res.json();
    gccShow(loading, false);

    if (!data.success) {
      alertBox('Scan Failed: ' + data.error, 'danger');
      return;
    }

    // Show group info banner
    const g = data.group;
    const liveAdmins = (data.members || []).filter(m => m.source === 'telegram').length;
    const dbUsers    = (data.members || []).filter(m => m.source === 'database').length;
    infoBanner.innerHTML = `
      <div class="gcc-info-item">
        <span class="gcc-info-label">Group ID</span>
        <span class="gcc-info-val"><code>${g.id}</code></span>
      </div>
      <div class="gcc-info-item">
        <span class="gcc-info-label">Title</span>
        <span class="gcc-info-val">${g.title || '—'}</span>
      </div>
      <div class="gcc-info-item">
        <span class="gcc-info-label">Type</span>
        <span class="gcc-info-val">${g.type || '—'}</span>
      </div>
      <div class="gcc-info-item">
        <span class="gcc-info-label">Total Members</span>
        <span class="gcc-info-val" style="color:var(--secondary);">${g.member_count ?? '—'}</span>
      </div>
      <div class="gcc-info-item">
        <span class="gcc-info-label">Username</span>
        <span class="gcc-info-val">${g.username ? '@' + g.username : '—'}</span>
      </div>
      <div class="gcc-info-item">
        <span class="gcc-info-label">Live Admins</span>
        <span class="gcc-info-val" style="color:#f43f5e;">⚡ ${liveAdmins}</span>
      </div>
      <div class="gcc-info-item">
        <span class="gcc-info-label">DB Users</span>
        <span class="gcc-info-val" style="color:var(--secondary);"> ${dbUsers}</span>
      </div>
      <div class="gcc-info-item" style="flex-basis:100%;">
        <span class="gcc-info-label">Description</span>
        <span class="gcc-info-val" style="max-width:500px;font-size:0.85rem;">${g.description || '—'}</span>
      </div>
    `;
    if (data.note) {
      const noteEl = document.createElement('div');
      noteEl.className = 'gcc-api-note';
      noteEl.innerHTML = `<i class="fa-solid fa-circle-info"></i> ${data.note}`;
      infoBanner.appendChild(noteEl);
    }
    gccShow(infoBanner, true);

    // Render members
    gccMembers = data.members || [];
    gccRenderMembers(gccMembers);

    // Show panels
    gccShow(membersCard, true);
    gccShow(bulkCard, true);

    setTimeout(() => membersCard.scrollIntoView({ behavior: 'smooth', block: 'start' }), 200);

  } catch (e) {
    gccShow(loading, false);
    alertBox('Scan error: ' + e.message, 'danger');
    console.error('GCC Scan Error:', e);
  }
}

function gccRenderMembers(members) {
  const tbody = document.getElementById('gcc-members-body');
  const countBadge = document.getElementById('gcc-count-badge');
  if (!tbody) return;

  const liveCount = members.filter(m => m.source === 'telegram').length;
  const dbCount   = members.filter(m => m.source === 'database').length;
  if (countBadge) {
    countBadge.innerHTML =
      `${members.length} Total &nbsp;│&nbsp; ` +
      `<span style="color:#f43f5e;">⚡ ${liveCount} Live</span> &nbsp;│&nbsp; ` +
      `<span style="color:var(--secondary);"> ${dbCount} DB</span>`;
  }

  if (members.length === 0) {
    tbody.innerHTML = `
      <tr><td colspan="8" style="text-align:center;padding:2.5rem;">
        <i class="fa-solid fa-triangle-exclamation" style="color:var(--warning);font-size:2rem;"></i><br><br>
        <strong style="font-size:1rem;">No data found</strong><br>
        <span style="color:var(--text-muted);font-size:0.85rem;">
          Make sure the bot is an admin in the group and the Group ID is correct.
        </span>
      </td></tr>`;
    return;
  }

  // Upgrade table header to include new columns
  const theadRow = document.querySelector('#gcc-members-table thead tr');
  if (theadRow) {
    theadRow.innerHTML = `
      <th style="width:36px;"><input type="checkbox" id="gcc-select-all" onchange="gccToggleAll(this)" /></th>
      <th>User ID</th>
      <th>Name</th>
      <th>Username</th>
      <th>Msgs</th>
      <th>Source</th>
      <th>Role</th>
      <th>Actions</th>
    `;
  }

  tbody.innerHTML = members.map((m) => {
    const rawStatus = String(m.status || '').toLowerCase();
    const roleLabel = rawStatus.includes('creator') ? 'creator' :
                      rawStatus.includes('admin') ? 'admin' :
                      m.user?.is_deleted ? 'deleted' : 'member';
    const roleCls   = 'gcc-role-' + roleLabel;

    const name      = ((m.user?.first_name || '') + ' ' + (m.user?.last_name || '')).trim() || 'Unknown';
    const username  = m.user?.username
      ? `<span style="color:var(--primary)">@${m.user.username}</span>`
      : `<span style="opacity:.45">—</span>`;
    const uid = m.user?.id ?? '—';

    const isLive     = m.source === 'telegram';
    const srcBadge   = isLive
      ? `<span class="gcc-src-badge gcc-src-live">⚡ LIVE</span>`
      : `<span class="gcc-src-badge gcc-src-db"> DB</span>`;

    const msgCount   = (m.msg_count != null && m.msg_count > 0)
      ? `<code style="color:var(--accent);">${m.msg_count}</code>`
      : `<span style="opacity:.35">—</span>`;

    const canEditTitle = roleLabel === 'admin' || roleLabel === 'creator';
    const titleBtn = canEditTitle 
      ? `<button class="gcc-mini-btn" style="color:var(--warning)" title="Edit Admin Title" onclick="gccEditAdminTitle('${uid}', '${name.replace(/'/g, "\\'")}')"><i class="fa-solid fa-crown"></i></button>`
      : '';

    return `
      <tr id="gcc-row-${uid}" data-uid="${uid}" data-name="${name}" data-username="${m.user?.username||''}">
        <td><input type="checkbox" class="gcc-member-check" value="${uid}" onchange="gccUpdateSelectedCount()" /></td>
        <td><code style="color:var(--secondary);font-size:.8rem;">${uid}</code></td>
        <td style="font-weight:600;">${name}</td>
        <td>${username}</td>
        <td style="text-align:center;">${msgCount}</td>
        <td>${srcBadge}</td>
        <td><span class="gcc-role-badge ${roleCls}">${roleLabel}</span></td>
        <td>
          <div class="gcc-mini-btns">
            ${titleBtn}
            <button class="gcc-mini-btn danger" title="Kick" onclick="gccSingleAction('kick','${uid}')"><i class="fa-solid fa-person-walking-arrow-right"></i></button>
            <button class="gcc-mini-btn danger" title="Ban" onclick="gccSingleAction('ban','${uid}')"><i class="fa-solid fa-ban"></i></button>
            <button class="gcc-mini-btn warn" title="Mute" onclick="gccSingleAction('mute','${uid}')"><i class="fa-solid fa-microphone-slash"></i></button>
            <button class="gcc-mini-btn success" title="Unmute" onclick="gccSingleAction('unmute','${uid}')"><i class="fa-solid fa-microphone"></i></button>
            <button class="gcc-mini-btn" title="Make Admin" onclick="gccSingleAction('addadmin','${uid}')"><i class="fa-solid fa-user-shield"></i></button>
          </div>
        </td>
      </tr>`;
  }).join('');
}

function gccFilterMembers() {
  const q = document.getElementById('gcc-member-search').value.toLowerCase();
  document.querySelectorAll('#gcc-members-table tbody tr').forEach(row => {
    row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none';
  });
}

function gccToggleAll(chk) {
  document.querySelectorAll('.gcc-member-check').forEach(cb => cb.checked = chk.checked);
  gccUpdateSelectedCount();
}

function gccUpdateSelectedCount() {
  const count = document.querySelectorAll('.gcc-member-check:checked').length;
  const lbl = document.getElementById('gcc-selected-label');
  if (lbl) lbl.textContent = `${count} Selected`;
}

function gccGetSelectedIds() {
  return Array.from(document.querySelectorAll('.gcc-member-check:checked')).map(cb => cb.value);
}

async function gccEditAdminTitle(userId, name) {
  if (!gccCurrentGroupId) return alertBox('No group loaded', 'danger');
  const newTitle = prompt(`Enter custom admin title for ${name}:`, "");
  if (newTitle === null) return; // Cancelled

  try {
    const res = await authFetch('/api/gcc/group_action', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        group_id: String(gccCurrentGroupId), 
        action: 'set_admin_custom_title', 
        user_ids: [String(userId)], 
        value: newTitle 
      })
    });
    const data = await res.json();
    if (data.success) {
      alertBox(`✅ Title updated for ${name} to "${newTitle}"`, 'success');
      // Update local data if possible or re-scan
    } else {
      alertBox(`❌ Failed: ${data.error}`, 'danger');
    }
  } catch (e) {
    alertBox('Network error', 'danger');
  }
}

async function gccSingleAction(action, userId) {
  if (!gccCurrentGroupId) return alertBox('No group loaded', 'danger');
  try {
    const res = await authFetch('/api/execute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command: action, user_id: String(userId), chat_id: String(gccCurrentGroupId) })
    });
    const data = await res.json();
    if (data.success) {
      alertBox(`✅ ${action} on ${userId} done!`, 'success');
      if (action === 'kick' || action === 'ban') {
        const row = document.getElementById(`gcc-row-${userId}`);
        if (row) row.style.opacity = '0.3';
      }
    } else {
      alertBox(`❌ Failed: ${data.error}`, 'danger');
    }
  } catch (e) {
    alertBox('Network error', 'danger');
  }
}

async function gccBulkAction(type) {
  if (!gccCurrentGroupId) return alertBox('No group loaded', 'danger');

  let targets = gccGetSelectedIds();
  if (type === 'remove_deleted') {
    targets = gccMembers
      .filter(m => m.user?.is_deleted || m.user?.first_name === 'Deleted Account')
      .map(m => String(m.user?.id));
    if (targets.length === 0) return alertBox('No deleted accounts found!', 'info');
  } else {
    if (targets.length === 0) targets = gccMembers.filter(m => m.status === 'member').map(m => String(m.user?.id));
    if (targets.length === 0) return alertBox('No members selected or loaded', 'danger');
  }

  const actionMap = {
    kick_all: 'kick', ban_all: 'ban', mute_all: 'mute',
    unmute_all: 'unmute', unban_all: 'unban', remove_deleted: 'kick'
  };
  const cmd = actionMap[type];
  const label = type.replace('_', ' ').toUpperCase();

  if (!confirm(`⚠️ ${label} ${targets.length} members from group ${gccCurrentGroupId}?`)) return;

  gccResult(`⏳ Executing ${label} on ${targets.length} members…`, 'info');

  try {
    const res = await authFetch('/api/gcc/bulk_action', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ group_id: gccCurrentGroupId, action: cmd, user_ids: targets })
    });
    const data = await res.json();
    if (data.success !== false) {
      gccResult(`✅ ${label} Complete — Success: ${data.success_count}, Failed: ${data.failed_count}`, 'success');
    } else {
      gccResult(`❌ Error: ${data.error}`, 'danger');
    }
  } catch (e) {
    gccResult('Network error during bulk action', 'danger');
  }
}

async function gccDeleteMsgs(scope) {
  if (!gccCurrentGroupId) return alertBox('No group loaded', 'danger');
  let userId = null;
  if (scope === 'user') {
    userId = document.getElementById('gcc-del-user-id')?.value.trim();
    if (!userId) return alertBox('Enter the User ID to wipe messages from', 'danger');
  }
  const label = scope === 'all' ? 'ALL messages' : `messages from user ${userId}`;
  if (!confirm(`⚠️ Delete ${label} in group ${gccCurrentGroupId}? This cannot be undone.`)) return;

  gccResult(`⏳ Wiping ${label}…`, 'info');
  try {
    const res = await authFetch('/api/gcc/delete_messages', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ group_id: gccCurrentGroupId, scope, user_id: userId })
    });
    const data = await res.json();
    if (data.success !== false) {
      gccResult(`✅ Wipe done — ${data.deleted} deleted, ${data.failed} failed`, 'success');
    } else {
      gccResult(`❌ Error: ${data.error}`, 'danger');
    }
  } catch (e) {
    gccResult('Network error during message wipe', 'danger');
  }
}

async function gccGroupSetting(action) {
  if (!gccCurrentGroupId) return alertBox('No group loaded', 'danger');

  let extra = {};
  if (action === 'set_title') {
    const v = document.getElementById('gcc-new-title')?.value.trim();
    if (!v) return alertBox('Enter new title', 'danger');
    extra.value = v;
  } else if (action === 'set_description') {
    const v = document.getElementById('gcc-new-desc')?.value.trim();
    if (!v) return alertBox('Enter new description', 'danger');
    extra.value = v;
  } else if (action === 'promote_all_admins') {
    extra.user_ids = gccGetSelectedIds();
    if (extra.user_ids.length === 0) return alertBox('Select members to promote', 'danger');
  }

  const confirmMap = {
    kick_all: true, ban_all: true, lock_group: true,
    unlock_group: false, disable_invite: true, leave_group: true
  };
  if (confirmMap[action] !== undefined && confirmMap[action]) {
    if (!confirm(`⚠️ Confirm action: ${action}?`)) return;
  }

  gccResult(`⏳ Executing ${action}…`, 'info');
  try {
    const res = await authFetch('/api/gcc/group_action', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ group_id: gccCurrentGroupId, action, ...extra })
    });
    const data = await res.json();
    if (data.success) {
      const msg = data.value ? `✅ ${action} — ${data.value}` : `✅ ${action} executed successfully!`;
      gccResult(msg, 'success');
      if (action === 'get_invite_link' && data.value) {
        navigator.clipboard?.writeText(data.value)
          .then(() => alertBox('Invite link copied to clipboard!', 'success'))
          .catch(() => {});
      }
    } else {
      gccResult(`❌ Error: ${data.error}`, 'danger');
    }
  } catch (e) {
    gccResult('Network error during group action', 'danger');
  }
}

function gccClearAll() {
  gccCurrentGroupId = null;
  gccMembers = [];
  const gidInput = document.getElementById('gcc-group-id');
  if (gidInput) gidInput.value = '';
  gccShow(document.getElementById('gcc-group-info'), false);
  gccShow(document.getElementById('gcc-members-card'), false);
  gccShow(document.getElementById('gcc-bulk-card'), false);
  gccShow(document.getElementById('gcc-loading'), false);
  alertBox('Group data cleared', 'info');
}

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•


// ==========================================================
//  MANUAL DATABASE ENTRY (MDB)
// ==========================================================

function mdbShowResult(elId, msg, type) {
  var el = document.getElementById(elId);
  if (!el) return;
  var colorMap = { success: 'var(--success)', warn: 'var(--warning)', danger: 'var(--danger)' };
  var color = colorMap[type] || colorMap.danger;
  el.style.display = 'block';
  el.innerHTML = '<div style="padding:.7rem 1rem;border-radius:10px;border:1px solid ' + color +
    ';background:' + color + '18;color:' + color + ';font-size:.85rem;margin-top:.5rem;">' + msg + '</div>';
}

async function mdbAddGroup() {
  var gid   = (document.getElementById('mdb-group-id') ? document.getElementById('mdb-group-id').value   : '').trim();
  var title = (document.getElementById('mdb-group-title') ? document.getElementById('mdb-group-title').value : '').trim();
  var gtEl  = document.getElementById('mdb-group-type');
  var gtype = gtEl ? gtEl.value : 'supergroup';
  var btn   = document.getElementById('mdb-add-group-btn');
  var resId = 'mdb-group-result';
  if (!gid)   { mdbShowResult(resId, 'Group ID is required', 'danger'); return; }
  if (!title) { mdbShowResult(resId, 'Group Title is required', 'danger'); return; }
  if (btn) { btn.disabled = true; btn.textContent = 'Adding...'; }
  try {
    var res  = await authFetch('/api/add_group', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ group_id: gid, title: title, group_type: gtype })
    });
    var data = await res.json();
    if (data.success) {
      mdbShowResult(resId, 'Added: ' + data.message, 'success');
      document.getElementById('mdb-group-id').value    = '';
      document.getElementById('mdb-group-title').value = '';
      alertBox(data.message, 'success');
    } else {
      mdbShowResult(resId, 'Error: ' + data.error, 'danger');
    }
  } catch (e) {
    mdbShowResult(resId, 'Network error: ' + e.message, 'danger');
  } finally {
    if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fa-solid fa-plus"></i> Add Group'; }
  }
}

async function mdbAddUser() {
  var uid      = (document.getElementById('mdb-user-id')       ? document.getElementById('mdb-user-id').value       : '').trim();
  var fullName = (document.getElementById('mdb-user-name')     ? document.getElementById('mdb-user-name').value     : '').trim();
  var username = (document.getElementById('mdb-user-username') ? document.getElementById('mdb-user-username').value : '').trim();
  var btn      = document.getElementById('mdb-add-user-btn');
  var resId    = 'mdb-user-result';
  if (!uid)      { mdbShowResult(resId, 'User ID is required', 'danger'); return; }
  if (!fullName) { mdbShowResult(resId, 'Full Name is required', 'danger'); return; }
  if (btn) { btn.disabled = true; btn.textContent = 'Adding...'; }
  try {
    var res  = await authFetch('/api/add_user', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: uid, full_name: fullName, username: username })
    });
    var data = await res.json();
    if (data.success) {
      var tag = data.is_new ? '[NEW] ' : '[UPDATED] ';
      mdbShowResult(resId, tag + data.message, 'success');
      document.getElementById('mdb-user-id').value       = '';
      document.getElementById('mdb-user-name').value     = '';
      document.getElementById('mdb-user-username').value = '';
      alertBox(data.message, 'success');
    } else {
      mdbShowResult(resId, 'Error: ' + data.error, 'danger');
    }
  } catch (e) {
    mdbShowResult(resId, 'Network error: ' + e.message, 'danger');
  } finally {
    if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fa-solid fa-user-plus"></i> Add User'; }
  }
}

// ══════════════════════════════════════════════════════════════
//  MISSING STUB FUNCTIONS — Fixed & Implemented
// ══════════════════════════════════════════════════════════════

async function refreshMood() {
  try {
    const res = await authFetch('/api/config');
    const config = await res.json();
    const moodSelect = document.getElementById('bot-mood-select');
    if (moodSelect && config.bot_mood) moodSelect.value = config.bot_mood;
  } catch (e) {}
}

// Duplicate UI functions deleted to prevent overriding index.html's inline scripts.
