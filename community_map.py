"""Generate the community map from the existing Carte des pays collection.

Every marker represents a country, never an individual's location. Natural
Earth paths are bundled locally so publishing needs no mapping service.
"""
import html
import json
import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))


def esc(value):
    return html.escape(str(value), quote=True)


def bi(fr, en):
    return '<span data-lang="fr">%s</span><span data-lang="en">%s</span>' % (esc(fr), esc(en))


def flag(code):
    return ''.join(chr(127397 + ord(c)) for c in code) if len(code) == 2 else ''


def country_code(row):
    code = row.get('country_code', '').upper()
    if code:
        return code
    # Backward compatibility with existing CMS entries using country flags.
    match = re.search(r'([\U0001f1e6-\U0001f1ff]{2})', row.get('country', ''))
    if match:
        return ''.join(chr(ord(c) - 127397) for c in match.group(1))
    return ''


def map_data(rows, geography):
    known = {item['code']: item for item in geography['countries']}
    grouped = {}
    for row in rows:
        code = country_code(row)
        # A missing/invalid count must not silently invent Jackys.
        raw = str(row.get('members', '')).strip()
        if not re.fullmatch(r'\d+', raw):
            raise ValueError('Nombre de Jackys invalide pour %s : utiliser un entier positif ou zéro.' % row.get('country', code))
        members = int(raw)
        if code not in known or not known[code]['selectable']:
            raise ValueError('Pays sur la carte invalide pour %s : sélectionner le pays dans l’administration.' % row.get('country', code))
        if not members:
            continue
        if code not in grouped:
            geo = known[code]
            # Keep the administrator's label; default translations come from Natural Earth.
            label = re.sub(r'[\U0001f1e6-\U0001f1ff]', '', row.get('country', '')).strip()
            grouped[code] = {'code': code, 'members': 0, 'fr': label or geo['fr'],
                             'en': row.get('country_en') or geo['en'], 'flag': flag(code),
                             'xy': geo['xy'], 'flag_image': '/assets/flags/%s.svg' % code.lower()}
        grouped[code]['members'] += members
    return list(grouped.values())


def render_community_map(rows):
    with open(os.path.join(ROOT, 'assets/world-geography.json'), encoding='utf-8') as file:
        geography = json.load(file)
    countries = map_data(rows, geography)
    total = sum(item['members'] for item in countries)
    active = {item['code'] for item in countries}
    paths = ''.join('<path d="%s" data-map-country="%s" class="map-land%s"/>' %
                    (esc(item['path']), esc(item['code']), ' represented' if item['code'] in active else '')
                    for item in geography['countries'])
    cards = []
    markers = []
    for item in countries:
        label = '%s · %s Jackys' % (item['fr'], item['members'])
        cards.append('<button class="country-card" data-select-country="%s" aria-pressed="false">'
                     '<span class="country-flag" aria-hidden="true">%s</span><span class="country-name">%s</span>'
                     '<span class="country-count">%s <small>Jacky%s</small></span></button>' %
                     (esc(item['code']), '<img src="%s" alt="" width="32" height="24">' % esc(item['flag_image']), bi(item['fr'], item['en']), item['members'], 's' if item['members'] != 1 else ''))
        markers.append('<g class="map-marker" data-marker-codes="%s" role="button" tabindex="0" '
                       'aria-label="%s" transform="translate(%s %s)"><title>%s</title>'
                       '<rect class="flag-plate" x="-24" y="-20" width="48" height="40" rx="5"/>'
                       '<image href="%s" x="-18" y="-13.5" width="36" height="27"/></g>' %
                       (esc(item['code']), esc(label), *item['xy'], esc(label), esc(item['flag_image'])))
    payload = json.dumps(countries, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
    stats = ('<div class="community-stats"><div><strong>%s</strong><span>Jacky%s</span></div><div><strong>%s</strong><span>%s</span></div></div>' %
             (total, 's' if total != 1 else '', len(countries), bi('pays représentés', 'countries represented')))
    result = stats + '<div class="community-map-layout"><div class="map-panel">'
    result += '<div class="map-toolbar"><span>%s</span><div><button data-map-zoom="out" aria-label="Dézoomer / Zoom out">−</button>' % bi('Les Jackys dans le monde', 'Jackys around the world')
    result += '<button data-map-zoom="in" aria-label="Zoomer / Zoom in">+</button><button data-map-zoom="reset">%s</button><button data-map-zoom="community">%s</button></div></div>' % (bi('Monde entier', 'Whole world'), bi('Nos pays', 'Our countries'))
    result += '<svg class="europe-map" id="europe-map" viewBox="0 0 %s %s" role="group" aria-labelledby="europe-map-title europe-map-desc">' % (geography['width'], geography['height'])
    result += '<title id="europe-map-title">EuroJackys — Monde / World</title><desc id="europe-map-desc">%s</desc>' % esc('Pays représentés dans la communauté, partout dans le monde. Un drapeau placé sur chaque pays. Sélectionnez un drapeau pour voir ses Jackys. / Countries represented in the community, around the world. One flag placed on each country. Select a flag to see its Jackys.')
    result += paths + '<g id="map-markers">' + ''.join(markers) + '</g></svg>'
    result += '<div class="map-popup" id="map-popup" hidden><button aria-label="Fermer / Close">×</button><strong class="popup-country"></strong><span class="popup-count"></span></div>'
    result += '<div class="map-legend"><span class="legend-dot"></span>%s</div>' % bi('Pays où la communauté est présente', 'Countries represented in the community')
    result += '<p class="map-hint">%s</p></div>' % bi('Chaque drapeau correspond à son pays : appuie dessus pour voir ses Jackys. Dézoome avec − ou choisis « Monde entier ». Zoome pour mieux voir les pays proches.', 'Each flag belongs to its country: select it to see its Jackys. Zoom out with − or choose “Whole world”. Zoom in to see nearby countries more clearly.')
    result += '<div class="country-panel"><h2>%s</h2><div id="map-selection" class="map-selection" role="status" aria-live="polite">%s</div><div class="country-list">%s</div></div></div>' % (bi('Nos pays', 'Our countries'), bi('Une même passion, au-delà des frontières.', 'One shared passion, across borders.'), ''.join(cards))
    if not countries:
        result += '<p class="no-results">%s</p>' % bi('Les premiers pays apparaîtront ici après publication.', 'The first countries will appear here after publication.')
    result += '<script type="application/json" id="community-map-data">%s</script>' % payload
    return result, total, len(countries)
