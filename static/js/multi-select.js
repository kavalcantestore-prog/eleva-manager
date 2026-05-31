// Multi-Select Services Component
const SERVICES = [
  "Tráfego Pago",
  "Gestão de Site",
  "Landing Page",
  "Automação",
  "IA",
  "Branding",
  "Social Media",
  "Consultoria",
  "E-commerce",
  "SEO",
  "Email Marketing",
  "CRM"
];

function initServicesSelector(containerId, hiddenInputId, initialValues = []) {
  const container = document.getElementById(containerId);
  if (!container) return;

  const hiddenInput = document.getElementById(hiddenInputId);
  let selected = initialValues.length > 0 ? initialValues : [];

  container.innerHTML = SERVICES.map(service => `
    <label class="service-chip ${selected.includes(service) ? 'selected' : ''}">
      <input type="checkbox" value="${service}" ${selected.includes(service) ? 'checked' : ''} />
      ${service}
    </label>
  `).join('');

  // Add click handlers
  container.querySelectorAll('.service-chip').forEach(chip => {
    chip.addEventListener('click', function(e) {
      if (e.target.tagName !== 'INPUT') {
        e.preventDefault();
        const input = this.querySelector('input');
        input.checked = !input.checked;
      }
      updateSelection();
    });

    const input = chip.querySelector('input');
    input.addEventListener('change', updateSelection);
  });

  function updateSelection() {
    const checked = Array.from(container.querySelectorAll('input:checked')).map(i => i.value);
    selected = checked;

    // Update hidden input with JSON
    hiddenInput.value = JSON.stringify(checked);

    // Update visual state
    container.querySelectorAll('.service-chip').forEach((chip, idx) => {
      const input = chip.querySelector('input');
      chip.classList.toggle('selected', input.checked);
    });
  }
}

// Display selected services as chips
function displayServices(services) {
  if (!services || services.length === 0) return '';

  const servicesList = typeof services === 'string' ? JSON.parse(services) : services;
  return servicesList.map(s => `<span class="service-badge">${s}</span>`).join('');
}
