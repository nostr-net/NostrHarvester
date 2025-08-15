const API_BASE = '/api/events';

const inputEl = document.getElementById('searchInput');
const buttonEl = document.getElementById('searchButton');
const resultsEl = document.getElementById('results');

buttonEl.addEventListener('click', () => performSearch());
inputEl.addEventListener('keydown', (e) => { if (e.key === 'Enter') performSearch(); });

const exampleEls = document.querySelectorAll('.example');
exampleEls.forEach(el => {
  el.addEventListener('click', (e) => {
    e.preventDefault();
    inputEl.value = el.textContent;
    performSearch();
  });
});

// Handle browser back/forward navigation
window.addEventListener('popstate', () => {
  loadFromURL();
});

// Load search from URL parameters on page load
document.addEventListener('DOMContentLoaded', () => {
  loadFromURL();
});

// Convert URL parameters to search query string
function urlParamsToQuery(params) {
  const tokens = [];
  
  for (const [key, value] of params.entries()) {
    if (key.startsWith('not-')) {
      const baseKey = key.slice(4);
      if (['pubkey', 'relay', 'kind', 'since', 'until', 'limit', 'offset'].includes(baseKey)) {
        tokens.push(`-${baseKey}:${value}`);
      } else if (baseKey === 'tag') {
        tokens.push(`-tag:${value}`);
      } else if (baseKey === 'q') {
        tokens.push(value.includes(' ') ? `-"${value}"` : `-${value}`);
      }
    } else if (['pubkey', 'relay', 'kind', 'since', 'until', 'limit', 'offset'].includes(key)) {
      tokens.push(`${key}:${value}`);
    } else if (key === 'tag') {
      tokens.push(`tag:${value}`);
    } else if (key === 'q') {
      tokens.push(value.includes(' ') ? `"${value}"` : value);
    } else if (key === 'not-q') {
      tokens.push(value.includes(' ') ? `-"${value}"` : `-${value}`);
    }
  }
  
  return tokens.join(' ');
}

// Load search parameters from URL and execute search
function loadFromURL() {
  const urlParams = new URLSearchParams(window.location.search);
  
  if (urlParams.toString()) {
    // Convert URL parameters back to search query
    const query = urlParamsToQuery(urlParams);
    inputEl.value = query;
    
    // Perform search without updating URL (to avoid infinite loop)
    performSearchInternal(false);
  }
}

// Update URL with current search parameters
function updateURL(params) {
  const url = new URL(window.location);
  url.search = params.toString();
  window.history.pushState({}, '', url);
}

async function performSearch() {
  await performSearchInternal(true);
}

