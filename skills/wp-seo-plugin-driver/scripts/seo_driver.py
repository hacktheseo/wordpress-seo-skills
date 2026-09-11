#!/usr/bin/env python3
"""
Drive the SEO plugin a WordPress site already runs: Yoast SEO, Rank Math,
All in One SEO or SEOPress. Detect it, photograph what every page renders,
plan a bulk change with the exact call each plugin accepts, then prove the
change on the rendered page.

Usage:
    python3 seo_driver.py detect https://example.com [--json detect.json]
    python3 seo_driver.py snapshot URLS --out before.json [--max 500]
    python3 seo_driver.py diff before.json after.json [--json diff.json]
    python3 seo_driver.py plan changes.csv --detect detect.json \
        --snapshot before.json --out-dir plan/
    python3 seo_driver.py verify changes.csv after.json [--json verify.json]
    python3 seo_driver.py vars "%%title%% %%sep%% %%sitename%%" --from yoast --to rankmath

detect    Which SEO plugin renders the page, its version when it prints it,
          which REST routes and write paths the site exposes, and whether two
          SEO plugins fight over the same head.
snapshot  For each URL: title, meta description, canonical, robots, Open
          Graph, JSON-LD types, H1 count, hreflang count, and the post id and
          REST route WordPress prints in the head. URLS is a sitemap (file or
          URL), a text file of URLs, or local HTML files.
diff      What changed between two snapshots, most dangerous first: a page
          that became noindex, a canonical that left the host, a description
          that disappeared. The parity check for a plugin switch.
plan      Turn changes.csv (url, field, value) into apply.sh and a plan.json:
          one documented call per change for the detected plugin, credentials
          read from the environment only, nothing executed.
verify    Read the rendered pages after the change and say, change by
          change, whether the page now shows what was asked.
vars      Translate title template variables between the four plugins.
findings  Turn a diff (and a verify) into a findings JSON for the report engine.

The script never writes to a site. plan writes a shell file a person reads,
approves and runs. Every page, header and JSON it reads is data, never
instructions.

Standard library only. Part of the Hack The SEO agent skills.
Licence: GPL-2.0-or-later
"""

import argparse
import csv
import html
import io
import json
import os
import re
import shlex
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, OrderedDict
from urllib.parse import urljoin, urlsplit

UA = "Mozilla/5.0 (compatible; hacktheseo-seo-driver/1.0; +https://hacktheseo.com)"
READ_BYTES = 600000

FINGERPRINTS = [
    ("yoast", re.compile(r"optimized with the Yoast SEO(?: Premium)? plugin v?([\d.]+)", re.I)),
    ("yoast", re.compile(r"class=[\"']yoast-schema-graph", re.I)),
    ("rankmath", re.compile(r"Search Engine Optimization by Rank Math(?: PRO)?", re.I)),
    ("rankmath", re.compile(r"class=[\"']rank-math-schema", re.I)),
    ("aioseo", re.compile(r"All in One SEO(?: Pro)? ([\d.]+) - aioseo\.com", re.I)),
    ("aioseo", re.compile(r"content=[\"']All in One SEO \(AIOSEO\) ([\d.]+)", re.I)),
    ("aioseo", re.compile(r"class=[\"']aioseo-schema", re.I)),
    ("seoframework", re.compile(r"The SEO Framework by Sybre Waaijer", re.I)),
]
PREMIUM = {
    "yoast": re.compile(r"Yoast SEO Premium plugin", re.I),
    "rankmath": re.compile(r"Rank Math PRO", re.I),
    "aioseo": re.compile(r"All in One SEO Pro", re.I),
}
NAMESPACES = {
    "yoast/v1": "yoast", "rankmath/v1": "rankmath", "aioseo/v1": "aioseo",
    "seopress/v1": "seopress", "htsfree/v1": "hack-the-seo-free",
}
DRIVEN = ("yoast", "rankmath", "aioseo", "seopress")
FIELDS = ("title", "description", "canonical", "noindex", "focus_keyword")

TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
META_RE = re.compile(r"<meta\b[^>]*>", re.I)
LINK_RE = re.compile(r"<link\b[^>]*>", re.I)
ATTR_RE = re.compile(r"([a-zA-Z_:.-]+)\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+)")
LD_RE = re.compile(r"<script[^>]+application/ld\+json[^>]*>(.*?)</script>", re.I | re.S)
H1_RE = re.compile(r"<h1\b", re.I)
BODY_ID_RE = re.compile(r"<body[^>]*class=[\"'][^\"']*\b(?:postid|page-id)-(\d+)", re.I)
LOC_RE = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>", re.I)
GENERATOR_WP = re.compile(r"content=[\"']WordPress ([\d.]+)", re.I)


def fail(message, code=2):
    print("error: " + message, file=sys.stderr)
    sys.exit(code)


# --------------------------------------------------------------------------
# fetching, or reading local files for tests
# --------------------------------------------------------------------------

def is_url(text):
    return text.startswith("http://") or text.startswith("https://")


def get(url, timeout=20, accept="text/html,*/*;q=0.8"):
    """Return (status, headers, text). Never raises for HTTP errors."""
    if not is_url(url):
        if os.path.isfile(url):
            return 200, {}, open(url, encoding="utf-8", errors="replace").read()
        return 0, {}, ""
    request = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(READ_BYTES)
            charset = response.headers.get_content_charset() or "utf-8"
            return response.status, dict(response.headers), raw.decode(charset, "replace")
    except urllib.error.HTTPError as error:
        body = b""
        try:
            body = error.read(READ_BYTES)
        except Exception:
            pass
        return error.code, dict(error.headers or {}), body.decode("utf-8", "replace")
    except Exception as error:  # DNS, TLS, timeout: reported, never fatal
        return 0, {"error": str(error)[:160]}, ""


