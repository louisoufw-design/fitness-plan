(() => {
  const store = window.__store = JSON.parse(sessionStorage.getItem('__seed') || '{}');
  window.__writes = 0;
  const listeners = [];
  const snap = (path) => { const d = store[path]; return { id: path.split('/').pop(), exists: !!d, data: () => d && JSON.parse(JSON.stringify(d)), metadata: { hasPendingWrites: false, fromCache: false } }; };
  const db = Object.freeze({
    doc: (path) => ({
      path,
      get: () => Promise.resolve(snap(path)),
      set: (data) => { window.__writes++; store[path] = JSON.parse(JSON.stringify(data)); setTimeout(() => listeners.filter(l => l.path === path).forEach(l => l.next(snap(path))), 0); return Promise.resolve(); },
      onSnapshot: (next) => { listeners.push({ path, next }); setTimeout(() => next(snap(path)), 0); return () => {}; }
    })
  });
  const user = Object.freeze({ id: () => Promise.resolve('u_test') });
  window.__remoteUpdate = (data) => { store['data/users/u_test/log'] = data; listeners.forEach(l => l.next(snap(l.path))); };
  const downloads = Object.freeze({ save: (req) => { window.__saved = req; return Promise.resolve({ status: 'saved' }); } });
  window.claude = { use: (n) => new Promise(r => setTimeout(() => r(n === 'db' ? db : n === 'user' ? user : n === 'downloads' ? downloads : null), 50)) };
})();
