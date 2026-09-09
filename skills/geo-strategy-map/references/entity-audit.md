# Entity diagnosis

A model does not cite a page, it cites an entity it has learned. When the entity
is wrong, absent or confused with another company, content does not compensate.
This file is the check order, the evidence to collect, and the repair order.

## Table of contents

- [The test that comes first](#the-test-that-comes-first)
- [The seven checks](#the-seven-checks)
- [Repair order](#repair-order)
- [What to put in the report](#what-to-put-in-the-report)

## The test that comes first

Ask each engine, fresh session, no memory:

```
Qui est <brand> ?
Que fait <brand> ?
Où est basée <brand> et depuis quand ?
Qui a fondé <brand> ?
```

Run each three times, keep the raw answers, and build a two column table: what
the model said, what is true. Then classify each gap:

| Gap | Meaning | Priority |
|---|---|---|
| Confusion with another company | The entity is not separated in the model. Everything else is pointless until this is fixed | 1 |
| Wrong facts (year, country, size, founders) | The sources the model learned from are wrong or absent | 2 |
| Vague but not wrong ("a software company") | Thin entity, no distinctive attribute learned | 3 |
| Outdated (a product removed two years ago) | Stale sources still dominate | 4 |
| No answer at all | The entity is unknown, the plan starts at zero | 1 |

What the model gets wrong designates exactly what to correct, and in what order.
This table goes into the report verbatim, because it is the finding a client
remembers.

## The seven checks

**1. Name consistency.** The exact string, everywhere: site, JSON-LD `name`,
social profiles, directories, invoices, press, app stores. Variants ("Acme",
"Acme SAS", "ACME Group", "acme.fr") split the entity across several learned
nodes. Pick one canonical form, list every variant found, and note which
properties still carry the wrong one. Evidence: the list of URLs and the string
each one shows.

**2. Organization JSON-LD.** One `Organization` (or the right subtype) on the
home page with `name`, `url`, `logo`, `description`, `foundingDate`, `address`,
and `sameAs` pointing at the profiles that actually carry authority: LinkedIn,
Wikidata, Crunchbase, GitHub, the sector directory, the professional register.
`sameAs` is the link that ties the site to the nodes the model already knows.
Evidence: the rendered JSON-LD, not the plugin setting.

**3. Presence in ingested bases.** Wikidata first, because it is structured,
public, and reused everywhere. Then Crunchbase, the national business register,
and the two or three sector directories the market recognises. Check that the
facts there match the site. A wrong founding year in a public base is a wrong
founding year in the answers.

**4. About page made of facts.** Founding year, headcount bracket, location,
founders with names, what the company sells in one sentence, and the number of
customers or years of operation if it can be stated honestly. Verifiable facts,
dated. Marketing prose ("we are passionate about") teaches a model nothing and
is never quoted.

**5. Authors.** Articles signed by a named person, with a biography page,
credentials, and `Person` JSON-LD linked to the Organization through
`worksFor` and `author`. An unsigned article is an orphan document.

**6. Agreement between the site and third parties.** Compare what the site says
with what LinkedIn, directories, review platforms and press say: headcount,
positioning, pricing, product names. Every disagreement is a place where the
model picks one version, and it is usually not the site's.

**7. The contradiction sweep.** Search the site for facts that contradict each
other across pages: two founding years, two headcounts, an old product name kept
in the footer. Internal contradiction is the cheapest thing to fix and the most
common cause of a hedged answer.

## Repair order

1. Anything causing confusion with another entity.
2. Wrong public facts in ingested bases, starting with Wikidata.
3. `sameAs` and the Organization JSON-LD, so the nodes are tied together.
4. The about page rewritten as dated facts.
5. Name variants normalised on the properties the client controls.
6. Authors and Person markup.
7. Third party disagreements, which take the longest because they need other
   people to act.

Entity repairs belong in wave 1 of the plan. They are cheap, they are one time,
and content produced before them lands on a broken foundation.

## What to put in the report

A `findings` block, one item per gap, severity mapped from the priority table:

- `high`: confusion, unknown entity, wrong facts in a public base.
- `medium`: missing `sameAs`, marketing about page, unsigned articles.
- `low`: name variants on properties the client does not control.
- `info`: agreements to obtain from third parties.

Fill `evidence` with the quoted model answer or the exact string found on the
property, and `action` with something doable this week. Quote the model, do not
paraphrase it: a client argues with a paraphrase and accepts a quote.
