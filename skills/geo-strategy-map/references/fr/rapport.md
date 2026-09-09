# Gabarits FR du livrable

À charger quand l'utilisateur écrit en français. Le livrable entier est en
français : titre, verdict, KPI, quadrants, plan, constats, note de méthode.
Mettre `"lang": "fr"` dans `meta`, le moteur bascule ses libellés internes.

## Table des matières

- [Vocabulaire imposé](#vocabulaire-imposé)
- [Titre, verdict, détail](#titre-verdict-détail)
- [Libellés des KPI](#libellés-des-kpi)
- [Familles de prompts](#familles-de-prompts)
- [Les quatre quadrants](#les-quatre-quadrants)
- [Colonnes du plan 90 jours](#colonnes-du-plan-90-jours)
- [Constats d'entité](#constats-dentité)
- [Checklist du protocole](#checklist-du-protocole)
- [Note de variance](#note-de-variance)
- [Phrases interdites](#phrases-interdites)

## Vocabulaire imposé

Un mot, un sens, dans tout le livrable.

| Terme | Emploi |
|---|---|
| relevé | une campagne de mesure complète, datée |
| observation | une ligne du CSV : un prompt, un moteur, une exécution |
| répétition | le numéro d'exécution d'un même prompt sur un même moteur |
| taux de présence | observations citées / observations |
| famille de prompts | une des six familles d'intention |
| seuil de bruit | l'écart minimal en dessous duquel rien n'est démontré |
| vague | une des trois périodes de 30 jours |

Ne jamais écrire « score GEO », « ranking IA » ni « position dans ChatGPT ».

## Titre, verdict, détail

Titre : `Carte de stratégie GEO`. Court, sans explication après deux points.

Verdict, gabarit à remplir avec des chiffres du relevé :

> La marque est citée dans X réponses sur Y, absente de la famille F, et dans
> Z % des citations c'est un site tiers qui est pointé, pas le vôtre.

Détail, deux lignes :

> Relevé du DATE : N prompts, M moteurs, R répétitions, T observations. Le plan
> attaque d'abord la famille F, où le volume est le plus fort et la présence la
> plus faible.

## Libellés des KPI

- `Prompts cartographiés`
- `Taux de présence global`
- `Moteur le plus favorable`
- `Familles sans présence observée`

Chaque `note` porte le dénominateur : « 86 observations citées sur 306 ».

## Familles de prompts

| Clé technique | Libellé FR du livrable |
|---|---|
| category-discovery | Découverte de catégorie |
| named-comparison | Comparaison nommée |
| qualification | Qualification |
| replacement | Remplacement |
| implementation | Mise en oeuvre |
| objection | Objection |

## Les quatre quadrants

Ordre attendu par le moteur : haut gauche, haut droite, bas gauche, bas droite.

| Quadrant | Titre FR | `reading` |
|---|---|---|
| Volume faible, présence forte | Surveiller | Acquis peu volumineux. Un contrôle par vague, aucun investissement. |
| Volume fort, présence forte | Défendre | Ça fonctionne. Garder les pages fraîches et datées, surveiller le déplacement par un concurrent. |
| Volume faible, présence faible | Ignorer | Hors périmètre ce trimestre, et c'est écrit pour que personne n'y passe une journée par accident. |
| Volume fort, présence faible | Attaquer | Volume fort, présence faible. C'est là que passent les 90 jours. |

`axes` : `{"x": "Axe horizontal : volume de la famille (prompts x poids)", "y":
"Axe vertical : présence mesurée au relevé initial"}`

## Colonnes du plan 90 jours

`["Vague", "Action", "Famille", "Pourquoi maintenant", "Jours", "Responsable",
"Preuve"]`, `numeric_columns: [4]`.

Légende sous la table : « Score = (prompts x poids x (1 - présence)) / jours.
Trié par score décroissant. »

## Constats d'entité

Gabarits de titres, à compléter avec la citation brute du modèle :

- « Le modèle attribue une année de création erronée »
- « Le modèle confond la marque avec une autre société »
- « Aucun `sameAs` ne relie le site aux profils qui font autorité »
- « La page à propos ne contient aucun fait vérifiable »
- « Les articles ne sont signés par personne »

`Constat` : la réponse du modèle citée mot pour mot, avec le moteur et la date.
`Ce qu'il faut faire` : une seule action, faisable cette semaine.

## Checklist du protocole

```
Jeu de prompts figé et versionné (prompts-v1.csv)
3 répétitions par prompt et par moteur
Sessions neuves, sans mémoire ni personnalisation
Réponses brutes conservées, un fichier par exécution
URL réellement citée relevée pour chaque citation
Relevé de contrôle programmé à J+30
```

## Note de variance

`tone: "warn"`, titre « Ce que ces chiffres ne peuvent pas montrer » :

> Les réponses varient d'une exécution à l'autre à question identique. Avec N
> observations par relevé, aucun écart inférieur à S points ne peut être présenté
> comme un résultat, et les répétitions d'un même prompt étant corrélées, le
> seuil réel est plus large que S, jamais plus étroit. Un relevé mesure ce que
> les moteurs ont répondu à cette date depuis ce pays, pas un classement.

## Phrases interdites

Aucune promesse de position, de trafic ou de citation, dans aucun objectif de
vague. Formuler les objectifs en travail livré et en faits corrigés.

- Interdit : « atteindre 50 % de présence », « être cité par ChatGPT », « gagner
  la première place dans les réponses ».
- Correct : « l'année de création et le pays sont exacts dans les réponses des
  trois moteurs, vérifié sur un relevé daté », « la page de migration existe,
  énonce les cinq points de rupture, et sera relue au prochain relevé face au
  seuil de bruit ».
