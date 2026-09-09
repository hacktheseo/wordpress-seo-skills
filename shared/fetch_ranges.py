#!/usr/bin/env python3
"""
Rebuild shared/ranges.json from the providers' own published IP range files.

    python3 shared/fetch_ranges.py                 # writes shared/ranges.json
    python3 shared/fetch_ranges.py --out other.json
    python3 shared/fetch_ranges.py --print         # show the report, write nothing

Why this exists: verifying an AI crawler by its user agent proves nothing, and
assembling the range files by hand is the step everyone skips. This fetches only
first party URLs, reports what each one returned, and never invents a prefix.

A provider that comes back empty stays empty. An empty provider means its hits
are reported as unverifiable, which is the honest answer, whereas a guessed
prefix would mark a real crawler as spoofed or a spoofer as real.

Standard library only. The only network calls are the URLs listed below.

Part of the Hack The SEO agent skills.
Licence: GPL-2.0-or-later
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import date

TIMEOUT = 20
AGENT = "hacktheseo-fetch-ranges/1.0 (+https://github.com/hacktheseo/wordpress-seo-skills)"

# First party only. Anything else is hearsay and does not belong in a file that
# decides whether a client report calls traffic real or forged.
SOURCES = {
    "openai": [
        "https://openai.com/gptbot.json",
        "https://openai.com/searchbot.json",
        "https://openai.com/chatgpt-user.json",
    ],
    "anthropic": [
        # Was www.anthropic.com/ips.json until 2026, that URL now 404s.
        "https://claude.com/crawling/bots.json",
    ],
    "google": [
        "https://developers.google.com/static/search/apis/ipranges/googlebot.json",
        "https://developers.google.com/static/search/apis/ipranges/special-crawlers.json",
        "https://developers.google.com/static/search/apis/ipranges/user-triggered-fetchers.json",
    ],
    "perplexity": [
        "https://www.perplexity.ai/perplexitybot.json",
        "https://www.perplexity.ai/perplexity-user.json",
    ],
    "apple": [
        "https://search.developer.apple.com/applebot.json",
    ],
    "microsoft": [
        "https://www.bing.com/toolbox/bingbot.json",
    ],
}

# Documented as having no first party CIDR list at survey date. They stay in the
# file, empty, so the shape is stable and the reason is visible.
NO_LIST = {
    "amazon": "no CIDR list published, verify by rDNS under crawl.amazonbot.amazon",
    "meta": "no JSON list, AS32934",
    "commoncrawl": "no list published, runs on AWS us-east-1",
    "bytedance": "no stable list published",
    "mistral": "IP list inside the documentation, no stable JSON",
    "xai": "no list published at survey date",
    "cohere": "no list published at survey date",
    "deepseek": "no crawler documented at survey date",
}

CIDR = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}/\d{1,2}$|^[0-9a-fA-F:]+/\d{1,3}$")


def harvest(payload):
    """Pull CIDR strings out of whatever shape the provider publishes."""
    found = []

    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key in ("ipv4Prefix", "ipv6Prefix", "prefix", "cidr") and isinstance(value, str):
                    found.append(value.strip())
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                if isinstance(item, str):
                    if CIDR.match(item.strip()):
                        found.append(item.strip())
                else:
                    walk(item)

    walk(payload)
    return [p for p in found if CIDR.match(p)]


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": AGENT})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        raw = response.read().decode("utf-8", "replace")
    return json.loads(raw)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    here = os.path.dirname(os.path.abspath(__file__))
    parser.add_argument("--out", default=os.path.join(here, "ranges.json"))
    parser.add_argument("--print", dest="dry", action="store_true",
                        help="report only, write nothing")
    args = parser.parse_args(argv)

    ranges, report, failures = {}, [], 0
    for provider, urls in SOURCES.items():
        collected = []
        for url in urls:
            try:
                payload = fetch(url)
            except urllib.error.HTTPError as error:
                report.append((provider, url, "HTTP %s" % error.code, 0))
                failures += 1
                continue
            except Exception as error:
                report.append((provider, url, type(error).__name__, 0))
                failures += 1
                continue
            prefixes = harvest(payload)
            collected.extend(prefixes)
            report.append((provider, url, "ok", len(prefixes)))
        ranges[provider] = sorted(set(collected))

    for provider, reason in NO_LIST.items():
        ranges[provider] = []
        report.append((provider, "-", reason, 0))

    width = max(len(p) for p in ranges)
    print("%-*s  %-8s  %s" % (width, "provider", "prefixes", "source"))
    for provider in sorted(ranges):
        rows = [r for r in report if r[0] == provider]
        print("%-*s  %-8d  %s" % (width, provider, len(ranges[provider]),
                                  "; ".join("%s -> %s" % (u.rsplit("/", 1)[-1] or u, s)
                                            for _, u, s, _ in rows)))
    empty = [p for p in SOURCES if not ranges[p]]
    if empty:
        print("\nempty after fetching: %s" % ", ".join(empty), file=sys.stderr)
        print("their hits will be reported as unverifiable, never as spoofed",
              file=sys.stderr)

    if args.dry:
        return 1 if failures else 0

    document = {
        "_comment": ("Generated by shared/fetch_ranges.py from first party URLs. "
                     "Re-run it before an audit, these lists move."),
        "_generated": date.today().isoformat(),
        "_sources": {p: u for p, u in SOURCES.items()},
        "_no_list": NO_LIST,
    }
    document.update(ranges)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(document, handle, indent=2, sort_keys=False)
        handle.write("\n")
    print("\nwrote %s" % args.out)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
