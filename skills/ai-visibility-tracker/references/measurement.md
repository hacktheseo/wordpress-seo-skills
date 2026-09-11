# Measuring visibility in AI answers

## Table of contents

- [Why one answer measures nothing](#why-one-answer-measures-nothing)
- [How many answers](#how-many-answers)
- [The metrics, defined once](#the-metrics-defined-once)
- [Intervals and the signal or noise call](#intervals-and-the-signal-or-noise-call)
- [API against app](#api-against-app)
- [Tracker exports](#tracker-exports)

## Why one answer measures nothing

- SparkToro and Gumshoe, January 2026: 600 volunteers, 12 prompts, 2 961
  runs on ChatGPT, Claude and Google AI Overviews and AI Mode. The same list
  of brands twice: fewer than 1 in 100. The same list in the same order:
  about 1 in 1 000. Yet presence had a pattern: leading brands of a narrow
  category appeared in 90 to 100 % of answers. Their advice: run each prompt
  many times and average; rank in a list is "full of baloney".
  https://sparktoro.com/blog/new-research-ais-are-highly-inconsistent-when-recommending-brands-or-products-marketers-should-take-care-when-tracking-ai-visibility/
- Contender, February 2026: 12 prompts, 100 runs each on ChatGPT, about 44
  distinct brands per prompt, about 10 per answer, only about 5 above 80 %.
  https://searchengineland.com/repeated-chatgpt-runs-brand-visibility-468552
- Sources drift too. Profound, July 2025: 40 to 59 % of cited domains changed
  from one month to the next depending on the engine. SISTRIX, May 2026,
  82 619 prompts over 17 weeks: ChatGPT search brought 74 % new domains each
  week, yet 86.5 % of prompts kept a stable core of one to five domains.
  https://www.sistrix.com/blog/ai-citation-drift-how-stable-are-sources-in-ai-search-results/

## How many answers

No published power calculation exists. What the studies support:

| Use | Answers per prompt and engine |
|---|---|
| A first look, clearly labelled anecdotal | 1 to 4 |
| A client report | **5**, the default of `run_survey.py` |
| A decision on one family of prompts | 10 or more |
| A narrow question about one brand's rate | 60 to 100 (SparkToro) |

More prompts beat more repeats of the same prompt when the budget is fixed: a
2026 preprint measured that the wording of the prompt explains as much
variance as re-running it. Keep the prompt set frozen between waves, or the
comparison is void.

## The metrics, defined once

| Metric | Definition here | Watch out |
|---|---|---|
| Mention rate | answers naming the brand (or citing its site) / answers | always with its interval |
| Share of voice | the brand's mentions / all tracked brands' mentions | depends on which competitors you track; name them |
| Own domain share | answers citing the brand's site / answers with sources | a mention without a link counts in the rate, not here |
| Position mix | first, passing, footnote, among answers naming the brand | a mix, never an average |
| Source gap | domains back in at least 75 % of the answers without the brand, for a prompt and an engine, four answers minimum; core when that holds on two questions or more | the list to work on |

Commercial tools do not share definitions: Peec computes a citation rate as
citations over retrievals, Profound a citation share over all citations.
Bing calls its own citation share "an observational metric, not a ranking
system". Name the definition in the report, every time.

## Intervals and the signal or noise call

Every rate carries a 95 % Wilson interval: it behaves at 0 % and 100 %, where
the textbook interval does not. A change between two waves carries a Newcombe
interval on the difference. It is a **signal** when that interval excludes
zero and **noise** otherwise, and the report prints the word. With 60 answers
per engine, a move of 10 points is usually noise; that is the measure being
honest, not failing.

## API against app

What an API returns is not what the app shows. Surfer, September 2026, 1 000
runs per scenario: ChatGPT's API skipped web search in about 23 % of answers
and cited on average 7 sources against 16 in the app; source overlap between
the two was about 4 % for ChatGPT and 8 % for Perplexity.
https://surferseo.com/blog/llm-scraped-ai-answers-vs-api-results
An API survey is a repeatable proxy, not a view of what users see. So is a
manual survey in a logged out app, with a different bias. Say which one the
report rests on.

## Tracker exports

None of the commercial trackers documents its CSV columns (Profound, Peec AI,
Otterly, Semrush AI Visibility Toolkit, Ahrefs Brand Radar, as of September
2026). Map one export by hand to the survey format once, and keep the
mapping with the client file:

| Survey column | Usually found as |
|---|---|
| `prompt_id`, `prompt` | prompt, question, query |
| `engine` | model, platform, engine |
| `cited` | mentioned, brand mentioned, visibility (per answer) |
| `brands` | brands mentioned, competitors (join with a vertical bar) |
| `sources` | citations, sources, URLs (join with spaces) |

An export that only holds aggregates (a visibility score per week) cannot
feed the source gap. Ask the tool for answer level data, or run a survey.
