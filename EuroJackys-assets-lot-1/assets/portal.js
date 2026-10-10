(() => {
  const toggle = document.querySelector('.menu-toggle');
  const nav = document.getElementById('site-nav');
  if (toggle && nav) {
    const close = () => { nav.classList.remove('open'); toggle.setAttribute('aria-expanded', 'false'); };
    toggle.addEventListener('click', () => {
      const open = nav.classList.toggle('open');
      toggle.setAttribute('aria-expanded', String(open));
    });
    nav.addEventListener('click', event => { if (event.target.closest('a')) close(); });
    document.addEventListener('keydown', event => { if (event.key === 'Escape' && nav.classList.contains('open')) { close(); toggle.focus(); } });
    window.matchMedia('(min-width: 1051px)').addEventListener('change', close);
  }
  const lang = document.documentElement.lang === 'en' ? 'en' : 'fr';
  try { localStorage.setItem('ej-lang', lang); } catch (_) {}
  const query = document.getElementById('article-search');
  const category = document.getElementById('article-category');
  if (!query || !category) return;
  const cards = [...document.querySelectorAll('.article-listing .item')];
  const count = document.getElementById('result-count');
  const empty = document.getElementById('no-results');
  const normalize = text => text.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  const filter = () => {
    const words = normalize(query.value).trim().split(/\s+/).filter(Boolean);
    let visible = 0;
    cards.forEach(card => {
      const matches = words.every(word => normalize(card.textContent).includes(word)) && (!category.value || category.value === card.dataset.category);
      card.hidden = !matches;
      if (matches) visible++;
    });
    count.textContent = lang === 'fr' ? `${visible} article${visible > 1 ? 's' : ''}` : `${visible} article${visible !== 1 ? 's' : ''}`;
    empty.hidden = visible !== 0;
  };
  const params = new URLSearchParams(location.search);
  query.value = params.get('q') || '';
  const initialCategory = params.get('category');
  if ([...category.options].some(option => option.value === initialCategory)) category.value = initialCategory;
  query.addEventListener('input', filter);
  category.addEventListener('change', filter);
  filter();
})();
