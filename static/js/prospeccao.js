// Prospection System - Google Maps + WhatsApp + AI

let map;
let markers = [];
let prospects = [];
let selectedProspect = null;
let selectedMessage = null;

const SEGMENTS = {
  "Restaurantes": "🍕",
  "Barbearias": "💈",
  "Clínicas": "🏥",
  "Academias": "💪",
  "Imobiliárias": "🏠",
  "Lojas": "🛍️",
  "Serviços": "🔧"
};

// Initialize Google Map
function initMap() {
  const mapOptions = {
    zoom: 13,
    center: { lat: -23.5505, lng: -46.6333 }, // São Paulo default
    styles: [
      { elementType: "geometry", stylers: [{ color: "#0a0a0a" }] },
      { elementType: "labels.text.stroke", stylers: [{ color: "#0a0a0a" }] },
      { elementType: "labels.text.fill", stylers: [{ color: "#f0f0f0" }] }
    ]
  };

  map = new google.maps.Map(document.getElementById('map'), mapOptions);

  // Auto-complete para localização
  const locationInput = document.getElementById('location-filter');
  const autocomplete = new google.maps.places.Autocomplete(locationInput);

  autocomplete.addListener('place_changed', () => {
    const place = autocomplete.getPlace();
    if (place.geometry) {
      map.setCenter(place.geometry.location);
      map.setZoom(14);
    }
  });

  // Radius slider update
  document.getElementById('radius-slider').addEventListener('input', (e) => {
    document.getElementById('radius-value').textContent = e.target.value;
  });
}

// Search for prospects using Google Maps Places API
async function buscarProspects() {
  const segment = document.getElementById('segment-filter').value;
  const location = document.getElementById('location-filter').value;
  const radius = parseInt(document.getElementById('radius-slider').value);

  if (!segment || !location) {
    alert('Por favor, selecione segmento e localização');
    return;
  }

  try {
    // Buscar coordenadas da localização
    const geocoder = new google.maps.Geocoder();
    geocoder.geocode({ address: location }, async (results, status) => {
      if (status === 'OK') {
        const center = results[0].geometry.location;
        map.setCenter(center);
        map.setZoom(14);

        // Buscar prospects via API
        const response = await fetch('/prospeccao/buscar', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            segment: segment,
            location: location,
            center: { lat: center.lat(), lng: center.lng() },
            radius_km: radius
          })
        });

        const data = await response.json();

        if (data.success) {
          exibirProspects(data.prospects, center);
          document.getElementById('total-found').textContent = data.prospects.length;
        } else {
          alert('Erro ao buscar: ' + data.error);
        }
      }
    });
  } catch (error) {
    console.error('Erro:', error);
    alert('Erro ao buscar prospects');
  }
}

// Display prospects on map and in list
function exibirProspects(prospectList, center) {
  // Limpar markers antigos
  markers.forEach(marker => marker.setMap(null));
  markers = [];
  prospects = prospectList;

  // Adicionar novos markers
  prospectList.forEach((prospect, index) => {
    const marker = new google.maps.Marker({
      position: { lat: prospect.latitude, lng: prospect.longitude },
      map: map,
      title: prospect.name,
      icon: getMarkerIcon(prospect.status)
    });

    marker.addListener('click', () => {
      selectedProspect = prospect;
      exibirDetalhesProspect(prospect);
    });

    markers.push(marker);
  });

  // Atualizar lista
  const list = document.getElementById('prospects-list');
  list.innerHTML = prospectList.map(p => `
    <div class="prospect-item" onclick="selecionarProspect('${p.id}')">
      <strong>${p.name}</strong>
      <small>${p.company} • ${p.segment}</small>
      <small>${p.phone || 'Sem telefone'}</small>
      <div class="prospect-actions">
        <button class="btn btn-sm btn-primary" onclick="abrirModalMensagem(event, '${p.id}')">
          <i class="fa fa-sparkles"></i> Mensagem
        </button>
        <button class="btn btn-sm btn-ghost" onclick="salvarProspect(event, '${p.id}')">
          <i class="fa fa-save"></i> Salvar
        </button>
      </div>
    </div>
  `).join('');
}

// Get marker icon based on status
function getMarkerIcon(status) {
  const colors = {
    'novo': '4A90E2',
    'enviado': 'F5A623',
    'convertido': '7ED321'
  };
  return `http://maps.google.com/mapfiles/ms/mcon/${colors[status] || '999999'}/`;
}

