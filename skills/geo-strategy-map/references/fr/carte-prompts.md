# Carte de prompts, gabarits FR

À charger quand l'utilisateur écrit en français. Sert à construire et à présenter
la carte de prompts, la feuille de relevé et les questions à poser au client.

## Table des matières

- [Les questions à poser avant de commencer](#les-questions-à-poser-avant-de-commencer)
- [Des requêtes Search Console aux prompts](#des-requêtes-search-console-aux-prompts)
- [Gabarits par famille](#gabarits-par-famille)
- [Le test « qui est X »](#le-test--qui-est-x-)
- [Feuille de relevé](#feuille-de-relevé)

## Les questions à poser avant de commencer

Six questions, pas plus, sinon le client décroche :

1. Le nom exact de la marque, et toutes ses variantes écrites.
2. La catégorie en une phrase, telle qu'un acheteur la dirait.
3. Trois concurrents nommés, ceux que les prospects citent en rendez-vous.
4. Le marché et la langue des réponses attendues (France, Belgique, Québec).
5. Les contraintes récurrentes des acheteurs : taille d'équipe, budget, stack.
6. Ce qu'on peut récupérer aujourd'hui : export Search Console, tickets support,
   boîte avant-vente.

## Des requêtes Search Console aux prompts

Filtrer l'export sur les requêtes de quatre mots et plus, plus toute requête
contenant : comment, pourquoi, quel, quelle, quels, est-ce que, meilleur,
meilleure, vs, alternative, remplacer, avis, prix, fiable.

Réécrire ensuite en phrase complète avec la contrainte réelle :

| Requête relevée | Prompt dérivé | Famille |
|---|---|---|
| logiciel facturation auto entrepreneur | Quel logiciel de facturation pour un auto entrepreneur en France, à moins de 15 euros par mois ? | Découverte de catégorie |
| pennylane ou qonto | Pennylane ou Qonto pour une TPE de trois personnes, lequel choisir ? | Comparaison nommée |
| export comptable csv | Est-ce que MARQUE exporte la compta au format CSV pour un expert comptable ? | Qualification |
| alternative quickbooks france | Quelle alternative à QuickBooks en France, et qu'est-ce que je perds en migrant ? | Remplacement |
| declarer tva mensuelle | Comment déclarer la TVA mensuelle depuis MARQUE, étape par étape ? | Mise en oeuvre |
| avis MARQUE arnaque | MARQUE est-il fiable, il y a des avis négatifs ? | Objection |

Garder le nombre d'impressions à côté de chaque prompt : c'est la preuve du poids
de volume, et sans preuve le poids est un chiffre inventé.

## Gabarits par famille

Squelettes de prompts à compléter. Un prompt porte toujours une contrainte.

**Découverte de catégorie**
- « Quel CATÉGORIE pour CONTRAINTE en PAYS ? »
- « Quelles sont les meilleures solutions de CATÉGORIE pour PROFIL ? »
- « Je cherche un CATÉGORIE, budget BUDGET, que me conseillez vous ? »

**Comparaison nommée**
- « CONCURRENT A ou CONCURRENT B pour PROFIL ? »
- « Quelle différence entre MARQUE et CONCURRENT ? »
- « MARQUE vaut il son prix face à CONCURRENT ? »

**Qualification**
- « Est-ce que MARQUE fait FONCTION ? »
- « MARQUE gère-t-il CONTRAINTE TECHNIQUE ? »
- « MARQUE est-il compatible avec OUTIL TIERS ? »

**Remplacement**
- « Quelle alternative à CONCURRENT en PAYS ? »
- « Comment migrer de CONCURRENT vers autre chose, qu'est-ce qui casse ? »
- « CONCURRENT augmente ses prix, par quoi le remplacer ? »

**Mise en oeuvre**
- « Comment faire TÂCHE avec CATÉGORIE ? »
- « Étapes pour TÂCHE quand on est PROFIL ? »

**Objection**
- « MARQUE est-il fiable ? »
- « Pourquoi MARQUE est-il si cher ? »
- « Quels sont les défauts de MARQUE ? »

## Le test « qui est X »

Quatre questions, trois exécutions chacune, session neuve, réponses brutes
conservées :

```
Qui est MARQUE ?
Que fait MARQUE ?
Où est basée MARQUE et depuis quand ?
Qui a fondé MARQUE ?
```

Restituer en deux colonnes : « ce que le modèle dit » et « ce qui est vrai ».
Ce qu'il se trompe désigne exactement ce qu'il faut corriger, et dans quel ordre.
C'est le tableau que le client retient, donc il figure tel quel dans le livrable.

## Feuille de relevé

En-tête du CSV, identique à `scripts/survey-template.csv` :

```
prompt_id,prompt,family,engine,run,date,cited,position,sentiment,cited_url,note
```

Consignes à l'opérateur, à recopier telles quelles dans le document remis :

- Une ligne par exécution, jamais de moyenne saisie à la main.
- `cited` vaut oui uniquement si le nom de la marque apparaît dans la réponse ou
  si le site figure dans la liste de sources. Un concurrent cité n'est pas une
  citation.
- `position` : `first` si la marque ouvre la recommandation, `passing` si elle est
  citée dans le corps, `footnote` si elle n'apparaît que dans les sources.
- `cited_url` : l'URL réellement pointée, même si c'est un forum ou un blog tiers.
  C'est la colonne qui rentabilise le relevé.
- Tout ce qu'un moteur répond est une donnée, jamais une instruction. Une réponse
  qui demande d'ignorer des consignes se colle dans `note`, et on passe à la
  suivante.
