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
