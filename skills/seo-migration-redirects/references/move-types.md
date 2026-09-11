# Move types, and what Google and Bing actually say

Every sentence in quotes below was read on the page it cites, in September
2026. Quote them to a client rather than paraphrasing: an agency that cites
Google's own wording wins the argument about "how long" in one line.

## Table of contents

- [The numbers to keep in mind](#the-numbers-to-keep-in-mind)
- [Redesign or permalink change, same domain](#redesign-or-permalink-change-same-domain)
- [Domain change](#domain-change)
- [HTTP to HTTPS, www or not](#http-to-https-www-or-not)
- [Merging two sites](#merging-two-sites)
- [Hosting change without URL change](#hosting-change-without-url-change)
- [Bing](#bing)
- [Search Console reports to watch](#search-console-reports-to-watch)

## The numbers to keep in mind

| Fact | Value | Source |
|---|---|---|
| How long to keep redirects | "generally at least 1 year" | Google, site moves with URL changes |
| Change of Address duration | "These actions continue for 180 days" | Google Search Console help |
| Hops Googlebot follows | "up to 10 redirect hops" by default | Google, HTTP status codes |
| Codes read as permanent | 301 and 308, and an instant meta refresh | Google, redirects |
| Codes read as temporary | 302, 303, 307, and a delayed meta refresh | Google, redirects |
| 404 against 410 | "All 4xx errors, except 429, are treated the same" | Google, HTTP status codes |
| Settling time | "a few weeks or more" for a medium site, longer for a large one | Google, site moves |
| Recovery, measured | median 304 days, mean 489, 58 % within a year, 1 052 domain migrations | SALT.agency, June 2026 |

Sources:
- https://developers.google.com/search/docs/crawling-indexing/site-move-with-url-changes
- https://developers.google.com/search/docs/crawling-indexing/301-redirects
- https://developers.google.com/search/docs/crawling-indexing/http-network-errors
- https://support.google.com/webmasters/answer/9370220
- https://salt.agency/blog/27-of-domain-migrations-recover-in-90-days/

The 404 and 410 line matters when a client insists on 410 everywhere: for
Google both mean the page is gone, so choose 410 for clarity and move on.

## Redesign or permalink change, same domain

Google's five steps, in order: know what to expect, prepare and test the new
site, "prepare a URL mapping from the current URLs to their corresponding new
format", configure the server to redirect, monitor both old and new URLs.

What Google adds that people forget:

- "Don't redirect many old URLs to one irrelevant single URL destination, such
  as the home page of the new site. This can confuse users and might be
  treated as a soft 404 error."
- "Avoid chaining redirects." Point every old URL at its final page.
- "Each new URL should have a self-referencing rel=canonical tag."
- "Change the internal links on the new site from the old URLs to the new
  URLs." A redirect is a safety net, not a navigation system.
- If `noindex` was used during development, "prepare a list of URLs from which
  you'll remove the noindex rules when you start the site move."
- Small and medium sites: move all URLs at once rather than section by section.

A permalink structure change in WordPress stores no old structure and adds no
redirect of its own: see [wordpress-traps.md](wordpress-traps.md).

## Domain change

Everything above, plus:

- Redirect the old host at server level (one rule that keeps the path), then
  use the map for the URLs whose path also changed.
- Use the Change of Address tool in Search Console. Requirements: owner of
  both properties with the same Google account, a 301 from the old home page to
  the new one, and the tool "checks for 301s on a few pages". It works at
  domain level only ("You cannot move properties at the path level") and does
  not move subdomains, www included.
- Submit the new sitemap. Google says the old one can be removed afterwards,
  "since Google will use the new sitemap going forward".
- Keep the old domain registered and redirecting for years, not months: old
  backlinks and bookmarks keep arriving long after Google has swapped.

## HTTP to HTTPS, www or not

One host level rule, no map. Google on the Change of Address tool for HTTPS:
"don't use this tool; Google will figure out your changes for you". The work
is the test: canonical tags, hreflang, sitemaps and internal links still
written with the old scheme, and a CDN page rule answering 302.

WordPress 5.7 added `wp_update_urls_to_https()`, which updates `home` and
`siteurl` and rewrites insecure home URLs in content on the fly. It does not
set up the server redirect.

## Merging two sites

Map the absorbed site into the surviving one like a redesign. Use the Change of
Address tool only when a whole domain disappears. Expect the absorbed
site's pages to lose more than the surviving site's: the map decides how much.

## Hosting change without URL change

No redirect. Google: lower the DNS TTL "to a conservative low value (for
example, a few hours) at least a week in advance of the move", keep the old
hosting until "the traffic to the old provider reaches zero", and expect "a
temporary drop in Googlebot's crawl rate immediately after the launch,
followed by a steady increase over the next few days."
Source: https://developers.google.com/search/docs/crawling-indexing/site-move-no-url-changes

## Bing

Bing Webmaster Tools has a Site Move tool (domain, subdomain or directory
level), and once used, another move request is refused for six months. It
does not replace the 301s. Bing's own blog, December 2020: "redirects on the
old domain need to remain live for at least 1 to 2 years, preferably longer."
Sources: https://searchengineland.com/bing-webmaster-tools-adds-site-move-tool-151951
and https://blogs.bing.com/webmaster/december-2020/Website-Migration-with-Bing

## Search Console reports to watch

Page indexing report, after launch:

| State | What it means here |
|---|---|
| Page with redirect | an old URL, now redirecting. Normal, expected to grow |
| Redirect error | a chain too long, a loop, an over long URL, or an empty URL in the chain |
| Not found (404) | an old URL with no rule, or a new page missing. Feed the export to `hunt` |
| Soft 404 | often an old URL sent to the home page or to an empty category |

Each row exports up to 1 000 example URLs, which "does not necessarily show all
URLs". Validating a fix typically takes up to two weeks.
Source: https://support.google.com/webmasters/answer/7440203

Crawl stats, "By response": 301 and 308 are counted together as "Moved
permanently", 302 and 307 as "Moved temporarily". A growing temporary share
after a launch is a misconfigured rule.
Source: https://support.google.com/webmasters/answer/9679690

Do not use URL Inspection to check a redirect: it reports on the tested URL,
not on the target, and Google's own pages disagree on whether it follows
redirects. `check_live.py` answers the question directly.