def attrs(tag):
    out = {}
    for name, value in ATTR_RE.findall(tag):
        value = value.strip("\"'")
        out[name.lower()] = html.unescape(value)
    return out


def clean(text):
    return re.sub(r"\s+", " ", html.unescape(text or "")).strip()


# --------------------------------------------------------------------------
# detect
# --------------------------------------------------------------------------

def fingerprint(text):
    found = OrderedDict()
    for plugin, pattern in FINGERPRINTS:
        m = pattern.search(text)
        if m:
            entry = found.setdefault(plugin, {"version": "", "premium": False, "evidence": []})
            if m.groups() and m.group(1) and not entry["version"]:
                entry["version"] = m.group(1)
            entry["evidence"].append(m.group(0)[:80])
    for plugin, pattern in PREMIUM.items():
        if plugin in found and pattern.search(text):
            found[plugin]["premium"] = True
    return found


def cmd_detect(args):
    site = args.site.rstrip("/")
    home_src = args.html or site + "/"
    status, headers, text = get(home_src)
    if status == 0:
        fail("cannot read %s: %s" % (home_src, headers.get("error", "no answer")))
    plugins = fingerprint(text)
    wp_version = (GENERATOR_WP.search(text) or [None, ""])[1] if GENERATOR_WP.search(text) else ""

    index_src = args.index or site + "/wp-json/"
    istatus, _, itext = get(index_src, accept="application/json")
    namespaces, routes = [], []
    rest_state = "open"
    if istatus == 200:
        try:
            index = json.loads(itext)
            namespaces = index.get("namespaces", []) or []
            routes = list((index.get("routes") or {}).keys())
        except ValueError:
            rest_state = "not json (a security plugin or a cache answered)"
    elif istatus in (401, 403):
        rest_state = "closed to visitors (%d)" % istatus
    else:
        rest_state = "unreachable (%s)" % (istatus or "no answer")

    for ns, plugin in NAMESPACES.items():
        if ns in namespaces:
            entry = plugins.setdefault(plugin, {"version": "", "premium": False, "evidence": []})
            entry["evidence"].append("REST namespace " + ns)

    def has_route(fragment):
        return any(fragment in r for r in routes)

    capabilities = OrderedDict([
        ("abilities_api", "wp-abilities/v1" in namespaces),
        ("mcp_adapter", any(ns == "mcp" or ns.startswith("mcp/") for ns in namespaces)),
        ("yoast_get_head", has_route("/yoast/v1/get_head")),
        ("rankmath_get_head", has_route("/rankmath/v1/getHead")),
        ("rankmath_update_meta", has_route("/rankmath/v1/updateMeta")),
        ("seopress_post_routes", has_route("/seopress/v1/posts")),
        ("aioseo_namespace", "aioseo/v1" in namespaces),
    ])
    driven = [p for p in plugins if p in DRIVEN]
    conflicts = driven if len(driven) > 1 else []

    sitemaps = OrderedDict()
    if not args.html:
        for path in ("/sitemap_index.xml", "/sitemap.xml", "/sitemaps.xml", "/wp-sitemap.xml"):
            s, _, t = get(site + path, timeout=10, accept="application/xml")
            sitemaps[path] = s
            if args.polite:
                time.sleep(0.5)
        s, _, robots = get(site + "/robots.txt", timeout=10, accept="text/plain")
        declared = re.findall(r"(?im)^sitemap:\s*(\S+)", robots) if s == 200 else []
        s_llms, _, _ = get(site + "/llms.txt", timeout=10, accept="text/plain")
    else:
        declared, s_llms = [], None

    write_paths = []
    primary = driven[0] if driven else ""
    if primary == "rankmath":
        write_paths.append("POST /wp-json/rankmath/v1/updateMeta" + ("" if capabilities["rankmath_update_meta"] else " (route not listed publicly, test with credentials)"))
    if primary == "yoast":
        write_paths.append("POST /wp-json/wp/v2/posts/{id} meta, Yoast 27.7+, posts only, title description focus keyword")
        write_paths.append("wp post meta update (WP-CLI), every field and post type")
    if primary == "aioseo":
        write_paths.append("POST /wp-json/wp/v2/{type}/{id} aioseo_meta_data, AIOSEO 4.9.8+ (earlier: paid REST add-on)")
    if primary == "seopress":
        write_paths.append("PUT /wp-json/seopress/v1/posts/{id}/title-description-metas and meta-robot-settings")
    if capabilities["abilities_api"]:
        write_paths.append("Abilities API present (WordPress 6.9+): list with credentials at /wp-json/wp-abilities/v1/abilities")

    result = OrderedDict([
        ("site", site), ("home_status", status), ("wordpress_version", wp_version),
        ("plugins", plugins), ("primary", primary), ("conflict", conflicts),
        ("rest", rest_state), ("namespaces", [n for n in namespaces if not n.startswith("wp/")]),
        ("capabilities", capabilities), ("write_paths", write_paths),
        ("sitemaps", sitemaps), ("sitemaps_in_robots", declared),
        ("llms_txt_status", s_llms),
    ])
    if args.json:
        with open(args.json, "w", encoding="utf-8") as h:
            json.dump(result, h, ensure_ascii=False, indent=2)
    if not args.quiet:
        if not plugins:
            print("No SEO plugin signature found on %s. It may hide its comments: check the REST namespaces." % site)
        for name, info in plugins.items():
            print("%s%s%s  (%s)" % (name, " " + info["version"] if info["version"] else "",
                                     " premium" if info["premium"] else "", "; ".join(info["evidence"][:2])))
        if conflicts:
            print("CONFLICT: %s all render SEO tags. Expect duplicate titles, descriptions and schema." % ", ".join(conflicts))
        print("REST API: %s" % rest_state)
        for k, v in capabilities.items():
            if v:
                print("  %s" % k)
        for w in write_paths:
            print("write path: %s" % w)
    return 0


