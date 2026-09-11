# The free plugin's MCP server

What the free Hack The SEO plugin exposes over MCP, read from the source of
version **1.1.2**. Read this before calling anything: the free plugin and the
paid one use completely different tool names, and guessing wastes a turn.

## The server

| | |
|---|---|
| Server id | `hack-the-seo-mcp` |
| Route | `/wp-json/htsfree/v1/mcp` |
| Transport | HTTP, application password |
| Access | **Read only.** Twelve abilities on a named allow list, nothing else |
| Since | Free plugin 1.1.2 |

Tool names are the ability id with the slash turned into a hyphen, because MCP
forbids `/` in a tool name. So the ability `hack-the-seo/ai-bots-summary` is
called as the tool `hack-the-seo-ai-bots-summary`, and your client will prefix
it with the server name it was configured under.

## The twelve tools

**AI crawler activity.** All three take one optional `days` integer, 1 to 365,
default 30.

| Tool | What it returns |
|---|---|
| `hack-the-seo-ai-bots-summary` | Hit counts over the window, broken down by robot. Aggregated only |
| `hack-the-seo-ai-bots-by-page` | Most crawled URLs, **and the published pages no AI crawler fetched at all**. That second list is the one nobody else has |
| `hack-the-seo-ai-bots-timeline` | Daily counts. Days before the first observation are omitted, never zero filled |

**Per page analysis.** All three take a required `postId` integer.

| Tool | What it returns |
|---|---|
| `hack-the-seo-page-geo-score` | GEO score for one post or page |
| `hack-the-seo-page-scores` | On-page score and title/description score, with their issues |
| `hack-the-seo-page-markdown` | The Markdown rendering served to AI agents, closer to what a model reads than the HTML |

**Site wide.** No parameters.

| Tool | What it returns |
|---|---|
| `hack-the-seo-site-global-score` | Distribution of the composite score, plus the worst content |
| `hack-the-seo-cannibalization-pairs` | Pages competing on the same query, with a severity score |
| `hack-the-seo-redirects-list` | The redirect rules configured on the site |
| `hack-the-seo-notfound-log` | URLs that returned 404 with a hit count, aggregated, no visitor data |
| `hack-the-seo-llmstxt-get` | The `llms.txt` the site serves to AI agents |
| `hack-the-seo-site-health` | Result of the **last** local health check, not a fresh one |

## What three of them return

Read from the source of 1.1.2. None declares an output schema, so these are
the keys the code builds. All three take no parameter.

| Tool | Returns | Limits |
|---|---|---|
| `hack-the-seo-redirects-list` | `count`, `rules[]` with `source`, `target`, `type` (int), `is_regex`, `enabled`, `hits`, `last_hit` | 200 rules, most hit first, disabled rules included |
| `hack-the-seo-notfound-log` | `count`, `urls[]` with `url`, `hits`, `is_external` (the referer is another site), `first_seen`, `last_seen` | 100 URLs, most hit first. Rows already redirected or ignored are included, without their status |
| `hack-the-seo-llmstxt-get` | `url`, `content` | Returns the generated file **even when the llms.txt module is switched off**: fetch `/llms.txt` itself to know what is served |

Before the first 404 or the first rule, the first two answer
`{"state": "no_data"}` with an empty list: that is an empty log, not an error.
Paths in the 404 log have their query string stripped, and the IP is only ever
stored hashed.

## What is not there, and what to do instead

There is no write path at all, by design. There is no Search Console data, no
embeddings, no cocoon, no internal linking, no impact measurement, and no
per-hit detail: everything crawler related is aggregated counts.

Two consequences you must respect rather than work around:

- **No IP addresses are ever returned.** So the free plugin cannot tell you
  whether a crawler hit was genuine or forged. If a report needs verified
  counts, it needs the raw server access log and `ai-bot-log-forensics`, not
  this MCP. Never present a figure from `ai-bots-summary` as verified.
- **`site-health` reports a stored result.** Say when it was computed, or say
  that you do not know, rather than presenting it as the state right now.

## Reading the crawler numbers honestly

The counts group robots whose purposes have nothing in common. Common Crawl
archives, ClaudeBot and Amazon and Meta train, and only ChatGPT, Perplexity and
Gemini can produce a citation a visitor will see. A single "AI crawler hits"
figure is flattering and close to meaningless.

Always split it before you show it: archive, training, and answer engines. On a
real site measured in September 2026 the split was 41 % archive, 48 % training
and 10,6 % answer engines. Reporting the raw total as "times you could be
cited" would have overstated the useful figure by a factor of nine.

## The paid plugin is a different server

If the site runs the paid extension, the tools are named `hts_*`
(`hts_get_ai_bot_visits`, `hts_get_geo_score`, `hts_get_cannibalization`, and
around sixty more across twelve toolsets, with a write path behind its own
gating). The two never run at the same time. When the paid one is active the
free one stops loading entirely, because `htsfree_paid_is_active()` returns
before the free modules load, so the free MCP route is never registered.

So the tool list itself tells you where you are, and no probe call is needed:
`hts_ping` is a paid tool and exists nowhere else. If you see it, you are on the
paid server and can read its `tier` field. If you see `hack-the-seo-*` tools
instead, you are on the free one and this page is your map.
