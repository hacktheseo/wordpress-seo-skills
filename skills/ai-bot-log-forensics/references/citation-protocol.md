# The crawl and citation matrix, and how to get the citation axis

A log answers one question perfectly: was this page read. It cannot answer the
second question: was this page used in an answer. Crossing the two is what turns
a traffic table into a diagnosis, because the same page can be in four states
and each one calls for a different fix.

## The matrix

Horizontal axis, crawled or not, from the log. Vertical axis, cited or not, from
a citation survey.

| | Crawled | Not crawled |
|---|---|---|
| **Cited** | The template to replicate | The model knows you through somebody else |
| **Not cited** | Citability problem | Access problem |

### Crawled and cited

It works. This quadrant is not a congratulation, it is a specification. Take
these pages and describe what they have in common: structure, length, presence
of a direct answer near the top, tables, named sources, dates, entity coverage.
That description is the brief for the rest of the site. Most audits skip this
quadrant because nothing looks broken in it, which wastes the only positive
evidence in the whole dataset.

### Crawled and never cited

The page is read and judged unusable. This is a **citability** problem, not an
access problem, and it is the most common quadrant on a content heavy site.
Adding links or fixing robots.txt does nothing here, the crawler is already
arriving. The content itself does not survive selection: no extractable answer,
claims without sources, dilution across too many subjects, or a passage that
cannot be quoted without the surrounding page.

Do not attempt the fix from this skill. Send the URL list to
`ai-citability-audit`, which works at passage level, and say so in the report.
Confusing the two failures is the single most expensive mistake in this domain,
because it turns into months of technical work on a problem that is editorial.

### Cited without being crawled

The model knows you through a third party: a directory, a marketplace, a forum
thread, a press article, a comparison site, or an older version of your pages in
a training corpus. The consequence is uncomfortable and worth stating plainly to
the client: **what is said about you is not under your control**, it is not
current, and you cannot correct it by editing your own site.

Two actions. Find the source of the citation and check what it says about you,
because that is your actual public description today. Then make the equivalent
page on your own domain reachable and citable, so the model has a first party
alternative.

### Neither crawled nor cited

An **access** problem, and access problems are cheap to fix. In order: a
robots.txt rule blocking the section, a WAF or Cloudflare rule serving 403 to
the crawler, the page missing from the sitemap, no internal link pointing to it,
or a response time so bad the crawl abandons before reaching it. The parser
gives you the first four directly, and [diagnostics.md](diagnostics.md) gives
the reading for each.

## When there is no citation survey

Say so. Do not simulate the vertical axis, do not infer citations from
`user_fetch` hits, and do not present a half matrix as a full one.

The report then shows the left column only: crawled, and not crawled against the
sitemap. In the matrix block, keep the four quadrants for the shape but fill the
two citation quadrants with the honest text, in the user's language:

> No citation survey supplied. This half requires a manual survey, described in
> the method section of this report, or a citation tracking tool.

That single sentence is worth more to an agency than a fabricated number, and it
sells the follow up work.

## The manual citation survey

No public API returns "the pages of this site that were cited". A manual survey
is the honest alternative, it takes about an hour, and it is reproducible if it
is dated and written down.

**1. Build the prompt list, 30 to 40 prompts.** Not keywords, questions. Split
them:

- 15 questions a buyer asks before choosing, in natural language.
- 10 questions on the specific subjects the site claims to cover.
- 5 brand questions, "what is X", "is X reliable", "X reviews".
- 5 comparison questions naming a competitor.

**2. Fix the conditions and write them down.** Which engines (ChatGPT with
browsing, Perplexity, Claude with search, Google AI Mode, Copilot), which
country, which language, logged out, no personalisation, one fresh conversation
per prompt. Conditions that are not written down make the survey
unreproducible, and an unreproducible survey cannot be compared next quarter.

**3. Record, for each prompt.** The date, the engine, the prompt, whether the
domain appears, and the exact URL cited when it does. Nothing else. Sources
listed in a sidebar count as citations, mentions of the brand name without a
link do not, and record those separately as brand mentions.

**4. Produce the file.** One URL per line, or a JSON list. Duplicates are fine,
the parser deduplicates:

```
https://example.com/guides/tailles/
/blog/choisir-ses-chaussons/
```

Pass it with `--citations citations.txt`. Full URLs and paths both work, query
strings and trailing slashes are normalised on both sides.

## Honesty rules for this half of the report

Four sentences that must survive into the deliverable, because they are what an
agency gets sued for omitting:

1. A survey of 40 prompts is a sample, not a measurement. It says these pages
   were cited on these prompts on this date, nothing more.
2. Generative answers are not stable. The same prompt gives a different answer
   an hour later, on another account, from another country. Reproducing the
   survey is what makes it a trend.
3. Absence in the survey is not absence in the model. It means these prompts, on
   this date, did not surface the page.
4. Never promise a citation, a ranking or a traffic figure. Report what was
   observed, recommend what to change, and state the uncertainty in the same
   sentence.
