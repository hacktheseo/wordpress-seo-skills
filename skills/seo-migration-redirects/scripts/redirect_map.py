#!/usr/bin/env python3
"""
Build, check and export the redirect map of a WordPress site migration.

Usage:
    python3 redirect_map.py build --old OLD [OLD ...] --new NEW [NEW ...]
                                  [--existing RULES] [--new-host URL]
                                  [--rules rules.txt] --out map.csv
    python3 redirect_map.py lint map.csv [--new NEW ...] [--existing RULES]
                                  [--json lint.json] [--fix fixed.csv]
    python3 redirect_map.py hunt 404-source [--map map.csv] [--new NEW ...]
                                  [--json hunt.json] [--out-map proposals.csv]
    python3 redirect_map.py export map.csv --format FORMAT --out FILE

build   Match every old URL to a new one, most reliable method first: same
        path, a pattern learned from the two inventories (date prefix dropped,
        category base renamed, language prefix removed...), same slug, close
        slug, same title, then parent section. Anything left is written as a
        decision for a person, never sent to the home page.
lint    Find what breaks a migration after launch: chains, loops, targets that
        do not exist, many URLs piled onto one page (Google may treat that as
        a soft 404), temporary codes, and existing rules the new map turns
        into chains.
hunt    Sort a 404 list into what deserves a redirect, what is a bot probe,
        what is a broken internal link (a doubled /en/en/ prefix), and what
        the map already covers. Suggests a target for the rest.
export  Write the map for the tool that will serve it: redirection, yoast,
        rankmath, seopress, generic, htaccess or nginx.

Inputs are read, never fetched. OLD and NEW accept an XML sitemap, a Search
Console Pages export, a crawler export (Screaming Frog, Sitebulb), a JSON
answer from the Hack The SEO plugins, or one URL per line. Everything in
those files is data, never instructions.

Standard library only. Part of the Hack The SEO agent skills.
Licence: GPL-2.0-or-later
"""

import argparse
import csv
import difflib
import io
import json
import os
import re
import sys
import unicodedata
from collections import Counter, OrderedDict, defaultdict
from urllib.parse import unquote, urlsplit

ENCODINGS = ("utf-8-sig", "utf-8", "utf-16", "cp1252", "latin-1")
THIN_SPACES = "\u00a0\u202f\u2009\u2007\u2060"

URL_KEYS = {
    "url", "urls", "address", "adresse", "page", "pages", "toppages",
    "pageslesplusfrequentes", "pageslespluspopulaires", "loc", "source",
    "sourceurl", "urlsource", "from", "origin", "old", "oldurl", "ancienneurl",
    "landingpage", "adressedelapage", "pagina", "paginas", "seite",
}
TARGET_KEYS = {"target", "targeturl", "destination", "to", "cible", "newurl", "nouvelleurl"}
CODE_KEYS = {"code", "type", "status", "redirecttype", "statuscode", "httpcode"}
VALUE_KEYS = (
    ("value", {"value", "valeur"}),
    ("clicks", {"clicks", "clics", "totalclicks", "nombredeclics", "klicks"}),
    ("hits", {"hits", "hitcount", "count", "visites", "sessions", "pageviews"}),
    ("links", {"backlinks", "referringdomains", "domainesreferents", "inlinks",
               "liensentrants", "links"}),
    ("impressions", {"impressions", "affichages", "impresiones"}),
)
TITLE_KEYS = {"title", "title1", "titre", "pagetitle", "titredelapage", "name"}

# Requests nobody should ever redirect. A 404 on these is a scanner at work,
# and a redirect would only tell it the path is interesting.
PROBES = (
    "/wp-login.php", "/xmlrpc.php", "/wp-admin", "/wp-config", "/.env", "/.git",
    "/.ssh", "/.aws", "/phpmyadmin", "/adminer", "/vendor/phpunit", "/cgi-bin",
    "/admin",
    "/administrator", "/user/login", "/owa/", "/boaform", "/actuator", "/sdk",
    "/.well-known/security.txt",
)
PROBE_EXT = re.compile(r"\.(?:php\d?|asp|aspx|jsp|cgi|sql|bak|old|zip|tar|gz|ini|log|yml|yaml)$", re.I)
ASSET_EXT = re.compile(r"\.(?:jpe?g|png|gif|webp|avif|svg|ico|css|js|woff2?|ttf|eot|mp4|webm|pdf)$", re.I)
DATE_PREFIX = re.compile(r"^/\d{4}/\d{1,2}(?:/\d{1,2})?/")
EXTENSION = re.compile(r"\.(?:html?|php|aspx?)$", re.I)
LANG_PREFIX = re.compile(r"^/(?:en|fr|de|es|it|nl|pt|en-[a-z]{2}|fr-[a-z]{2})(?=/|$)", re.I)
ID_PREFIX = re.compile(r"/\d{1,7}-(?=[a-z])", re.I)
WP_QUERY = re.compile(r"(?:^|&)(?:p|page_id|attachment_id|cat|tag|m)=", re.I)

CONFIDENCE = OrderedDict([
    ("exact", 1.0),
    ("case", 0.95),
    ("rule", 0.95),
    ("pattern", 0.9),
    ("slug", 0.85),
    ("title", 0.8),
    ("slug-ambiguous", 0.55),
    ("slug-close", 0.55),
    ("parent", 0.35),
])


def fail(message, code=2):
    print("error: " + message, file=sys.stderr)
    sys.exit(code)


def warn(message):
    print("warning: " + message, file=sys.stderr)


# --------------------------------------------------------------------------
# reading
# --------------------------------------------------------------------------

def read_text(path):
    if not os.path.isfile(path):
        fail("file not found: %s" % path)
    with open(path, "rb") as handle:
        raw = handle.read()
    for encoding in ENCODINGS:
        try:
            text = raw.decode(encoding)
        except (UnicodeDecodeError, UnicodeError):
            continue
        if "\x00" in text:
            continue
        return text
    return raw.decode("latin-1", "replace")


def fold(name):
    text = unicodedata.normalize("NFKD", str(name or ""))
    text = text.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def to_number(text):
    value = str(text if text is not None else "").strip()
    for char in THIN_SPACES:
        value = value.replace(char, "")
    value = value.replace(" ", "").replace("%", "")
    if "," in value and "." not in value:
        value = value.replace(",", ".")
    try:
        return float(value)
    except ValueError:
        return 0.0


