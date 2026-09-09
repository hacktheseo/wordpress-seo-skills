# Eight diagnostics a senior reads in a log, and a beginner walks past

Each entry gives the signal in the parser output, the threshold that makes it
worth reporting, the reading, and the action. Work through them in this order:
the first three change what the client does this week, the last five shape the
quarter.

Every figure quoted in a finding must come from a field named here. Never
estimate, never round up in the client's favour, and put the observed number in
the `evidence` field of the finding.

## Table of contents

- [1. Status codes served to bots](#1-status-codes-served-to-bots)
- [2. Response time for bots against humans](#2-response-time-for-bots-against-humans)
- [3. A bot that disappears between two months](#3-a-bot-that-disappears-between-two-months)
- [4. Crawl budget burnt on parameters, facets and pagination](#4-crawl-budget-burnt-on-parameters-facets-and-pagination)
- [5. Redirect chains served to bots](#5-redirect-chains-served-to-bots)
- [6. Sitemap against reality](#6-sitemap-against-reality)
- [7. Orphan pages that get crawled](#7-orphan-pages-that-get-crawled)
- [8. Content update, then crawl return](#8-content-update-then-crawl-return)
- [Severity scale](#severity-scale)

## 1. Status codes served to bots

**Signal.** `status_served_to_ai_bots`, and `status` inside each bot entry.

**Threshold.** Any `403`, `401` or `429` above 2 percent of a bot's verified
hits. A single `403` on a verified crawler is already worth a line.

**Reading.** This is the most common finding of the whole audit and the client
is almost always unaware of it. A 403 or a 429 served to a verified AI crawler
is a silent block. Nobody chose it in the CMS: it comes from a WAF rule, a
Cloudflare bot fight mode, a security plugin, a rate limiter, or a hosting
level bot filter switched on by default. The site owner sees nothing, the
content is simply absent from the model. A 429 in particular means the site said
"come back later", and crawlers do come back less often after that.

Read the split carefully. A 403 on `/wp-login.php` from an unverified GPTBot is
a scraper being blocked correctly, which is good news. A 403 on `/produits/`
from a verified ClaudeBot is a revenue problem.

**Action.** Reproduce it, then name the layer. The reproduction command belongs
in the report because the client can run it themselves:

```bash
curl -s -o /dev/null -w '%{http_code} %{time_total}s\n' \
  -A "Mozilla/5.0 (compatible; GPTBot/1.2; +https://openai.com/gptbot)" \
  https://example.com/produits/
```

Compare with the same URL and a browser user agent. Different codes means the
block is user agent based, so look at the WAF and the security plugin. Same code
means it is not about bots at all.

## 2. Response time for bots against humans

**Signal.** `bots[].response_time` against `human_baseline.response_time`. Both
in milliseconds, both from the log itself, present only when the log format
carries a duration field (Nginx `$request_time`, Apache `%D` or `%T`,
Cloudflare `OriginResponseDurationMs`).

**Threshold.** Bot p50 above 1 500 ms, or bot p50 above twice the human p50.

**Reading.** Crawlers are impatient and cheap. They allocate a budget per host,
and a slow host gets fewer pages fetched for the same budget. Bots are also
systematically served worse than humans, for a structural reason: they land on
cold cache. A human arrives on a page some other human warmed up, a crawler
walks the deep archive nobody has requested in weeks, so it gets the
uncached, database heavy render every time. A 4 second time to first byte on a
crawler is a crawl that stops early and comes back less often.

**Action.** Do not start with the CDN. Look at what the bots actually request:
if the slow p90 sits on paginated archives or filtered listings, the fix is
caching those templates for anonymous traffic, not buying a bigger server.

## 3. A bot that disappears between two months

**Signal.** `bots[].monthly`, and `bots[].last_seen`.

**Threshold.** A bot with more than 50 hits in month N and fewer than 10 percent
of that in month N+1. Or `last_seen` more than 21 days before the end of the
period.

**Reading.** Crawlers do not lose interest suddenly. A drop of that shape is
almost always something the site did: a new robots.txt disallow, a WAF rule
added on the day of the drop, a Cloudflare setting flipped, a migration that
changed the response for that user agent, or an IP block applied after somebody
saw "bot traffic" in a hosting dashboard. Cross the drop date with the deploy
calendar and the answer is usually in the same week.

**Action.** Name the date of the drop in the finding, then check the three
suspects in order: `robots.txt` history, firewall rules added that week, and the
status codes served to that bot just before it left. A bot that received 429s
for three days and then vanished has told you exactly what happened.

## 4. Crawl budget burnt on parameters, facets and pagination

**Signal.** `crawl_waste.hits_with_query_string`,
`crawl_waste.top_query_parameters`, `crawl_waste.pagination_hits`, and the
`top_urls` of each bot.

**Threshold.** Query string hits above 15 percent of counted hits, or pagination
above 20 percent, or a single parameter appearing in more than 10 percent.

**Reading.** Every hit spent on `?utm_source=`, `?orderby=`, a colour facet or
`/page/47/` is a hit not spent on a page that could be cited. On WooCommerce the
usual suspects are attribute filters and sort orders; on any WordPress site the
usual suspect is `/page/N/` archives that go on forever. Tracking parameters in
the list are worse than waste: they mean the crawler found those URLs somewhere
public, usually in a sitemap or an internal link, and it is now indexing
duplicate versions of the same page.

**Action.** Three moves, in order of effect: canonical on the filtered URLs,
`Disallow` on the parameter patterns that carry no unique content, and remove
the tracking parameters from internal links and from the sitemap. Quote the
observed count of wasted hits in the finding, it is what makes the client act.

## 5. Redirect chains served to bots

**Signal.** `redirects.3xx_served_to_ai_bots`, `redirects.top_redirected_urls`.

**Threshold.** 3xx above 10 percent of counted hits, or a URL redirected more
than 20 times in the period.

**Reading.** Each redirect is a round trip the crawler pays for. Some AI
crawlers follow far fewer redirect hops than a search engine does, and a chain
of three ends in nothing being read. A URL that keeps being requested and keeps
being redirected also tells you the old URL is still linked somewhere: in the
sitemap, in the internal linking, or in a third party page that is the actual
source of your model visibility.

**Action.** Rewrite the internal links and the sitemap entries to the final
target instead of leaving the redirect to absorb them. Keep the redirect in
place for external links, that is what it is for. If the same URL redirects
hundreds of times, find the source that keeps sending traffic there before
deciding anything.

## 6. Sitemap against reality

**Signal.** The `sitemap` block: `urls_in_sitemap`, `crawled`, `not_crawled`,
`sample_not_crawled`. Requires `--sitemap`.

**Threshold.** Under 40 percent of the sitemap crawled over a 30 day window, on
a site under a few thousand URLs.

**Reading.** The sitemap is what the site declares. The log is what happened.
The gap is the honest measure of AI crawl coverage, and it is usually far worse
than the client imagines. Look at the shape of the gap rather than the number:
if the uncrawled set is one whole section, it is an access problem in that
section, a robots rule or a linking dead end. If the uncrawled set is spread
evenly, it is a budget problem, and diagnostics 2 and 4 are the causes.

**Action.** Take the twenty most commercially important uncrawled URLs and link
them from the pages the bots actually visit, which the `top_urls` list gives you
for free. That is the cheapest intervention in this whole document.

## 7. Orphan pages that get crawled

**Signal.** `sitemap.crawled_not_in_sitemap` and its sample.

**Threshold.** Any URL crawled repeatedly that is absent from the sitemap.

**Reading.** Two very different situations behind one signal, so read the sample
before writing anything. Old URLs still being crawled long after they left the
sitemap mean a stale source keeps pointing at them, and they may be what the
model actually knows about you. Deep URLs never declared anywhere mean the
crawler found them through internal links your sitemap generator excluded, which
is a configuration bug worth an easy win.

Also watch for `/wp-login.php`, `/xmlrpc.php`, `/wp-json/` and `.env` in this
list. Those are not crawlers, they are the spoofed hits, and the parser already
lists them separately under `spoofed_targets`.

**Action.** Add the legitimate ones to the sitemap. For the obsolete ones,
redirect to the current equivalent rather than letting them 404, because the
model is being fed the old content.

## 8. Content update, then crawl return

**Signal.** `bots[].daily` for the bots whose purpose is `user_fetch` or
`search`, read against the publication and update dates of the pages concerned.

**Threshold.** Requires two runs, or one run over a period that contains the
update. Compare the 14 days before and the 14 days after.

**Reading.** This is the only causal experiment available from a log without any
extra tool. Update a page, keep everything else constant, and watch whether the
crawl of that URL and of its section comes back. A return within a few days on a
`user_fetch` bot is the strongest confirmation available that the page is in the
retrieval set for real questions. No return after three weeks means the page is
not being reached, and the problem is access, not content.

**Action.** Turn it into a standing measurement rather than a one off: keep the
JSON output of each run, name the file with the period, and compare. That is
what makes the second audit worth as much as the first.

## Severity scale

Use it consistently, the report engine renders it as a badge.

| Severity | Use for |
|---|---|
| `high` | A verified crawler is being blocked or served errors, a whole revenue section is uncrawled, a bot disappeared |
| `medium` | Measurable waste or slowness, a significant spoofed share, a large sitemap gap |
| `low` | Local inefficiency, a handful of redirects, a parameter with a small footprint |
| `info` | An observation with no action this week, or a pointer to another audit |

Do not put more than six findings in one report. Beyond six nobody acts, and the
top three stop being read as priorities.
