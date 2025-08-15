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

// Configure marked for safe markdown rendering
if (typeof marked !== 'undefined') {
  marked.setOptions({
    breaks: true,
    gfm: true,
    sanitize: false, // We'll do our own sanitization
    smartLists: true,
    smartypants: true
  });
}

// Render markdown content safely
function renderMarkdown(content) {
  if (!content || typeof marked === 'undefined') {
    return escapeHtml(content || '');
  }
  
  try {
    // Basic sanitization - remove potentially dangerous elements
    const sanitized = content
      .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
      .replace(/<iframe\b[^<]*(?:(?!<\/iframe>)<[^<]*)*<\/iframe>/gi, '')
      .replace(/<object\b[^<]*(?:(?!<\/object>)<[^<]*)*<\/object>/gi, '')
      .replace(/<embed\b[^<]*(?:(?!<\/embed>)<[^<]*)*<\/embed>/gi, '');
    
    return marked.parse(sanitized);
  } catch (e) {
    console.warn('Markdown parsing failed:', e);
    return escapeHtml(content);
  }
}

// HTML escape function
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Parse kind 6 repost content
function parseRepost(event) {
  try {
    // Try to parse the content as JSON (original event)
    const originalEvent = JSON.parse(event.content);
    if (originalEvent && originalEvent.id && originalEvent.content !== undefined) {
      return originalEvent;
    }
  } catch (e) {
    // If parsing fails, look for event reference in tags
    const eTags = event.raw_data?.tags?.filter(tag => tag[0] === 'e') || [];
    if (eTags.length > 0) {
      // Return a placeholder for the referenced event
      return {
        id: eTags[0][1],
        content: event.content || '(Original event not embedded)',
        kind: 1, // Assume kind 1
        pubkey: event.raw_data?.tags?.find(tag => tag[0] === 'p')?.[1] || 'unknown',
        created_at: event.created_at
      };
    }
  }
  
  // Fallback - treat as regular event
  return null;
}

// Get user-friendly display for pubkey
function formatPubkey(pubkey) {
  if (!pubkey || pubkey === 'unknown') return 'unknown user';
  return pubkey.slice(0, 8) + '...' + pubkey.slice(-8);
}

// Render event details (used for both regular events and original events in reposts)
function renderEventDetails(container, ev, isOriginal = false) {
  if (!isOriginal) {
    // Event ID
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
    container.appendChild(idP);
  }

  // Pubkey
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
  container.appendChild(pkP);

  // Kind (only show if not original event in repost, or if not kind 1)
  if (!isOriginal || ev.kind !== 1) {
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
    container.appendChild(kindP);
  }

  // Content with markdown rendering
  if (ev.content) {
    const contentDiv = document.createElement('div');
    contentDiv.className = 'event-content';
    contentDiv.innerHTML = renderMarkdown(ev.content);
    container.appendChild(contentDiv);
  }
}

// Add event metadata (tags, relays, etc.)
function addEventMetadata(container, ev) {
  // Tags
  if (ev.raw_data?.tags && ev.raw_data.tags.length) {
    const tagsP = document.createElement('p');
    tagsP.innerHTML = '<strong>tags:</strong> ';
    const tagsSpan = document.createElement('span');
    tagsSpan.textContent = ev.raw_data.tags.map(t => t.join(':')).join(', ');
    tagsP.appendChild(tagsSpan);
    container.appendChild(tagsP);
  }

  // Relays
  if (ev.relays && ev.relays.length) {
    const relaysP = document.createElement('p');
    relaysP.innerHTML = '<strong>relays:</strong> ';
    const relaysSpan = document.createElement('span');
    relaysSpan.textContent = ev.relays.join(', ');
    relaysP.appendChild(relaysSpan);
    container.appendChild(relaysP);
  }

  // Copy JSON button
  const copyJsonBtn = document.createElement('button');
  copyJsonBtn.textContent = 'Copy event json';
  copyJsonBtn.className = 'copy-json-btn';
  copyJsonBtn.addEventListener('click', () => {
    const jsonString = JSON.stringify(ev, null, 2);
    navigator.clipboard.writeText(jsonString);
  });
  container.appendChild(copyJsonBtn);
}

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
        evDiv.className = `event${ev.kind === 6 ? ' kind-6' : ''}`;

        // Handle kind 6 reposts specially
        if (ev.kind === 6) {
          const originalEvent = parseRepost(ev);
          if (originalEvent) {
            // Repost header
            const repostHeader = document.createElement('div');
            repostHeader.className = 'repost-header';
            repostHeader.innerHTML = `🔄 Repost by ${formatPubkey(ev.pubkey)}`;
            evDiv.appendChild(repostHeader);

            // Original event container
            const originalDiv = document.createElement('div');
            originalDiv.className = 'original-event';
            
            renderEventDetails(originalDiv, originalEvent, true);
            evDiv.appendChild(originalDiv);

            // Add repost metadata
            addEventMetadata(evDiv, ev);
          } else {
            // Fallback to regular display if can't parse repost
            renderEventDetails(evDiv, ev, false);
            addEventMetadata(evDiv, ev);
          }
        } else {
          // Regular event display
          renderEventDetails(evDiv, ev, false);
          addEventMetadata(evDiv, ev);
        }

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