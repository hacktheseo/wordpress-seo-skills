# Prompt taxonomy

The six GEO intent families, how to recognise one, what content wins it, and the
trap that wastes a quarter. Read this before classifying the prompt map.

## Table of contents

- [Why families and not keywords](#why-families-and-not-keywords)
- [Turning owned material into prompts](#turning-owned-material-into-prompts)
- [The six families](#the-six-families)
- [Classification rules](#classification-rules)
- [Volume weight](#volume-weight)
- [Sizing the map](#sizing-the-map)

## Why families and not keywords

A keyword groups strings. A family groups **the shape of the answer the engine
produces**, and therefore the shape of the content that gets pulled into it. Two
prompts with almost the same words belong to different families when the answer
differs: "quel CRM pour une PME" produces a shortlist, "est-ce que Pipedrive fait
de la facturation" produces a yes or a no. A shortlist is won with a category
page, a yes or no is won with a factual feature page. Planning by keyword mixes
them and produces content that wins neither.

## Turning owned material into prompts

Ranked by value, because the first two are free and nobody uses them.

**Search Console export.** Filter to queries of four words or more, plus every
query containing an interrogative form (comment, pourquoi, quel, quelle, est-ce
que, meilleur, vs, alternative, how, what, which, best). Rewrite each as a full
sentence and add the constraint a real buyer carries: team size, country, budget,
stack, deadline. One query yields one to three prompts. Keep the impressions
figure next to the prompt, it becomes the volume evidence.

**Support and pre-sales questions.** Take the last 100 tickets and the sales
inbox. These are already prompts: they are long, conversational and constrained.
They are also the only source that reveals objection prompts, which never appear
in Search Console because nobody types "is X reliable" into Google, they ask a
model. Count how many times each question recurs, that count is the weight.

**People Also Ask.** Harvest on the three category head terms. Useful for
qualification and implementation, weak for comparison.

**Forum and Reddit thread titles.** Take them verbatim, including the sloppy
phrasing. Models trained on these pages reproduce their vocabulary, and threads
are frequently the third party source cited instead of the client site.

**Competitor comparisons.** The competitors' own comparison pages, their
"alternatives" pages, and autocomplete on "X vs", "alternative à X". Every
competitor named in those pages is a candidate for a named-comparison prompt.

Record for each prompt: id, text, family, source, and the observed figure that
justifies its weight. A prompt with no source does not enter the map.

## The six families

### 1. category-discovery

Shape: "quel outil pour", "meilleur logiciel de", "what is the best X for Y".
The engine returns a shortlist of three to six names with one line each.

Wins it: a **category page** that states explicit selection criteria, names the
use cases, and compares options including competitors. Models reuse criteria
lists, so the page must contain the criteria in plain sentences, not in a
marketing grid.

Trap: writing about the product instead of the category. A product page is never
pulled into a shortlist answer, because the answer needs a frame to rank inside.

### 2. named-comparison

Shape: "X ou Y", "X vs Y", "différence entre X et Y".
The engine returns a balanced paragraph, often a table.

Wins it: a **first person comparison page** that is honest about where the other
option wins. Models penalise one sided pages by pulling the balanced third party
instead, which is exactly how a comparison blog ends up cited in place of the
client site.

Trap: refusing to name the competitor. If the brand never writes the competitor
name, the only pages containing both names are other people's.

### 3. qualification

Shape: "est-ce que X fait Z", "does X support Z", "X gère-t-il Z".
The engine returns a yes, a no, or a hedge, plus one justification.

Wins it: a **factual feature page**, one claim per sentence, each claim dated and
verifiable. Feature matrices in images are invisible. A hedged answer usually
means the fact exists on the site but is buried in a paragraph.

Trap: answering with a benefit ("gagnez du temps") where a fact is required
("exporte au format CSV et XLSX, depuis la version 3.2").

### 4. replacement

Shape: "alternative à X", "remplacer X", "migrer de X vers".
The engine returns a list of substitutes with a migration comment.

Wins it: a **migration page**: what changes, what breaks, what is lost, how long
it takes, what it costs. The most under-produced content type in every sector,
and the one with the clearest buying intent.

Trap: producing a comparison page and calling it a migration page. The reader in
this family has already decided to leave, they need the operation, not the
argument.

### 5. implementation

Shape: "comment faire Z", "how to Z", "guide pour Z".
The engine returns a procedure and cites whoever wrote the clearest one.

Wins it: a **numbered procedure** with prerequisites, steps, and a verifiable end
state. Usually the family where a brand already has presence, because this is
what blogs produce. Check before investing: it is often a defend, not an attack.

Trap: spending the quarter here because it is comfortable to write.

### 6. objection

Shape: "X est-il fiable", "X est-il cher", "avis sur X", "is X secure".
The engine assembles third party signals: reviews, incidents, forums, pricing
pages.

Wins it: **public evidence**, not prose. Visible pricing, an uptime or status
page, a security page, documented support terms, and third party reviews that
exist. Content on the site alone rarely moves this family, which is why it must
be planned as an evidence task, not a writing task.

Trap: treating a zero presence on objection prompts as a content gap. It is
usually an evidence gap, and sometimes a reputation fact the client must fix in
the real world first.

## Classification rules

- One prompt, one family. If it fits two, classify by the shape of the answer the
  engine actually returned during the baseline survey, not by the wording.
- A prompt naming a competitor is `named-comparison`, unless it also carries
  "alternative", "remplacer" or "migrer", which makes it `replacement`.
- A prompt starting with "est-ce que" and expecting yes or no is `qualification`
  even when it names a competitor.
- A prompt containing "avis", "fiable", "arnaque", "cher", "lent" is `objection`
  even when it looks like qualification.
- Anything left over goes to `category-discovery` only if it asks for a
  shortlist. Otherwise drop it from the map rather than force it.

## Volume weight

Weight 1 to 3, and the weight is never a feeling:

| Weight | Evidence required |
|---|---|
| 3 | The family maps to queries above the median impressions of the export, or to the ten most recurring support questions |
| 2 | Present in the sources, below the median, recurring at least three times |
| 1 | Present once or twice, kept for coverage |

Write the evidence next to the weight in the report. A weight with no counted
source is an invented number.

## Sizing the map

- 40 to 80 prompts total. Below 40 the presence rate per family is unreadable,
  above 80 the survey stops being repeatable by a human every 30 days.
- 5 to 12 prompts per family. A family with fewer than 5 prompts cannot support
  a rate, report it as an observation and not as a percentage.
- Three engines and three runs turn 40 prompts into 360 observations, which is
  roughly four hours of manual work. Say that number to the client before they
  commit to the protocol.
