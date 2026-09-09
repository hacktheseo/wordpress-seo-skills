# Turning the parser output into the client deliverable

Read `shared/report-engine/CONTRACT.md` for the JSON grammar. This file says
which parser field feeds which block, and what to write in the prose parts.
Follow the section order below, it is the order a client reads in.

Rule that overrides everything else here: **every number in the deliverable
comes from a field of `bots.json`.** If a sentence needs a figure that is not in
that file, either compute it from fields that are (and say how in the caption),
or drop the sentence.

## meta

```json
{"title": "AI crawler forensics", "subject": "<domain>",
 "period": "<parsing period, in the user's language>",
 "generated": "<today>", "lang": "<en or fr>", "credit": true}
```

`period` comes from `period.first_hit` and `period.last_hit`, not from what the
client said they sent. If the log only covers 9 days, it says 9 days.

Add `brand` only if the user gave an agency name and colour.

## headline

The verdict is one sentence, and it is a finding, not a description. Build it
from the two most striking observed facts, and put a number in it:

> Four AI crawlers reached the site 1 812 times in August, and not one of them
> read a product page.

> ChatGPT fetched 47 pages in real time following user questions, all of them on
> the blog, none on the offer.

> GPTBot has received a 403 on every one of its 1 240 requests since 12 August,
> so the site is currently invisible to OpenAI.

Bad verdicts, avoid: "Analysis of AI crawler traffic" (a title, not a finding),
"Traffic is up 34 percent" (no consequence), anything containing a prediction.

`detail` gets two lines: the shape of the crawl, plus the reminder that none of
this appears in a JavaScript analytics tool.

## kpis, three to five

Pick from this list, in this order, keeping only what the data supports:

| KPI | Value from | Tone |
|---|---|---|
| Verified AI hits | `totals.ai_counted` | `good` if non zero |
| Verification rate | `ai_verified / ai_claimed` | `warn` under 90 percent, `bad` under 60 |
| Real time fetches | `by_purpose.user_fetch.counted` | `good` if non zero, `bad` if zero |
| Errors served to bots | sum of 4xx and 5xx in `status_served_to_ai_bots` | `bad` above 2 percent |
| Sitemap coverage | `sitemap.crawled / urls_in_sitemap` | `bad` under 40 percent |
| Invisible in analytics | always `100 %` | `neutral` |

That last one is a KPI on purpose. It is the line that makes the client
understand why this work exists, and it costs nothing to state: no crawler in
this table executed JavaScript, so no analytics tag fired for any of it.

Every KPI carries a `note` with the breakdown behind it. A bare number invites
the client to argue with it.

## Section 1, who actually crawled

One `table` block, from `bots`. Columns: bot, provider, purpose, counted hits,
verified, spoofed. `numeric_columns` on the three count columns.

Translate `purpose` into the user's language: training, real time fetch, search
index. Never leave the raw key in the deliverable.

Sort by counted hits descending, and cut the table at ten rows. Below ten hits a
bot belongs in a caption, not a row.

Caption, mandatory, adapted from `verification.mode` and
`verification.ranges_loaded`:

> Source: <format> access log, <period>. Verified against the IP ranges
> published by each provider and by reverse DNS. Requests carrying a crawler
> name without coming from that provider are excluded from every figure here.

## Section 2, where the crawl goes

One `bars` block from `sections`, at most eight rows, `value` numeric and
`display` formatted for the language. Set `tone` per row: `bad` on a section
that matters commercially and receives almost nothing, `good` on a healthy one,
`neutral` everywhere else. The bars make the imbalance visible in two seconds,
so choose the sections rather than dumping the top eight blindly: always include
the commercial section even when its value is zero.

Then the `matrix` block, four quadrants in contract order (crawled and cited,
cited not crawled, crawled not cited, neither), fed by `matrix.*`. Readings are
in [citation-protocol.md](citation-protocol.md), rewritten in the user's
language, one sentence each, and the `items` list holds at most three sample
URLs plus a count line.

When `matrix.citations_available` is `false`, keep the four quadrants, fill the
two citation ones with the honest sentence from that file, and set their `count`
to `null`.

## Section 3, what to fix

One `findings` block, three to six items, ordered by severity. Sources and
thresholds are in [diagnostics.md](diagnostics.md).

Each item: `evidence` is an observed figure with its field behind it, `action`
is something doable this week by the person reading. Not "improve crawlability".
Something like "check that /produits/ is not disallowed in robots.txt, then link
it from the five most crawled blog posts, listed above".

When the `crawled_not_cited` quadrant is populated, one finding must point at
`ai-citability-audit` and say explicitly that this is a citability problem and
not an access problem.

## Section 4, method and limits

Three blocks, in this order, all three mandatory.

A `note` with `tone: "warn"`, titled "What this cannot show", covering at least:
a log proves a page was read and never that it was cited; unverifiable hits and
why; the citation half if it is missing; the period actually covered if it is
shorter than requested; and the fact that a crawler hit is not a visit and not a
session.

A `code` block with the reproduction command, the client's real domain and a
real path:

```
curl -s -o /dev/null -w '%{http_code} %{time_total}s\n' -A "GPTBot" https://example.com/produits/
```

A `checklist` of what was done and what remains: logs collected over N days, IP
ranges refreshed on <date>, citation survey done or not, robots.txt checked,
countermeasure applied. Unchecked items are the next engagement.

## Rendering

```bash
python3 "${CLAUDE_SKILL_DIR}/../../shared/report-engine/render_report.py" findings.json report.html
```

If it exits non zero, it prints the offending line. Fix the JSON and run again.
Never hand write the HTML, and never paste the content into the chat as markdown
instead: the file is the deliverable.

## Two worked mappings

**Silent block.** `status_served_to_ai_bots` shows `{"403": 1240}` and
`bots[0].status` shows the same 1 240 on GPTBot, all verified.
Verdict: GPTBot has been refused on every request since <first_seen>, so the
site is currently unreadable by OpenAI. KPI "Errors served to bots" at 100
percent, tone `bad`. Finding, severity `high`, evidence "1 240 verified GPTBot
requests, 1 240 responses in 403, from 12 August", action "reproduce with the
curl command below, then look at the WAF rules added that week".

**Demand without offer.** `by_purpose.user_fetch.counted` is 47, and every one
of the `top_urls` for `ChatGPT-User` is under `/blog/`.
Verdict: 47 pages were fetched in real time following user questions, all of
them editorial, none on the offer. Finding, severity `high`, evidence "47 real
time fetches, 0 on /produits/ and /tarifs/", action "link the two commercial
pages from the three articles that received those fetches, listed above".