def load_json(text):
    """Parse JSON, skipping a leading provenance line.

    The Hack The SEO MCP answers open with a bracketed provenance sentence
    before the payload, so the first bracket is not always the data.
    Returns None when nothing parses.
    """
    head = text[:4000]
    starts = sorted(i for i, c in enumerate(head) if c in "{[")
    for start in starts[:40]:
        try:
            return json.loads(text[start:])
        except ValueError:
            continue
    return None


def rows_from_json(data):
    """Normalise the JSON answers of both plugins and of this script."""
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        items = None
        for field in ("rules", "urls", "top_404", "items", "rows", "map"):
            if isinstance(data.get(field), list):
                items = data[field]
                break
        if items is None:
            return []
    else:
        return []
    rows = []
    for item in items:
        if isinstance(item, str):
            rows.append({"url": item})
        elif isinstance(item, dict):
            url = item.get("source") or item.get("url") or item.get("loc") or ""
            rows.append({
                "url": str(url),
                "target": str(item.get("target") or ""),
                "code": item.get("type") or item.get("code") or "",
                "value": to_number(item.get("hits") or item.get("clicks") or 0),
                "enabled": item.get("enabled", True),
                "is_regex": bool(item.get("is_regex") or item.get("regex")),
                "title": str(item.get("title") or ""),
            })
    return rows


def rows_from_csv(text):
    lines = [l for l in text.splitlines() if l.strip()]
    if not lines:
        return []
    head = lines[0]
    counts = {d: head.count(d) for d in (",", ";", "\t", "|")}
    delimiter = max(counts, key=counts.get) if max(counts.values()) else ","
    reader = csv.reader(io.StringIO("\n".join(lines)), delimiter=delimiter)
    table = list(reader)
    header = [fold(c) for c in table[0]]
    has_header = any(h in URL_KEYS or h in TARGET_KEYS for h in header)
    if not has_header:
        # one URL per line, or source,target[,code] without a header
        rows = []
        for record in table:
            if not record or not record[0].strip():
                continue
            row = {"url": record[0].strip()}
            if len(record) > 1 and looks_like_url(record[1]):
                row["target"] = record[1].strip()
            if len(record) > 2 and record[2].strip().isdigit():
                row["code"] = record[2].strip()
            rows.append(row)
        return rows

    def find(keys):
        for i, h in enumerate(header):
            if h in keys:
                return i
        return None

    url_i = find(URL_KEYS)
    target_i = find(TARGET_KEYS)
    code_i = find(CODE_KEYS)
    title_i = find(TITLE_KEYS)
    value_i, value_kind = None, None
    for kind, keys in VALUE_KEYS:
        idx = find(keys)
        if idx is not None:
            value_i, value_kind = idx, kind
            break
    rows = []
    for record in table[1:]:
        if url_i is None or url_i >= len(record):
            continue
        url = record[url_i].strip()
        if not url:
            continue
        row = {"url": url}
        if target_i is not None and target_i < len(record):
            row["target"] = record[target_i].strip()
        if code_i is not None and code_i < len(record):
            row["code"] = record[code_i].strip()
        if title_i is not None and title_i < len(record):
            row["title"] = record[title_i].strip()
        if value_i is not None and value_i < len(record):
            row["value"] = to_number(record[value_i])
            row["value_kind"] = value_kind
        for extra in ("method", "confidence", "decision", "note"):
            idx = find({extra})
            if idx is not None and idx < len(record):
                row[extra] = record[idx].strip()
        rows.append(row)
    return rows


LOC_RE = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>", re.I)


def read_rows(path):
    text = read_text(path)
    stripped = text.lstrip()
    if stripped.startswith("<") or "<urlset" in text[:2000] or "<sitemapindex" in text[:2000]:
        locs = [unescape_xml(m) for m in LOC_RE.findall(text)]
        if "<sitemapindex" in text[:4000]:
            fail("%s is a sitemap index listing %d child sitemaps. Save each child "
                 "sitemap and pass them all: %s" % (path, len(locs), ", ".join(locs[:3])))
        return [{"url": u} for u in locs]
    if "{" in text[:4000] or text.lstrip()[:1] == "[":
        data = load_json(text)
        if data is not None:
            return rows_from_json(data)
    return rows_from_csv(text)


def unescape_xml(text):
    return (text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
            .replace("&quot;", '"').replace("&apos;", "'"))


def looks_like_url(text):
    text = (text or "").strip()
    return text.startswith("/") or text.startswith("http://") or text.startswith("https://")


def read_many(paths, label):
    rows = []
    for path in paths or []:
        got = read_rows(path)
        if not got:
            warn("no URL found in %s (%s)" % (path, label))
        rows.extend(got)
    return rows


# --------------------------------------------------------------------------
# URLs
# --------------------------------------------------------------------------

def split(url):
    """Return (host, path, query) with the path decoded and never empty."""
    url = (url or "").strip()
    if url.startswith("//"):
        url = "http:" + url
    if not re.match(r"^[a-z][a-z0-9+.-]*://", url, re.I):
        parts = urlsplit("http://placeholder" + (url if url.startswith("/") else "/" + url))
        host = ""
    else:
        parts = urlsplit(url)
        host = (parts.hostname or "").lower()
    path = unquote(parts.path or "/")
    path = re.sub(r"/{2,}", "/", path) or "/"
    return host, path, parts.query


def key(path):
    """Comparison key: lower case, no trailing slash, root kept as '/'."""
    path = path.lower()
    if len(path) > 1:
        path = path.rstrip("/")
    return path or "/"


def segments(path):
    return [s for s in key(path).split("/") if s]


def last_slug(path):
    segs = segments(path)
    if not segs:
        return ""
    slug = EXTENSION.sub("", segs[-1])
    return slug


def tokens(slug):
    return [t for t in re.split(r"[-_.]+", slug.lower()) if t and not t.isdigit()]


def fold_title(title):
    return fold(re.sub(r"\s[|\-:]\s.*$", "", title or ""))


