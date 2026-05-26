// --- проверка авторизации при загрузке ---
(async () => {
  const r = await fetch('/api/auth/me');
  if (!r.ok) { window.location.href = '/login'; return; }
  const me = await r.json();

  // Хедер: email + ссылки
  const header = document.querySelector('header');
  if (header) {
    const div = document.createElement('div');
    div.className = 'header-user';
    div.innerHTML =
      `<span class="user-email">${escHtmlSimple(me.email)}${me.is_admin ? ' <span class="badge-admin">admin</span>' : ''}</span>` +
      `<a href="/settings" class="ghost-link">⚙ Настройки</a>` +
      `<button id="logout-btn" class="ghost">Выйти</button>`;
    header.appendChild(div);
    document.getElementById('logout-btn').addEventListener('click', async () => {
      await fetch('/api/auth/logout', { method: 'POST' });
      window.location.href = '/login';
    });
  }

  // Баннер "нет WaveSpeed ключа"
  const wsRes = await fetch('/api/settings');
  if (wsRes.ok) {
    const ws = await wsRes.json();
    if (!ws.has_wavespeed_key) {
      const banner = document.createElement('div');
      banner.className = 'banner-warn';
      banner.innerHTML = '⚠ WaveSpeed API ключ не установлен. <a href="/settings">Добавить ключ →</a>';
      document.querySelector('main')?.prepend(banner);
    }
  }
})();

function escHtmlSimple(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

const form = document.getElementById('job-form');
const jobsDiv = document.getElementById('jobs');
const genSel = document.getElementById('generator');
const sceneSel = document.getElementById('scene_mode');
const drop = document.getElementById('drop');
const audio = document.getElementById('audio');
const dropSub = document.getElementById('drop-sub');
const goBtn = document.getElementById('go');
const healthBanner = document.getElementById('health-banner');

let canSubmit = false;

async function loadGenerators() {
  try {
    const r = await fetch('/api/models');
    const data = await r.json();
    const list = data.generators || data; // совместимость
    genSel.innerHTML = list.map(g => {
      const id = g.id || g.name;
      const title = g.title || g.name || id;
      const avail = g.available === false ? ' (нет)' : '';
      return `<option value="${id}">${title}${avail}</option>`;
    }).join('');
  } catch (e) {
    genSel.innerHTML = '<option value="ws-wan22-ti2v-5b">Wan 2.2 TI2V-5B (WaveSpeed)</option>';
  }
}

// drag-drop
['dragenter','dragover'].forEach(ev => drop.addEventListener(ev, e => {
  e.preventDefault(); drop.classList.add('hover');
}));
['dragleave','drop'].forEach(ev => drop.addEventListener(ev, e => {
  e.preventDefault(); drop.classList.remove('hover');
}));
drop.addEventListener('drop', e => {
  if (e.dataTransfer.files.length) {
    audio.files = e.dataTransfer.files;
    updateDropLabel();
  }
});
audio.addEventListener('change', updateDropLabel);
function updateDropLabel() {
  if (audio.files && audio.files[0]) {
    dropSub.textContent = audio.files[0].name;
  }
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  goBtn.disabled = true;
  try {
    const fd = new FormData(form);

    // авто-режим: если есть лирика → whisper, иначе uniform
    const lyrics = (fd.get('lyrics') || '').toString().trim();
    if (fd.get('scene_mode') === 'auto') {
      fd.set('scene_mode', lyrics ? 'whisper' : 'uniform');
    }

    // нормализовать чекбоксы
    fd.set('burn_subtitles', fd.has('burn_subtitles') ? 'true' : 'false');
    fd.set('llm_detail', fd.has('llm_detail') ? 'true' : 'false');

    // пустые числовые поля не отправлять (бэк подставит дефолты)
    ['width','height','fps'].forEach(k => {
      const v = fd.get(k);
      if (v === '' || v == null) fd.delete(k);
    });
    if (!fd.get('language')) fd.delete('language');

    const r = await fetch('/api/jobs', { method: 'POST', body: fd });
    if (!r.ok) { alert('Ошибка: ' + (await r.text())); return; }
    await refresh();
  } finally {
    goBtn.disabled = false;
  }
});

function fmtEta(s) {
  if (s == null || isNaN(s)) return '';
  s = Math.round(s);
  if (s < 60) return `~${s}с`;
  const m = Math.floor(s/60), r = s % 60;
  return `~${m}м${r ? ' ' + r + 'с' : ''}`;
}

function renderJob(j) {
  const pct = Math.round((j.progress || 0) * 100);
  const video = j.output_url ? `<video controls src="${j.output_url}"></video>` : '';
  const err = j.error
    ? `<div class="err">
         <button class="copy-err ghost" type="button">копировать</button>
         <pre>${escapeHtml(j.error)}</pre>
       </div>` : '';
  const eta = j.eta_seconds ? ` · осталось ${fmtEta(j.eta_seconds)}` : '';
  const active = !['done','error','cancelled'].includes(j.status);
  const cancelBtn = active
    ? `<button class="cancel" data-id="${j.id}">отменить</button>`
    : '';
  return `
    <div class="job">
      <div class="head">
        <div class="id">${j.id}</div>
        ${cancelBtn}
      </div>
      <div class="status">${j.status} — ${escapeHtml(j.message || '')} (${pct}%)${eta}</div>
      <div class="bar"><div style="width:${pct}%"></div></div>
      ${video}
      ${err}
    </div>
  `;
}