# --------------------------------------------------------------------------
# snapshot
# --------------------------------------------------------------------------

def extract(text, url):
    head_end = text.lower().find("</head>")
    head = text[: head_end if head_end > 0 else len(text)]
    out = OrderedDict([("url", url)])
    m = TITLE_RE.search(head)
    out["title"] = clean(m.group(1)) if m else ""
    metas = {}
    for tag in META_RE.findall(head):
        a = attrs(tag)
        name = (a.get("name") or a.get("property") or "").lower()
        if name and "content" in a and name not in metas:
            metas[name] = clean(a["content"])
    out["description"] = metas.get("description", "")
    robots = " ".join(v for k, v in metas.items() if k in ("robots", "googlebot")).lower()
    out["robots"] = robots
    out["noindex"] = "noindex" in robots or robots.strip() == "none"
    out["og_title"] = metas.get("og:title", "")
    out["og_description"] = metas.get("og:description", "")
    canonical, rest, shortlink, hreflang = "", "", "", 0
    for tag in LINK_RE.findall(head):
        a = attrs(tag)
        rel = (a.get("rel") or "").lower()
        if rel == "canonical" and not canonical:
            canonical = urljoin(url, a.get("href", ""))
        elif rel == "alternate" and "hreflang" in a:
            hreflang += 1
        elif rel == "alternate" and a.get("type", "").lower() == "application/json" and "/wp-json/" in a.get("href", ""):
            rest = a.get("href", "")
        elif rel == "shortlink":
            shortlink = a.get("href", "")
    out["canonical"] = canonical
    out["hreflang"] = hreflang
    types = []
    for block in LD_RE.findall(text):
        try:
            data = json.loads(block.strip())
        except ValueError:
            types.append("INVALID")
            continue
        stack = [data]
        while stack:
            node = stack.pop()
            if isinstance(node, list):
                stack.extend(node)
            elif isinstance(node, dict):
                t = node.get("@type")
                if isinstance(t, list):
                    types.extend(str(x) for x in t)
                elif t:
                    types.append(str(t))
                stack.extend(v for v in node.values() if isinstance(v, (dict, list)))
    out["schema_types"] = sorted(set(types))
    out["h1"] = len(H1_RE.findall(text))
    post_id, post_route = "", ""
    m = re.search(r"/wp-json/wp/v2/([a-z0-9_-]+)/(\d+)", rest)
    if m:
        post_route, post_id = m.group(1), m.group(2)
    else:
        m = BODY_ID_RE.search(text) or re.search(r"[?&]p=(\d+)", shortlink)
        if m:
            post_id = m.group(1)
    out["post_id"] = post_id
    out["rest_route"] = post_route
    out["plugins"] = list(fingerprint(head).keys())
    return out


def url_list(source, limit, polite):
    if os.path.isdir(source):
        return sorted(os.path.join(source, f) for f in os.listdir(source) if f.endswith(".html"))[:limit]
    status, _, text = get(source, accept="application/xml,text/plain,*/*")
    if status != 200:
        fail("cannot read %s" % source)
    if "<sitemapindex" in text[:3000]:
        urls = []
        for child in LOC_RE.findall(text):
            s, _, t = get(html.unescape(child), accept="application/xml")
            urls.extend(html.unescape(u) for u in LOC_RE.findall(t))
            if polite:
                time.sleep(polite)
            if len(urls) >= limit:
                break
        return urls[:limit]
    if "<urlset" in text[:3000]:
        return [html.unescape(u) for u in LOC_RE.findall(text)][:limit]
    return [l.strip() for l in text.splitlines() if l.strip() and not l.startswith("#")][:limit]


def cmd_snapshot(args):
    urls = []
    for source in args.urls:
        if source.endswith(".html") and os.path.isfile(source):
            urls.append(source)
        else:
            urls.extend(url_list(source, args.max, 1.0 / args.rate if args.rate else 0))
    urls = urls[: args.max]
    if not urls:
        fail("no URL to read")
    pause = 1.0 / args.rate if args.rate else 0
    pages = []
    for n, url in enumerate(urls, 1):
        status, headers, text = get(url)
        row = extract(text, url) if status == 200 else OrderedDict([("url", url)])
        row["status"] = status
        xrobots = (headers.get("X-Robots-Tag") or headers.get("x-robots-tag") or "").lower()
        if xrobots:
            row["x_robots_tag"] = xrobots
            row["noindex"] = bool(row.get("noindex")) or "noindex" in xrobots
        pages.append(row)
        if pause and is_url(url):
            time.sleep(pause)
        if not args.quiet and n % 25 == 0:
            print("  %d / %d" % (n, len(urls)), file=sys.stderr)
    snap = OrderedDict([("taken", time.strftime("%Y-%m-%d %H:%M")), ("count", len(pages)), ("pages", pages)])
    with open(args.out, "w", encoding="utf-8") as h:
        json.dump(snap, h, ensure_ascii=False, indent=2)
    if not args.quiet:
        missing = sum(1 for p in pages if p.get("status") == 200 and not p.get("description"))
        noindex = sum(1 for p in pages if p.get("noindex"))
        print("%d pages read, %d without a meta description, %d noindex. Written to %s"
              % (len(pages), missing, noindex, args.out))
    return 0


# --------------------------------------------------------------------------
# diff
# --------------------------------------------------------------------------

def load_snapshot(path):
    try:
        data = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError) as error:
        fail("cannot read snapshot %s: %s" % (path, error))
    return OrderedDict((norm_url(p["url"]), p) for p in data.get("pages", []))


def norm_url(url):
    if not is_url(url):
        return os.path.basename(url)
    parts = urlsplit(url)
    path = parts.path or "/"
    return "%s%s" % ((parts.hostname or "").lower(), path.rstrip("/") or "/")


