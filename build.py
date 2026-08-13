#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EuroJackys — generateur de pages statiques SEO.
Lance automatiquement par Netlify a chaque deploiement (voir netlify.toml).

Ce script :
  1. lit les articles (articles/*.md) publies via l'admin Decap CMS ;
  2. genere une vraie page HTML par article, en FR (/fr/articles/<slug>/)
     et en EN (/en/articles/<slug>/), avec canonical, hreflang, Open Graph
     et donnees structurees Article + BreadcrumbList ;
  3. genere les pages listes /fr/articles/ et /en/articles/ ;
  4. genere sitemap.xml ;
  5. insere le contenu du CMS (articles, calendrier, projets, galerie,
     carte, textes "A propos") directement dans index.html entre les
     marqueurs <!-- BUILD:xxx --> pour que Google voie tout sans JavaScript.

Aucune dependance externe : Python 3.6+ standard uniquement.
"""

import os
import re
import html
import json
import sys
from datetime import date

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = "https://eurojackys.com"
TODAY = date.today().isoformat()

OG_IMAGE = SITE + "/images/brand/og-image.jpg"
LOGO_512 = SITE + "/images/brand/icon-512.png"

SOCIALS = [
    ("Instagram", "https://instagram.com/eurojackys"),
    ("TikTok", "https://tiktok.com/@eurojackys"),
    ("Facebook", "https://www.facebook.com/share/14k1TZ9hEmq/"),
    ("Threads", "https://threads.net/@eurojackys"),
    ("X", "https://x.com/eurojackys"),
    ("YouTube", "https://www.youtube.com/@eurojackys"),
]

ORG_DESCRIPTION = ("Independent European fanbase for Jackson Wang. Verified news, "
                   "French-English translations, fan projects and community events "
                   "for Jackys across Europe.")

MONTHS_FR = ["janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet",
             "aout", "septembre", "octobre", "novembre", "decembre"]
MONTHS_FR = ["janvier", "f\u00e9vrier", "mars", "avril", "mai", "juin", "juillet",
             "ao\u00fbt", "septembre", "octobre", "novembre", "d\u00e9cembre"]
MONTHS_EN = ["January", "February", "March", "April", "May", "June", "July",
             "August", "September", "October", "November", "December"]


# ---------------------------------------------------------------- parsing ---

def parse_yaml(block):
    """Flat YAML parser handling block scalars (| >) and folded continuation
    lines, matching what Decap CMS writes."""
    data = {}
    lines = block.split("\n")
    i = 0
    last_key = None
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.strip().startswith("#"):
            i += 1
            continue
        m = re.match(r"^([A-Za-z0-9_\-]+):\s*(.*)$", line)
        if m:
            key, value = m.group(1), m.group(2).strip()
            if value in ("|", ">", "|-", ">-"):
                buf = []
                i += 1
                while i < len(lines) and (lines[i].startswith("  ") or not lines[i].strip()):
                    buf.append(lines[i][2:] if lines[i].startswith("  ") else "")
                    i += 1
                data[key] = "\n".join(buf).strip("\n")
                last_key = None
                continue
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                value = value[1:-1]
            data[key] = value
            last_key = key
            i += 1
        elif line.startswith("  ") and last_key:
            # continuation of a plain scalar written on several lines
            data[last_key] = (data[last_key] + " " + line.strip()).strip()
            i += 1
        else:
            i += 1
    return data


def parse_front_matter(raw):
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", raw, re.S)
    if not m:
        return {}, raw.strip()
    return parse_yaml(m.group(1)), m.group(2).strip()


def load_folder(folder):
    """Returns a list of dicts for every .yml/.md file of a content folder."""
    path = os.path.join(ROOT, folder)
    items = []
    if not os.path.isdir(path):
        return items
    for name in sorted(os.listdir(path)):
        if not (name.endswith(".yml") or name.endswith(".md")):
            continue
        try:
            with open(os.path.join(path, name), "r", encoding="utf-8") as f:
                raw = f.read()
            if raw.lstrip().startswith("---"):
                data, body = parse_front_matter(raw)
                data["_body"] = body
            else:
                data = parse_yaml(raw)
            data["_file"] = name
            items.append(data)
        except Exception as e:  # one broken file must never break the build
            print("[build] skipping %s/%s: %s" % (folder, name, e))
    return items


def by_order(item):
    try:
        return int(item.get("order", 99))
    except (ValueError, TypeError):
        return 99


# ------------------------------------------------------------- micro utils ---

def esc(s):
    return html.escape(s or "", quote=False)


def esca(s):
    return html.escape(s or "", quote=True)


def bi(fr, en, tag="span"):
    return ('<{t} data-lang="fr">{f}</{t}><{t} data-lang="en">{e}</{t}>'
            .format(t=tag, f=esc(fr), e=esc(en or fr)))


def fix_url(u):
    u = (u or "").strip()
    if u and not re.match(r"^https?://", u, re.I):
        u = "https://" + u
    return u


def abs_url(u):
    u = (u or "").strip()
    if not u:
        return ""
    if re.match(r"^https?://", u, re.I):
        return u
    if not u.startswith("/"):
        u = "/" + u
    return SITE + u


def slug_of(filename):
    s = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", filename)
    s = re.sub(r"\.md$", "", s)
    s = re.sub(r"[^a-zA-Z0-9\-]+", "-", s).strip("-").lower()
    return s or "article"


def date_parts(iso):
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", iso or "")
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def date_fr(iso):
    p = date_parts(iso)
    if not p:
        return ""
    y, mo, d = p
    return "%d %s %d" % (d, MONTHS_FR[mo - 1], y)


def date_en(iso):
    p = date_parts(iso)
    if not p:
        return ""
    y, mo, d = p
    return "%s %d, %d" % (MONTHS_EN[mo - 1], d, y)


# ------------------------------------------------------- markdown -> html ---

def md_inline(text):
    text = html.escape(text, quote=False)
    text = re.sub(r"\[([^\]]+)\]\((https?://[^\s)]+)\)",
                  r'<a href="\2" target="_blank" rel="noopener">\1</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", text)
    return text


def md_to_html(md, external_link=None):
    out = []
    for block in re.split(r"\n\s*\n", (md or "").strip()):
        s = block.strip()
        if not s:
            continue
        if s.startswith("### "):
            out.append("<h3>%s</h3>" % md_inline(s[4:].strip()))
        elif s.startswith("## "):
            out.append("<h2>%s</h2>" % md_inline(s[3:].strip()))
        elif s.startswith("# "):
            out.append("<h2>%s</h2>" % md_inline(s[2:].strip()))
        elif s.startswith(">"):
            rows = []
            for ln in s.split("\n"):
                ln = re.sub(r"^>\s?", "", ln).strip()
                if ln:
                    rows.append(md_inline(ln))
            out.append("<blockquote>%s</blockquote>" % "<br><br>".join(rows))
        elif re.match(r"^[-*] ", s):
            items = [md_inline(re.sub(r"^[-*] ", "", ln.strip()))
                     for ln in s.split("\n") if ln.strip()]
            out.append("<ul>%s</ul>" % "".join("<li>%s</li>" % it for it in items))
        elif (s.startswith("\u25b6") or s.lower().startswith("regarder ") or
              s.lower().startswith("watch ")) and external_link:
            label = md_inline(s.lstrip("\u25b6\u2192 ").strip())
            out.append('<p><a class="ext-link" href="%s" target="_blank" '
                       'rel="noopener">\u25b6 %s</a></p>'
                       % (esca(external_link), label))
        else:
            out.append("<p>%s</p>" % md_inline(s).replace("\n", "<br>"))
    return "\n".join(out)


# ---------------------------------------------------------- page template ---

PAGE_CSS = """
:root{--bg:#0b0b0d;--bg-soft:#141417;--gold:#d4af37;--gold-soft:#e8c766;--cream:#f2ede2;--ink:#c9c3b6;--muted:#9a958a;--line:rgba(212,175,55,0.18);--radius:2px;}
*{box-sizing:border-box;}html{scroll-behavior:smooth;}
body{margin:0;background:var(--bg);color:var(--cream);font-family:Georgia,'Times New Roman',serif;line-height:1.7;}
h1,h2,h3,.brand{font-family:'Helvetica Neue',Arial,sans-serif;letter-spacing:0.03em;}
a{color:inherit;}img{max-width:100%;display:block;}
header{position:sticky;top:0;z-index:50;display:flex;align-items:center;justify-content:space-between;gap:14px;padding:16px 24px;background:rgba(11,11,13,0.92);backdrop-filter:blur(8px);border-bottom:1px solid var(--line);}
.brand{font-size:18px;font-weight:700;color:var(--gold-soft);text-decoration:none;text-transform:uppercase;}
.brand span{color:var(--cream);}
nav{display:flex;gap:18px;font-size:12px;letter-spacing:0.08em;text-transform:uppercase;font-family:'Helvetica Neue',Arial,sans-serif;}
nav a{text-decoration:none;color:var(--muted);transition:color .2s;}
nav a:hover,nav a.active{color:var(--gold-soft);}
.lang-switch{display:flex;border:1px solid var(--line);border-radius:var(--radius);overflow:hidden;font-size:12px;font-family:'Helvetica Neue',Arial,sans-serif;flex-shrink:0;}
.lang-switch a{padding:5px 12px;text-decoration:none;color:var(--muted);}
.lang-switch a.active{background:var(--gold);color:#000;}
main{max-width:760px;margin:0 auto;padding:56px 24px 80px;}
.breadcrumb{font-family:'Helvetica Neue',Arial,sans-serif;font-size:12px;letter-spacing:0.06em;text-transform:uppercase;color:var(--muted);margin-bottom:26px;}
.breadcrumb a{color:var(--muted);text-decoration:none;}
.breadcrumb a:hover{color:var(--gold-soft);}
.eyebrow{font-family:'Helvetica Neue',Arial,sans-serif;font-size:12px;letter-spacing:0.15em;text-transform:uppercase;color:var(--gold-soft);margin-bottom:14px;}
h1{font-size:clamp(30px,5vw,42px);margin:0 0 24px;color:var(--cream);line-height:1.18;}
.lead{color:var(--muted);font-size:17px;margin:0 0 28px;}
.cover{width:100%;border:1px solid var(--line);margin:6px 0 32px;}
.article-body{color:var(--ink);font-size:17px;}
.article-body p{margin:0 0 20px;}
.article-body h2{font-size:21px;color:var(--gold-soft);margin:44px 0 16px;letter-spacing:0.02em;}
.article-body h3{font-size:17px;color:var(--cream);margin:32px 0 12px;}
.article-body strong{color:var(--cream);}
.article-body a{color:var(--gold-soft);}
.article-body blockquote{border-left:2px solid var(--gold);margin:26px 0;padding:16px 20px;background:var(--bg-soft);}
.article-body ul{margin:0 0 20px;padding-left:22px;}
.ext-link{display:inline-block;margin-top:4px;color:var(--gold-soft);text-decoration:none;border-bottom:1px solid var(--gold-soft);font-family:'Helvetica Neue',Arial,sans-serif;font-size:14px;letter-spacing:0.04em;}
.postnav{margin-top:56px;padding-top:28px;border-top:1px solid var(--line);display:flex;flex-wrap:wrap;gap:10px 24px;font-family:'Helvetica Neue',Arial,sans-serif;font-size:13px;letter-spacing:0.05em;text-transform:uppercase;}
.postnav a{color:var(--gold-soft);text-decoration:none;}
.article-listing a.item{display:block;padding:24px 0;border-bottom:1px solid var(--line);text-decoration:none;}
.item .t{color:var(--cream);font-size:19px;font-family:'Helvetica Neue',Arial,sans-serif;transition:color .2s;}
.item:hover .t{color:var(--gold-soft);}
.item .s{color:var(--muted);font-size:14px;margin-top:6px;line-height:1.6;}
.item .d{color:var(--gold-soft);font-family:'Helvetica Neue',Arial,sans-serif;font-size:12px;letter-spacing:0.08em;text-transform:uppercase;margin-top:10px;}
.fact-list{border:1px solid var(--line);padding:26px;margin:36px 0;}
.fact{margin-bottom:20px;}.fact:last-child{margin-bottom:0;}
.fact-label{font-family:'Helvetica Neue',Arial,sans-serif;font-size:11px;letter-spacing:0.12em;text-transform:uppercase;color:var(--gold-soft);margin-bottom:5px;}
.fact-value{color:var(--cream);}
.btn{display:inline-block;padding:13px 26px;border-radius:var(--radius);font-family:'Helvetica Neue',Arial,sans-serif;font-size:13px;letter-spacing:0.06em;text-transform:uppercase;text-decoration:none;border:1px solid var(--gold);background:var(--gold);color:#000;}
footer{border-top:1px solid var(--line);padding:44px 24px;text-align:center;color:var(--muted);font-size:13px;}
footer .brand{margin-bottom:12px;display:inline-block;}
footer .social{display:flex;gap:18px;justify-content:center;margin-top:16px;font-family:'Helvetica Neue',Arial,sans-serif;font-size:12px;text-transform:uppercase;letter-spacing:0.06em;flex-wrap:wrap;}
footer .social a{text-decoration:none;color:var(--gold-soft);}
footer .footer-nav{margin-top:16px;font-family:'Helvetica Neue',Arial,sans-serif;font-size:12px;text-transform:uppercase;letter-spacing:0.06em;}
footer .footer-nav a{text-decoration:none;color:var(--muted);}
footer .footer-nav a:hover{color:var(--gold-soft);}
@media(max-width:700px){nav{display:none;}}
"""

NAV = {
    "fr": [("/", "Accueil"), ("/fr/articles/", "Articles"), ("/fr/a-propos/", "\u00c0 propos")],
    "en": [("/", "Home"), ("/en/articles/", "Articles"), ("/en/about/", "About")],
}

FOOTER_TAGLINE = {
    "fr": "EuroJackys est une fanbase ind\u00e9pendante, g\u00e9r\u00e9e par des fans. Nous ne sommes affili\u00e9s ni \u00e0 Jackson Wang, ni \u00e0 Team Wang, ni \u00e0 aucun de leurs partenaires.",
    "en": "EuroJackys is an independent, fan-run fanbase. We are not affiliated with Jackson Wang, Team Wang, or any of their partners.",
}


def social_links_html():
    return "".join('<a href="%s" target="_blank" rel="noopener">%s</a>'
                   % (esca(u), esc(n)) for n, u in SOCIALS)


def page_shell(lang, head_extra, active_path, body_html, alt_url):
    nav_html = "".join(
        '<a href="%s"%s>%s</a>' % (esca(p), ' class="active"' if p == active_path else "", esc(label))
        for p, label in NAV[lang])
    other = "en" if lang == "fr" else "fr"
    switch = ('<div class="lang-switch">'
              '<a href="%s"%s>FR</a><a href="%s"%s>EN</a></div>'
              % (esca(alt_url if lang == "en" else active_path),
                 ' class="active"' if lang == "fr" else "",
                 esca(alt_url if lang == "fr" else active_path),
                 ' class="active"' if lang == "en" else ""))
    foot_nav = " \u00b7 ".join('<a href="%s">%s</a>' % (esca(p), esc(label))
                               for p, label in NAV[lang])
    return """<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
{head_extra}
<link rel="icon" href="/images/brand/favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="32x32" href="/images/brand/favicon-32.png">
<link rel="apple-touch-icon" href="/images/brand/apple-touch-icon.png">
<style>{css}</style>
</head>
<body>
<header>
  <a href="/" class="brand">EURO<span>JACKYS</span></a>
  <nav>{nav}</nav>
  {switch}
</header>
<main>
{body}
</main>
<footer>
  <a href="/" class="brand">EURO<span style="color:var(--cream)">JACKYS</span></a>
  <p>{tagline}</p>
  <div class="social">{socials}</div>
  <div class="footer-nav">{footnav}</div>
</footer>
</body>
</html>
""".format(lang=lang, head_extra=head_extra, css=PAGE_CSS, nav=nav_html,
           switch=switch, body=body_html, tagline=esc(FOOTER_TAGLINE[lang]),
           socials=social_links_html(), footnav=foot_nav)


def head_block(lang, title, description, url, alt_fr, alt_en, og_type="website",
               og_image=OG_IMAGE, jsonld=None, published=None):
    parts = [
        "<title>%s</title>" % esc(title),
        '<meta name="description" content="%s">' % esca(description),
        '<link rel="canonical" href="%s">' % esca(url),
        '<link rel="alternate" hreflang="fr" href="%s">' % esca(alt_fr),
        '<link rel="alternate" hreflang="en" href="%s">' % esca(alt_en),
        '<link rel="alternate" hreflang="x-default" href="%s">' % esca(alt_en),
        '<meta property="og:type" content="%s">' % og_type,
        '<meta property="og:site_name" content="EuroJackys">',
        '<meta property="og:title" content="%s">' % esca(title),
        '<meta property="og:description" content="%s">' % esca(description),
        '<meta property="og:url" content="%s">' % esca(url),
        '<meta property="og:image" content="%s">' % esca(og_image),
        '<meta property="og:locale" content="%s">' % ("fr_FR" if lang == "fr" else "en_GB"),
        '<meta name="twitter:card" content="summary_large_image">',
        '<meta name="twitter:site" content="@eurojackys">',
        '<meta name="twitter:image" content="%s">' % esca(og_image),
    ]
    if published:
        parts.append('<meta property="article:published_time" content="%s">' % esca(published))
    if jsonld:
        parts.append('<script type="application/ld+json">%s</script>'
                     % json.dumps(jsonld, ensure_ascii=False))
    return "\n".join(parts)


def org_jsonld():
    return {
        "@type": "Organization",
        "@id": SITE + "/#org",
        "name": "EuroJackys",
        "url": SITE + "/",
        "logo": {"@type": "ImageObject", "url": LOGO_512, "width": 512, "height": 512},
        "description": ORG_DESCRIPTION,
        "foundingDate": "2025-08-14",
        "areaServed": "Europe",
        "sameAs": [u for _, u in SOCIALS],
    }


def breadcrumb_jsonld(items):
    return {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": name, "item": url}
            for i, (name, url) in enumerate(items)
        ],
    }


# ------------------------------------------------------------ generation ---

def write_page(path, html_text):
    full = os.path.join(ROOT, path.lstrip("/"))
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(html_text)
    print("[build] wrote %s" % path)


def load_articles():
    arts = []
    for data in load_folder("articles"):
        slug = slug_of(data.get("_file", ""))
        iso = data.get("date", "")
        art = {
            "slug": slug,
            "iso": iso,
            "title_fr": data.get("title", "(sans titre)"),
            "title_en": data.get("title_en") or data.get("title", "(untitled)"),
            "summary_fr": data.get("summary", ""),
            "summary_en": data.get("summary_en") or data.get("summary", ""),
            "body_fr": data.get("_body", ""),
            "body_en": data.get("body_en") or data.get("_body", ""),
            "cover": data.get("cover", ""),
            "external": fix_url(data.get("external_link", "")),
            "url_fr": SITE + "/fr/articles/%s/" % slug,
            "url_en": SITE + "/en/articles/%s/" % slug,
        }
        arts.append(art)
    arts.sort(key=lambda a: a["iso"] or "", reverse=True)
    return arts


def gen_article_pages(articles):
    for art in articles:
        for lang in ("fr", "en"):
            title = art["title_fr"] if lang == "fr" else art["title_en"]
            summary = art["summary_fr"] if lang == "fr" else art["summary_en"]
            body_md = art["body_fr"] if lang == "fr" else art["body_en"]
            url = art["url_fr"] if lang == "fr" else art["url_en"]
            date_disp = date_fr(art["iso"]) if lang == "fr" else date_en(art["iso"])
            listing = "/%s/articles/" % lang
            listing_label = "Articles & R\u00e9caps" if lang == "fr" else "Articles & Recaps"
            home_label = "Accueil" if lang == "fr" else "Home"
            cover_abs = abs_url(art["cover"]) if art["cover"] else ""

            jsonld = {"@context": "https://schema.org", "@graph": [
                {
                    "@type": "Article",
                    "@id": url + "#article",
                    "mainEntityOfPage": url,
                    "headline": title,
                    "description": summary,
                    "inLanguage": lang,
                    "datePublished": art["iso"] or None,
                    "dateModified": art["iso"] or None,
                    "image": [cover_abs or OG_IMAGE],
                    "author": {"@type": "Organization", "name": "EuroJackys", "url": SITE + "/"},
                    "publisher": {"@type": "Organization", "name": "EuroJackys",
                                  "url": SITE + "/",
                                  "logo": {"@type": "ImageObject", "url": LOGO_512}},
                },
                breadcrumb_jsonld([
                    (home_label, SITE + "/"),
                    (listing_label, SITE + listing),
                    (title, url),
                ]),
            ]}

            head = head_block(
                lang,
                "%s | EuroJackys" % title,
                summary or ORG_DESCRIPTION,
                url,
                art["url_fr"], art["url_en"],
                og_type="article",
                og_image=cover_abs or OG_IMAGE,
                jsonld=jsonld,
                published=art["iso"] or None,
            )

            cover_html = ('<img class="cover" src="%s" alt="%s">'
                          % (esca(art["cover"]), esca(title))) if art["cover"] else ""
            ext_html = ""
            if art["external"] and "\u25b6" not in body_md:
                label = ("Voir la publication d'origine" if lang == "fr"
                         else "See the original post")
                ext_html = ('<p><a class="ext-link" href="%s" target="_blank" '
                            'rel="noopener">\u2192 %s</a></p>'
                            % (esca(art["external"]), esc(label)))

            back = "\u2190 Tous les articles" if lang == "fr" else "\u2190 All articles"
            about_href = "/fr/a-propos/" if lang == "fr" else "/en/about/"
            about_label = ("\u00c0 propos d'EuroJackys" if lang == "fr"
                           else "About EuroJackys")

            body_html = """<div class="breadcrumb"><a href="/">{home}</a> \u2192 <a href="{listing}">{listing_label}</a></div>
<div class="eyebrow">{date}</div>
<h1>{title}</h1>
{cover}
<div class="article-body">
{body}
{ext}
</div>
<div class="postnav">
  <a href="{listing}">{back}</a>
  <a href="{about_href}">{about_label}</a>
</div>""".format(home=esc(home_label), listing=esca(listing),
                 listing_label=esc(listing_label), date=esc(date_disp),
                 title=esc(title), cover=cover_html,
                 body=md_to_html(body_md, art["external"]), ext=ext_html,
                 back=esc(back), about_href=about_href, about_label=esc(about_label))

            write_page("/%s/articles/%s/index.html" % (lang, art["slug"]),
                       page_shell(lang, head, listing, body_html,
                                  alt_url=("/en/articles/%s/" % art["slug"]) if lang == "fr"
                                  else ("/fr/articles/%s/" % art["slug"])))


def gen_listing_pages(articles):
    meta = {
        "fr": {
            "title": "Articles & R\u00e9caps | EuroJackys \u2014 Actus Jackson Wang en Europe",
            "desc": ("Tous les articles et r\u00e9caps d'EuroJackys : actualit\u00e9s "
                     "v\u00e9rifi\u00e9es de Jackson Wang, traductions et projets de fans "
                     "europ\u00e9ens, en fran\u00e7ais et en anglais."),
            "h1": "Articles & R\u00e9caps",
            "lead": ("Actualit\u00e9s v\u00e9rifi\u00e9es, analyses et r\u00e9caps de "
                     "l'univers Jackson Wang, c\u00f4t\u00e9 Europe."),
            "path": "/fr/articles/",
        },
        "en": {
            "title": "Articles & Recaps | EuroJackys \u2014 Jackson Wang News in Europe",
            "desc": ("All EuroJackys articles and recaps: verified Jackson Wang news, "
                     "translations and European fan projects, in French and English."),
            "h1": "Articles & Recaps",
            "lead": "Verified news, deep dives and recaps from the Jackson Wang universe, European side.",
            "path": "/en/articles/",
        },
    }
    for lang in ("fr", "en"):
        m = meta[lang]
        url = SITE + m["path"]
        rows = []
        for art in articles:
            title = art["title_fr"] if lang == "fr" else art["title_en"]
            summary = art["summary_fr"] if lang == "fr" else art["summary_en"]
            d = date_fr(art["iso"]) if lang == "fr" else date_en(art["iso"])
            href = "/%s/articles/%s/" % (lang, art["slug"])
            rows.append(
                '<a class="item" href="{h}"><div class="t">{t}</div>'
                '{s}<div class="d">{d}</div></a>'.format(
                    h=esca(href), t=esc(title),
                    s=('<div class="s">%s</div>' % esc(summary)) if summary else "",
                    d=esc(d)))
        if not rows:
            rows.append('<p class="lead">%s</p>'
                        % ("Les premiers articles arrivent bient\u00f4t."
                           if lang == "fr" else "First articles coming soon."))
        jsonld = {"@context": "https://schema.org", "@graph": [
            {"@type": "CollectionPage", "@id": url, "name": m["h1"],
             "url": url, "inLanguage": lang, "isPartOf": {"@id": SITE + "/#website"}},
            breadcrumb_jsonld([("Accueil" if lang == "fr" else "Home", SITE + "/"),
                               (m["h1"], url)]),
        ]}
        head = head_block(lang, m["title"], m["desc"], url,
                          SITE + "/fr/articles/", SITE + "/en/articles/",
                          jsonld=jsonld)
        body = """<div class="breadcrumb"><a href="/">{home}</a></div>
<div class="eyebrow">EuroJackys</div>
<h1>{h1}</h1>
<p class="lead">{lead}</p>
<div class="article-listing">
{rows}
</div>""".format(home="Accueil" if lang == "fr" else "Home",
                 h1=esc(m["h1"]), lead=esc(m["lead"]), rows="\n".join(rows))
        write_page(m["path"] + "index.html",
                   page_shell(lang, head, m["path"], body,
                              alt_url="/en/articles/" if lang == "fr" else "/fr/articles/"))


def gen_sitemap(articles):
    entries = [
        (SITE + "/", TODAY, "1.0"),
        (SITE + "/fr/a-propos/", TODAY, "0.8"),
        (SITE + "/en/about/", TODAY, "0.8"),
        (SITE + "/fr/articles/", TODAY, "0.8"),
        (SITE + "/en/articles/", TODAY, "0.8"),
    ]
    for art in articles:
        lastmod = (art["iso"] or TODAY)[:10]
        entries.append((art["url_fr"], lastmod, "0.7"))
        entries.append((art["url_en"], lastmod, "0.7"))
    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, lastmod, prio in entries:
        xml.append("  <url><loc>%s</loc><lastmod>%s</lastmod>"
                   "<priority>%s</priority></url>" % (esc(loc), lastmod, prio))
    xml.append("</urlset>\n")
    with open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write("\n".join(xml))
    print("[build] wrote /sitemap.xml (%d URLs)" % len(entries))


# ------------------------------------------------- index.html injection ---

def inject(content, marker, inner):
    start = "<!-- BUILD:%s -->" % marker
    end = "<!-- /BUILD:%s -->" % marker
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    if not pattern.search(content):
        print("[build] WARNING: marker %s not found in index.html" % marker)
        return content
    return pattern.sub(start + inner + end, content)


def build_index(articles):
    idx_path = os.path.join(ROOT, "index.html")
    with open(idx_path, "r", encoding="utf-8") as f:
        content = f.read()

    # --- textes A propos / accueil (content/about.yml) ---
    about = {}
    for item in load_folder("content"):
        if item.get("_file") == "about.yml":
            about = item
    pairs = [
        ("FOUNDED", about.get("founded", "14.08.2025")),
        ("PLATFORMS", about.get("platforms", "Instagram \u00b7 TikTok \u00b7 Facebook \u00b7 Threads \u00b7 X \u00b7 YouTube")),
        ("STATUS_FR", about.get("status_fr", "")),
        ("STATUS_EN", about.get("status_en", "")),
        ("HERO_FR", about.get("hero_fr", "")),
        ("HERO_EN", about.get("hero_en", "")),
        ("ABOUT_FR", about.get("text_fr", "")),
        ("ABOUT_EN", about.get("text_en", "")),
        ("BANNER_FR", about.get("banner_fr", "")),
        ("BANNER_EN", about.get("banner_en", "")),
    ]
    for marker, value in pairs:
        if value:
            content = inject(content, marker, md_inline(value))

    # --- calendrier ---
    cal = sorted(load_folder("content/calendar"), key=by_order)
    cal_html = "".join(
        '<div class="cal-item"><div class="cal-date">{d}</div>'
        '<div><div class="cal-title">{t}</div><div class="cal-desc">{de}</div></div>'
        '<div class="cal-tag">{tag}</div></div>'.format(
            d=esc(ev.get("date_display", "")),
            t=bi(ev.get("title_fr", ""), ev.get("title_en", "")),
            de=bi(ev.get("desc_fr", ""), ev.get("desc_en", "")),
            tag=bi(ev.get("tag_fr", ""), ev.get("tag_en", "")))
        for ev in cal)
    content = inject(content, "CALENDAR", cal_html)

    # --- projets ---
    projs = sorted(load_folder("content/projects"), key=by_order)
    cards = []
    for p in projs:
        link = fix_url(p.get("link", ""))
        inner = ('<div class="project-icon">{i}</div><h3>{t}</h3>'
                 '<div class="project-freq">{f}</div>'
                 '<p data-lang="fr">{dfr}</p><p data-lang="en">{den}</p>'.format(
                     i=esc(p.get("icon", "")), t=esc(p.get("title", "")),
                     f=bi(p.get("freq_fr", ""), p.get("freq_en", "")),
                     dfr=esc(p.get("desc_fr", "")),
                     den=esc(p.get("desc_en") or p.get("desc_fr", ""))))
        if link:
            cards.append('<a class="project-card" href="%s" target="_blank" rel="noopener" '
                         'style="text-decoration:none;display:block;">%s</a>' % (esca(link), inner))
        else:
            cards.append('<div class="project-card">%s</div>' % inner)
    content = inject(content, "PROJECTS", "".join(cards))

    # --- galerie ---
    gal = sorted(load_folder("content/gallery"), key=by_order)
    tiles = []
    for g in gal:
        img = g.get("image", "")
        tiles.append(
            '<div class="gallery-tile" data-gtitle="{t}" data-gsubfr="{sf}" '
            'data-gsuben="{se}" data-gimg="{img}" data-glink="{link}" '
            'style="background-image:url(\'{imgcss}\');cursor:pointer;">'
            '<small>{t}</small><span>{sub}</span></div>'.format(
                t=esca(g.get("title", "")),
                sf=esca(g.get("subtitle_fr", "")),
                se=esca(g.get("subtitle_en", "")),
                img=esca(img), link=esca(fix_url(g.get("link", ""))),
                imgcss=esca(img).replace("'", "%27"),
                sub=bi(g.get("subtitle_fr", ""), g.get("subtitle_en", ""))))
    if not tiles:
        tiles.append('<p class="empty-state" data-lang="fr">Photos \u00e0 venir.</p>'
                     '<p class="empty-state" data-lang="en">Photos coming soon.</p>')
    content = inject(content, "GALLERY", "".join(tiles))

    # --- carte ---
    rows = sorted(load_folder("content/map"), key=by_order)
    map_html = "".join(
        "<tr><td>{c}</td><td>{m}</td><td><span class=\"status-dot\"></span>{s}</td></tr>".format(
            c=esc(r.get("country", "")), m=esc(r.get("members", "\u2014") or "\u2014"),
            s=esc(r.get("status", "")))
        for r in rows)
    content = inject(content, "MAP", map_html)

    # --- articles (liste statique de vrais liens) ---
    art_rows = []
    for art in articles:
        d = ('<span data-lang="fr">%s</span><span data-lang="en">%s</span>'
             % (esc(date_fr(art["iso"])), esc(date_en(art["iso"]))))
        summary = ""
        if art["summary_fr"] or art["summary_en"]:
            summary = ('<div style="color:var(--muted);font-size:13px;margin-top:4px;">%s</div>'
                       % bi(art["summary_fr"], art["summary_en"]))
        art_rows.append(
            '<a class="article-row" data-slug="{slug}" href="/fr/articles/{slug}/">'
            '<div><div class="article-title">{t}</div>{s}</div>'
            '<div class="article-date">{d}</div></a>'.format(
                slug=esca(art["slug"]), t=bi(art["title_fr"], art["title_en"]),
                s=summary, d=d))
    if not art_rows:
        art_rows.append('<p class="empty-state" data-lang="fr">Les premiers articles arrivent bient\u00f4t.</p>'
                        '<p class="empty-state" data-lang="en">First articles coming soon.</p>')
    content = inject(content, "ARTICLES", "".join(art_rows))

    with open(idx_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("[build] index.html updated")


def main():
    articles = load_articles()
    print("[build] %d article(s) found" % len(articles))
    gen_article_pages(articles)
    gen_listing_pages(articles)
    gen_sitemap(articles)
    build_index(articles)
    print("[build] done.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Never break the deploy: log and exit cleanly, the committed
        # fallback content will be published instead.
        import traceback
        traceback.print_exc()
        print("[build] ERROR: %s (deploy continues with committed files)" % e)
        sys.exit(0)
