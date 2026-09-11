# Livrables en français

À charger quand l'utilisateur écrit en français. Le rapport, les tableaux et
le message au client sont en français, sans exception.

## Vocabulaire constant

| Terme | À employer | À éviter |
|---|---|---|
| migration, refonte, bascule | « la bascule du 15 juillet » | « la mise en prod » dans un livrable client |
| plan de redirection | « le plan » | « le mapping » |
| ancienne URL, nouvelle page | | « source », « cible » hors tableau technique |
| redirection permanente (301) | | « redirection définitive » |
| page qui répond 410 | « supprimée volontairement » | « page morte » |
| clics | chiffre Search Console | « visites », « trafic » quand il s'agit de clics |

## Verdicts types

Une phrase, un constat, un chiffre observé :

- « 6 anciennes URL qui recevaient 350 clics n'arrivent pas sur la bonne page »
- « Les redirections tiennent, trop tôt pour juger le trafic : 12 jours depuis la bascule »
- « Le site a retrouvé 94 % de ses clics, deux pages ont perdu plus que le reste »
- « Une page sur trois arrive sur une page encore en noindex depuis la préproduction »

## Le message au client, le jour de la bascule

> Bonjour,
>
> La bascule est faite. Nous avons testé une à une les 214 anciennes adresses
> qui recevaient des visites : 208 arrivent sur leur nouvelle page. Les 6
> autres sont corrigées dans l'heure, la liste est dans le rapport joint.
>
> Les semaines qui viennent, Google remplace progressivement les anciennes
> adresses par les nouvelles. Il indique lui-même que cela prend « quelques
> semaines ou plus » : une baisse temporaire est normale, et nous la suivons
> chaque semaine. Premier point chiffré dans 28 jours.

Adapter les chiffres, ne jamais en ajouter un qui n'est pas dans `live.json`
ou dans `proof.json`.

## Ce qu'on ne promet jamais

Une date de retour du trafic, une position, un volume. On cite Google
(« quelques semaines ou plus ») et la mesure de SALT.agency (médiane de 304
jours sur 1 052 migrations de domaine), et on s'engage sur ce qu'on contrôle :
les redirections testées, les 404 traitées, le suivi chaque semaine.
