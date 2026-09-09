# AI crawler user agents, provider and declared purpose

Survey date: **2026-09-08**. This list moves faster than any other table in this
repository. Providers add crawlers, rename them and split them by purpose
several times a year. Re-check the vendor documentation before you put a bot
name in a client deliverable, and print the survey date next to the table in
the report so the reader knows how old the mapping is.

`scripts/parse_logs.py` carries the same table in code, with the same survey
date in the field `bot_table_survey_date` of its output. If you correct one,
correct both.

## Table of contents

- [Why purpose matters more than volume](#why-purpose-matters-more-than-volume)
- [The table](#the-table)
- [Traps in this table](#traps-in-this-table)
- [How to read a user agent string](#how-to-read-a-user-agent-string)

## Why purpose matters more than volume

A user agent declares two things: who is asking, and why. Almost every audit on
the market reports the first and drops the second, which is how a client ends up
being told "ChatGPT visited you 4 000 times" when what happened is that a
training crawler swept the blog archive and no human question was ever involved.

Three purposes, three different meanings:

| Purpose | What it is | What it means for the client |
|---|---|---|
| `training` | Corpus collection, batch, scheduled by the provider | Your content may enter a future model. No demand signal, no timing signal |
| `user_fetch` | One page fetched now because a person asked a question | **The strongest signal in the log.** Somebody asked, and the model went to get this page. Timing, page and frequency are all real demand data |
| `search` | Building or refreshing an index queried at answer time | Eligibility to be cited. Between the two others in value |

Rank the report around `user_fetch`. A page that receives repeated `Claude-User`
or `ChatGPT-User` hits is a page the models reach for when a real question comes
in, and that fact is worth more than the whole training volume column.

## The table

Verification column: `ranges` means the provider publishes IP ranges,
`rDNS` means reverse DNS then forward DNS resolves under a provider domain,
`none` means no published method exists, so hits can only be reported as
unverifiable. Details and URLs in [verification.md](verification.md).

| User agent token | Provider | Purpose | Verification | robots.txt token |
|---|---|---|---|---|
| `GPTBot` | OpenAI | training | ranges | `GPTBot` |
| `ChatGPT-User` | OpenAI | user_fetch | ranges | `ChatGPT-User` |
| `OAI-SearchBot` | OpenAI | search | ranges | `OAI-SearchBot` |
| `ClaudeBot` | Anthropic | training | ranges | `ClaudeBot` |
| `Claude-User` | Anthropic | user_fetch | ranges | `Claude-User` |
| `Claude-SearchBot` | Anthropic | search | ranges | `Claude-SearchBot` |
| `anthropic-ai` | Anthropic | training (legacy) | ranges | `anthropic-ai` |
| `claude-web` | Anthropic | user_fetch (legacy) | ranges | `claude-web` |
| `PerplexityBot` | Perplexity | search | ranges | `PerplexityBot` |
| `Perplexity-User` | Perplexity | user_fetch | ranges | `Perplexity-User` |
| `Googlebot` | Google | search | rDNS + ranges | `Googlebot` |
| `Google-Extended` | Google | training | see trap below | `Google-Extended` |
| `GoogleOther` | Google | training and product crawls | rDNS + ranges | `GoogleOther` |
| `Google-CloudVertexBot` | Google | user_fetch | rDNS + ranges | `Google-CloudVertexBot` |
| `Bingbot` | Microsoft | search, feeds Copilot | rDNS + ranges | `Bingbot` |
| `CCBot` | Common Crawl | training | none | `CCBot` |
| `Amazonbot` | Amazon | search and assistant | rDNS | `Amazonbot` |
| `meta-externalagent` | Meta | training | rDNS | `meta-externalagent` |
| `meta-externalfetcher` | Meta | user_fetch | rDNS | `meta-externalfetcher` |
| `FacebookBot` | Meta | training | rDNS | `FacebookBot` |
| `facebookexternalhit` | Meta | preview, not AI | rDNS | `facebookexternalhit` |
| `Applebot` | Apple | search | rDNS + ranges | `Applebot` |
| `Applebot-Extended` | Apple | training | see trap below | `Applebot-Extended` |
| `Bytespider` | ByteDance | training | none reliable | `Bytespider` |
| `TikTokSpider` | ByteDance | training | none reliable | `TikTokSpider` |
| `cohere-ai` | Cohere | user_fetch | none published | `cohere-ai` |
| `cohere-training-data-crawler` | Cohere | training | none published | same |
| `MistralAI-User` | Mistral AI | user_fetch | list in vendor docs | `MistralAI-User` |
| `xAI-Bot`, `GrokBot` | xAI | training and fetch | none published | as written |
| `DeepSeek` (any spelling) | DeepSeek | claimed training | none, undocumented | none published |
| `YouBot` | You.com | search | none published | `YouBot` |
| `Diffbot` | Diffbot | training, resold corpus | none published | `Diffbot` |
| `Omgilibot`, `Webzio-Extended` | Webz.io | training, resold corpus | none published | as written |
| `Timpibot` | Timpi | training | none published | `Timpibot` |
| `ImagesiftBot` | Hive | training, images | none published | `ImagesiftBot` |
| `PetalBot` | Huawei | search | rDNS | `PetalBot` |

## Traps in this table

Five things a beginner gets wrong here, each of which turns into a false
statement in a client report.

**`Google-Extended` is a robots.txt token, not a crawler.** It never appears in
an access log. It is the control surface that says whether Google may use
already crawled content for Gemini training and grounding. The fetching is done
by `Googlebot`. If you report "Google-Extended crawled you 98 times", the log
line you are reading is almost certainly forged. Same structure for
`Applebot-Extended`, which governs training use of what `Applebot` already
fetched.

**`facebookexternalhit` is not AI traffic.** It is link unfurling: somebody
pasted the URL into a Meta product. Keep it out of the AI totals or the numbers
inflate for the wrong reason.

**`CCBot` is not a search engine.** Common Crawl publishes an open corpus that
almost every model has trained on at some point. A CCBot hit is a training
signal with a delay of months, never a demand signal.

**DeepSeek has no documented crawler.** Any hit claiming it is unverifiable by
construction, and in practice most of them are scrapers borrowing a fashionable
name. Report it as unverifiable, never as DeepSeek traffic.

**A user agent is a declarative string.** Everything in this table describes
what a request *claims*. Nothing here is evidence. Evidence comes from
[verification.md](verification.md), and a bot table without a verification
column is a rumour with a header row.

## How to read a user agent string

Real examples, and what to extract from each:

```
Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; GPTBot/1.2; +https://openai.com/gptbot
```
Token `GPTBot`, version 1.2, self declared documentation URL. The `Mozilla/5.0`
prefix is decoration, every crawler carries it, it means nothing.

```
Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15
```
No crawler token. This is the human baseline bucket, and it is only a
convention, not proof of a human: any script can send this exact string.

```
Mozilla/5.0 (compatible; ClaudeBot/1.0; +claudebot@anthropic.com)
```
Token `ClaudeBot`, contact address. Note that `Claude-User` and `ClaudeBot` are
two different bots with two different meanings, and a substring match on
`claude` alone merges them and destroys the purpose split. The parser matches
the longest token first for exactly this reason.

Matching rule used by the parser: lowercase the whole string, then look for the
tokens above, longest first. That is deliberately loose, because vendors change
version suffixes constantly, and deliberately case insensitive, because half the
hosts in the wild rewrite the case of the header.
