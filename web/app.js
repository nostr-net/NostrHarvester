const API_BASE = `${window.location.protocol}//${window.location.hostname}:8008/api/events`;

const inputEl = document.getElementById('searchInput');
const buttonEl = document.getElementById('searchButton');
const resultsEl = document.getElementById('results');

buttonEl.addEventListener('click', () => performSearch());
inputEl.addEventListener('keydown', (e) => { if (e.key === 'Enter') performSearch(); });

async function performSearch() {
  const query = inputEl.value.trim();
  const tokens = query ? query.split(/\s+/) : [];
  const params = new URLSearchParams();
  const freeText = [];

  for (const token of tokens) {
    const parts = token.split(':');
    if (parts.length >= 2) {
      const key = parts[0];
      const value = parts.slice(1).join(':');
      switch (key) {
        case 'pubkey':
        case 'relay':
        case 'kind':
        case 'since':
        case 'until':
        case 'limit':
        case 'offset':
          params.append(key, value);
          continue;
        case 'tag':
          params.append('tag', value);
          continue;
      }
    }
    freeText.push(token);
  }
  if (freeText.length) {
    params.append('q', freeText.join(' '));
  }

  const url = `${API_BASE}?${params.toString()}`;
  resultsEl.innerHTML = '<p>Loading...</p>';
  try {
    const resp = await fetch(url);
    const data = await resp.json();
    if (data.status === 'success') {
      const header = `<p>Found ${data.count} of ${data.total} events.</p>`;
      const body = `<pre>${JSON.stringify(data.events, null, 2)}</pre>`;
      resultsEl.innerHTML = header + body;
    } else {
      resultsEl.innerHTML = `<p>Error: ${data.message || data.detail}</p>`;
    }
  } catch (err) {
    resultsEl.innerHTML = `<p>Fetch error: ${err}</p>`;
  }
}