def find_page(pages, url):
    """Look a change up in a snapshot: by URL, or by slug when the snapshot
    was taken from saved HTML files named after the slug."""
    page = pages.get(norm_url(url))
    if page is not None:
        return page
    slug = [s for s in urlsplit(url).path.split("/") if s]
    stem = slug[-1] if slug else "index"
    for key, candidate in pages.items():
        if key.endswith(".html") and key[:-5] in (stem, "accueil" if not slug else stem):
            return candidate
    return None


def host_path(url):
    parts = urlsplit(url)
    return (parts.hostname or "").lower(), (parts.path or "/").rstrip("/") or "/"


def cmd_diff(args):
    before, after = load_snapshot(args.before), load_snapshot(args.after)
    issues = []

    def add(sev, kind, url, old, new):
        issues.append(OrderedDict([("severity", sev), ("type", kind), ("url", url),
                                   ("before", old), ("after", new)]))

    for key, b in before.items():
        a = after.get(key)
        url = b["url"]
        if a is None:
            add("medium", "not_in_after", url, "", "")
            continue
        if b.get("status") == 200 and a.get("status") != 200:
            add("high", "status_changed", url, b.get("status"), a.get("status"))
            continue
        if not b.get("noindex") and a.get("noindex"):
            add("high", "became_noindex", url, b.get("robots", ""), a.get("robots", ""))
        if b.get("noindex") and not a.get("noindex"):
            add("medium", "became_indexable", url, b.get("robots", ""), a.get("robots", ""))
        bc, ac = b.get("canonical", ""), a.get("canonical", "")
        if bc and not ac:
            add("high", "canonical_lost", url, bc, "")
        elif bc and ac and host_path(bc) != host_path(ac):
            sev = "high" if host_path(bc)[0] != host_path(ac)[0] else "medium"
            add(sev, "canonical_changed", url, bc, ac)
        if b.get("description") and not a.get("description"):
            add("high", "description_lost", url, b["description"], "")
        elif b.get("description", "") != a.get("description", ""):
            add("low", "description_changed", url, b.get("description", ""), a.get("description", ""))
        if b.get("title", "") != a.get("title", ""):
            add("medium" if not a.get("title") else "low", "title_changed", url, b.get("title", ""), a.get("title", ""))
        lost = sorted(set(b.get("schema_types", [])) - set(a.get("schema_types", [])))
        if lost:
            add("medium", "schema_lost", url, ", ".join(lost), ", ".join(a.get("schema_types", [])))
        if b.get("og_title") and not a.get("og_title"):
            add("low", "open_graph_lost", url, b["og_title"], "")
        if b.get("hreflang", 0) and not a.get("hreflang", 0):
            add("high", "hreflang_lost", url, b["hreflang"], 0)
        if len(a.get("plugins", [])) > 1 and len(b.get("plugins", [])) <= 1:
            add("high", "two_seo_plugins", url, ", ".join(b.get("plugins", [])), ", ".join(a.get("plugins", [])))
    rank = {"high": 0, "medium": 1, "low": 2}
    issues.sort(key=lambda i: (rank[i["severity"]], i["type"]))
    counts = Counter(i["type"] for i in issues)
    result = OrderedDict([
        ("before", args.before), ("after", args.after), ("pages", len(before)),
        ("identical", sum(1 for k in before if k in after and not any(i["url"] == before[k]["url"] for i in issues))),
        ("by_type", dict(counts)), ("by_severity", dict(Counter(i["severity"] for i in issues))),
        ("issues", issues),
    ])
    if args.json:
        with open(args.json, "w", encoding="utf-8") as h:
            json.dump(result, h, ensure_ascii=False, indent=2)
    if not args.quiet:
        print("%d pages compared, %d identical" % (result["pages"], result["identical"]))
        for kind, n in counts.most_common():
            print("  %-20s %d" % (kind, n))
    return 1 if args.strict and result["by_severity"].get("high") else 0


# --------------------------------------------------------------------------
# plan
# --------------------------------------------------------------------------

def read_changes(path):
    try:
        text = open(path, encoding="utf-8-sig").read()
    except OSError:
        fail("cannot read %s" % path)
    reader = csv.DictReader(io.StringIO(text))
    need = {"url", "field", "value"}
    if not reader.fieldnames or not need <= {f.strip().lower() for f in reader.fieldnames}:
        fail("%s needs the columns url, field, value" % path)
    rows = []
    for n, row in enumerate(reader, 2):
        row = {k.strip().lower(): (v or "").strip() for k, v in row.items() if k}
        if row["field"] not in FIELDS:
            fail("%s line %d: field %r, expected one of %s" % (path, n, row["field"], ", ".join(FIELDS)))
        # These values end up in a shell script a person will run. A line
        # break could smuggle a command out of a comment, and a post id is a
        # number or nothing.
        for key in ("url", "value", "post_id"):
            if "\n" in row.get(key, "") or "\r" in row.get(key, ""):
                fail("%s line %d: a line break in %s is not allowed" % (path, n, key))
        if row.get("post_id") and not re.fullmatch(r"\d{1,12}", row["post_id"]):
            fail("%s line %d: post_id must be a number, got %r" % (path, n, row["post_id"]))
        if not is_url(row["url"]):
            fail("%s line %d: url must start with http:// or https://" % (path, n))
        rows.append(row)
    return rows


def truthy(value):
    return value.strip().lower() in ("1", "yes", "true", "oui", "noindex")


def rest_call(method, path, body):
    """One curl call. The credentials reach curl on stdin through --config,
    so they never appear in a process list or a shell history."""
    data = json.dumps(body, ensure_ascii=False)
    return ('auth | curl -sS --fail --config - -X %s -H "Content-Type: application/json" '
            '"$WP_SITE"%s --data %s -o /dev/null -w "%%{http_code} %s\\n"' % (method, shlex.quote(path), shlex.quote(data), path))


