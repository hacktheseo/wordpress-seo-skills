# llms.txt: the format, the evidence, the generators

## The format

Proposed by Jeremy Howard (Answer.AI) on 3 September 2024. The current text,
"The /llms.txt file, v2", dated August 2026, at https://llmstxt.org/ lists,
in order:

1. An optional byte order mark.
2. "An H1 with the name of the project or site. This is the only required section."
3. "A blockquote with a short summary of the project".
4. Zero or more sections of any Markdown except headings.
5. Zero or more sections under H2 headings, each a list of links:
   `- [name](url)`, then optionally `: notes`.

It lives at `/llms.txt`, or at a subpath (`/docs/llms.txt`), "and the most
specific file applies". Pages can offer a Markdown version at the same URL
with `.md` appended or replacing the extension.

What v2 changed (https://llmstxt.org/changes.html):

- Discovery by link relations: `rel="alternate" type="text/markdown"` for a
  page's Markdown version, `rel="describedby"` for the llms.txt that covers
  it, as an HTML `<link>` or an HTTP `Link:` header.
- The "Optional" section keeps being "a useful convention for secondary
  links, but they no longer carry mechanical semantics".
- "agents view or search the llms.txt to find what they need, then follow the
  relevant links". A map, read whole or searched.

`llms-full.txt`, one file holding a site's whole text in Markdown, comes from
Mintlify and Anthropic's documentation and does not appear in the llmstxt.org
text. AIOSEO generates one; so does the paid Hack The SEO plugin.

## The evidence, as of September 2026

**Google.** The Search documentation, updated 10 July 2026: creating LLMS.txt
files "will neither harm nor help your site's visibility or rankings in
Google Search, as Google Search ignores them."
https://developers.google.com/search/docs/fundamentals/ai-optimization-guide
John Mueller, June 2026: "it's purely speculative for now". Chrome's
Lighthouse added an llms.txt audit in a new Agentic Browsing category (May
2026): a missing file scores not applicable, only a server error fails.
https://developer.chrome.com/docs/lighthouse/agentic-browsing/llms-txt

**OpenAI, Anthropic, Perplexity.** Each publishes an llms.txt for its own
documentation. None has said its crawlers read other sites' files.

**Logs.** Ahrefs, June 2026, 137 210 domains, May 2026 logs: 28 % publish an
llms.txt, 97 % of those files received zero requests in the month, about
22 000 requests in all, of which SEO tools 21.7 %, all AI categories 19.5 %,
AI retrieval bots 1.1 %. https://ahrefs.com/blog/llmstxt-study/

**Citations.** SE Ranking, November 2025, about 300 000 domains: no measurable
effect of llms.txt on AI citations.
https://www.searchenginejournal.com/llms-txt-shows-no-clear-effect-on-ai-citations-based-on-300k-domains/561542/

**Adoption.** Rankability, August 2026: 8.7 % of the top 1 000 sites, 5.6 % of
the top 10 000. https://www.rankability.com/data/llms-txt-adoption/

Say it plainly to a client: the file is cheap, harmless and read by some
agents; nobody has measured traffic or citations coming from it.

## The generators on WordPress

| Plugin | Since | Default | File | What it lists |
|---|---|---|---|---|
| Yoast SEO | 25.3, June 2025 | opt-in | **physical**, rewritten weekly, wins over any virtual one, stays when the feature is turned off | recent cornerstone content, pages, top categories and tags, manual selection since July 2025 |
| Rank Math | 2025 module | off | virtual | chosen post types and taxonomies, up to 100, noindex excluded |
| AIOSEO | 2025 | **on by default** | virtual, plus `llms-full.txt` | post types and taxonomies, a cap per type |
| SEOPress | PRO 9.5, January 2026 | off | virtual | a text area with placeholders |
| Website LLMs.txt | plugin | set up by the admin | physical when writable | chosen post types, noindex excluded |
| Hack The SEO, free | 1.x | on | virtual, served with `X-Robots-Tag: noindex` | front page and structural pages (10), recent posts ranked (15), products, categories and brands with WooCommerce; noindex excluded |

Two consequences for an audit: a site on AIOSEO has an llms.txt nobody
decided on, and a site that once tried Yoast's feature may serve a stale
physical file whatever the current plugin says.

## Writing a good one

- The H1 is the name people use for the brand, not the page title.
- The blockquote is one factual sentence: what, for whom, where, since when.
- Key pages first, by hand: home, about, pricing or offer, contact, FAQ.
- Then the pages that already earn clicks, from Search Console, not the
  newest ones.
- Never a cart, an account, a checkout, a search page, another host, or a page
  robots.txt refuses to answer engines.
- Under 60 links. An agent reads the file whole or searches it; 134 product
  links make both harder.
