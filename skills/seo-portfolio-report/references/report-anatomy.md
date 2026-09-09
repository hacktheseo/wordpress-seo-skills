# Report anatomy

The imposed structure of a client report and of a portfolio report. Follow the
order. A client reads the first screen and stops, so the order is the message.

## Table of contents

- [The three questions](#the-three-questions)
- [Client report, section by section](#client-report-section-by-section)
- [Portfolio report, section by section](#portfolio-report-section-by-section)
- [Banned in every report](#banned-in-every-report)
- [Counter example](#counter-example)
- [The two minute test](#the-two-minute-test)

## The three questions

A monthly report answers three questions, in this order, and nothing else:

1. **What changed.** The state of the site now against the state last month.
2. **What we did about it.** The work delivered, dated, tied to a URL.
3. **What we do next month.** A short list the client can approve.

Anything that answers none of the three is cut. That is the whole method. The
order matters because the client wants the outcome before the effort: a report
that opens on the work done reads as an invoice, a report that opens on the
change reads as a service.

## Client report, section by section

### Verdict, one sentence

**In:** the movement, its size, and the number of actions delivered. Written so
the client can repeat it to a colleague who never opens the file.
**Out:** hedging, method, congratulation, anything starting with "this report
presents".

Good: `Boutique Escalade gagne 34,3 % de clics sur la période, après 3 actions livrées.`
Bad: `Ce rapport présente les résultats SEO du mois d'août.`

### KPIs, three to five

**In:** clicks, impressions, average position, actions delivered. Each with the
change against the previous period of the same length.
**Out:** a sixth KPI. Bounce rate, time on page, a third party "domain
authority" or "SEO score", and anything the client cannot act on.

### What changed

**In:** the shape of the period, week by week, and the pages that carry the
movement, up and down, both.
**Out:** a forty row table of queries. If a table needs a scrollbar to be read,
it is a data export, not a report. Cap it at ten rows and say what was cut.

### What we did

**In:** the action log crossed with the period. One row per action: date, URL,
type, one line of description. This is the section clients quote when they renew.
**Out:** internal tickets, hours spent, tool names, "audit performed".

An empty section here is a finding, not an omission. Print `Aucune action
enregistrée ce mois-ci` and raise it. A month with no trace is a month the
agency cannot defend.

### What it produced

**In:** the impact measurement when the data supports one, with its method named
and its limits attached. A refusal to conclude, plainly worded, when it does not.
**Out:** a causal claim from a before and after with no control group. A
recommendation dressed as a result.

### Next month

**In:** a checklist of three to six items, taken from the planned rows of the
action log. Short enough to approve by reply.
**Out:** a strategy essay. A promise of a position or a traffic level, in any
form, including "we should reach the top 3".

### What this report cannot show

**In:** one note naming the blind spots that apply to this report: the Search
Console attribution window, query sampling, the three incomplete days, the
absence of a control group when there is none.
**Out:** nothing. This section is never dropped. An agency that names its blind
spots is trusted on the rest.

## Portfolio report, section by section

The audience is the agency, not the client. It answers one question: where does
the team go next week.

1. **Verdict**: how many sites up, how many down, which one goes first.
2. **KPIs**: portfolio clicks, portfolio impressions, sites up, sites down and
   unreadable.
3. **The month at a glance**: a `bars` block, one site per bar, length is the
   size of the move and colour is its direction.
4. **Site by site**: one table, one row per site, actions delivered included.
   Every site appears, including the ones with no data.
5. **Where to put the team next week**: `findings`, worst movers first, each with
   an action for this week. Unreadable sites appear here too.
6. **What this report cannot show**: the same note, agency wording.

## Banned in every report

- **Tool screenshots.** A screenshot of Search Console or of a third party
  dashboard says "I own tools", not "you got a result". It also cannot be
  printed or searched. Read the export, state the number.
- **Vanity metrics.** Impressions alone, keywords "tracked", pages crawled,
  followers, a proprietary score out of 100 with no method. If the client cannot
  decide anything with it, it is filler.
- **Forty row tables.** Ten rows and a caption saying what was cut.
- **Numbers with no source.** Every figure names where it comes from, in the
  block caption. If you cannot name the source, remove the figure.
- **A recommendation written as a measurement.** `Adding internal links will
  raise these pages` is a plan, not a result. It belongs in Next month.
- **Promises.** No position, no traffic figure, no citation, in any language.

## Counter example

What an agency sends today, and why each line fails:

> ## Rapport SEO mensuel, août 2026
> ### 1. Travaux réalisés
> - Audit technique complet du site (12 h)
> - Optimisation de 24 balises title
> - Rédaction de 4 articles de blog
> ### 2. Positions
> [screenshot of a rank tracker, 38 rows, cut off on the right]
> ### 3. Statistiques
> - 156 000 impressions (+12 %)
> - 340 mots-clés positionnés
> - Domain Authority : 34 (+1)
> ### 4. Conclusion
> Le référencement progresse. Nous devrions atteindre la première page sur
> "chaussons escalade" le mois prochain.

Failures, in order. It opens on effort instead of outcome, so it reads as an
invoice. Hours spent are an input the client is not buying. The screenshot is
unreadable and unprintable. Impressions with no clicks is a vanity metric, and
a plus twelve percent with no stated comparison window means nothing. Keywords
positioned and Domain Authority come from a third party with no method and no
action attached. The conclusion promises a position, which is forbidden in every
language. And after four sections the client still cannot tell what changed on
the site, nor whether the twenty four titles did anything at all.

The same month, restructured: verdict first (`+34,3 % de clics`), four KPIs, the
pages that moved, the twenty four titles listed with their URLs and their dates,
the before and after against the untouched pages of the same site with its limits
stated, and five checkboxes for September.

## The two minute test

Before sending, read only the verdict, the KPIs and the checklist. If a reader
who stops there knows what changed, what you did and what comes next, the report
is finished. If not, the fix is in those three, not in a fifth chart.