async function performSearchInternal(updateUrl = true) {
  const query = inputEl.value.trim();
  // Tokenize on whitespace, keeping quoted phrases together and handling negation
  const tokens = query
    ? query.match(/(?:-?"[^"]+"|-?\S+)/g) || []
    : [];
  const params = new URLSearchParams();
  const freeText = [];

  for (let token of tokens) {
    let neg = false;
    if (token.startsWith('-')) {
      neg = true;
      token = token.slice(1);
    }
    // Strip surrounding quotes
    if ((token.startsWith('"') && token.endsWith('"')) ||
        (token.startsWith("'") && token.endsWith("'"))) {
      token = token.slice(1, -1);
    }
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
          params.append(neg ? `not-${key}` : key, value);
          continue;
        case 'tag':
          params.append(neg ? 'not-tag' : 'tag', value);
          continue;
      }
    }
    // Free-text term
    if (neg) {
      params.append('not-q', token);
    } else {
      freeText.push(token);
    }
  }
  if (freeText.length) {
    params.append('q', freeText.join(' '));
  }

  const url = `${API_BASE}?${params.toString()}`;
  
  // Update URL with search parameters (only when not loading from URL)
  if (updateUrl) {
    updateURL(params);
  }
  
  resultsEl.innerHTML = '<p>Loading...</p>';
  try {
    const resp = await fetch(url);
    const data = await resp.json();
    if (data.status === 'success') {
      const summaryP = document.createElement('p');
      summaryP.textContent = `Found ${data.count} of ${data.total} events.`;
      resultsEl.innerHTML = '';
      resultsEl.appendChild(summaryP);
      data.events.forEach(ev => {
        const evDiv = document.createElement('div');
        evDiv.className = 'event';

        const idP = document.createElement('p');
        idP.innerHTML = '<strong>id:</strong> ';
        const idSpan = document.createElement('span');
        idSpan.className = 'ev-id';
        idSpan.textContent = ev.id;
        idP.appendChild(idSpan);
        const idBtn = document.createElement('button');
        idBtn.textContent = 'Copy';
        idBtn.className = 'copy-btn';
        idBtn.addEventListener('click', () => navigator.clipboard.writeText(ev.id));
        idP.appendChild(idBtn);
        evDiv.appendChild(idP);

        const pkP = document.createElement('p');
        pkP.innerHTML = '<strong>pubkey:</strong> ';
        const pkSpan = document.createElement('span');
        pkSpan.className = 'ev-pubkey';
        pkSpan.textContent = ev.pubkey;
        pkP.appendChild(pkSpan);
        const pkBtn = document.createElement('button');
        pkBtn.textContent = 'Copy';
        pkBtn.className = 'copy-btn';
        pkBtn.addEventListener('click', () => navigator.clipboard.writeText(ev.pubkey));
        pkP.appendChild(pkBtn);
        evDiv.appendChild(pkP);

        const kindP = document.createElement('p');
        kindP.innerHTML = '<strong>kind:</strong> ';
        const kindSpan = document.createElement('span');
        kindSpan.textContent = ev.kind;
        kindP.appendChild(kindSpan);
        const kindBtn = document.createElement('button');
        kindBtn.textContent = 'Copy';
        kindBtn.className = 'copy-btn';
        kindBtn.addEventListener('click', () => navigator.clipboard.writeText(ev.kind));
        kindP.appendChild(kindBtn);
        evDiv.appendChild(kindP);

        const contentP = document.createElement('p');
        contentP.innerHTML = '<strong>content:</strong> ';
        const contentSpan = document.createElement('span');
        contentSpan.textContent = ev.content;
        contentP.appendChild(contentSpan);
        evDiv.appendChild(contentP);

        if (ev.tags && ev.tags.length) {
          const tagsP = document.createElement('p');
          tagsP.innerHTML = '<strong>tags:</strong> ';
          const tagsSpan = document.createElement('span');
          tagsSpan.textContent = ev.tags.map(t => t.join(':')).join(', ');
          tagsP.appendChild(tagsSpan);
          evDiv.appendChild(tagsP);
        }

        if (ev.relays && ev.relays.length) {
          const relaysP = document.createElement('p');
          relaysP.innerHTML = '<strong>relays:</strong> ';
          const relaysSpan = document.createElement('span');
          relaysSpan.textContent = ev.relays.join(', ');
          relaysP.appendChild(relaysSpan);
          evDiv.appendChild(relaysP);
        }

        // Add Copy JSON button at the bottom
        const copyJsonBtn = document.createElement('button');
        copyJsonBtn.textContent = 'Copy event json';
        copyJsonBtn.className = 'copy-json-btn';
        copyJsonBtn.addEventListener('click', () => {
          const jsonString = JSON.stringify(ev, null, 2);
          navigator.clipboard.writeText(jsonString);
        });
        evDiv.appendChild(copyJsonBtn);

        resultsEl.appendChild(evDiv);
      });
    } else {
      const errP = document.createElement('p');
      errP.textContent = `Error: ${data.message || data.detail}`;
      resultsEl.innerHTML = '';
      resultsEl.appendChild(errP);
    }
  } catch (err) {
    const errP = document.createElement('p');
    errP.textContent = `Fetch error: ${err}`;
    resultsEl.innerHTML = '';
    resultsEl.appendChild(errP);
  }
}