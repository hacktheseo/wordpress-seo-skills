# Formulations françaises du livrable

À charger quand l'utilisateur écrit en français, au moment de construire
`findings.json`. Mettre `meta.lang` à `"fr"` : le moteur traduit ses propres
libellés (Généré le, Période, Constat, Ce qu'il faut faire), tout le reste
vient d'ici.

## Titre et objet

- `meta.title` : `Audit de citabilité IA`
- `meta.subject` : l'URL auditée, telle quelle
- `meta.period` : la date de récupération du HTML, par exemple `HTML servi récupéré le 9 septembre 2026`

## Verdict

Une phrase, un constat chiffré, jamais une description. Gabarits :

- `Sur les <n> passages de la page, <k> sont citables tels quels et <m> ne le seront pas tant qu'ils ouvriront sur une mise en contexte.`
- `<k> des <n> passages de la page n'existent pas pour un robot IA : ils sont injectés en JavaScript.`
- `La page répond deux fois à la même question, avec deux passages qui se neutralisent.`

`detail` : deux lignes, la cause dominante et ce qu'elle coûte.

## Intitulés des KPI

| KPI | Libellé | Note type |
|---|---|---|
| Score médian | `Score médian des passages` | `Médiane sur <n> passages, barème détaillé en fin de document` |
| Citables | `Citables tels quels` | `Score 80 et plus` |
| À réécrire | `À réécrire ou à supprimer` | `Score sous 60` |
| Invisible sans JS | `Contenu invisible sans JavaScript` | `<n> mots absents du HTML servi` |

## Titres de sections

1. `Carte de citabilité de la page`
2. `Le détail par critère`
3. `Ce qui plombe la page`
4. `Cinq passages réécrits`
5. `Balisage JSON-LD et contenu visible`
6. `Méthode et limites`

## Bandes de citabilité

| Bande | Libellé | Tonalité |
|---|---|---|
| 80 à 100 | `Citable tel quel` | `good` |
| 60 à 79 | `Citable après une retouche` | `neutral` |
| 40 à 59 | `À réécrire` | `warn` |
| 0 à 39 | `Remplissage` | `bad` |

## Colonnes de la table de détail

`Passage`, `Extractibilité`, `Autonomie`, `Réponse directe`, `Faits`,
`Forme`, `Longueur`, `Attribution`, `Total`, `Bande`.

## Blocs de réécriture

Titre du constat : `Passage <n> : <titre actuel>`.
`evidence` : la mesure observée, par exemple `72 mots, 5 anaphores dont une en
première phrase, aucun chiffre, titre non interrogeable.`
`action` : `Retitrer en question, remonter la réponse en première phrase,
désanaphoriser, planter un fait déjà publié. Avant et après ci-dessous.`

## Note de limites, à recopier

Titre : `Ce que ce document ne peut pas montrer`, tonalité `warn`.

> Ce barème est une heuristique construite sur des régularités observables : ce
> qu'un robot peut lire, ce qui survit à l'extraction hors de sa page, ce à quoi
> ressemble un bloc effectivement recopié. Ce n'est pas l'algorithme d'un
> moteur de réponse, et aucun barème public ne l'est. Un passage à 95 est un
> passage citable, pas un passage qui sera cité. La mesure porte sur la page
> telle qu'elle est servie le jour de la récupération, elle ne porte ni sur les
> citations réelles ni sur leur évolution.

## Phrase de dégradation, plugin absent

> Le plugin Hack The SEO ne répond pas sur ce site, j'ai donc fait les
> vérifications publiques seulement : découpage en passages du HTML servi,
> notation des <n> passages et contrôle du JSON-LD. Avec le plugin installé,
> cette skill lirait aussi la version Markdown de la page et le score GEO
> calculé côté serveur, parce que ces données ne sont pas visibles par un
> crawler. Le plugin gratuit : https://wordpress.org/plugins/hack-the-seo/

Une seule fois par exécution, jamais répétée.