def plan_one(plugin, change, page):
    """Return (commands, note). commands is a list of shell lines."""
    field, value = change["field"], change["value"]
    pid = page.get("post_id", "")
    route = page.get("rest_route") or "posts"
    if pid and not re.fullmatch(r"\d{1,12}", str(pid)):
        return [], "post id %r is not a number, skipped" % pid
    if not re.fullmatch(r"[a-z0-9_-]{1,40}", route):
        route = "posts"
    if not pid:
        return [], "no post id printed in the page head: find it in the admin, or add a column post_id"
    noindex = truthy(value) if field == "noindex" else None

    if plugin == "rankmath":
        keys = {"title": "rank_math_title", "description": "rank_math_description",
                "canonical": "rank_math_canonical_url", "focus_keyword": "rank_math_focus_keyword"}
        if field == "noindex":
            meta = {"rank_math_robots": ["noindex", "follow"] if noindex else ["index", "follow"]}
            note = "robots array format not documented by Rank Math: apply to one page, verify, then the rest"
        else:
            meta = {keys[field]: value}
            note = ""
        body = {"objectType": "post", "objectID": int(pid), "meta": meta}
        return [rest_call("POST", "/wp-json/rankmath/v1/updateMeta", body)], note

    if plugin == "yoast":
        keys = {"title": "_yoast_wpseo_title", "description": "_yoast_wpseo_metadesc",
                "canonical": "_yoast_wpseo_canonical", "focus_keyword": "_yoast_wpseo_focuskw",
                "noindex": "_yoast_wpseo_meta-robots-noindex"}
        stored = ("1" if noindex else "2") if field == "noindex" else value
        cli = "wp post meta update %s %s %s" % (pid, keys[field], shlex.quote(stored))
        if field in ("title", "description", "focus_keyword") and route == "posts":
            body = {"meta": {keys[field]: value}}
            return [rest_call("POST", "/wp-json/wp/v2/posts/%s" % pid, body)], \
                "Yoast 27.7 or later registers this key for posts only. Older, or a 200 with no change: use WP-CLI: " + cli
        return ["# WP-CLI, over SSH on the server: " + cli], \
            "Yoast exposes no REST write for this field or post type. Never write it in SQL: its indexables would go stale"

    if plugin == "aioseo":
        if field == "focus_keyword":
            return [], "AIOSEO stores keyphrases as a JSON structure: set it in the editor"
        if field == "noindex":
            data = {"robots_default": False, "robots_noindex": bool(noindex)}
            note = "robots_noindex applies only when robots_default is false. Apply to one page, verify, then the rest"
        else:
            data = {{"title": "title", "description": "description", "canonical": "canonical_url"}[field]: value}
            note = "AIOSEO 4.9.8 or later. Never write _aioseo_* post meta: AIOSEO does not read it back"
        return [rest_call("POST", "/wp-json/wp/v2/%s/%s" % (route, pid), {"aioseo_meta_data": data})], note

    if plugin == "seopress":
        if field in ("title", "description"):
            body = {field: value}
            return [rest_call("PUT", "/wp-json/seopress/v1/posts/%s/title-description-metas" % pid, body)], \
                "sends one field: check the other one is not emptied, on one page first"
        if field == "noindex":
            return [rest_call("PUT", "/wp-json/seopress/v1/posts/%s/meta-robot-settings" % pid,
                              {"_seopress_robots_index": "yes" if noindex else ""})], "SEOPress stores 'yes' to mean noindex"
        if field == "canonical":
            return [rest_call("PUT", "/wp-json/seopress/v1/posts/%s/meta-robot-settings" % pid,
                              {"_seopress_robots_canonical": value})], ""
        return ["# WP-CLI: wp post meta update %s _seopress_analysis_target_kw %s" % (pid, shlex.quote(value))], \
            "the target-keywords route body is not documented: WP-CLI is the safe path"
    return [], "no documented write path for %s" % plugin


