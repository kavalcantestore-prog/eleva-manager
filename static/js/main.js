/* ── Modals ─────────────────────────────────────────────────────────────── */
function openModal(id) {
  document.getElementById(id).classList.add('open');
  document.getElementById('modal-overlay').classList.add('open');
  document.body.style.overflow = 'hidden';
}

function closeModal() {
  document.querySelectorAll('.modal.open').forEach(m => m.classList.remove('open'));
  document.getElementById('modal-overlay').classList.remove('open');
  document.body.style.overflow = '';
}

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closeModal();
});

/* ── Mobile Sidebar ─────────────────────────────────────────────────────── */
function toggleSidebar() {
  const sidebar  = document.getElementById('sidebar');
  const overlay  = document.getElementById('sidebar-overlay');
  const hamburger = document.getElementById('hamburger');
  const isOpen   = sidebar.classList.contains('open');

  if (isOpen) {
    closeSidebar();
  } else {
    sidebar.classList.add('open');
    overlay.classList.add('open');
    hamburger.classList.add('open');
    document.body.style.overflow = 'hidden';
  }
}

function closeSidebar() {
  const sidebar   = document.getElementById('sidebar');
  const overlay   = document.getElementById('sidebar-overlay');
  const hamburger = document.getElementById('hamburger');
  if (!sidebar) return;
  sidebar.classList.remove('open');
  overlay.classList.remove('open');
  if (hamburger) hamburger.classList.remove('open');
  document.body.style.overflow = '';
}

/* Close sidebar on resize to desktop */
window.addEventListener('resize', () => {
  if (window.innerWidth > 768) closeSidebar();
});

/* ── Theme Toggle (Dark/Light) ──────────────────────────────────────────── */
function initTheme() {
  const savedTheme = localStorage.getItem('theme') || 'dark';
  const prefersLight = window.matchMedia('(prefers-color-scheme: light)').matches;
  const theme = savedTheme === 'light' || (savedTheme === 'auto' && prefersLight) ? 'light' : 'dark';

  applyTheme(theme);
}

function applyTheme(theme) {
  const root = document.documentElement;
  const icon = document.getElementById('theme-icon');

  if (theme === 'light') {
    root.setAttribute('data-theme', 'light');
    if (icon) icon.className = 'fa fa-moon';
    localStorage.setItem('theme', 'light');
  } else {
    root.removeAttribute('data-theme');
    if (icon) icon.className = 'fa fa-sun';
    localStorage.setItem('theme', 'dark');
  }
}

function toggleTheme() {
  const root = document.documentElement;
  const currentTheme = root.getAttribute('data-theme') || 'dark';
  const newTheme = currentTheme === 'light' ? 'dark' : 'light';
  applyTheme(newTheme);
}

// Inicializar tema ao carregar a página
document.addEventListener('DOMContentLoaded', initTheme);

// Se DOMContentLoaded já passou, inicializar imediatamente
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initTheme);
} else {
  initTheme();
}

/* ── Notifications ──────────────────────────────────────────────────────────── */
let notificationsOpen = false;

function toggleNotifications() {
  const panel = document.getElementById('notifications-panel');
  notificationsOpen = !notificationsOpen;

  if (notificationsOpen) {
    panel.classList.add('open');
    loadNotifications();
    // Close when clicking outside
    setTimeout(() => {
      document.addEventListener('click', closeNotificationsOnClickOutside);
    }, 100);
  } else {
    panel.classList.remove('open');
    document.removeEventListener('click', closeNotificationsOnClickOutside);
  }
}

function closeNotifications() {
  const panel = document.getElementById('notifications-panel');
  panel.classList.remove('open');
  notificationsOpen = false;
  document.removeEventListener('click', closeNotificationsOnClickOutside);
}

function closeNotificationsOnClickOutside(e) {
  const panel = document.getElementById('notifications-panel');
  const btn = document.getElementById('notifications-btn');
  if (!panel.contains(e.target) && !btn.contains(e.target)) {
    closeNotifications();
  }
}

function loadNotifications() {
  fetch('/api/notificacoes?limit=20')
    .then(r => r.json())
    .then(notifs => {
      const list = document.getElementById('notif-list');
      if (!notifs || notifs.length === 0) {
        list.innerHTML = '<div style="padding: 1rem; text-align: center; color: var(--muted);">Nenhuma notificação</div>';
        return;
      }
      list.innerHTML = notifs.map(n => `
        <div class="notif-item ${n.is_read ? 'read' : 'unread'}" onclick="markNotifRead(${n.id})">
          <div class="notif-icon ${n.type}">
            <i class="fa ${getNotifIcon(n.type)}"></i>
          </div>
          <div class="notif-content">
            <div class="notif-title">${n.title}</div>
            <div class="notif-message">${n.message}</div>
            <div class="notif-time">${formatTime(n.created_at)}</div>
          </div>
        </div>
      `).join('');
    });
}

function markNotifRead(nid) {
  fetch(`/api/notificacoes/${nid}/ler`, { method: 'POST' })
    .then(() => {
      loadNotifications();
      updateUnreadCount();
    });
}

function clearAllNotifications() {
  if (!confirm('Limpar todas as notificações?')) return;
  fetch('/api/notificacoes/limpar-tudo', { method: 'POST' })
    .then(() => {
      loadNotifications();
      updateUnreadCount();
    });
}

function updateUnreadCount() {
  fetch('/api/notificacoes/nao-lidas')
    .then(r => r.json())
    .then(d => {
      const badge = document.getElementById('notif-badge');
      if (d.count > 0) {
        badge.textContent = d.count;
        badge.style.display = 'block';
      } else {
        badge.style.display = 'none';
      }
    });
}

function getNotifIcon(type) {
  const icons = {
    'tarefa': 'fa-check-circle',
    'lead': 'fa-star',
    'proposta': 'fa-file-contract',
    'atividade': 'fa-clock',
    'info': 'fa-info-circle'
  };
  return icons[type] || 'fa-bell';
}

function formatTime(dt) {
  const d = new Date(dt);
  const now = new Date();
  const diff = (now - d) / 1000; // seconds

  if (diff < 60) return 'agora';
  if (diff < 3600) return Math.floor(diff / 60) + 'm atrás';
  if (diff < 86400) return Math.floor(diff / 3600) + 'h atrás';
  return Math.floor(diff / 86400) + 'd atrás';
}

// Check for new notifications every 30 seconds
setInterval(updateUnreadCount, 30000);

// Initial load
document.addEventListener('DOMContentLoaded', updateUnreadCount);