// Select prospect from list
function selecionarProspect(prospectId) {
  selectedProspect = prospects.find(p => p.id === prospectId);
  if (selectedProspect) {
    map.panTo({ lat: selectedProspect.latitude, lng: selectedProspect.longitude });
  }
}

// Display prospect details
function exibirDetalhesProspect(prospect) {
  console.log('Detalhes:', prospect);
  // UI Update pode ser feito aqui
}

// Open message generation modal
function abrirModalMensagem(event, prospectId) {
  event.stopPropagation();
  selectedProspect = prospects.find(p => p.id === prospectId);

  if (selectedProspect) {
    document.getElementById('prospect-name-modal').textContent = selectedProspect.name;
    document.getElementById('prospect-company-modal').textContent = selectedProspect.company;
    document.getElementById('prompt-adicional').value = '';

    gerarMensagens(selectedProspect);
    openModal('modal-gerar-mensagem');
  }
}

// Generate messages using AI
async function gerarMensagens(prospect) {
  const container = document.getElementById('messages-options');
  container.innerHTML = '<p class="loading">Gerando mensagens com IA...</p>';

  try {
    const response = await fetch('/prospeccao/gerar-mensagem', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prospect_id: prospect.id,
        company: prospect.company,
        segment: prospect.segment,
        location: prospect.location,
        prompt_custom: document.getElementById('prompt-adicional').value
      })
    });

    const data = await response.json();

    if (data.success) {
      container.innerHTML = data.messages.map((msg, idx) => `
        <div class="message-option" onclick="selecionarMensagem(this, '${msg}')">
          <small>#${idx + 1}</small><br/>
          ${msg}
        </div>
      `).join('');
    } else {
      container.innerHTML = '<p class="error">Erro ao gerar mensagens</p>';
    }
  } catch (error) {
    console.error('Erro:', error);
    container.innerHTML = '<p class="error">Erro ao gerar mensagens</p>';
  }
}

// Select a message
function selecionarMensagem(element, message) {
  document.querySelectorAll('.message-option').forEach(m => m.classList.remove('selected'));
  element.classList.add('selected');
  selectedMessage = message;
}

// Send via WhatsApp
function enviarWhatsApp() {
  if (!selectedMessage) {
    alert('Selecione uma mensagem primeiro');
    return;
  }

  if (!selectedProspect || !selectedProspect.whatsapp) {
    alert('Prospect sem número de WhatsApp');
    return;
  }

  // Exibir QR Code
  const qrContainer = document.getElementById('qr-code');
  qrContainer.innerHTML = '';

  new QRCode(qrContainer, {
    text: `https://wa.me/${selectedProspect.whatsapp}?text=${encodeURIComponent(selectedMessage)}`,
    width: 200,
    height: 200
  });

  document.getElementById('message-display').innerHTML = `
    <strong>Para:</strong> ${selectedProspect.name} (${selectedProspect.whatsapp})<br/><br/>
    <strong>Mensagem:</strong><br/>
    <em>${selectedMessage}</em>
  `;

  closeModal('modal-gerar-mensagem');
  openModal('modal-whatsapp-qr');
}

// Copy message to clipboard
function copiarMensagem() {
  if (selectedMessage) {
    navigator.clipboard.writeText(selectedMessage).then(() => {
      alert('Mensagem copiada! Cole no WhatsApp');
    });
  }
}

// Save prospect to database
async function salvarProspect(event, prospectId) {
  event.stopPropagation();

  try {
    const response = await fetch('/prospeccao/importar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prospect_id: prospectId })
    });

    const data = await response.json();
    if (data.success) {
      alert('Prospect salvo!');
      document.getElementById('total-saved').textContent =
        parseInt(document.getElementById('total-saved').textContent) + 1;
    }
  } catch (error) {
    console.error('Erro:', error);
  }
}

// Create new campaign
async function criarCampanha(event) {
  event.preventDefault();

  const data = {
    name: document.getElementById('campaign-name').value,
    segment: document.getElementById('campaign-segment').value,
    location: document.getElementById('campaign-location').value,
    template: document.getElementById('campaign-template').value
  };

  try {
    const response = await fetch('/prospeccao/campanhas/nova', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });

    const result = await response.json();
    if (result.success) {
      alert('Campanha criada!');
      closeModal('modal-nova-campanha');
      // Reset form
      event.target.reset();
    }
  } catch (error) {
    console.error('Erro:', error);
  }
}

// Initialize on page load
window.addEventListener('load', initMap);