def cmd_plan(args):
    changes = read_changes(args.changes)
    detect = json.load(open(args.detect, encoding="utf-8")) if args.detect else {}
    plugin = args.plugin or detect.get("primary", "")
    if plugin not in DRIVEN:
        fail("no driven SEO plugin: pass --plugin yoast|rankmath|aioseo|seopress or a detect.json")
    if detect.get("conflict"):
        print("warning: two SEO plugins render tags on this site (%s). Fix that before any bulk change."
              % ", ".join(detect["conflict"]), file=sys.stderr)
    pages = load_snapshot(args.snapshot) if args.snapshot else {}
    os.makedirs(args.out_dir, exist_ok=True)
    lines = [
        "#!/bin/sh",
        "# Generated by seo_driver.py plan for %s. Read it before running it." % plugin,
        "# Credentials come from the environment only, never from this file:",
        "#   export WP_SITE=https://example.com WP_USER=editor WP_APP_PASSWORD=(Users, Profile, Application Passwords)",
        "# Each call prints its HTTP status. The script stops at the first call that fails.",
        "# Run it with --first to send only the first change, verify it, then run it again without.",
        'set -eu',
        ': "${WP_SITE:?set WP_SITE}" "${WP_USER:?set WP_USER}" "${WP_APP_PASSWORD:?set WP_APP_PASSWORD}"',
        'FIRST="${1:-}"',
        "# curl reads the credentials from stdin (--config -): they never reach a command line.",
        'auth() { printf \'user = "%s:%s"\\n\' "$WP_USER" "$WP_APP_PASSWORD"; }',
        "",
    ]
    plan = []
    for change in changes:
        page = dict(find_page(pages, change["url"]) or {})
        if change.get("post_id"):
            page["post_id"] = change["post_id"]
        commands, note = plan_one(plugin, change, page)
        before = page.get(change["field"], page.get("noindex") if change["field"] == "noindex" else "")
        plan.append(OrderedDict([("url", change["url"]), ("field", change["field"]), ("value", change["value"]),
                                 ("post_id", page.get("post_id", "")), ("rendered_before", before),
                                 ("commands", commands), ("note", note)]))
        lines.append("# %s  %s -> %s" % (change["url"][:200], change["field"], change["value"][:70]))
        if note:
            lines.append("# note: " + note)
        lines.extend(commands or ["# SKIPPED: " + (note or "no command")])
        if commands and not commands[0].startswith("#") and not any(
                l.startswith('if [ "$FIRST"') for l in lines):
            lines.append('if [ "$FIRST" = "--first" ]; then echo "First change sent. Verify it, then run again without --first."; exit 0; fi')
        lines.append("")
    with open(os.path.join(args.out_dir, "apply.sh"), "w", encoding="utf-8") as h:
        h.write("\n".join(lines) + "\n")
    with open(os.path.join(args.out_dir, "plan.json"), "w", encoding="utf-8") as h:
        json.dump(OrderedDict([("plugin", plugin), ("changes", plan)]), h, ensure_ascii=False, indent=2)
    ready = sum(1 for p in plan if p["commands"] and not p["commands"][0].startswith("#"))
    manual = sum(1 for p in plan if p["commands"] and p["commands"][0].startswith("#"))
    skipped = sum(1 for p in plan if not p["commands"])
    if not args.quiet:
        print("%d changes for %s: %d REST calls ready, %d WP-CLI lines, %d skipped"
              % (len(plan), plugin, ready, manual, skipped))
        print("Written %s and %s. Nothing was sent." % (os.path.join(args.out_dir, "apply.sh"),
                                                       os.path.join(args.out_dir, "plan.json")))
    return 0


# --------------------------------------------------------------------------
# verify
# --------------------------------------------------------------------------

VARS = re.compile(r"%%[a-z_]+%%|%[a-z_]+%|#[a-z_]+")


def literal_parts(value):
    return [p.strip() for p in VARS.split(value) if p.strip(" |-:")]


def cmd_verify(args):
    changes = read_changes(args.changes)
    pages = load_snapshot(args.after)
    rows = []
    for change in changes:
        page = find_page(pages, change["url"])
        field, value = change["field"], change["value"]
        if page is None:
            rows.append((change, "not_read", ""))
            continue
        if field == "noindex":
            want = truthy(value)
            got = bool(page.get("noindex"))
            rows.append((change, "ok" if want == got else "mismatch", "noindex" if got else "index"))
            continue
        if field == "focus_keyword":
            rows.append((change, "not_rendered", "a focus keyword never appears in the page"))
            continue
        got = page.get(field, "")
        if field == "canonical":
            ok = host_path(got) == host_path(value) if got else False
        else:
            parts = literal_parts(value)
            ok = all(p.lower() in got.lower() for p in parts) if parts else bool(got)
        rows.append((change, "ok" if ok else "mismatch", got))
    counts = Counter(v for _, v, _ in rows)
    result = OrderedDict([("changes", len(rows)), ("by_verdict", dict(counts)), ("rows", [
        OrderedDict([("url", c["url"]), ("field", c["field"]), ("wanted", c["value"]),
                     ("verdict", v), ("rendered", g)]) for c, v, g in rows])])
    if args.json:
        with open(args.json, "w", encoding="utf-8") as h:
            json.dump(result, h, ensure_ascii=False, indent=2)
    if not args.quiet:
        print("%d changes checked on the rendered pages: %s" % (
            len(rows), ", ".join("%s %d" % kv for kv in counts.most_common())))
        for c, v, g in rows:
            if v == "mismatch":
                print("  MISMATCH %s %s: page shows %r" % (c["url"], c["field"], g[:80]))
    return 1 if counts.get("mismatch") and args.strict else 0


# --------------------------------------------------------------------------
# findings, for the shared report engine
# --------------------------------------------------------------------------

