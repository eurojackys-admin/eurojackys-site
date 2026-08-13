# 🚀 EuroJackys — Guide de mise en ligne du pack SEO

## Ce que contient ce pack (résumé 30 secondes)

- Une **vraie page par article**, en FR et en EN, que Google peut enfin lire (fini le « Chargement… »)
- Des pages **À propos** : `/fr/a-propos/` et `/en/about/` — avec la clarification sur « Team Jackson Wang Europe »
- **sitemap.xml** + **robots.txt**
- La **carte d'identité Google** d'EuroJackys (données structurées Organization avec tes 6 réseaux) → pour que Google associe « EuroJackys » à TON projet
- Des **aperçus de partage** dorés (WhatsApp, Instagram DM, X…) + **favicon EJ**
- Un **générateur automatique** (`build.py` + `netlify.toml`) : à chaque article publié dans ton admin, les pages et le sitemap se régénèrent **tout seuls**. Zéro maintenance.

Ce qui change pour tes visiteurs : cliquer sur un article ouvre maintenant sa propre page (plus la petite fenêtre), le footer affiche les 6 réseaux, et le site charge plus vite.

---

## Étape 1 — Mettre les fichiers sur GitHub (~5 min)

1. Décompresse le zip sur ton ordinateur
2. Va sur **github.com/eurojackys-admin/eurojackys-site**
3. Clique **Add file → Upload files**
4. Glisse **TOUT le contenu** du dossier décompressé dans la fenêtre (fichiers ET dossiers : `fr`, `en`, `images`, `content`, `index.html`, `build.py`, etc.)
5. Message de commit : `SEO : pages articles, à propos, sitemap`
6. Clique **Commit changes**

⚠️ GitHub va remplacer `index.html` et `content/about.yml` — c'est normal et voulu.

## Étape 2 — Vérifier le déploiement Netlify (~2 min)

1. Va sur **app.netlify.com** → ton site → onglet **Deploys**
2. Attends le statut **Published** (1–2 min)
3. Si tu vois **Failed** : clique dessus, copie le journal (log) et envoie-le-moi — le site reste en ligne sur l'ancienne version, rien ne casse.

## Étape 3 — Vérifier le site (~2 min)

Ouvre ces adresses, tout doit s'afficher :

- eurojackys.com/fr/a-propos/
- eurojackys.com/en/about/
- eurojackys.com/fr/articles/
- eurojackys.com/sitemap.xml
- eurojackys.com/robots.txt

L'article Cartier doit avoir sa propre page en FR et en EN. ✅

## Étape 4 — Réparer www.eurojackys.com (~5 min)

1. Netlify → ton site → **Domain management** → **Add domain alias** → tape `www.eurojackys.com`
2. Netlify t'affiche l'enregistrement DNS à créer (généralement un **CNAME** vers `ton-site.netlify.app`)
3. GoDaddy → ton domaine → **DNS** → **Ajouter** → type `CNAME`, nom `www`, valeur = celle donnée par Netlify
4. Attends jusqu'à ~1 h. Netlify redirigera ensuite automatiquement www → eurojackys.com. ✅

## Étape 5 — Google Search Console (~10 min)

C'est ce qui dit officiellement à Google « ce site existe, indexe-le ».

1. Va sur **search.google.com/search-console**
2. **Ajouter une propriété** → choisis le type **Domaine** → `eurojackys.com`
3. Google te donne un code **TXT** → GoDaddy → **DNS** → **Ajouter** → type `TXT`, nom `@`, valeur = le code Google
4. Retour dans Search Console → **Vérifier** (si ça échoue, attends 1 h et réessaie)
5. Menu **Sitemaps** → tape `sitemap.xml` → **Envoyer**
6. Barre du haut « Inspection d'URL » : colle `https://eurojackys.com/` → **Demander une indexation**. Refais la même chose pour `/en/about/` et pour la page de l'article Cartier.

---

## Et pour publier un article maintenant ?

**Rien ne change pour toi.** Tu passes par `/admin/` comme d'habitude. À chaque publication, Netlify régénère automatiquement la page FR, la page EN, la liste des articles et le sitemap.

Petit bonus : le bug qui **coupait les résumés** des articles sur l'accueil est corrigé au passage. 😉

## À m'envoyer quand tu peux

1. **L'URL exacte de ta page Facebook** (ouvre ta page dans un navigateur et copie l'adresse) — je remplacerai le lien de partage temporaire partout
2. **Ton logo en haute résolution** — je remplacerai le monogramme EJ doré (favicon + image de partage)

## Prochaines étapes (quand tu veux)

1. Page **« Qui est Jackson Wang ? »** (`/fr/qui-est-jackson-wang/` + `/en/who-is-jackson-wang/`)
2. Page pilier **« Jackson Wang en Europe »** — la grosse pièce du positionnement « Jackson Wang Europe », avec la chronologie de ses venues européennes
