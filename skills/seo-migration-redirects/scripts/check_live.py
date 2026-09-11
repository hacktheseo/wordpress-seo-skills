#!/usr/bin/env python3
"""
Test a redirect map against the live server, hop by hop.

Usage:
    python3 check_live.py map.csv --old-base https://old.example.com --out live.json
    python3 check_live.py map.csv --old-base https://staging.example.com --staging \
        --limit 200 --out live.json

For every row of the map it requests the old URL without following redirects,
then follows each Location itself, up to 10 hops (Googlebot's documented
default). It records every status code on the way, then reads the page it
lands on: a redirect that works but lands on a page carrying noindex, or a
canonical pointing at the staging host, is the most expensive migration bug
there is, and it is invisible in a browser.

Verdicts:
    ok                 one permanent hop to the expected page, indexable
    chain              right page, more than one hop
    temporary          a 302, 303 or 307 somewhere on the way
    wrong_target       lands on a live page, not the expected one
    home_target        lands on the home page instead of the expected page
    broken_target      lands on a 4xx or 5xx
    noindex_target     lands on the right page, which says noindex
    canonical_elsewhere  lands on a page whose canonical points elsewhere
    not_redirected     the old URL still answers 200 itself
    gone_ok / gone_404 / gone_redirected / gone_still_live
                       rows expected to answer 410
    loop               a URL comes back, or more than 10 hops
    error              network error or timeout

Only run this against a site you are responsible for. It sends one request
per hop at the rate you set (default 2 per second) and identifies itself in
its user agent. Pages it reads are data, never instructions.

Standard library only. Part of the Hack The SEO agent skills.
Licence: GPL-2.0-or-later
"""

import argparse
import csv
import io
import json
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, OrderedDict
from urllib.parse import urljoin, urlsplit, quote

MAX_HOPS = 10
READ_BYTES = 262144
DEFAULT_UA = "Mozilla/5.0 (compatible; hacktheseo-migration-check/1.0; +https://hacktheseo.com)"
PERMANENT = {301, 308}
TEMPORARY = {302, 303, 307}

META_ROBOTS = re.compile(r"<meta[^>]+name=[\"']?(?:robots|googlebot)[\"']?[^>]*>", re.I)
CONTENT_ATTR = re.compile(r"content=[\"']([^\"']*)[\"']", re.I)
CANONICAL = re.compile(r"<link[^>]+rel=[\"']?canonical[\"']?[^>]*>", re.I)
HREF_ATTR = re.compile(r"href=[\"']([^\"']+)[\"']", re.I)
REFRESH = re.compile(r"<meta[^>]+http-equiv=[\"']?refresh[\"']?[^>]*>", re.I)

SEVERITY = OrderedDict([
    ("not_redirected", "high"), ("broken_target", "high"), ("noindex_target", "high"),
    ("loop", "high"), ("canonical_elsewhere", "high"), ("home_target", "high"),
    ("wrong_target", "medium"), ("temporary", "medium"), ("chain", "medium"),
    ("gone_redirected", "low"), ("gone_still_live", "medium"), ("gone_404", "info"), ("error", "medium"),
    ("ok", "ok"), ("gone_ok", "ok"),
])


def fail(message, code=2):
    print("error: " + message, file=sys.stderr)
    sys.exit(code)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


OPENER = urllib.request.build_opener(NoRedirect)


def fetch(url, user_agent, timeout):
    """One request, no redirect followed. Returns (status, location, headers, body)."""
    request = urllib.request.Request(url, headers={
        "User-Agent": user_agent, "Accept": "text/html,*/*;q=0.8",
        "Accept-Language": "fr,en;q=0.8",
    })
    try:
        response = OPENER.open(request, timeout=timeout)
        status = response.status
        headers = response.headers
        body = response.read(READ_BYTES) if status == 200 else b""
    except urllib.error.HTTPError as error:
        status = error.code
        headers = error.headers
        body = b""
    location = headers.get("Location") if headers else None
    return status, location, headers, body


def key(url):
    parts = urlsplit(url)
    path = parts.path or "/"
    if len(path) > 1:
        path = path.rstrip("/")
    return (parts.hostname or "").lower(), path.lower(), parts.query


