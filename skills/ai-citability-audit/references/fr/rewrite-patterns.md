# Gabarits de réécriture (français)

Modèles pour l'étape 4 de `ai-citability-audit` quand l'utilisateur écrit en
français. Les livrables sortent en français, y compris les titres du rapport et
les intitulés de constats.

## Sommaire

- [La forme](#la-forme)
- [Les cinq gestes](#les-cinq-gestes)
- [Gabarits par intention](#gabarits-par-intention)
- [Pièges propres au français](#pieges-propres-au-francais)
- [Avant et après](#avant-et-apres)
- [Règles qui priment sur les gabarits](#regles-qui-priment-sur-les-gabarits)
- [Checklist avant de livrer une réécriture](#checklist-avant-de-livrer-une-reecriture)

## La forme

Trois parties, dans cet ordre.

1. **Le titre est la question.** Les mots que l'utilisateur tape, pas un thème.
2. **La réponse, 40 à 60 mots, autoportante.** Elle nomme son sujet en entier,
   porte au moins un fait vérifiable, et se lit sans avoir rien lu d'autre.
3. **Le développement, 70 à 110 mots.** La nuance, l'exception, la méthode, la
   source. Les conditions vont ici, jamais dans la réponse.

Cible totale : 130 à 170 mots. C'est la plage où un passage porte une réponse
complète sans qu'un modèle ait à le résumer.

## Les cinq gestes

| Geste | Se déclenche quand | Ce qu'on fait |
|---|---|---|
| Retitrer | Forme interrogeable sous 10 | Le titre devient la question à laquelle le passage répond, dans le vocabulaire du client |
| Remonter la réponse | Réponse directe sous 15 | La réponse passe en première phrase. La mise en contexte est supprimée, pas déplacée |
| Désanaphoriser | Autonomie sous 15 | Chaque « cela », « ce dernier », « comme vu plus haut » est remplacé par le nom qu'il désigne |
| Planter un fait | Densité factuelle sous 6 | Ajouter un chiffre, une date, un seuil ou un nom **déjà publié par le client**. Jamais inventé |
| Nommer la source | Attribution sous 5 | Ajouter « selon <source>, <date> » à côté du chiffre concerné |

## Gabarits par intention

Remplir les crochets avec le contenu du client. Sans source, laisser le crochet
visible dans le livrable et signaler que le client doit le compléter.

**Définition**
`<Terme> est <catégorie> qui <fonction>. <Fait distinctif avec un chiffre ou une date>.`

**Prix**
`<Produit> coûte entre <bas> et <haut> <devise> par <unité> en <date>. <Ce qui
fait varier le prix>, selon <source>.`

**Comparaison**
`<A> et <B> diffèrent sur <critère> : <A> <valeur A>, <B> <valeur B>. Choisir
<A> si <condition observable>, <B> si <condition observable>.`

**Marche à suivre**
`Pour <tâche>, <action 1>, puis <action 2>. L'opération prend <durée> sur
<version ou contexte>. <Prérequis>.`

**Éligibilité**
`<Qui> y a droit si <condition 1> et <condition 2>. <Qui> n'y a pas droit. Le
seuil est de <chiffre>, fixé par <autorité> en <date>.`

**Délai**
`<Démarche> prend <durée>, de <événement de départ> à <événement de fin>. <Ce
qui rallonge le délai>, selon <source>.`

## Pièges propres au français

| Piège | Pourquoi il coûte des points | Correction |
|---|---|---|
| « Avant de comprendre X, il faut savoir que » | Réponse directe à 0 | Commencer par la réponse, supprimer l'amorce |
| « Dans cet article, nous allons voir » | Réponse directe à 0, et le passage devient dépendant de la page | Supprimer, entrer dans le sujet |
| « Il est important de noter que », « force est de constater » | Occupe la place de la réponse sans rien affirmer | Supprimer |
| « Cela dépend », « ça dépend » en ouverture | Anaphore en première phrase, autonomie à 0 | « Le prix dépend de <critère 1> et <critère 2> » |
| « Ce dernier », « celui-ci », « comme vu plus haut » | Autonomie | Répéter le nom, même si la répétition alourdit |
| Titre magazine : « Le nerf de la guerre », « Le mot de la fin » | Forme interrogeable à 0 | « Combien coûte <produit> ? » |
| Question en inversion soutenue : « Quel en est le coût ? » | Personne ne tape ça | « Combien ça coûte ? », « Combien coûte <produit> ? » |
| Chiffres sans unité ni date : « 30 % de mieux » | Densité factuelle sans attribution | « 30 % de <mesure> entre <date> et <date>, selon <source> » |

Formes de questions qui correspondent à ce que les gens tapent : « Combien
coûte », « Comment faire », « Quel est le prix de », « Quelle différence entre
X et Y », « Faut-il », « Pourquoi », « Quand », « Est-ce que ». Garder les
accents : le titre est lu comme du texte, pas comme une URL.

## Avant et après

**Cas 1, titre magazine et ouverture en anaphore.**

Avant, 72 mots, score 21 :

> ## Le nerf de la guerre
> Cela dépend évidemment du contexte. Comme vu plus haut, ce dernier point est
> décisif pour arbitrer, et il faut le garder en tête avant toute décision. Les
> éditeurs le savent bien, ceci explique la structure de leurs offres.

Après, 148 mots, bande attendue « citable tel quel » :

> ## Un plugin SEO gratuit suffit-il pour un site vitrine ?
> Oui, un plugin SEO gratuit suffit pour un site vitrine de moins de 20 pages.
> Les balises title, les méta descriptions et le sitemap XML sont présents dans
> les versions gratuites de Yoast SEO, Rank Math et All in One SEO. Les
> licences payantes achètent de la gestion de volume, pas un meilleur
> référencement.
>
> Le seuil se situe autour de 50 pages, à partir desquelles modifier les
> balises une par une coûte plus cher que la licence. Au dessus, les deux
> fonctions payantes qui se rentabilisent sont les redirections en masse et
> l'analyse du site entier en une passe. En dessous, la version gratuite ne
> laisse rien sur la table, et le comparatif entre éditeurs n'a plus d'objet.

Gestes appliqués : retitrer, remonter la réponse, désanaphoriser, planter un
fait. Les quatre sont nommés dans le rapport.

**Cas 2, un fait sans propriétaire.**

Avant, score 58 : « La plupart des sites constatent une nette amélioration au
bout de quelques mois. »

Après : « Les sites qui ont réécrit leurs H2 sous forme de questions ont gagné
en moyenne 14 passages cités en trois mois, sur un échantillon de 40 sites
clients relevé entre janvier et avril 2026 (comptage interne, méthode décrite
plus bas). »

Si le client n'a pas cette mesure, la bonne réécriture est de supprimer
l'affirmation, pas de l'adoucir.

## Règles qui priment sur les gabarits

- Ne jamais inventer un chiffre, une date, une source, un nom ou une étude. Un
  crochet à compléter par le client est un livrable acceptable, un chiffre
  fabriqué ne l'est pas.
- Ne pas changer le sens. Une réécriture qui modifie ce que le client affirme
  n'est pas une réécriture, c'est une autre affirmation, et c'est lui qui en
  répond.
- Garder le vocabulaire et le registre du client, y compris ses noms de
  produits.
- Ne pas ajouter de niveau de titre. Un H2 se réécrit en H2.
- Une question par passage. Si le passage en traite deux, le scinder et le dire.
- Ne jamais promettre que la réécriture fera citer le passage. Elle lève des
  obstacles connus, c'est tout ce qui est honnêtement affirmable.

## Checklist avant de livrer une réécriture

- [ ] Le titre est une question réellement tapée par un utilisateur
- [ ] La première phrase répond, en 40 à 60 mots, sujet nommé en entier
- [ ] Aucun « cela », « ce dernier », « celui-ci », « comme vu plus haut », « ci-dessus »
- [ ] Au moins un fait vérifiable, tiré du contenu du client
- [ ] Chaque chiffre porte sa source et sa date
- [ ] Total entre 130 et 170 mots
- [ ] L'avant et l'après figurent tous les deux dans le rapport, avec les gestes nommés
