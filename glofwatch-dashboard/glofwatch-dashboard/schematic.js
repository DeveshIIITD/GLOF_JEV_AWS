(() => {
  'use strict';
  const paths = {
    layout:'<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
    map:'<polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21 3 6"/><path d="M9 3v15M15 6v15"/>',
    chart:'<path d="M3 3v18h18M7 16l4-5 3 3 6-8"/>',
    activity:'<path d="M3 12h4l3-8 4 16 3-8h4"/>',
    layers:'<path d="m12 2 9 5-9 5-9-5 9-5ZM3 12l9 5 9-5M3 17l9 5 9-5"/>',
    shield:'<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/><path d="m9 12 2 2 4-4"/>',
    menu:'<path d="M4 6h16M4 12h16M4 18h16"/>',
    info:'<circle cx="12" cy="12" r="10"/><path d="M12 11v6M12 7h.01"/>',
    'arrow-left':'<path d="M20 12H4m6-6-6 6 6 6"/>'
  };
  for (const el of document.querySelectorAll('[data-icon]')) {
    el.innerHTML = `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[el.dataset.icon] || paths.info}</svg>`;
  }
  document.getElementById('today-label').textContent = new Date().toLocaleDateString('en-IN', {day:'numeric',month:'short',year:'numeric'});
  const menu = document.getElementById('menu-button');
  const sidebar = document.getElementById('sidebar');
  menu.setAttribute('aria-expanded','false');
  menu.addEventListener('click', () => {
    const open = sidebar.classList.toggle('open');
    menu.setAttribute('aria-expanded', String(open));
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') { sidebar.classList.remove('open'); menu.setAttribute('aria-expanded','false'); }
  });
  const button = document.getElementById('animation-toggle');
  const images = [...document.querySelectorAll('img[data-motion]')];
  const preference = window.matchMedia('(prefers-reduced-motion: reduce)');
  let playing = !preference.matches;
  function updateAnimations() {
    for (const img of images) img.src = `./assets/schematic/${img.dataset.motion}.${playing ? 'gif' : 'png'}`;
    button.textContent = playing ? 'Pause GIFs' : 'Play GIFs';
    button.setAttribute('aria-pressed', String(!playing));
    button.setAttribute('aria-label', playing ? 'Pause schematic animations' : 'Play schematic animations');
  }
  button.addEventListener('click', () => { playing = !playing; updateAnimations(); });
  preference.addEventListener('change', event => { playing = !event.matches; updateAnimations(); });
  updateAnimations();
})();