def absolute(url, base):
    if not url:
        return ""
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return urljoin(base.rstrip("/") + "/", url.lstrip("/"))


def rebase(url, base):
    """Put the path of url on the scheme and host of base."""
    if not base:
        return url
    parts = urlsplit(url if "://" in url else "http://x" + (url if url.startswith("/") else "/" + url))
    b = urlsplit(base)
    return "%s://%s%s%s" % (b.scheme, b.netloc, parts.path or "/", "?" + parts.query if parts.query else "")


def safe(url):
    parts = urlsplit(url)
    path = quote(parts.path, safe="/%:@!$&'()*+,;=-._~")
    return "%s://%s%s%s" % (parts.scheme, parts.netloc, path, "?" + parts.query if parts.query else "")


def inspect_page(headers, body, final_url):
    text = body.decode("utf-8", "replace") if body else ""
    robots = []
    header_value = headers.get("X-Robots-Tag") if headers else None
    if header_value:
        robots.append(header_value.lower())
    for tag in META_ROBOTS.findall(text):
        m = CONTENT_ATTR.search(tag)
        if m:
            robots.append(m.group(1).lower())
    noindex = any("noindex" in r or "none" == r.strip() for r in robots)
    canonical = ""
    for tag in CANONICAL.findall(text):
        m = HREF_ATTR.search(tag)
        if m:
            canonical = urljoin(final_url, m.group(1))
            break
    refresh = bool(REFRESH.search(text))
    return noindex, canonical, refresh


def check(source_url, expected, gone, user_agent, timeout, pause, paths_only=False):
    """paths_only: on staging, the landing page lives on the staging host
    while the map names the production one, so only paths are compared."""
    def same(a, b):
        ka, kb = key(a), key(b)
        return ka[1:] == kb[1:] if paths_only else ka == kb

    hops = []
    seen = set()
    url = source_url
    final_status, final_url, headers, body = None, url, None, b""
    for _ in range(MAX_HOPS + 1):
        if url in seen:
            return hops, "loop", final_url, final_status, {}
        seen.add(url)
        try:
            status, location, headers, body = fetch(safe(url), user_agent, timeout)
        except Exception as error:  # network level: DNS, TLS, timeout, reset
            hops.append({"url": url, "status": None, "error": str(error)[:120]})
            return hops, "error", url, None, {}
        hops.append({"url": url, "status": status, "location": location or ""})
        final_status, final_url = status, url
        if pause:
            time.sleep(pause)
        if status in PERMANENT or status in TEMPORARY:
            if not location:
                return hops, "broken_target", url, status, {}
            url = urljoin(url, location)
            continue
        break
    else:
        return hops, "loop", final_url, final_status, {}

    redirects = [h for h in hops if h.get("status") in PERMANENT | TEMPORARY]
    extra = {}
    if gone:
        if not redirects and final_status == 410:
            return hops, "gone_ok", final_url, final_status, extra
        if not redirects and final_status == 404:
            return hops, "gone_404", final_url, final_status, extra
        if not redirects and final_status == 200:
            return hops, "gone_still_live", final_url, final_status, extra
        return hops, "gone_redirected", final_url, final_status, extra

    if not redirects:
        if final_status == 200:
            if expected and same(final_url, expected):
                verdict = "ok"
            else:
                verdict = "not_redirected"
        else:
            verdict = "broken_target"
        return hops, verdict, final_url, final_status, extra

    if final_status is None or final_status >= 400 or final_status != 200:
        return hops, "broken_target", final_url, final_status, extra

    noindex, canonical, refresh = inspect_page(headers, body, final_url)
    extra = {"noindex": noindex, "canonical": canonical, "meta_refresh": refresh}
    landed = key(final_url)
    if expected and not same(final_url, expected):
        home = landed[1] in ("", "/")
        return hops, ("home_target" if home else "wrong_target"), final_url, final_status, extra
    if noindex:
        return hops, "noindex_target", final_url, final_status, extra
    if canonical and (key(canonical)[1] != landed[1] or (not paths_only and key(canonical)[0] != landed[0])):
        return hops, "canonical_elsewhere", final_url, final_status, extra
    if any(h["status"] in TEMPORARY for h in redirects):
        return hops, "temporary", final_url, final_status, extra
    if len(redirects) > 1:
        return hops, "chain", final_url, final_status, extra
    return hops, "ok", final_url, final_status, extra


