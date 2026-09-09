# Verifying that an AI crawler hit is real

Read this before producing any number. It is the step that separates an audit
from a guess, and it is the step almost every published analysis skips.

## Table of contents

- [Why a user agent proves nothing](#why-a-user-agent-proves-nothing)
- [The three states, and the rule](#the-three-states-and-the-rule)
- [Method 1, reverse DNS then forward DNS](#method-1-reverse-dns-then-forward-dns)
- [Method 2, published IP ranges](#method-2-published-ip-ranges)
- [Where each provider publishes](#where-each-provider-publishes)
- [Building the ranges file](#building-the-ranges-file)
- [Checking one address by hand](#checking-one-address-by-hand)
- [What to write in the report](#what-to-write-in-the-report)

## Why a user agent proves nothing

The `User-Agent` header is a free text field chosen by the client. Anybody can
send it:

```
curl -A "Mozilla/5.0 (compatible; GPTBot/1.2; +https://openai.com/gptbot)" https://example.com/
```

That request appears in the access log, character for character, exactly like a
real GPTBot hit. Scrapers do this on purpose, because a bot name that site
owners want to allow gets through firewalls and rate limits that would stop an
anonymous script.

Two consequences that decide how the report is written:

1. A count of hits by user agent is a count of *claims*, not of traffic. In
   audits where verification is applied, a double digit percentage of hits
   claiming a popular AI crawler turns out to be forged, and the forged share is
   concentrated on login pages, admin paths, feeds and price pages.
2. **An agency report that counts spoofed traffic is a false report.** The
   client makes decisions on it, sometimes buys hosting capacity on it, and the
   number is wrong. This is not a nuance, it is the reason this skill exists.

## The three states, and the rule

Every hit gets exactly one of three labels. The parser emits them per bot as
`verified`, `spoofed`, `unverifiable`.

| Label | Meaning | Evidence required |
|---|---|---|
| `verified` | The request came from the provider it claims | Inside a published range, or rDNS and fDNS both agree |
| `spoofed` | The request did **not** come from that provider | Positive contradiction: a PTR that belongs to somebody else, a PTR that does not resolve back to the address, or a request only a forgery would make |
| `unverifiable` | Not enough evidence either way | Outside a published range, no published range, no documented rDNS domain, no PTR record, or the lookup budget ran out |

Note what is **not** in the `spoofed` row: being outside a published range. That
absence is not evidence, and the section on ranges below explains why the parser
used to treat it as such and no longer does.

Three rules follow, and the parser enforces all three:

1. **Spoofed hits are excluded from every client facing number.** Volumes,
   sections, status codes, response times, top pages, the matrix. All of it.
   They appear in exactly two places: a "claimed versus verified" line, and the
   list of URLs the spoofers targeted, which is a security finding.
2. **Absence of evidence is never spoofing.** A missing PTR record is normal for
   several providers. Reporting it as spoofing manufactures an incident.
3. **Unverifiable is reported as unverifiable.** If most of the volume is
   unverifiable, say so in the verdict. A number with a stated confidence beats a
   confident wrong number.

## Method 1, reverse DNS then forward DNS

This is the method Google documents for validating Googlebot, and it works for
any provider that assigns PTR records under its own domain. Two lookups, in this
order, and the order matters.

**Step 1, reverse lookup.** Take the IP from the log line and ask for its PTR
record.

```
dig -x 66.249.66.1 +short
crawl-66-249-66-1.googlebot.com.
```

**Step 2, check the domain.** The hostname must end in a domain the provider
owns, from the table below. `crawl-66-249-66-1.googlebot.com` ends in
`.googlebot.com`, so far so good. A hostname ending in
`ec2-13-58-x-x.compute.amazonaws.com` for a request claiming Googlebot is a
contradiction, and that is a spoof.

**Step 3, forward lookup on the hostname returned.** This is the step people
skip, and skipping it makes the whole method worthless.

```
dig crawl-66-249-66-1.googlebot.com +short
66.249.66.1
```

The forward lookup must return the original IP. Reverse DNS is controlled by
whoever owns the address block, so an attacker with their own block can publish
a PTR record saying `crawl-66-249-66-1.googlebot.com`. What they cannot do is
make Google's authoritative zone resolve that name back to their address. The
round trip closes the hole.

Verdict: the IP is verified only when step 2 and step 3 both pass. Step 2 fails
means spoofed. Step 3 fails means spoofed. No PTR at all means unverifiable.

## Method 3, what the request asked for

The only test that needs no cooperation from the provider, and the only one that
can call a forgery on positive evidence alone. A user agent claiming to be a
crawler while requesting `/wp-login.php`, `/xmlrpc.php`, `/wp-admin`,
`wp-config`, `/.env`, `/.git`, `/.ssh`, `/.aws`, `/phpmyadmin`, `/adminer` or
`/vendor/phpunit`, or issuing a POST, PUT, DELETE or PATCH, is forged. A crawler
reads public pages. It does not log in and it does not write.

The list is deliberately short, and every entry has to be something a real
crawler cannot want. A false accusation in a report an agency sends its client
costs more than a forgery that goes uncounted, so the bar for adding a path is
that no legitimate crawler could ever request it.

Applied only when the origin is not already proven, so a verified crawler is
never accused of forging itself.

Documented rDNS domains, by provider:

| Provider | Expected PTR suffix |
|---|---|
| Google (`Googlebot`, `GoogleOther`, `Google-CloudVertexBot`) | `.googlebot.com`, `.google.com`, `.googleusercontent.com` |
| Microsoft (`Bingbot`) | `.search.msn.com` |
| Amazon (`Amazonbot`) | `.crawl.amazonbot.amazon` |
| Apple (`Applebot`) | `.applebot.apple.com` |
| Meta (`meta-externalagent`, `facebookexternalhit`) | `.fbsv.net`, `.facebook.com` |
| Huawei (`PetalBot`) | `.petalsearch.com` |
| OpenAI, Anthropic, Perplexity, Mistral, xAI, Cohere | none documented, use ranges |

## Method 2, published IP ranges

Several providers publish the address blocks their crawlers come from, as JSON,
and update them. **Membership in a published range is conclusive in one
direction only.** Inside the range proves the origin. Outside it proves nothing.

This is not caution for its own sake, it is what the files say when you read
them. Two measurements, both taken on 2026-09-09:

- Anthropic's `bots.json` carried a `creationTime` of 2026-08-18 and did **not**
  list `160.79.104.0/23`, a block ClaudeBot has served from. A log full of real
  ClaudeBot hits from that block would have been reported as a forgery.
- OpenAI's `gptbot.json` carried a `creationTime` of **2025-10-30**, eleven
  months old. Any range GPTBot started using in that time is missing from it.

Run on our own fixture, the difference is not theoretical. With the fixture's
own trimmed range file the log reads 13 verified and 2 spoofed. With the real
published lists the same log used to read 7 verified and **8 spoofed**: eight
genuine crawler hits accused of forgery, in a document an agency sends its
client. The parser now reads the same log as 7 verified, 8 unverifiable and 2
spoofed, and the 2 are the two that deserve it.

So the rule is: outside a published range downgrades a hit to `unverifiable`,
and the reason names the list's date, because the age is the argument. Nothing
is ever called a forgery on an absence.

## Where each provider publishes

Checked on 2026-09-08. **Verify each URL still responds before you rely on it.**
These files move, and a 404 silently turns every hit into unverifiable, which is
a failure mode you want to notice.

| Provider | Published source |
|---|---|
| OpenAI | `https://openai.com/gptbot.json`, `https://openai.com/chatgpt-user.json`, `https://openai.com/searchbot.json` |
| Anthropic | `https://claude.com/crawling/bots.json (was www.anthropic.com/ips.json until 2026, that URL now 404s)` |
| Perplexity | `https://www.perplexity.ai/perplexitybot.json`, `https://www.perplexity.ai/perplexity-user.json` |
| Google | `https://developers.google.com/static/search/apis/ipranges/googlebot.json`, `special-crawlers.json`, `user-triggered-fetchers.json`, `user-triggered-fetchers-google.json` in the same folder |
| Microsoft | `https://www.bing.com/toolbox/bingbot.json` |
| Apple | `https://search.developer.apple.com/applebot.json` |
| Amazon | No CIDR list. Verification is rDNS under `crawl.amazonbot.amazon`, documented in the Amazonbot help page |
| Meta | No CIDR file. Meta documents verification by autonomous system, AS32934, on the web crawlers page of the developer documentation |
| Common Crawl | No list published. Crawls run from AWS, so `https://ip-ranges.amazonaws.com/ip-ranges.json` is a weak plausibility check and nothing more. Treat CCBot as unverifiable |
| ByteDance | No stable list. `Bytespider` is among the most spoofed tokens in the wild. Treat as unverifiable unless you can check the AS |
| Mistral AI | Address list inside the vendor documentation, no stable JSON endpoint |
| xAI, Cohere, DeepSeek | Nothing published at survey date. Unverifiable by construction |

## Building the ranges file

The parser takes one JSON file keyed by provider. Create the skeleton:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/parse_logs.py" --print-ranges-template > ranges.json
```

Then fill each key. Two accepted shapes, so vendor payloads can be pasted
unchanged:

```json
{
  "openai": {"prefixes": [{"ipv4Prefix": "20.171.207.0/24"}]},
  "anthropic": ["160.79.104.0/23"],
  "google": {"prefixes": [{"ipv4Prefix": "66.249.64.0/19"}, {"ipv6Prefix": "2001:4860:4801::/48"}]}
}
```

Fetch each URL, paste the whole response under its provider key, save. The
parser reads `prefixes`, `ranges` or `ips` arrays, and accepts `ipv4Prefix`,
`ipv6Prefix`, `ip_prefix`, `prefix` and `cidr` field names. Malformed entries are
skipped silently rather than aborting the run, and the count actually loaded per
provider is reported in `verification.ranges_loaded`, so check that number is not
zero before trusting a `spoofed` verdict.

Keep the file next to the logs, never in the skill folder, and regenerate it at
each audit. A ranges file three months old produces false spoofing verdicts,
which is worse than no verification at all.

## Checking one address by hand

When a client disputes a verdict, reproduce it in front of them. This is
copyable and takes ten seconds:

```bash
IP=20.171.207.15
dig -x "$IP" +short                        # PTR, empty for OpenAI and Anthropic
whois "$IP" | grep -iE 'org|netname|origin' # owner and AS, works for every provider
```

For a provider with rDNS, the round trip in one line:

```bash
IP=66.249.66.1; H=$(dig -x "$IP" +short | sed 's/\.$//'); echo "$H"; dig "$H" +short
```

The second output must contain the original IP. If it does not, the PTR is
forged.

## What to write in the report

The verification method is a selling point, not a footnote. Put it in a caption
under the bot table, in the user's language, naming the method actually used:

> Verified against the IP ranges published by each provider on 2026-09-08, and
> by reverse DNS then forward DNS for Google, Bing, Apple, Amazon and Meta.
> Requests carrying a crawler name without coming from that provider are
> excluded from every figure in this report.

And when a large share is unverifiable, say it in the verdict rather than
hiding it in a caption. "1 240 hits, of which 900 cannot be attributed because
this provider publishes no verification method" is a professional sentence. "1
240 hits from DeepSeek" is not.
