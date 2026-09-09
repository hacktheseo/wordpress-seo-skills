# Passage citability scoring

The scale used by `ai-citability-audit`. Read it before scoring, and quote the
band names from it in the report so two runs on the same page agree.

## Table of contents

- [What is scored, and why the passage](#what-is-scored-and-why-the-passage)
- [Weights](#weights)
- [Criterion 1: technical extractability, 20 points](#criterion-1-technical-extractability-20-points)
- [Criterion 2: autonomy, 15 points](#criterion-2-autonomy-15-points)
- [Criterion 3: direct answer, 15 points](#criterion-3-direct-answer-15-points)
- [Criterion 4: fact density, 15 points](#criterion-4-fact-density-15-points)
- [Criterion 5: interrogable form, 10 points](#criterion-5-interrogable-form-10-points)
- [Criterion 6: length, 10 points](#criterion-6-length-10-points)
- [Criterion 7: attribution, 8 points](#criterion-7-attribution-8-points)
- [Criterion 8: signalled freshness, 4 points](#criterion-8-signalled-freshness-4-points)
- [Criterion 9: internal competition, 3 points](#criterion-9-internal-competition-3-points)
- [Caps](#caps)
- [Bands and tones](#bands-and-tones)
- [Worked example](#worked-example)
- [What this scale is not](#what-this-scale-is-not)

## What is scored, and why the passage

A language model does not quote a page, it quotes a passage: a block short
enough to fit in an answer, self-contained enough to survive being cut out of
its page, and specific enough to be worth cutting out. Page-level scores
average a quotable block and a filler block into one meaningless number and
hide which paragraph did the work.

So the unit is the passage: one H2 or H3 section, or, for a section longer than
200 words, a block of 120 to 200 words cut at a paragraph boundary. The script
`scripts/segment_passages.py` produces those units and every measurable value
quoted below. Never score a criterion whose value you did not observe: write
`not measured` instead.

## Weights

| # | Criterion | Points | Why this weight |
|---|---|---|---|
| 1 | Technical extractability | 20 | The only criterion that can zero the rest. Text a crawler cannot read is not a weak passage, it is not a passage |
| 2 | Autonomy | 15 | The cut is the moment a passage lives or dies. An unresolved anaphora makes the block unusable outside its page |
| 3 | Direct answer | 15 | An answer engine assembles answers. A block that opens on context has to be rewritten to be used, and a block that has to be rewritten is usually dropped |
| 4 | Fact density | 15 | A model adds nothing to its answer by quoting a claim it could already generate. Verifiable specifics are the reason to quote a source |
| 5 | Interrogable form | 10 | The heading is what matches the query. A magazine title matches nothing anyone types |
| 6 | Length | 10 | Real weight but narrow range: outside 60 to 320 words a block is either empty or has to be summarised, and summarising loses the attribution |
| 7 | Attribution | 8 | Traceability inside the block itself makes a quote defensible. Lower weight because a good passage without a citable source still gets quoted |
| 8 | Signalled freshness | 4 | Page-level signal, identical for every passage of the page, so it separates pages, not passages |
| 9 | Internal competition | 3 | Small on one passage, decisive on a site: two blocks answering the same question split whatever authority the page has |

Total 100. Points 1 to 7 are measured on the passage, 8 on the page, 9 on the
pair.

## Criterion 1: technical extractability, 20 points

Operational test: is the text in the HTML the server sends, in semantic markup,
and is it text rather than links or pixels? Script fields:
`extractability.in_served_html`, `extractability.hazards`,
`extractability.link_word_ratio`, `extractability.in_table`.

| Points | Condition |
|---|---|
| 20 | In the served HTML, no hazard flag, `link_word_ratio` under 0.30 |
| 12 | In the served HTML but inside `details`, an accordion, a tab or a carousel |
| 6 | In the served HTML but a link list (`is_link_list` true) or inside a table with no `th` |
| 0 | Absent from the served HTML: injected by JavaScript, or in an image |

Reason for the harshest rule: the crawlers that feed answer engines fetch the
HTML and do not execute JavaScript. What is not in the served HTML does not
exist for them, whatever a browser shows.

## Criterion 2: autonomy, 15 points

Operational test: does the passage hold without the rest of the page? Count
unresolved references, do not judge the style. Script fields:
`autonomy.anaphora_count`, `autonomy.anaphora_in_first_sentence`,
`autonomy.opens_on_anaphora`, `autonomy.anaphora_terms`.

| Points | Condition |
|---|---|
| 15 | No anaphora, no back reference, every pronoun has its antecedent inside the passage |
| 11 | One or two anaphora, none in the first sentence |
| 6 | An anaphora in the first sentence, or three to four in the passage |
| 0 | Opens on an anaphora (`opens_on_anaphora`), or five or more |

The script catches the explicit markers (`cela`, `ce dernier`, `comme vu plus
haut`, `ci-dessus`, `the latter`, `as seen above`). Add by reading: a pronoun
whose antecedent sits in the previous section, and a numbered reference
(`the third criterion`) whose list is not in the passage.

## Criterion 3: direct answer, 15 points

Operational test: read the first sentence alone. Does it answer the question in
the heading? Script fields: `direct_answer.opens_on_context`,
`direct_answer.context_opener`, `first_sentence`, `first_sentence_words`.

| Points | Condition |
|---|---|
| 15 | The first sentence answers, and runs 15 to 40 words |
| 9 | The answer arrives in the second sentence |
| 4 | The answer arrives after 40 words or in the third sentence |
| 0 | `opens_on_context` is true, or the passage never answers its own heading |

The shape that works: the answer in 40 to 60 words, then the development.
`Before understanding X, you need to know that` is the canonical failure: the
model has to cut, and it does not cut, it moves on.

## Criterion 4: fact density, 15 points

Operational test: count what can be checked. Script field
`facts.density_per_100w`, computed as (numeric tokens + unique proper nouns)
per 100 words, with `facts.numbers`, `facts.years`, `facts.percentages`,
`facts.units`, `facts.proper_nouns` broken out.

| Points | Density per 100 words |
|---|---|
| 15 | 8 or more |
| 11 | 5 to 7.9 |
| 6 | 2 to 4.9 |
| 2 | 0.1 to 1.9 |
| 0 | 0, no number, no date, no proper noun, no threshold |

Read the value before trusting it: a nav list of brand names scores high on
proper nouns and is worthless. Fact density is a necessary condition, not a
sufficient one, and the report should say so when a high density comes from a
link list.

## Criterion 5: interrogable form, 10 points

Operational test: would a person type this heading into a search box or a chat
prompt? Script field `heading_is_question` checks syntax only, the judgement is
yours.

| Points | Heading |
|---|---|
| 10 | A real user question: `How much does an SEO plugin cost?` |
| 6 | A precise noun phrase: `Agency licence prices in 2026` |
| 3 | A generic noun phrase: `Our services`, `Pricing` |
| 0 | Magazine title, pun or teaser: `The heart of the matter` |

## Criterion 6: length, 10 points

Operational test: `words`, from the script.

| Points | Words |
|---|---|
| 10 | 130 to 170 |
| 8 | 110 to 129, or 171 to 200 |
| 5 | 90 to 109, or 201 to 250 |
| 2 | 60 to 89, or 251 to 320 |
| 0 | Under 60, or over 320 |

The 130 to 170 band is where a passage carries a full answer and still fits an
answer without being summarised. Below it there is not enough information to be
worth a quote, above it the block has to be condensed, and a condensed block
loses the source name along the way.

## Criterion 7: attribution, 8 points

Operational test: can a reader check the facts from the passage alone? Script
fields `attribution.markers`, `attribution.marker_count`,
`attribution.external_links`.

| Points | Condition |
|---|---|
| 8 | Named source and date inside the passage: `according to the W3Techs report, February 2026` |
| 5 | Named source, no date |
| 3 | Vague marker: `a study shows`, `experts agree` |
| 0 | Figures with no source at all |

## Criterion 8: signalled freshness, 4 points

Page-level, so identical for every passage. Script block `dates`.

| Points | Condition |
|---|---|
| 4 | Published and modified dates present in the HTML and in the JSON-LD, agreeing, modified under 12 months ago |
| 2 | Dates present but HTML and JSON-LD disagree, or last modified 12 to 24 months ago |
| 0 | No date, modified over 24 months ago, or a date in the future |

A disagreement between the visible date and the JSON-LD date is worse than no
date: it is a contradiction inside the same document.

## Criterion 9: internal competition, 3 points

Script block `internal_competition`, which pairs passages on three signals:
near-identical headings, near-verbatim body, or the same topic vocabulary
reused (paraphrase).

| Points | Condition |
|---|---|
| 3 | No competing passage on the page |
| 0 | Competes with another passage of the same page or site |

Small in points, large in consequence: always name the pair in the findings and
say which one to keep. The right move is a merge, not a rewrite of both.

## Caps

Applied after the sum. A cap replaces the score, it does not subtract from it.
When several caps fire, the lowest one applies, and the deliverable names it
next to the score.

| Cap | Condition | Reason |
|---|---|---|
| 25 | `in_served_html` false | The block only exists after JavaScript runs |
| 30 | Hazard `hidden`, `aria-hidden` or `display-none` | Marked as not for display |
| 40 | `promo_block` or `boilerplate_block` true | Promotional or template block, quotable in theory, worthless in practice |
| 45 | `template_duplicate` true | The same text sits on other pages of the site |

## Bands and tones

| Band | Score | Verdict | `bars` tone |
|---|---|---|---|
| Quotable as is | 80 to 100 | Leave it alone, use it as the template for the rest | `good` |
| Quotable after one edit | 60 to 79 | One defect, usually the opening sentence | `neutral` |
| Rewrite | 40 to 59 | The information is there, the form blocks it | `warn` |
| Filler | 0 to 39 | Cut, merge, or move out of the body | `bad` |

Report KPIs: median passage score, count in the `quotable as is` band, count in
`rewrite` plus `filler`, and share of body words absent from the served HTML.
Use the median, not the mean: one long filler block drags a mean and tells the
reader nothing.

## Worked example

Passage measured by the script: 104 words, `density_per_100w` 19.2, 0 anaphora,
`heading_is_question` true, heading `How much does a WordPress SEO plugin
cost?`, first sentence 22 words and answering, one attribution marker with a
named source and a date, in the served HTML, no hazard, page dates disagree
between HTML and JSON-LD, competes with one other passage.

Extractability 20, autonomy 15, direct answer 15, facts 15, form 10, length 5
(104 words), attribution 8, freshness 2, competition 0. Total 90, no cap fires,
band `quotable as is`. The two lost blocks name the two actions: merge with the
competing passage, and fix the date contradiction.

## What this scale is not

This is a heuristic built on observable regularities: what crawlers can read,
what survives being cut out of a page, what a quoted block looks like. It is
not an answer engine ranking algorithm, and no public scale is. It predicts
nothing on its own.

Write that in the report, and never turn a score into a promise. A passage at
95 is a passage that can be quoted, not a passage that will be.
