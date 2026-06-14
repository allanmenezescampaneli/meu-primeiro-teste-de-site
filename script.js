const contactForm = document.getElementById('contactForm');
const messageOutput = document.getElementById('formMessage');
const searchForm = document.getElementById('searchForm');
const resultsContainer = document.getElementById('results');

contactForm.addEventListener('submit', (event) => {
  event.preventDefault();
  const name = document.getElementById('name').value.trim();
  const email = document.getElementById('email').value.trim();
  const message = document.getElementById('message').value.trim();

  if (!name || !email || !message) {
    messageOutput.textContent = 'Preencha todos os campos antes de enviar.';
    messageOutput.style.color = '#b91c1c';
    return;
  }

  messageOutput.textContent = `Obrigado, ${name}! Sua mensagem foi recebida.`;
  messageOutput.style.color = '#166534';
  contactForm.reset();
});

searchForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const itemName = document.getElementById('itemName').value.trim();

  if (!itemName) {
    resultsContainer.innerHTML = '<p class="form-message" style="color: #b91c1c;">Digite o nome do item para buscar.</p>';
    return;
  }

  resultsContainer.innerHTML = '<p class="form-message" style="color: #2563eb;">Buscando preços em sites reais...</p>';

  try {
    // Detecta a URL da API automaticamente
    const apiUrl = window.location.hostname === 'localhost' 
      ? 'http://localhost:5000/api/search'
      : `${window.location.origin}/api/search`;
    
    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: itemName })
    });

    if (!response.ok) {
      throw new Error('Erro ao conectar ao servidor');
    }

    const data = await response.json();
    const searchResults = data.results;

    if (!searchResults || searchResults.length === 0) {
      resultsContainer.innerHTML = '<p class="form-message" style="color: #ea580c;">Nenhum resultado encontrado.</p>';
      return;
    }

    const cheapestPrice = Math.min(...searchResults.map(result => {
      const price = result.price.replace('R$ ', '').replace('.', '').replace(',', '.');
      return parseFloat(price) || Infinity;
    }));

    const cards = searchResults.map((result) => {
      const price = parseFloat(result.price.replace('R$ ', '').replace('.', '').replace(',', '.')) || Infinity;
      const isCheapest = price === cheapestPrice;

      return `
        <article class="result-card">
          <div class="result-header">
            <h3>${result.site}</h3>
            ${isCheapest ? '<span class="badge best">Mais barato</span>' : ''}
          </div>
          <p>Preço: <strong>${result.price}</strong></p>
          <p>Prazo: <strong>${result.delivery}</strong></p>
          <p><a class="link-button" href="${result.url}" target="_blank" rel="noopener noreferrer">Ver oferta</a></p>
        </article>
      `;
    }).join('');

    resultsContainer.innerHTML = `
      <div class="result-summary">
        <p>Resultados para <strong>${itemName}</strong> em sites reais.</p>
        <p class="small-note">Clique em "Ver oferta" para abrir o anúncio no site.</p>
      </div>
      <div class="cards results-grid">${cards}</div>
    `;
  } catch (error) {
    resultsContainer.innerHTML = `
      <p class="form-message" style="color: #b91c1c;">
        Erro ao buscar preços. Verifique se o servidor está rodando em localhost:5000
      </p>
      <p style="font-size: 0.9rem; color: #666;">
        Para usar o site, execute no terminal: <code>python site/server.py</code>
      </p>
    `;
    console.error('Erro:', error);
  }
});