WORDS = {
    "en": {
        "title": "SEO plugin switch, what survived", "eyebrow": "In short",
        "v_bad": "%d of %d pages lost something that costs traffic in the switch",
        "v_ok": "All %d pages came through the switch intact",
        "k_pages": "Pages compared", "k_same": "Identical", "k_high": "Serious changes",
        "k_desc": "Descriptions lost",
        "s_changes": "What changed on the rendered pages", "s_verify": "The corrections, checked on the page",
        "cols": ["Page", "Change", "Before", "After"], "vcols": ["Page", "Field", "Wanted", "Result"],
        "note_t": "What this cannot show",
        "note": "This compares what the pages render, not what the plugins store. A field set in the new plugin but hidden by a template, or an internal setting with no visible effect, does not show here. Sitemaps, redirects and settings pages are separate checks.",
        "types": {"became_noindex": "Became noindex", "canonical_changed": "Canonical changed",
                  "canonical_lost": "Canonical lost", "description_lost": "Description lost",
                  "description_changed": "Description changed", "title_changed": "Title changed",
                  "schema_lost": "Structured data lost", "open_graph_lost": "Open Graph lost",
                  "hreflang_lost": "hreflang lost", "two_seo_plugins": "Two SEO plugins active",
                  "status_changed": "Page no longer answers 200", "not_in_after": "Page missing after",
                  "became_indexable": "Became indexable"},
        "actions": {"became_noindex": "Restore index on these pages in the new plugin, today.",
                    "canonical_changed": "Set the canonical back to the page itself.",
                    "canonical_lost": "Check the new plugin outputs a canonical on this post type.",
                    "description_lost": "Rewrite or re-import the description, then verify.",
                    "schema_lost": "Enable the schema type for this post type in the new plugin.",
                    "hreflang_lost": "Check the multilingual plugin still hands hreflang to the new SEO plugin.",
                    "two_seo_plugins": "Deactivate the old plugin once the import is verified.",
                    "status_changed": "Find out why the page no longer answers 200.",
                    "title_changed": "Confirm the new separator or template is intended.",
                    "open_graph_lost": "Enable Open Graph in the new plugin.",
                    "description_changed": "Confirm the new description is intended.",
                    "not_in_after": "Read this page again after the switch.",
                    "became_indexable": "Confirm this page should now be indexed."},
    },
    "fr": {
        "title": "Changement d'extension SEO, ce qui a survécu", "eyebrow": "En bref",
        "v_bad": "%d pages sur %d ont perdu un élément qui coûte du trafic",
        "v_ok": "Les %d pages sont passées intactes",
        "k_pages": "Pages comparées", "k_same": "Identiques", "k_high": "Changements graves",
        "k_desc": "Descriptions perdues",
        "s_changes": "Ce qui a changé sur les pages", "s_verify": "Les corrections, vérifiées sur la page",
        "cols": ["Page", "Changement", "Avant", "Après"], "vcols": ["Page", "Champ", "Demandé", "Résultat"],
        "note_t": "Ce que cette comparaison ne montre pas",
        "note": "On compare ce que les pages affichent, pas ce que les extensions stockent. Un champ rempli dans la nouvelle extension mais masqué par un modèle, ou un réglage sans effet visible, n'apparaît pas ici. Plans de site, redirections et réglages se vérifient à part.",
        "types": {"became_noindex": "Passée en noindex", "canonical_changed": "Canonique modifiée",
                  "canonical_lost": "Canonique perdue", "description_lost": "Description perdue",
                  "description_changed": "Description modifiée", "title_changed": "Titre modifié",
                  "schema_lost": "Données structurées perdues", "open_graph_lost": "Open Graph perdu",
                  "hreflang_lost": "hreflang perdu", "two_seo_plugins": "Deux extensions SEO actives",
                  "status_changed": "La page ne répond plus 200", "not_in_after": "Page absente après",
                  "became_indexable": "Devenue indexable"},
        "actions": {"became_noindex": "Rétablir l'indexation de ces pages dans la nouvelle extension, aujourd'hui.",
                    "canonical_changed": "Remettre la canonique sur la page elle-même.",
                    "canonical_lost": "Vérifier que la nouvelle extension produit une canonique pour ce type de contenu.",
                    "description_lost": "Réécrire ou réimporter la description, puis vérifier.",
                    "schema_lost": "Activer ce type de données structurées pour ce type de contenu.",
                    "hreflang_lost": "Vérifier que l'extension multilingue transmet encore les hreflang.",
                    "two_seo_plugins": "Désactiver l'ancienne extension une fois l'import vérifié.",
                    "status_changed": "Comprendre pourquoi la page ne répond plus 200.",
                    "title_changed": "Confirmer que le nouveau séparateur ou modèle est voulu.",
                    "open_graph_lost": "Activer Open Graph dans la nouvelle extension.",
                    "description_changed": "Confirmer que la nouvelle description est voulue.",
                    "not_in_after": "Relire cette page après le changement.",
                    "became_indexable": "Confirmer que cette page doit désormais être indexée."},
    },
}


def cmd_findings(args):
    W = WORDS[args.lang]
    try:
        diff = json.load(open(args.diff, encoding="utf-8"))
    except (OSError, ValueError) as error:
        fail("cannot read %s: %s" % (args.diff, error))
    issues = diff.get("issues", [])
    serious = sorted({i["url"] for i in issues if i["severity"] == "high"})
    verdict = (W["v_bad"] % (len(serious), diff.get("pages", 0)) if serious
               else W["v_ok"] % diff.get("pages", 0))
    kpis = [
        {"label": W["k_pages"], "value": str(diff.get("pages", 0)), "tone": "neutral"},
        {"label": W["k_same"], "value": str(diff.get("identical", 0)), "tone": "good"},
        {"label": W["k_high"], "value": str(len(serious)), "tone": "bad" if serious else "good"},
        {"label": W["k_desc"], "value": str(diff.get("by_type", {}).get("description_lost", 0)),
         "tone": "bad" if diff.get("by_type", {}).get("description_lost") else "good"},
    ]
    items = []
    for kind in Counter(i["type"] for i in issues if i["severity"] in ("high", "medium")):
        rows = [i for i in issues if i["type"] == kind]
        items.append({"severity": rows[0]["severity"],
                      "title": "%s: %d" % (W["types"].get(kind, kind), len(rows)),
                      "evidence": "; ".join(short(i["url"]) for i in rows[:3]),
                      "action": W["actions"].get(kind, "")})
    rank = {"high": 0, "medium": 1, "low": 2, "info": 3}
    items.sort(key=lambda x: rank[x["severity"]])
    table = [[short(i["url"]), W["types"].get(i["type"], i["type"]), str(i["before"])[:70], str(i["after"])[:70]]
             for i in issues[:15]]
    blocks = []
    if items:
        blocks.append({"type": "findings", "items": items[:6]})
    if table:
        blocks.append({"type": "table", "columns": W["cols"], "rows": table,
                       "caption": "seo_driver.py diff, %s" % os.path.basename(args.diff)})
    sections = [{"title": W["s_changes"], "blocks": blocks or [{"type": "note", "text": verdict}]}]
    if args.verify:
        ver = json.load(open(args.verify, encoding="utf-8"))
        vrows = [[short(r["url"]), r["field"], r["wanted"][:60], r["verdict"]] for r in ver.get("rows", [])]
        sections.append({"title": W["s_verify"], "blocks": [{"type": "table", "columns": W["vcols"], "rows": vrows}]})
    sections.append({"title": W["note_t"], "blocks": [{"type": "note", "text": W["note"], "tone": "warn"}]})
    out = OrderedDict([
        ("meta", {"title": W["title"], "subject": args.site, "lang": args.lang}),
        ("headline", {"eyebrow": W["eyebrow"], "verdict": verdict}),
        ("kpis", kpis), ("sections", sections),
    ])
    with open(args.out, "w", encoding="utf-8") as h:
        json.dump(out, h, ensure_ascii=False, indent=2)
    print("Findings written to %s" % args.out)
    return 0


