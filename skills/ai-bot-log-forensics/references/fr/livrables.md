# Gabarits FR, formulations prêtes pour le livrable

À charger uniquement quand l'utilisateur écrit en français. Mettre
`"lang": "fr"` dans `meta`, le moteur bascule ses libellés internes tout seul.

Vocabulaire constant sur tout le livrable, ne jamais alterner :

| Notion | Terme retenu | À ne pas écrire |
|---|---|---|
| une requête d'un robot dans le log | un **passage** | une visite, une session, un hit |
| l'ensemble des passages d'un robot | le **crawl** | le scan, l'exploration |
| passage dont l'origine est prouvée | **vérifié** | authentifié, confirmé |
| passage prouvé non conforme | **usurpé** | faux, frauduleux |
| passage sans preuve dans un sens ni l'autre | **invérifiable** | inconnu, douteux |
| récupération temps réel déclenchée par une question | **récupération temps réel** | visite ChatGPT |

Un passage n'est pas une visite. Le mot visite fait croire à un humain et à une
session, et c'est exactement le malentendu que ce livrable existe pour lever.

## Traduction des finalités

| Clé du parser | Libellé FR | Une phrase pour le client |
|---|---|---|
| `training` | Entraînement | Le contenu est collecté pour de futurs modèles, sans lien avec une question posée aujourd'hui |
| `user_fetch` | Récupération temps réel | Quelqu'un a posé une question et le modèle est allé chercher cette page maintenant |
| `search` | Index de réponse | Le contenu est indexé pour pouvoir être cité au moment d'une réponse |
| `preview` | Aperçu de lien | Un lien a été collé quelque part, ce n'est pas un signal IA |

## Verdicts, trois patrons

Un verdict est un constat chiffré, jamais une description de l'analyse.

> Quatre robots IA ont atteint le site 1 812 fois en août, et aucun n'a lu une
> page produit.

> ChatGPT est venu chercher 47 pages en temps réel après des questions
> d'utilisateurs, toutes éditoriales, aucune sur l'offre.

> GPTBot reçoit un 403 sur la totalité de ses 1 240 requêtes depuis le 12 août :
> le site est aujourd'hui illisible pour OpenAI.

À proscrire : « Analyse du trafic des robots IA » (c'est un titre), « le trafic
progresse de 34 % » (aucune conséquence), toute phrase qui promet une position,
une citation ou un volume de trafic.

## Libellés de KPI

| Libellé | Note dessous |
|---|---|
| Passages robots IA vérifiés | Répartition par robot, ex. GPTBot 61 %, ClaudeBot 22 % |
| Taux de vérification | X passages usurpés, écartés de tous les chiffres |
| Récupérations temps réel | Signal de demande réelle, N pages concernées |
| Erreurs servies aux robots | N passages en 4xx ou 5xx sur N |
| Couverture du sitemap | N URL sur N atteintes sur la période |
| Invisible en analytics | Aucun de ces passages n'exécute JavaScript |

## Lectures des quatre quadrants

Une phrase par quadrant, telle quelle.

- **Crawlée et citée** : « Ça fonctionne. C'est le gabarit à répliquer sur le
  reste du site. »
- **Citée sans être crawlée** : « Le modèle vous connaît par une source tierce.
  Vous ne contrôlez ni ce qui est dit, ni sa fraîcheur. »
- **Crawlée sans être citée** : « Problème de citabilité, pas d'accès. La page
  est lue, puis jugée inutilisable. »
- **Ni crawlée ni citée** : « Problème d'accès. À vérifier dans l'ordre :
  robots.txt, pare-feu, sitemap, maillage interne, temps de réponse. »

Sans relevé de citations, garder les quatre cases et remplir les deux du bas
avec :

> Aucun relevé de citations fourni. Cette moitié demande un relevé manuel,
> décrit dans la partie méthode de ce document, ou un outil de suivi de
> citations.

## Constats, formulations types

- « Le catalogue produit est hors du champ de crawl des robots IA »
- « Un pare-feu bloque silencieusement GPTBot depuis le 12 août »
- « 11,5 % des passages revendiqués sont usurpés et n'ont pas été comptés »
- « Le crawl part dans les paramètres d'URL au lieu des pages de l'offre »
- « 63 pages sont lues à répétition et jamais citées »
- « PerplexityBot a disparu du log entre juillet et août »

Chaque constat porte son chiffre observé dans le champ `evidence`, et une action
faisable cette semaine dans `action`. Pas « améliorer la crawlabilité », mais
« vérifier que /produits/ n'est pas exclu du robots.txt, puis le lier depuis les
cinq articles les plus crawlés listés plus haut ».

## Note de limites, à copier

Titre : **Ce que ce rapport ne peut pas montrer**, ton `warn`.

> Un access log prouve qu'une page a été lue, jamais qu'elle a été citée. Les
> passages marqués invérifiables proviennent de fournisseurs qui ne publient ni
> plage IP ni domaine de résolution inverse : ils sont comptés à part et jamais
> présentés comme vérifiés. Les passages usurpés sont exclus de tous les
> chiffres. Un passage de robot n'est ni une visite ni une session, et aucun de
> ces passages n'apparaîtra jamais dans un outil analytics à base de JavaScript.
> La période couverte est celle du fichier réellement fourni, pas celle demandée.

## Légende sous le tableau des robots

> Source : access log <format>, du <date> au <date>. Vérification par les plages
> IP publiées par chaque fournisseur et par résolution inverse puis directe.
> Les requêtes qui portent un nom de robot sans provenir du fournisseur sont
> exclues de tous les chiffres de ce rapport.

## Checklist de fin

- Logs récupérés sur N jours complets
- Plages IP fournisseurs rafraîchies le <date>
- Relevé de citations sur N prompts
- robots.txt et pare-feu vérifiés
- Contre-mesure appliquée et recontrôlée

## Chiffres en français

Espace insécable avant les signes doubles, virgule décimale, espace comme
séparateur de milliers : « 1 812 passages », « 11,5 % », « 4,2 s ». Dates en
toutes lettres dans le verdict (« depuis le 12 août »), format ISO uniquement
dans les tableaux techniques.