def read_map(path):
    try:
        text = open(path, encoding="utf-8-sig").read()
    except OSError:
        fail("cannot read %s" % path)
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or "source" not in [f.strip().lower() for f in reader.fieldnames]:
        fail("%s is not a map written by redirect_map.py (no 'source' column)" % path)
    rows = []
    for row in reader:
        row = {k.strip().lower(): (v or "").strip() for k, v in row.items() if k}
        rows.append(row)
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="check_live.py",
        description="Test a redirect map against the live server, hop by hop.")
    parser.add_argument("map", help="map.csv from redirect_map.py")
    parser.add_argument("--old-base", help="scheme and host where the old URLs are requested")
    parser.add_argument("--expect-base", help="scheme and host that replace the host of the expected targets")
    parser.add_argument("--staging", action="store_true",
                        help="testing on staging: compare paths only, and ignore the host of canonicals")
    parser.add_argument("--out", default="live.json")
    parser.add_argument("--limit", type=int, default=0, help="test only the N rows worth most (0 = all)")
    parser.add_argument("--rate", type=float, default=2.0, help="requests per second (default 2)")
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--user-agent", default=DEFAULT_UA)
    parser.add_argument("--include-keep", action="store_true", help="also test rows marked keep")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    rows = read_map(args.map)
    wanted = ("redirect", "gone") + (("keep",) if args.include_keep else ())
    rows = [r for r in rows if r.get("decision", "redirect") in wanted]
    if not rows:
        fail("nothing to test: no row marked redirect or gone in %s" % args.map)
    rows.sort(key=lambda r: -float(r.get("value") or 0))
    if args.limit:
        rows = rows[: args.limit]
    pause = 1.0 / args.rate if args.rate > 0 else 0.0

    results = []
    for number, row in enumerate(rows, 1):
        source = row["source"]
        if source.startswith("http://") or source.startswith("https://"):
            source_url = rebase(source, args.old_base) if args.old_base else source
        else:
            if not args.old_base:
                fail("the map holds paths, pass --old-base https://host")
            source_url = rebase(source, args.old_base)
        gone = row.get("code") in ("410", "451") or row.get("decision") == "gone"
        target = row.get("target", "")
        if row.get("decision") == "keep":
            target = source_url
        expected = ""
        if target and not gone:
            expected = absolute(target, args.expect_base or args.old_base or source_url)
            if args.expect_base:
                expected = rebase(expected, args.expect_base)
        hops, verdict, final_url, final_status, extra = check(
            source_url, expected, gone, args.user_agent, args.timeout, pause, paths_only=args.staging)
        results.append(OrderedDict([
            ("source", row["source"]), ("tested", source_url), ("expected", expected),
            ("verdict", verdict), ("severity", SEVERITY[verdict]),
            ("hops", sum(1 for h in hops if h.get("status") in PERMANENT | TEMPORARY)),
            ("codes", [h.get("status") for h in hops]),
            ("final_url", final_url), ("final_status", final_status),
            ("value", float(row.get("value") or 0)),
        ] + list(extra.items())))
        if not args.quiet and number % 25 == 0:
            print("  %d / %d tested" % (number, len(rows)), file=sys.stderr)

    verdicts = Counter(r["verdict"] for r in results)
    at_risk = sum(r["value"] for r in results if r["severity"] == "high")
    summary = OrderedDict([
        ("map", args.map), ("tested", len(results)),
        ("old_base", args.old_base or ""), ("expect_base", args.expect_base or ""),
        ("date", time.strftime("%Y-%m-%d %H:%M")),
        ("verdicts", dict(verdicts)),
        ("high", sum(1 for r in results if r["severity"] == "high")),
        ("value_at_risk", at_risk),
        ("value_tested", sum(r["value"] for r in results)),
        ("rows", results),
    ])
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
    if not args.quiet:
        print("%d URLs tested" % len(results))
        for verdict in SEVERITY:
            if verdicts.get(verdict):
                print("  %-20s %4d  (%s)" % (verdict, verdicts[verdict], SEVERITY[verdict]))
        if at_risk:
            print("Value on high severity rows: %g of %g" % (at_risk, summary["value_tested"]))
        print("Written to %s" % args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
