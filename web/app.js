const API_BASE = `${window.location.protocol}//${window.location.hostname}:${window.location.port}/api/events`;

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

async function performSearch() {
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