function escapeHtml(s){ return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
function escapeAttr(s){ return escapeHtml(s); }

async function refresh() {
  try {
    const r = await fetch('/api/jobs');
    const list = await r.json();
    list.sort((a,b) => (b.created_at || 0) - (a.created_at || 0));
    jobsDiv.innerHTML = list.map(renderJob).join('') ||
      '<small style="color:#6b7280">Пока пусто</small>';
  } catch (e) {}
}

function setHealthState(state, text) {
  if (!healthBanner) return;
  healthBanner.classList.remove('health-loading', 'health-ok', 'health-warn', 'health-error');
  healthBanner.classList.add(state);
  healthBanner.textContent = text;
}

async function refreshHealth() {
  try {
    const r = await fetch('/api/health');
    if (!r.ok) {
      canSubmit = false;
      goBtn.disabled = true;
      setHealthState('health-error', 'Health endpoint недоступен: ' + r.status);
      return;
    }
    const h = await r.json();
    const whisper = h.whisper_device
      ? ` Whisper: ${h.whisper_device}/${h.whisper_compute_type}${h.whisper_loaded ? '' : ' (не загружен)'}.`
      : '';
    if (h.comfy_alive) {
      canSubmit = true;
      goBtn.disabled = false;
      const cpuFallback = h.whisper_loaded && h.whisper_device === 'cpu';
      if (cpuFallback) {
        setHealthState('health-warn', `ComfyUI доступен.${whisper} Whisper работает на CPU (fallback), выравнивание лирики будет медленнее.`);
      } else if (h.openrouter_configured) {
        setHealthState('health-ok', `ComfyUI доступен. Сервис готов к генерации.${whisper}`);
      } else {
        setHealthState('health-warn', `ComfyUI доступен. OpenRouter не настроен: LLM-режимы будут ограничены.${whisper}`);
      }
    } else {
      canSubmit = false;
      goBtn.disabled = true;
      setHealthState('health-error', `ComfyUI недоступен: ${h.comfyui_url}. Проверьте запуск ComfyUI.`);
    }
  } catch (e) {
    canSubmit = false;
    goBtn.disabled = true;
    setHealthState('health-error', 'Нет связи с backend. Проверьте, что ClipMaker запущен.');
  }
}

jobsDiv.addEventListener('click', async (e) => {
  const cp = e.target.closest('.copy-err');
  if (cp) {
    const txt = cp.parentElement?.querySelector('pre')?.textContent || '';
    try {
      await navigator.clipboard.writeText(txt);
      const old = cp.textContent;
      cp.textContent = '✓ скопировано';
      setTimeout(() => { cp.textContent = old; }, 1500);
    } catch (err) {
      // fallback
      const ta = document.createElement('textarea');
      ta.value = txt; document.body.appendChild(ta); ta.select();
      try { document.execCommand('copy'); } catch(_){}
      ta.remove();
    }
    return;
  }
  const btn = e.target.closest('.cancel');
  if (!btn) return;
  btn.disabled = true;
  await fetch('/api/jobs/' + btn.dataset.id, { method: 'DELETE' });
  refresh();
});

const clearBtn = document.getElementById('clear-jobs');
if (clearBtn) {
  clearBtn.addEventListener('click', async () => {
    clearBtn.disabled = true;
    try {
      await fetch('/api/jobs/clear', { method: 'POST' });
      await refresh();
    } finally { clearBtn.disabled = false; }
  });
}

loadGenerators();
refresh();
refreshHealth();
setInterval(refresh, 2000);
setInterval(refreshHealth, 5000);

// --- редактор системных промтов ---
const pDir = document.getElementById('p-director');
const pDet = document.getElementById('p-detail');
const pSave = document.getElementById('p-save');
const pReset = document.getElementById('p-reset');
const pStatus = document.getElementById('p-status');

function flashStatus(msg, ok = true) {
  pStatus.textContent = msg;
  pStatus.style.color = ok ? '#10b981' : '#ef4444';
  setTimeout(() => { pStatus.textContent = ''; }, 2000);
}

async function loadPrompts() {
  try {
    const r = await fetch('/api/prompts');
    const d = await r.json();
    pDir.value = d.director_system || '';
    pDet.value = d.detail_system || '';
  } catch (e) {}
}

if (pSave) {
  pSave.addEventListener('click', async () => {
    pSave.disabled = true;
    try {
      const r = await fetch('/api/prompts', {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ director_system: pDir.value, detail_system: pDet.value }),
      });
      if (!r.ok) { flashStatus('ошибка сохранения', false); return; }
      flashStatus('сохранено ✓');
    } finally { pSave.disabled = false; }
  });
  pReset.addEventListener('click', async () => {
    if (!confirm('Сбросить промты к дефолту?')) return;
    const r = await fetch('/api/prompts/reset', { method: 'POST' });
    const d = await r.json();
    pDir.value = d.director_system; pDet.value = d.detail_system;
    flashStatus('сброшено');
  });
  loadPrompts();
}
