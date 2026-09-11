# Reading live.json

`check_live.py` requests each old URL without following redirects, follows
every `Location` itself up to 10 hops, then reads the first 256 KB of the
page it lands on for a robots `noindex` (meta tag or `X-Robots-Tag` header)
and for the canonical link. One row per URL, with `codes` (every status on
the way), `final_url`, `verdict` and `severity`.

## Verdicts

| Verdict | Severity | What it means | Usual cause | Fix |
|---|---|---|---|---|
| `not_redirected` | high | the old URL answers 200 itself | rule missing, cache, another plugin answering first | add the rule, purge the cache, keep one redirect engine |
| `broken_target` | high | lands on a 4xx or 5xx | target never published, slug differs | point at a live page, or publish it |
| `noindex_target` | high | lands right, the page says noindex | staging setting carried over | untick "Discourage search engines", check the SEO plugin's per page robots |
| `canonical_elsewhere` | high | lands right, canonical names another host or path | staging host in the SEO plugin settings or the database | search and replace the old host, clear the plugin's cache |
| `loop` | high | a URL comes back, or more than 10 hops | two rules pointing at each other, often an old rule plus the new map | delete one, run `lint --existing` |
| `home_target` | high | lands on the home page instead of its page | a catch all rule, or a theme redirecting 404s home | remove the catch all, give each URL its page or a 410 |
| `wrong_target` | medium | lands on another live page | WordPress 404 guess, a regex rule wider than meant | see [wordpress-traps.md](wordpress-traps.md), order plain rules before regex |
| `temporary` | medium | a 302, 303 or 307 on the way | plugin default, CDN page rule | switch to 301 |
| `chain` | medium | right page, several hops | HTTP to HTTPS then path, or an old rule | point the first URL at the final page |
| `gone_ok` | ok | 410 as planned | | |
| `gone_404` | info | 404 instead of 410 | no 410 rule | fine for Google, which treats them the same |
| `gone_redirected` | low | planned 410, got a redirect | a pattern or the 404 guess caught it | decide which is right |
| `gone_still_live` | medium | planned 410, page still 200 | page not unpublished | unpublish or change the plan |
| `error` | medium | no answer | firewall blocking the user agent, rate limit, DNS | retry with `--rate 1`, or `--user-agent` |

## Staging first

Before the DNS switch, point `--old-base` at staging, where the rules are
installed, and add `--staging`: the checker then compares paths only, because
a staging server lands on its own host, and it tolerates canonicals naming the
staging host, which a search and replace fixes at launch. `--expect-base` is
for another case: putting the expected targets on a different host than the
map names, as the test fixture does. Run it again on
production on launch day and on day 7: the first catches the map, the second
catches the cache and the plugin that updated itself.

## Reproducing a hop

The report carries one command so the client's developer can see it without
trusting us:

```bash
curl -sI https://old.example.com/old-page/ | grep -iE '^(HTTP|location)'
```

Run it once per hop, following the `location` by hand.

## Limits

It tests what is in the map, not what the map forgot: that is the job of the
404 hunt and of the Search Console exports. It reads the landing page as a
browser without JavaScript would, which is how most crawlers read it. And a
server may answer a script differently from Googlebot: when a verdict looks
impossible, test the same URL from the browser's network tab.