class Inventory:
    """The new site: every live URL, indexed several ways."""

    def __init__(self, rows):
        self.by_key = OrderedDict()
        self.by_slug = defaultdict(list)
        self.by_token = defaultdict(set)
        self.by_title = {}
        self.hosts = Counter()
        for row in rows:
            host, path, _ = split(row["url"])
            k = key(path)
            if k in self.by_key:
                continue
            self.by_key[k] = path
            self.hosts[host] += 1
            slug = last_slug(path)
            if slug:
                self.by_slug[slug].append(k)
                for t in tokens(slug):
                    self.by_token[t].add(slug)
            if row.get("title"):
                self.by_title.setdefault(fold_title(row["title"]), k)

    def __contains__(self, path):
        return key(path) in self.by_key

    def canonical(self, path):
        return self.by_key.get(key(path))

    def candidates(self, slug, n=3):
        """New pages sharing a word with an unmatched slug, for a person to pick."""
        shared = Counter()
        limit = max(3, 0.2 * len(self.by_slug))
        for t in tokens(slug):
            if len(t) < 3 or len(self.by_token.get(t, ())) > limit:
                continue
            for candidate in self.by_token.get(t, ()):
                shared[candidate] += 1
        out = []
        for candidate, _ in shared.most_common(n):
            out.extend(self.by_key[k] for k in self.by_slug[candidate][:1])
        return out[:n]

    def close_slug(self, slug):
        wanted = tokens(slug)
        if not wanted:
            return None
        shared = Counter()
        for t in wanted:
            for candidate in self.by_token.get(t, ()):
                shared[candidate] += 1
        pool = [s for s, n in shared.most_common(60) if n >= max(1, len(wanted) // 2)]
        best = difflib.get_close_matches(slug, pool, n=1, cutoff=0.82)
        return best[0] if best else None


# --------------------------------------------------------------------------
# transformations and learned patterns
# --------------------------------------------------------------------------

def transforms(path):
    """Candidate new paths for an old one, cheapest assumption first."""
    out = []
    base = path
    for name, new in (
        ("date prefix dropped", DATE_PREFIX.sub("/", base)),
        ("extension dropped", EXTENSION.sub("", base.rstrip("/"))),
        ("index file dropped", re.sub(r"/index\.(?:html?|php)$", "/", base, flags=re.I)),
        ("language prefix dropped", LANG_PREFIX.sub("", base) or "/"),
        ("category base dropped", re.sub(r"^/(?:category|categorie|tag|etiquette)/", "/", base, flags=re.I)),
        ("underscores to hyphens", base.replace("_", "-")),
        ("numeric id dropped", ID_PREFIX.sub("/", base)),
    ):
        if new and new != base:
            if key(new) == "/" and name != "language prefix dropped":
                continue
            out.append((name, new))
    # two assumptions together, the classic WordPress restructure
    combo = EXTENSION.sub("", DATE_PREFIX.sub("/", base).rstrip("/"))
    if combo != base:
        out.append(("date prefix and extension dropped", combo))
    return out


def learn_prefix_swaps(old_paths, inventory, min_support=3, min_share=0.6):
    """Learn '/a/rest' -> '/b/rest' moves from the two inventories.

    A swap is kept only when enough old URLs agree on it and when it explains
    most of the old URLs under that prefix, so one coincidence never becomes
    a rule that sends a whole section to the wrong place.
    """
    by_rest = defaultdict(set)
    for k in inventory.by_key:
        segs = [s for s in k.split("/") if s]
        if len(segs) >= 2:
            by_rest["/".join(segs[1:])].add(segs[0])
        if segs:
            by_rest.setdefault("/".join(segs), set())
    support = Counter()
    first_count = Counter()
    for path in old_paths:
        if path in inventory:
            continue
        segs = segments(path)
        if not segs:
            continue
        first_count[segs[0] if len(segs) >= 2 else ""] += 1
        if len(segs) >= 2:
            rest = "/".join(segs[1:])
            for new_first in by_rest.get(rest, ()):
                if new_first != segs[0]:
                    support[(segs[0], new_first)] += 1
            if key("/" + rest) in inventory.by_key:
                support[(segs[0], "")] += 1
        else:
            for new_first in by_rest.get(segs[0], ()):
                support[("", new_first)] += 1
    swaps = []
    for (a, b), n in support.most_common():
        total = first_count.get(a, 0)
        if n >= min_support and total and n / total >= min_share:
            if any(s[0] == a for s in swaps):
                continue
            swaps.append((a, b, n))
    return swaps


def apply_swap(path, swap):
    a, b, _ = swap
    segs = segments(path)
    if a:
        if not segs or segs[0] != a or len(segs) < 2:
            return None
        rest = segs[1:]
    else:
        if len(segs) != 1:
            return None
        rest = segs
    new = "/" + "/".join(([b] if b else []) + rest)
    return new


def swap_label(swap):
    a, b, n = swap
    return "/%s/* -> /%s/*" % (a, b) if a and b else (
        "/%s/* -> /*" % a if a else "/* -> /%s/*" % b)


def swap_regex(swap):
    a, b, _ = swap
    if a and b:
        return "^/%s/(.+)$" % re.escape(a), "/%s/$1" % b
    if a:
        return "^/%s/(.+)$" % re.escape(a), "/$1"
    return None


def read_rules(path):
    """User supplied rules, one per line: regex => replacement."""
    rules = []
    if not path:
        return rules
    for number, line in enumerate(read_text(path).splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=>" not in line:
            fail("%s line %d: expected 'regex => replacement'" % (path, number))
        pattern, _, replacement = line.partition("=>")
        try:
            compiled = re.compile(pattern.strip(), re.I)
        except re.error as error:
            fail("%s line %d: bad regex (%s)" % (path, number, error))
        rules.append((compiled, replacement.strip().replace("$", "\\")))
    return rules


# --------------------------------------------------------------------------
# matching
# --------------------------------------------------------------------------

def match(path, inventory, swaps, rules, title=""):
    """Return (new_path, method, note) or (None, None, note)."""
    if path in inventory:
        exact = inventory.canonical(path)
        return exact, ("exact" if exact == path or exact.rstrip("/") == path.rstrip("/") else "case"), ""
    for compiled, replacement in rules:
        if compiled.search(path):
            new = compiled.sub(replacement, path)
            if new in inventory:
                return inventory.canonical(new), "rule", compiled.pattern
    for swap in swaps:
        new = apply_swap(path, swap)
        if new and new in inventory:
            return inventory.canonical(new), "pattern", swap_label(swap)
    for name, new in transforms(path):
        if new in inventory:
            return inventory.canonical(new), "pattern", name
        for swap in swaps:
            swapped = apply_swap(new, swap)
            if swapped and swapped in inventory:
                return inventory.canonical(swapped), "pattern", "%s, then %s" % (name, swap_label(swap))
    slug = last_slug(path)
    if slug and len(slug) > 2:
        hits = inventory.by_slug.get(slug, [])
        if len(hits) == 1:
            return inventory.by_key[hits[0]], "slug", ""
        if len(hits) > 1:
            old_segs = set(segments(path))
            best = max(hits, key=lambda k: len(old_segs & set(k.split("/"))))
            return inventory.by_key[best], "slug-ambiguous", "%d pages share this slug" % len(hits)
    if title:
        found = inventory.by_title.get(fold_title(title))
        if found:
            return inventory.by_key[found], "title", ""
    if slug and len(tokens(slug)) >= 2:
        close = inventory.close_slug(slug)
        if close and len(inventory.by_slug[close]) == 1:
            return inventory.by_key[inventory.by_slug[close][0]], "slug-close", "slug %s" % close
    segs = segments(path)
    for depth in range(len(segs) - 1, 0, -1):
        parent = "/" + "/".join(segs[:depth])
        for candidate in [parent] + [apply_swap(parent + "/x", s) for s in swaps]:
            if candidate and candidate.endswith("/x"):
                candidate = candidate[:-2]
            if candidate and candidate in inventory and key(candidate) != "/":
                return inventory.canonical(candidate), "parent", "nearest surviving section"
    return None, None, ""


def decide(method, value, is_same):
    if method is None:
        return "manual" if value > 0 else "gone"
    if method in ("exact", "case") and is_same:
        return "keep"
    if CONFIDENCE.get(method, 0) >= 0.6 and method != "slug-ambiguous":
        return "redirect"
    return "review"


def cmd_build(args):
    old_rows = read_many(args.old, "old inventory")
    new_rows = read_many(args.new, "new inventory")
    if not old_rows:
        fail("the old inventory is empty. Pass the old sitemap, a Search Console "
             "Pages export or a crawl with --old")
    if not new_rows:
        fail("the new inventory is empty. Pass the new sitemap or a crawl of the "
             "staging site with --new")
    inventory = Inventory(new_rows)
    new_host = ""
    if args.new_host:
        h = urlsplit(args.new_host if "://" in args.new_host else "https://" + args.new_host)
        new_host = "%s://%s" % (h.scheme or "https", h.hostname or "")
    elif inventory.hosts:
        top = inventory.hosts.most_common(1)[0][0]
        new_host = "https://" + top if top else ""

    merged = OrderedDict()
    for row in old_rows:
        host, path, query = split(row["url"])
        if ASSET_EXT.search(path):
            continue
        k = (key(path), query)
        entry = merged.setdefault(k, {"path": path, "query": query, "host": host,
                                      "value": 0.0, "title": row.get("title", "")})
        entry["value"] += row.get("value", 0.0) or 0.0
    old_hosts = Counter(e["host"] for e in merged.values())
    old_host = old_hosts.most_common(1)[0][0] if old_hosts else ""
    same_host = (not old_host) or old_host == urlsplit(new_host).hostname

    rules = read_rules(args.rules)
    swaps = learn_prefix_swaps([e["path"] for e in merged.values()], inventory,
                               min_support=args.min_support)
    out = []
    for entry in merged.values():
        path, query = entry["path"], entry["query"]
        note = ""
        if query and WP_QUERY.search(query):
            # ?p=123 names a post by its database id. Nothing in a URL list
            # says which post that was, so a person has to look it up.
            note = "WordPress query URL (?%s): look up the post id in the old database" % query
            target, method, why = None, None, ""
        else:
            target, method, why = match(path, inventory, swaps, rules, entry["title"])
        decision = decide(method, entry["value"], same_host)
        if note and method is None:
            decision = "manual"
        if decision == "manual" and not note:
            hints = inventory.candidates(last_slug(path))
            if hints:
                note = "candidates: " + ", ".join(hints)
        if decision == "keep" and query:
            decision = "redirect"
        target_url = ""
        if target:
            target_url = target if same_host else new_host + target
        code = "410" if decision == "gone" else "301"
        if decision == "keep":
            code = ""
        out.append(OrderedDict([
            ("source", path + ("?" + query if query else "")),
            ("target", target_url),
            ("code", code),
            ("method", method or "none"),
            ("confidence", "%.2f" % CONFIDENCE.get(method, 0.0)),
            ("decision", decision),
            ("value", ("%g" % entry["value"]) if entry["value"] else "0"),
            ("note", "; ".join(x for x in (why, note) if x)),
        ]))
    order = {"manual": 0, "review": 1, "gone": 2, "redirect": 3, "keep": 4}
    out.sort(key=lambda r: (order[r["decision"]], -float(r["value"]), r["source"]))
    write_map(out, args.out)

    counts = Counter(r["decision"] for r in out)
    methods = Counter(r["method"] for r in out)
    summary = OrderedDict([
        ("old_urls", len(out)),
        ("new_urls", len(inventory.by_key)),
        ("old_host", old_host), ("new_host", urlsplit(new_host).hostname or ""),
        ("domain_change", not same_host),
        ("decisions", dict(counts)),
        ("methods", dict(methods)),
        ("host_rule_candidates", sum(1 for r in out if r["method"] in ("exact", "case") and r["decision"] == "redirect")),
        ("value_unresolved", sum(float(r["value"]) for r in out if r["decision"] in ("manual", "review"))),
        ("value_total", sum(float(r["value"]) for r in out)),
        ("learned_patterns", [OrderedDict([
            ("rule", swap_label(s)), ("support", s[2]),
            ("regex", (swap_regex(s) or ("", ""))[0]),
            ("replacement", (swap_regex(s) or ("", ""))[1]),
            ("exceptions", [e["path"] for e in merged.values()
                            if apply_swap(e["path"], s) and apply_swap(e["path"], s) not in inventory]),
        ]) for s in swaps]),
        ("map", args.out),
    ])
    if args.json:
        with open(args.json, "w", encoding="utf-8") as handle:
            json.dump(summary, handle, ensure_ascii=False, indent=2)
    if not args.quiet:
        print_build(summary)
    return 0


def write_map(rows, path):
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["source", "target", "code", "method", "confidence",
                         "decision", "value", "note"])
        for row in rows:
            writer.writerow([row.get(k, "") for k in ("source", "target", "code", "method",
                                                        "confidence", "decision", "value", "note")])


def print_build(s):
    d = s["decisions"]
    print("Old URLs %d, new URLs %d%s" % (
        s["old_urls"], s["new_urls"],
        ", domain change %s -> %s" % (s["old_host"], s["new_host"]) if s["domain_change"] else ""))
    print("  redirect %d   keep %d   review %d   manual %d   gone (410) %d" % (
        d.get("redirect", 0), d.get("keep", 0), d.get("review", 0),
        d.get("manual", 0), d.get("gone", 0)))
    print("  by method: " + ", ".join("%s %d" % kv for kv in sorted(s["methods"].items(), key=lambda kv: -kv[1])))
    if s["value_total"]:
        share = 100.0 * s["value_unresolved"] / s["value_total"]
        print("  value still undecided: %g of %g (%.1f %%). Decide those rows first."
              % (s["value_unresolved"], s["value_total"], share))
    if s["domain_change"] and s["host_rule_candidates"]:
        print("  %d URLs keep the same path on the new host: one server level host rule "
              "covers them, the lines are there for testing" % s["host_rule_candidates"])
    for p in s["learned_patterns"]:
        print("  learned pattern %s, supported by %d URLs%s" % (
            p["rule"], p["support"],
            ", %d exception(s): %s" % (len(p["exceptions"]), ", ".join(p["exceptions"][:3]))
            if p["exceptions"] else ""))
    print("Map written to %s" % s["map"])


# --------------------------------------------------------------------------
# lint
# --------------------------------------------------------------------------

def read_map(path):
    rows = read_rows(path)
    out = []
    for row in rows:
        source = row.get("url", "")
        target = row.get("target", "")
        code = str(row.get("code") or "").strip()
        decision = row.get("decision") or ("gone" if code in ("410", "451") else "redirect")
        out.append({"source": source, "target": target, "code": code or ("410" if not target else "301"),
                    "decision": decision, "value": float(row.get("value") or 0),
                    "method": row.get("method", ""), "note": row.get("note", "")})
    return out


def active_rows(rows):
    return [r for r in rows if r["decision"] not in ("keep",)]


def cmd_lint(args):
    rows = read_map(args.map)
    if not rows:
        fail("no row found in %s" % args.map)
    inventory = Inventory(read_many(args.new, "new inventory")) if args.new else None
    existing = read_many([args.existing], "existing rules") if args.existing else []

    issues = []

    def add(kind, severity, source, target, detail, value=0.0, final=""):
        issues.append(OrderedDict([("type", kind), ("severity", severity), ("source", source),
                                   ("target", target), ("detail", detail), ("value", value),
                                   ("final", final)]))

    live = active_rows(rows)
    site = (args.host or "").lower()
    site = urlsplit(site if "://" in site else "https://" + site).hostname if site else ""

    def node(url):
        """A redirect graph node. Relative URLs live on the site being moved;
        an absolute URL on another host (the new domain) can never chain back
        into this map, so it gets its own namespace."""
        host, path, _ = split(url)
        if host and host != site:
            return host + key(path)
        return key(path)

    graph = {}
    seen = {}
    source_hosts = {split(r["source"])[0] for r in live if r["source"]}
    target_hosts = Counter(split(r["target"])[0] for r in live if r["target"].startswith("http"))
    host_warning = ""
    if not site and source_hosts <= {""} and target_hosts:
        top = target_hosts.most_common(1)[0][0]
        host_warning = ("targets are absolute on %s and --host was not given: if %s is the site being "
                        "moved, pass --host %s so chains and loops through it are followed" % (top, top, top))
    for r in live:
        _, spath, squery = split(r["source"])
        skey = key(spath) + ("?" + squery if squery else "")
        if skey in seen and seen[skey] != r["target"]:
            add("duplicate_source", "high", r["source"], r["target"],
                "also sent to %s" % seen[skey], r["value"])
        seen[skey] = r["target"]
        if r["target"]:
            graph[node(r["source"])] = r["target"]
        if r["decision"] in ("manual", "review"):
            add("undecided", "high" if r["decision"] == "manual" and r["value"] > 0 else "medium",
                r["source"], r["target"],
                "decision %s, method %s" % (r["decision"], r["method"] or "none"), r["value"])
        if r["code"] in ("302", "303", "307"):
            add("temporary_code", "medium", r["source"], r["target"],
                "%s tells Google the move is temporary, use 301 or 308" % r["code"], r["value"])
        if squery:
            add("query_source", "low", r["source"], r["target"],
                "most redirect tools ignore or strip the query string, test this one by hand", r["value"])

    for existing_rule in existing:
        if existing_rule.get("is_regex") or not existing_rule.get("target"):
            continue
        graph.setdefault(node(existing_rule["url"]), existing_rule["target"])

    fixed = {}
    for r in live:
        if not r["target"]:
            continue
        start = node(r["source"])
        path_seen = [start]
        current = r["target"]
        hops = 0
        loop = False
        while True:
            tkey = node(current)
            if tkey in path_seen:
                loop = True
                break
            if tkey not in graph:
                break
            path_seen.append(tkey)
            current = graph[tkey]
            hops += 1
            if hops > 10:
                loop = True
                break
        if loop:
            add("loop", "high", r["source"], r["target"], "the redirects come back to a URL already visited", r["value"])
        elif hops:
            add("chain", "medium" if hops == 1 else "high", r["source"], r["target"],
                "%d extra hop(s), point it straight at %s" % (hops, current), r["value"], current)
            fixed[r["source"]] = current

    if inventory is not None:
        for r in live:
            if not r["target"]:
                continue
            final = fixed.get(r["source"], r["target"])
            _, tpath, _ = split(final)
            if tpath not in inventory:
                add("target_missing", "high", r["source"], final,
                    "the target is not in the new inventory, so it may answer 404", r["value"])

    targets = Counter()
    for r in live:
        if r["target"]:
            _, tpath, _ = split(fixed.get(r["source"], r["target"]))
            targets[key(tpath)] += 1
    n_redirects = sum(targets.values()) or 1
    home = sum(1 for r in live if r["target"]
               and key(split(fixed.get(r["source"], r["target"]))[1]) == "/"
               and key(split(r["source"])[1]) != "/"
               and not LANG_PREFIX.fullmatch(key(split(r["source"])[1])))
    if home:
        add("home_target", "high" if home >= 10 or home / n_redirects > 0.05 else "medium",
            "%d URLs" % home, "/",
            "Google may treat mass redirects to the home page as soft 404s. Pick a close page or answer 410")
    for tkey, n in targets.most_common(5):
        if tkey != "/" and (n >= 20 or (n >= 10 and n / n_redirects > 0.1)):
            add("concentration", "medium", "%d URLs" % n, tkey,
                "many URLs piled onto one page read as a soft 404 when the page is not a real replacement")

    for existing_rule in existing:
        if existing_rule.get("is_regex") or existing_rule.get("enabled") is False:
            continue
        target = existing_rule.get("target") or ""
        if not target:
            continue
        _, tpath, _ = split(target)
        if node(target) in graph and node(target) in {node(r["source"]) for r in live}:
            final = graph[node(target)]
            add("existing_chain", "high", existing_rule["url"], target,
                "an existing rule now lands on a URL the migration redirects. Rewrite it to %s" % final,
                existing_rule.get("value", 0.0), final)
        elif inventory is not None and tpath not in inventory and node(target) not in graph:
            add("existing_dead_target", "medium", existing_rule["url"], target,
                "an existing rule points at a URL absent from the new site. Correct the target, keep the rule",
                existing_rule.get("value", 0.0))

    severity_rank = {"high": 0, "medium": 1, "low": 2}
    issues.sort(key=lambda i: (severity_rank[i["severity"]], -float(i["value"] or 0)))
    by_type = Counter(i["type"] for i in issues)
    result = OrderedDict([
        ("map", args.map),
        ("rows", len(rows)),
        ("redirects", sum(1 for r in live if r["target"])),
        ("gone", sum(1 for r in live if r["code"] in ("410", "451"))),
        ("issues_by_type", dict(by_type)),
        ("issues_by_severity", dict(Counter(i["severity"] for i in issues))),
        ("value_at_risk", sum(float(i["value"] or 0) for i in issues if i["severity"] == "high")),
        ("inventory_checked", inventory is not None),
        ("warning", host_warning),
        ("existing_rules_checked", len(existing)),
        ("issues", issues),
    ])
    if args.json:
        with open(args.json, "w", encoding="utf-8") as handle:
            json.dump(result, handle, ensure_ascii=False, indent=2)
    if args.fix:
        fixed_rows = []
        for r in rows:
            copy = dict(r)
            if r["source"] in fixed:
                copy["target"] = fixed[r["source"]]
                copy["note"] = (r.get("note", "") + "; chain collapsed").strip("; ")
            _, spath, _ = split(copy["source"])
            _, tpath, _ = split(copy["target"]) if copy["target"] else ("", "", "")
            if copy["target"] and key(spath) == key(tpath) and not split(copy["target"])[0]:
                continue
            fixed_rows.append(copy)
        write_map([{k: ("%g" % v if k == "value" else v) for k, v in r.items()} for r in fixed_rows],
                  args.fix)
    if not args.quiet:
        print("%d rows, %d redirects, %d answered 410" % (result["rows"], result["redirects"], result["gone"]))
        if not issues:
            print("No issue found.")
        for kind, n in by_type.most_common():
            print("  %-22s %d" % (kind, n))
        if not result["inventory_checked"]:
            print("  (targets not checked against the new site: pass --new)")
        if host_warning:
            print("  note: " + host_warning)
        if args.fix:
            print("Corrected map written to %s" % args.fix)
    return 1 if result["issues_by_severity"].get("high") and args.strict else 0


# --------------------------------------------------------------------------
# hunt
# --------------------------------------------------------------------------

LOG_RE = re.compile(r'"(?:GET|HEAD|POST) (\S+) HTTP/[\d.]+" (\d{3})')


def read_404s(path):
    text = read_text(path)
    head = text[:3000]
    if LOG_RE.search(head):
        counts = Counter()
        for line in text.splitlines():
            m = LOG_RE.search(line)
            if m and m.group(2) == "404":
                counts[m.group(1)] += 1
        return [{"url": u, "value": float(n)} for u, n in counts.items()]
    return read_rows(path)


def classify_404(path):
    lower = path.lower()
    for probe in PROBES:
        if lower == probe or lower.startswith(probe.rstrip("/") + "/") or lower.startswith(probe + "."):
            return "probe"
    if PROBE_EXT.search(lower) and not lower.startswith("/wp-content/uploads/"):
        return "suspicious"
    segs = segments(path)
    if len(segs) >= 2 and segs[0] == segs[1]:
        return "doubled_segment"
    if ASSET_EXT.search(lower):
        return "asset"
    return "page"


def cmd_hunt(args):
    rows = read_404s(args.source)
    if not rows:
        fail("no 404 URL found in %s" % args.source)
    mapped = {}
    if args.map:
        for r in read_map(args.map):
            _, p, _ = split(r["source"])
            mapped[key(p)] = r
    inventory = Inventory(read_many(args.new, "new inventory")) if args.new else None
    swaps = learn_prefix_swaps([split(r["url"])[1] for r in rows], inventory) if inventory else []

    merged = OrderedDict()
    for r in rows:
        _, path, _ = split(r["url"])
        entry = merged.setdefault(key(path), {"path": path, "hits": 0.0})
        entry["hits"] += r.get("value", 0.0) or 0.0

    out = []
    for entry in merged.values():
        path = entry["path"]
        kind = classify_404(path)
        suggestion, method = "", ""
        status = kind
        if kind == "suspicious":
            # An old static site had real .php or .asp pages. Keep the URL only
            # if the new site has a counterpart, otherwise it is a scanner.
            kind = status = "probe"
            if key(path) in mapped:
                kind = "page"
            elif inventory is not None:
                target, method, _ = match(path, inventory, swaps, [])
                if target and method not in ("parent", "slug-close", "slug-ambiguous"):
                    kind = "page"
        if kind == "page":
            if key(path) in mapped:
                status = "covered_but_404"
                suggestion = mapped[key(path)]["target"]
                method = "map"
            elif inventory is not None:
                target, method, _ = match(path, inventory, swaps, [])
                if target and CONFIDENCE.get(method, 0) >= 0.6:
                    status, suggestion = "suggested", target
                elif target:
                    status, suggestion = "review", target
                else:
                    status = "no_match"
            else:
                status = "unmatched"
        elif kind == "doubled_segment":
            fixed = "/" + "/".join(segments(path)[1:])
            if inventory is not None and fixed in inventory:
                suggestion = inventory.canonical(fixed)
        out.append(OrderedDict([("url", path), ("hits", entry["hits"]), ("status", status),
                                ("suggested_target", suggestion), ("method", method or "")]))
    out.sort(key=lambda r: -r["hits"])
    by_status = Counter()
    hits_by_status = Counter()
    for r in out:
        by_status[r["status"]] += 1
        hits_by_status[r["status"]] += r["hits"]
    doubled = Counter(segments(r["url"])[0] for r in out if r["status"] == "doubled_segment")
    result = OrderedDict([
        ("source", args.source),
        ("urls", len(out)),
        ("hits", sum(r["hits"] for r in out)),
        ("by_status", dict(by_status)),
        ("hits_by_status", {k: v for k, v in hits_by_status.items()}),
        ("doubled_prefixes", dict(doubled)),
        ("rows", out[: args.top]),
    ])
    if args.json:
        with open(args.json, "w", encoding="utf-8") as handle:
            json.dump(result, handle, ensure_ascii=False, indent=2)
    if args.out_map:
        proposals = []
        for r in out:
            if r["status"] in ("suggested", "review") and r["suggested_target"]:
                proposals.append({"source": r["url"], "target": r["suggested_target"], "code": "301",
                                  "method": r["method"], "confidence": "%.2f" % CONFIDENCE.get(r["method"], 0),
                                  "decision": "redirect" if r["status"] == "suggested" else "review",
                                  "value": "%g" % r["hits"], "note": "from the 404 log"})
        write_map(proposals, args.out_map)
    if not args.quiet:
        print("%d URLs in 404, %g hits" % (result["urls"], result["hits"]))
        labels = OrderedDict([
            ("covered_but_404", "in the map but still 404: the rule is not active"),
            ("suggested", "a target was found, review then add"),
            ("review", "only a parent section matched, decide by hand"),
            ("no_match", "no counterpart on the new site: 410 or leave"),
            ("unmatched", "not checked, pass --new"),
            ("doubled_segment", "doubled prefix: a broken internal link, fix the link"),
            ("asset", "media or file: check the uploads were moved"),
            ("probe", "scanner probing, never redirect"),
        ])
        for status, label in labels.items():
            if by_status.get(status):
                print("  %-16s %4d URLs %8g hits  %s" % (status, by_status[status], hits_by_status[status], label))
        for prefix, n in doubled.items():
            print("  /%s/%s/ appears %d times: look for a relative link or a language switcher" % (prefix, prefix, n))
    return 0


# --------------------------------------------------------------------------
# export
# --------------------------------------------------------------------------

FORMATS = ("redirection", "yoast", "rankmath", "seopress", "generic", "htaccess", "nginx")


def export_rows(rows):
    for r in rows:
        if r["decision"] in ("keep", "manual"):
            continue
        if r["decision"] == "review" and not r["target"]:
            continue
        yield r


def rel(url):
    host, path, query = split(url)
    return path + ("?" + query if query else ""), host


def cmd_export(args):
    rows = read_map(args.map)
    skipped = Counter(r["decision"] for r in rows if r["decision"] in ("manual", "review", "keep"))
    patterns = []
    if args.patterns:
        data = load_json(read_text(args.patterns)) or {}
        patterns = [(p["regex"], p["replacement"]) for p in data.get("learned_patterns", []) if p.get("regex")]
        for p in data.get("learned_patterns", []):
            if p.get("regex") and p.get("exceptions"):
                print("Pattern %s would send %d URL(s) to a page that does not exist (%s). "
                      "Decide them in the map: an explicit row must win over the pattern, "
                      "so check your tool evaluates plain rules before regex ones."
                      % (p["rule"], len(p["exceptions"]), ", ".join(p["exceptions"][:3])),
                      file=sys.stderr)
    rows = [r for r in export_rows(rows) if r["decision"] != "review" or args.include_review]
    fmt = args.format
    hosts = Counter(split(r["target"])[0] for r in rows if r["target"].startswith("http"))
    if patterns and hosts:
        # a domain change: pattern targets must land on the new host too
        top = hosts.most_common(1)[0][0]
        scheme = "https" if any(r["target"].startswith("https://" + top) for r in rows) else "http"
        patterns = [(rx, "%s://%s%s" % (scheme, top, rep) if rep.startswith("/") else rep)
                    for rx, rep in patterns]
    if fmt in ("rankmath", "seopress"):
        home = [r for r in rows if key(split(r["source"])[1]) == "/"]
        if home:
            rows = [r for r in rows if r not in home]
            print("The home page row is not written for %s: an empty source would match "
                  "everything. Redirect the old home with a host level rule." % fmt, file=sys.stderr)
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    count = 0
    if fmt == "redirection":
        writer.writerow(["source", "target", "regex", "code", "type"])
        for r in rows:
            src, _ = rel(r["source"])
            gone = r["code"] in ("410", "451")
            writer.writerow([src, "" if gone else r["target"], 0, r["code"], "error" if gone else "url"])
            count += 1
        for regex, replacement in patterns:
            writer.writerow([regex, replacement, 1, 301, "url"])
            count += 1
    elif fmt == "yoast":
        writer.writerow(["Origin", "Target", "Type", "Format"])
        for r in rows:
            src, _ = rel(r["source"])
            gone = r["code"] in ("410", "451")
            writer.writerow([src, "" if gone else r["target"], r["code"], "plain"])
            count += 1
        for regex, replacement in patterns:
            writer.writerow([regex, replacement, 301, "regex"])
            count += 1
    elif fmt == "rankmath":
        writer.writerow(["id", "source", "matching", "destination", "type", "category", "status", "ignore"])
        for r in rows:
            src, _ = rel(r["source"])
            writer.writerow(["", src.strip("/"), "exact", r["target"], r["code"], "", "active", ""])
            count += 1
    elif fmt == "seopress":
        if not args.host:
            fail("seopress needs absolute targets: pass --host https://www.example.com")
        for r in rows:
            src, _ = rel(r["source"])
            target = r["target"]
            if target.startswith("/"):
                target = args.host.rstrip("/") + target
            gone = r["code"] in ("410", "451")
            writer.writerow([src.lstrip("/"), "" if gone else target, r["code"], "yes",
                             "exact_match", "", "", "", "both"])
            count += 1
    elif fmt == "generic":
        writer.writerow(["source", "target", "code"])
        for r in rows:
            src, _ = rel(r["source"])
            writer.writerow([src, r["target"], r["code"]])
            count += 1
    elif fmt == "htaccess":
        lines = ["# Redirects generated by redirect_map.py. Place ABOVE the # BEGIN WordPress block.",
                 "<IfModule mod_alias.c>"]
        for r in rows:
            src, _ = rel(r["source"])
            if "?" in src:
                lines.append("# needs mod_rewrite with a QUERY_STRING condition, skipped: %s" % src)
                continue
            anchored = "^" + re.escape(src.rstrip("/") or "/") + ("/?$" if src != "/" else "$")
            if r["code"] in ("410", "451"):
                lines.append("RedirectMatch 410 %s" % anchored)
            else:
                lines.append("RedirectMatch %s %s %s" % (r["code"], anchored, r["target"]))
            count += 1
        for regex, replacement in patterns:
            lines.append("RedirectMatch 301 %s %s" % (regex, replacement))
            count += 1
        lines.append("</IfModule>")
        buf.write("\n".join(lines) + "\n")
    elif fmt == "nginx":
        lines = ["# map file generated by redirect_map.py",
                 "# In http {}:   map $uri $hts_redirect { include /etc/nginx/redirects.map; }",
                 "# In server {}: if ($hts_redirect) { return 301 $hts_redirect; }",
                 "# Raise map_hash_max_size first, then map_hash_bucket_size, if nginx asks.",
                 "# 410 rows are listed separately below: map them to a location returning 410."]
        gone = []
        for r in rows:
            src, _ = rel(r["source"])
            if "?" in src:
                lines.append("# query string source, handle with $request_uri: %s" % src)
                continue
            if r["code"] in ("410", "451"):
                gone.append(src)
                continue
            base = src.rstrip("/") or "/"
            lines.append("%s %s;" % (nginx_quote(base), nginx_quote(r["target"])))
            if base != "/":
                lines.append("%s %s;" % (nginx_quote(base + "/"), nginx_quote(r["target"])))
            count += 1
        for regex, replacement in patterns:
            lines.append("~%s %s;" % (nginx_quote(regex), nginx_quote(replacement)))
            count += 1
        if gone:
            lines.append("")
            lines.append("# 410 candidates (location = /path { return 410; }):")
            lines.extend("#   %s" % g for g in gone)
        buf.write("\n".join(lines) + "\n")
    with open(args.out, "w", encoding="utf-8", newline="") as handle:
        handle.write(buf.getvalue())
    if not args.quiet:
        print("%d rules written to %s (%s)" % (count, args.out, fmt))
        if skipped:
            print("Not exported: " + ", ".join("%s %d" % kv for kv in skipped.items())
                  + ". Rows marked manual or review wait for a person.")
        if fmt in ("rankmath", "seopress") and patterns:
            print("Pattern rules are not written for %s: its regex syntax is not documented "
                  "publicly. Add them by hand from the build summary." % fmt)
    return 0


def nginx_quote(text):
    if re.search(r"[\s;{}'\"]", text):
        return '"%s"' % text.replace('"', '\\"')
    return text


# --------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="redirect_map.py",
        description="Build, check and export the redirect map of a WordPress migration.")
    sub = parser.add_subparsers(dest="command")

    b = sub.add_parser("build", help="match old URLs to new ones")
    b.add_argument("--old", nargs="+", required=True, help="old inventory files")
    b.add_argument("--new", nargs="+", required=True, help="new inventory files")
    b.add_argument("--existing", help="unused by build, accepted for symmetry")
    b.add_argument("--new-host", help="scheme and host of the new site, for a domain change")
    b.add_argument("--rules", help="your own rules, one 'regex => replacement' per line")
    b.add_argument("--min-support", type=int, default=3, help="URLs needed to learn a pattern (default 3)")
    b.add_argument("--out", default="redirect-map.csv")
    b.add_argument("--json", help="write the summary as JSON")
    b.add_argument("--quiet", action="store_true")

    l = sub.add_parser("lint", help="check a map before it goes live")
    l.add_argument("map")
    l.add_argument("--new", nargs="+", help="new inventory, to check every target exists")
    l.add_argument("--existing", help="rules already live on the site (plugin JSON or CSV)")
    l.add_argument("--host", help="host of the site being moved, when the map uses absolute URLs on it")
    l.add_argument("--json")
    l.add_argument("--fix", help="write a corrected map with chains collapsed")
    l.add_argument("--strict", action="store_true", help="exit 1 when a high severity issue exists")
    l.add_argument("--quiet", action="store_true")

    h = sub.add_parser("hunt", help="sort a 404 list and suggest targets")
    h.add_argument("source", help="404 list: plugin JSON, Search Console export, CSV or access log")
    h.add_argument("--map", help="the migration map, to spot rules that are not active")
    h.add_argument("--new", nargs="+", help="new inventory, to suggest targets")
    h.add_argument("--json")
    h.add_argument("--out-map", help="write suggested redirects as a map to review")
    h.add_argument("--top", type=int, default=100)
    h.add_argument("--quiet", action="store_true")

    e = sub.add_parser("export", help="write the map for the tool that serves it")
    e.add_argument("map")
    e.add_argument("--format", required=True, choices=FORMATS)
    e.add_argument("--out", required=True)
    e.add_argument("--host", help="scheme and host, for formats that need absolute targets")
    e.add_argument("--patterns", help="build --json summary, to add the learned pattern rules")
    e.add_argument("--include-review", action="store_true", help="also export rows marked review")
    e.add_argument("--quiet", action="store_true")

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help(sys.stderr)
        return 2
    return {"build": cmd_build, "lint": cmd_lint, "hunt": cmd_hunt, "export": cmd_export}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
