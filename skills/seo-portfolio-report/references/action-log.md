# The action log

The bridge between the work delivered and the result observed. Without it, the
question "what did you do for us this month" has no answer, and the impact
measurement has no action date to test.

Five columns, one CSV, kept as you work. It takes ten seconds per action, and it
is the reason a client renews.

## Table of contents

- [Format](#format)
- [Columns](#columns)
- [Example](#example)
- [How the skill uses it](#how-the-skill-uses-it)
- [With a subscription, it fills itself](#with-a-subscription-it-fills-itself)
- [Habits that make it work](#habits-that-make-it-work)

## Format

`actions.csv`, UTF-8, one row per action, comma or semicolon separated.

```
date,site,url,type,description,statut
```

Column names are matched case and accent insensitively, in French and English:
`date/jour`, `site/domaine/client`, `url/page/lien`, `type/action/categorie`,
`description/detail/commentaire`, `status/statut/etat`. Order does not matter.
Only `date` and `site` are required for the file to be read at all.

## Columns

| Column | Content |
|---|---|
| `date` | ISO date the action went live, not the date it was decided |
| `site` | The `id`, `domain` or `client` of the site in `portfolio.json` |
| `url` | The page touched, path or full URL. Leave empty for a site wide action |
| `type` | One word from a fixed vocabulary, see below |
| `description` | One line the client can understand. No ticket number, no tool name |
| `statut` | `fait` or `done` (default), or `prevu` / `planned` for next month |

Keep the type vocabulary short and stable, or the reports stop being comparable
from one month to the next. A workable set: `contenu`, `technique`, `maillage`,
`schema`, `redirection`, `performance`, `netlinking`. Use the same words in the
same language every month.

The `description` is written for the client, not for the team. `Réécriture du
guide des tailles, ajout d'un tableau de correspondance` is a description.
`Fix #4412` is not.

## Example

```csv
date,site,url,type,description,statut
2026-08-05,boutique-escalade,/guides/tailles/,contenu,"Réécriture du guide des tailles, ajout d'un tableau de correspondance",fait
2026-08-05,boutique-escalade,/blog/choisir-ses-chaussons/,maillage,6 liens internes ajoutés vers les fiches produit,fait
2026-08-12,boutique-escalade,/produits/corde-9-2/,technique,Balise title et meta description réécrites,fait
2026-08-19,cabinet-mercier,/honoraires/,contenu,"Page honoraires réécrite, FAQ ajoutée",fait
2026-09-15,boutique-escalade,/produits/,maillage,Cocon produits : relier les 40 fiches orphelines,prévu
```

## How the skill uses it

1. **What we did.** Rows for this site, with a date inside the period and a done
   status, become the table of the section. Straight from the log, no rewriting.
2. **Next month.** Rows with a planned status and a date after the period become
   the checklist. The client approves it by replying to the email.
3. **Action count.** The number of rows per site becomes a KPI on the client
   report and a column on the portfolio table. A site with a heavy drop and zero
   actions is the first finding of the portfolio report.
4. **Impact.** The date of an action is the `--action` argument of `impact.py`,
   and its `url` says which pages belong to the treated group. Everything else
   comparable on the site is the control group.

Two rows on the same date and the same page mean one action for the measurement,
not two. Group them before running the impact script.

## With a subscription, it fills itself

With a Pro or Ultra subscription, `hts_get_audit_trail` returns what the plugin
actually changed on the site, with dates and URLs, and fills this log without
anyone typing it. Anything done by hand, off platform, still has to be logged by
the agency: the trail records what passed through the plugin, not the article a
freelance writer published in WordPress.

Cross the two before writing the report. Where they disagree, the trail is right
about the plugin and the human log is right about everything else.

## Habits that make it work

- Log at deployment, not at the end of the month. A log written from memory on
  the 30th is a list of intentions.
- One row per action, one URL per row. It is what makes the treated group
  definable later.
- Log the client's own changes too, with the client as the author in the
  description. A redesign you did not know about explains a month you cannot
  otherwise explain.
- Never delete a row. A reverted action is a new row of type `rollback`.
