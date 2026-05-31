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