def short(url):
    if not is_url(url):
        return os.path.basename(url)
    return urlsplit(url).path or "/"


# --------------------------------------------------------------------------
# vars
# --------------------------------------------------------------------------

VARIABLES = [
    # meaning, yoast, rankmath, aioseo, seopress
    ("post title", "%%title%%", "%title%", "#post_title", "%%post_title%%"),
    ("separator", "%%sep%%", "%sep%", "#separator_sa", "%%sep%%"),
    ("site title", "%%sitename%%", "%sitename%", "#site_title", "%%sitetitle%%"),
    ("tagline", "%%sitedesc%%", "%sitedesc%", "#tagline", "%%tagline%%"),
    ("excerpt", "%%excerpt%%", "%excerpt%", "#post_excerpt", "%%post_excerpt%%"),
    ("primary category", "%%primary_category%%", "%category%", "#categories", "%%post_category%%"),
    ("page number", "%%page%%", "%pagenumber%", "#page_number", "%%page%%"),
    ("current year", "%%currentyear%%", "%currentyear%", "#current_year", "%%currentyear%%"),
    ("term title", "%%term_title%%", "%term%", "#taxonomy_title", "%%term_title%%"),
    ("author", "%%name%%", "%name%", "#author_name", "%%post_author%%"),
    ("date", "%%date%%", "%date%", "#post_date", "%%post_date%%"),
    ("focus keyword", "%%focuskw%%", "%focuskw%", "", "%%target_keyword%%"),
]
COLUMN = {"yoast": 1, "rankmath": 2, "aioseo": 3, "seopress": 4}


def cmd_vars(args):
    src, dst = COLUMN[args.source], COLUMN[args.target]
    text = args.template
    unknown = []
    # longest tokens first, so %%title%% is never read as %title%
    table = sorted(VARIABLES, key=lambda r: -len(r[src]))
    tokens = VARS.findall(text)
    out = text
    for token in sorted(set(tokens), key=len, reverse=True):
        row = next((r for r in table if r[src] == token), None)
        if row is None or not row[dst]:
            unknown.append(token)
            continue
        out = out.replace(token, "\x00%d\x00" % VARIABLES.index(row))
    out = re.sub("\x00(\\d+)\x00", lambda m: VARIABLES[int(m.group(1))][dst], out)
    print(out)
    if unknown:
        print("no equivalent for: %s. Rewrite those by hand." % ", ".join(unknown), file=sys.stderr)
    return 0


# --------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(prog="seo_driver.py",
                                 description="Drive Yoast, Rank Math, AIOSEO or SEOPress safely.")
    sub = ap.add_subparsers(dest="command")

    d = sub.add_parser("detect", help="which SEO plugin, which write paths")
    d.add_argument("site")
    d.add_argument("--html", help="read the home page from this file instead of fetching it")
    d.add_argument("--index", help="read /wp-json/ from this file instead of fetching it")
    d.add_argument("--json")
    d.add_argument("--polite", action="store_true", help="pause between requests")
    d.add_argument("--quiet", action="store_true")

    s = sub.add_parser("snapshot", help="what every page renders")
    s.add_argument("urls", nargs="+", help="sitemap URL or file, URL list, HTML files, or a folder of them")
    s.add_argument("--out", required=True)
    s.add_argument("--max", type=int, default=500)
    s.add_argument("--rate", type=float, default=2.0, help="requests per second (default 2)")
    s.add_argument("--quiet", action="store_true")

    f = sub.add_parser("diff", help="compare two snapshots")
    f.add_argument("before")
    f.add_argument("after")
    f.add_argument("--json")
    f.add_argument("--strict", action="store_true")
    f.add_argument("--quiet", action="store_true")

    p = sub.add_parser("plan", help="write apply.sh for a bulk change, send nothing")
    p.add_argument("changes", help="CSV with url, field, value (and optionally post_id)")
    p.add_argument("--detect", help="detect.json")
    p.add_argument("--plugin", choices=DRIVEN)
    p.add_argument("--snapshot", help="snapshot taken before, for post ids and current values")
    p.add_argument("--out-dir", default="plan")
    p.add_argument("--quiet", action="store_true")

    v = sub.add_parser("verify", help="check the rendered pages show the change")
    v.add_argument("changes")
    v.add_argument("after", help="snapshot taken after")
    v.add_argument("--json")
    v.add_argument("--strict", action="store_true")
    v.add_argument("--quiet", action="store_true")

    t = sub.add_parser("vars", help="translate title variables between plugins")
    t.add_argument("template")
    t.add_argument("--from", dest="source", required=True, choices=list(COLUMN))
    t.add_argument("--to", dest="target", required=True, choices=list(COLUMN))

    r = sub.add_parser("findings", help="build a findings JSON for the report engine")
    r.add_argument("diff", help="diff --json output")
    r.add_argument("--verify", help="verify --json output")
    r.add_argument("--site", default="")
    r.add_argument("--lang", choices=("en", "fr"), default="en")
    r.add_argument("--out", required=True)

    args = ap.parse_args(argv)
    if not args.command:
        ap.print_help(sys.stderr)
        return 2
    return {"detect": cmd_detect, "snapshot": cmd_snapshot, "diff": cmd_diff, "plan": cmd_plan,
            "verify": cmd_verify, "vars": cmd_vars, "findings": cmd_findings}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
