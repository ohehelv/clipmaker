// Вспомогательные функции авторизации

export async function getMe() {
  try {
    const r = await fetch('/api/auth/me');
    if (!r.ok) return null;
    return await r.json();
  } catch {
    return null;
  }
}

export async function requireAuth() {
  const me = await getMe();
  if (!me) {
    window.location.href = '/login';
    return null;
  }
  return me;
}

export async function logout() {
  await fetch('/api/auth/logout', { method: 'POST' });
  window.location.href = '/login';
}

// Рендерит хедер: email, настройки, кнопка выхода.
export function renderHeader(me) {
  const header = document.querySelector('header');
  if (!header || !me) return;
  const div = document.createElement('div');
  div.className = 'header-user';
  div.innerHTML = `
    <span class="user-email">${escHtml(me.email)}${me.is_admin ? ' <span class="badge-admin">admin</span>' : ''}</span>
    <a href="/settings" class="ghost-link">⚙ Настройки</a>
    <button id="logout-btn" class="ghost">Выйти</button>
  `;
  header.appendChild(div);
  document.getElementById('logout-btn').addEventListener('click', logout);
}

function escHtml(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
