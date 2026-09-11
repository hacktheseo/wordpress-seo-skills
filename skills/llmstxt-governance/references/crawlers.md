# AI crawlers and control tokens

Read on each provider's own page in September 2026. Purposes: **training**
(content may enter a model), **search** (an index used to answer and cite),
**user** (a fetch triggered by a person's question, now). The fourth column
is the provider's own wording about robots.txt, which is the only thing a
robots.txt rule can rely on.

## Table of contents

- [The tokens](#the-tokens)
- [Traps](#traps)
- [Cloudflare in 2026](#cloudflare-in-2026)
- [Checking that a crawler obeys](#checking-that-a-crawler-obeys)

## The tokens

| Token | Provider | Purpose | robots.txt, per the provider | Documentation |
|---|---|---|---|---|
| GPTBot | OpenAI | training | "Disallowing GPTBot indicates a site's content should not be used in training" | https://developers.openai.com/api/docs/bots |
| OAI-SearchBot | OpenAI | search | honoured; sites that disallow it will not appear in ChatGPT search answers | same |
| ChatGPT-User | OpenAI | user | "Because these actions are initiated by a user, robots.txt rules may not apply" (changed 9 December 2025) | same |
| ClaudeBot | Anthropic | training | honoured, crawl-delay supported | https://support.claude.com/en/articles/8896518 |
| Claude-SearchBot | Anthropic | search | honoured; blocking "may reduce your site's visibility" in search results | same |
| Claude-User | Anthropic | user | honoured | same |
| PerplexityBot | Perplexity | search | honoured, "not used to crawl content for AI foundation models" | https://docs.perplexity.ai/guides/bots |
| Perplexity-User | Perplexity | user | "this fetcher generally ignores robots.txt rules" | same |
| Google-Extended | Google | training, and grounding in Gemini apps | a control token, no crawler. "does not impact a site's inclusion in Google Search nor is it used as a ranking signal" | https://developers.google.com/crawling/docs/crawlers-fetchers/google-common-crawlers |
| GoogleOther | Google | research and one-off crawls | honoured, no effect on Search | same |
| Applebot-Extended | Apple | training | a control token, "does not crawl webpages" | https://support.apple.com/en-us/119829 |
| meta-externalagent | Meta | training and indexing | honoured | https://developers.facebook.com/docs/sharing/webmasters/web-crawlers/ |
| meta-webindexer | Meta | search | honoured | same |
| meta-externalfetcher | Meta | user | "may bypass robots.txt rules" | same |
| Amazonbot | Amazon | training | honoured | https://developer.amazon.com/amazonbot |
| Amzn-SearchBot | Amazon | search | honoured | same |
| Amzn-User | Amazon | user | "may not follow all robots.txt directives" | same |
| MistralAI-User | Mistral | user | not stated | https://docs.mistral.ai/robots |
| DuckAssistBot | DuckDuckGo | search, "not used in any way to train AI models" | honoured within 72 hours | https://duckduckgo.com/duckduckgo-help-pages/results/duckassistbot |
| CCBot | Common Crawl | training (open dataset) | honoured | https://commoncrawl.org/ccbot |
| Bytespider | ByteDance | training | no provider documentation; CDN operators report it ignoring robots.txt | none |
| cohere-training-data-crawler | Cohere | training | no provider documentation | none |

Googlebot and Bingbot are search engines, not AI crawlers, and they feed
AI Overviews, AI Mode and Copilot. An AI policy never refuses them; the
`policy` command refuses to write a file that would.

## Traps

- **One group, two jobs.** `User-agent: GPTBot` then `User-agent: OAI-SearchBot`
  then `Disallow: /` refuses both: the second line joins the first group. It
  is the most common way a site "stops training" and loses ChatGPT search.
- **OpenAI shares crawls.** OpenAI says that when GPTBot and OAI-SearchBot are
  both allowed, "we may use results from just one crawl for both use cases".
  Refusing GPTBot is therefore how to keep one and not the other.
- **Google-Extended and AI Overviews.** Google's AI features page sends
  site owners to `nosnippet`, `data-nosnippet`, `max-snippet` or `noindex` to
  control AI Overviews and AI Mode, not to Google-Extended.
  https://developers.google.com/search/docs/appearance/ai-features
- **Old tokens.** `anthropic-ai` and `claude-web` no longer appear on
  Anthropic's page. Leaving them costs nothing; relying on them does.
- **Perplexity.** Cloudflare reported on 4 August 2025 that Perplexity used
  undeclared crawlers with browser user agents to get around refusals, and
  removed it from its verified bots.
  https://blog.cloudflare.com/perplexity-is-using-stealth-undeclared-crawlers-to-evade-website-no-crawl-directives/

## Cloudflare in 2026

A site behind Cloudflare may carry rules the WordPress robots.txt never shows.

- 1 July 2025: new domains are asked whether to allow AI crawlers, blocking by
  default; over a million customers had already blocked them.
- The managed robots.txt adds `Content-signal: search=yes, ai-train=no` and
  refuses Amazonbot, Applebot-Extended, Bytespider, CCBot, ClaudeBot,
  Google-Extended, GPTBot and meta-externalagent.
  https://developers.cloudflare.com/bots/additional-configurations/managed-robots-txt/
- 1 July 2026: crawlers sorted into Search, Agent and Training. "On September
  15, 2026 [...] For all new domains onboarding to Cloudflare, the categories
  of Training and Agent will be blocked by default on the pages that display
  ads, while Search will remain allowed." Multi-purpose crawlers (Googlebot,
  Applebot, Bingbot) are blocked for customers who chose to block Training.
  https://blog.cloudflare.com/content-independence-day-ai-options/

When the audit says the site answers through Cloudflare, ask for a look at
Security, Bots, and the AI crawler settings of the zone.

## Checking that a crawler obeys

robots.txt says what is asked. The access log says what happened. Anyone can
send a `GPTBot` user agent, so a hit must be verified (provider IP ranges,
reverse then forward DNS) before being quoted: that is `ai-bot-log-forensics`.
The audit's `--log` count is only a first look and says so.
