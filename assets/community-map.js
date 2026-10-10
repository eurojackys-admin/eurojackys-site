(() => {
  const svg = document.getElementById('europe-map');
  const payload = document.getElementById('community-map-data');
  if (!svg || !payload) return;
  const countries = JSON.parse(payload.textContent);
  const layer = document.getElementById('map-markers');
  const detail = document.getElementById('map-selection');
  const popup = document.getElementById('map-popup');
  const cards = [...document.querySelectorAll('[data-select-country]')];
  const ns = 'http://www.w3.org/2000/svg';
  const lang = document.documentElement.lang === 'en' ? 'en' : 'fr';
  const base = svg.getAttribute('viewBox').split(' ').map(Number);
  const maxZoom = 16;
  let zoom = 1, selected = null;
  const view = () => svg.getAttribute('viewBox').split(' ').map(Number);
  const make = (type, attributes) => {
    const el = document.createElementNS(ns, type);
    Object.entries(attributes).forEach(([key, value]) => el.setAttribute(key, String(value)));
    return el;
  };
  const communityView = (() => {
    if (!countries.length) return {center: [base[2] / 2, base[3] / 2], zoom: 1};
    const xs = countries.map(c => c.xy[0]), ys = countries.map(c => c.xy[1]);
    const center = [(Math.min(...xs) + Math.max(...xs)) / 2, (Math.min(...ys) + Math.max(...ys)) / 2];
    const width = Math.max(Math.max(...xs) - Math.min(...xs) + 110, (Math.max(...ys) - Math.min(...ys) + 110) * base[2] / base[3]);
    return {center, zoom: Math.max(1, Math.min(maxZoom, base[2] / width))};
  })();
  function positionPopup() {
    if (!popup || popup.hidden || !selected) return;
    const [vx, vy, vw, vh] = view(), rect = svg.getBoundingClientRect();
    const left = (selected.xy[0] - vx) / vw * rect.width;
    const top = (selected.xy[1] - vy) / vh * rect.height;
    if (left < 0 || left > rect.width || top < 0 || top > rect.height) { popup.hidden = true; return; }
    popup.style.left = `${Math.max(96, Math.min(rect.width - 96, left))}px`;
    popup.style.top = `${Math.max(100, svg.offsetTop + top - 24)}px`;
  }
  function select(country) {
    selected = country;
    detail.replaceChildren();
    const heading = document.createElement('strong');
    heading.textContent = `${country.flag} ${country[lang]}`;
    const count = document.createElement('span');
    count.textContent = `${country.members} Jacky${country.members === 1 ? '' : 's'}`;
    detail.append(heading, count);
    if (popup) {
      popup.querySelector('.popup-country').textContent = country[lang];
      popup.querySelector('.popup-count').textContent = count.textContent;
      popup.hidden = false;
      positionPopup();
    }
    cards.forEach(card => {
      const active = card.dataset.selectCountry === country.code;
      card.classList.toggle('selected', active);
      card.setAttribute('aria-pressed', String(active));
    });
    svg.querySelectorAll('[data-map-country]').forEach(path => path.classList.toggle('selected', path.dataset.mapCountry === country.code));
    layer.querySelectorAll('[data-marker-codes]').forEach(marker => marker.classList.toggle('selected', marker.dataset.markerCodes === country.code));
  }
  function render() {
    const [vx, vy, vw, vh] = view(), rect = svg.getBoundingClientRect();
    const pixelsPerUnit = Math.min(rect.width / vw, rect.height / vh);
    if (!pixelsPerUnit) return;
    const visible = countries.filter(c => c.xy[0] >= vx && c.xy[0] <= vx + vw && c.xy[1] >= vy && c.xy[1] <= vy + vh);
    const focused = document.activeElement?.dataset.markerCodes;
    layer.replaceChildren();
    // Every flag stays at its own country's geographic label position.
    // Reduce its size in a wide view instead of combining or moving countries.
    for (const country of visible) {
      const nearest = visible.filter(c => c.code !== country.code).reduce((distance, c) => Math.min(distance, Math.hypot(c.xy[0] - country.xy[0], c.xy[1] - country.xy[1]) * pixelsPerUnit), Infinity);
      const flagWidth = Math.min(32, Math.max(8, nearest * 0.58));
      const flagHeight = flagWidth * 0.75, unit = 1 / pixelsPerUnit;
      const name = `${country[lang]} · ${country.members} Jacky${country.members === 1 ? '' : 's'}`;
      const marker = make('g', {class: 'map-marker' + (selected?.code === country.code ? ' selected' : ''), 'data-marker-codes': country.code, 'data-marker-members': country.members, role: 'button', tabindex: '0', 'aria-label': name, transform: `translate(${country.xy[0]} ${country.xy[1]})`});
      const title = make('title', {}); title.textContent = name;
      marker.append(title, make('rect', {class: 'flag-plate', x: -(flagWidth + 6) * unit / 2, y: -(flagHeight + 6) * unit / 2, width: (flagWidth + 6) * unit, height: (flagHeight + 6) * unit, rx: 3 * unit}), make('image', {href: country.flag_image, x: -flagWidth * unit / 2, y: -flagHeight * unit / 2, width: flagWidth * unit, height: flagHeight * unit}));
      marker.addEventListener('click', () => select(country));
      marker.addEventListener('keydown', event => {
        if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); select(country); }
      });
      layer.append(marker);
      if (focused === country.code) marker.focus();
    }
    positionPopup();
  }
  function setView(center, level) {
    zoom = Math.max(1, Math.min(maxZoom, level));
    const width = base[2] / zoom, height = base[3] / zoom;
    const cx = Math.max(width / 2, Math.min(base[2] - width / 2, center[0]));
    const cy = Math.max(height / 2, Math.min(base[3] - height / 2, center[1]));
    svg.setAttribute('viewBox', `${cx - width / 2} ${cy - height / 2} ${width} ${height}`);
    document.querySelector('[data-map-zoom="out"]').disabled = zoom === 1;
    document.querySelector('[data-map-zoom="in"]').disabled = zoom === maxZoom;
    render();
  }
  cards.forEach(card => card.addEventListener('click', () => {
    const country = countries.find(c => c.code === card.dataset.selectCountry);
    if (!country) return;
    const [x, y, w, h] = view();
    if (country.xy[0] < x || country.xy[0] > x + w || country.xy[1] < y || country.xy[1] > y + h) setView(country.xy, zoom);
    select(country);
  }));
  document.querySelectorAll('[data-map-zoom]').forEach(button => button.addEventListener('click', () => {
    const direction = button.dataset.mapZoom;
    if (direction === 'reset') return setView([base[2] / 2, base[3] / 2], 1);
    if (direction === 'community') return setView(communityView.center, communityView.zoom);
    const [x, y, w, h] = view();
    setView(selected ? selected.xy : [x + w / 2, y + h / 2], direction === 'in' ? zoom * 1.5 : zoom / 1.5);
  }));
  popup?.querySelector('button').addEventListener('click', () => { popup.hidden = true; });
  document.addEventListener('keydown', event => { if (event.key === 'Escape' && popup) popup.hidden = true; });
  new ResizeObserver(render).observe(svg);
  setView(communityView.center, communityView.zoom);
})();
