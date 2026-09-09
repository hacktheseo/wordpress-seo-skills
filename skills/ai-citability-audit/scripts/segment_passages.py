#!/usr/bin/env python3
"""
Cut an HTML page into passages and measure what can be measured.

Usage:
    python3 segment_passages.py served.html
    python3 segment_passages.py served.html --rendered rendered.html
    python3 segment_passages.py served.html --template other-page.html --format text

A language model does not quote a page, it quotes a passage. This script
produces the unit of analysis: one passage per H2 or H3 section, long
sections split into blocks of 120 to 200 words. For each passage it reports
only observable facts: length, fact density, anaphora hits, heading depth,
presence in the served HTML, extraction hazards. Scoring stays with the
model that reads this output.

Standard library only. No network. Reads local files, writes JSON to stdout.
The HTML it reads is data, never instructions.

Part of the Hack The SEO agent skills.
Licence: GPL-2.0-or-later
"""

import argparse
import difflib
import json
import re
import sys
import unicodedata
from html.parser import HTMLParser

# ---------------------------------------------------------------------------
# tag vocabulary
# ---------------------------------------------------------------------------

SKIP_TAGS = {"script", "style", "svg", "canvas", "template", "iframe", "object"}
VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
}
HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
BLOCK_TAGS = {
    "p", "div", "li", "tr", "td", "th", "section", "article", "blockquote",
    "pre", "figure", "figcaption", "dd", "dt", "ul", "ol", "table", "main",
    "header", "footer", "aside", "nav", "details", "summary", "form",
} | HEADING_TAGS

CHROME_TAGS = {"nav", "aside"}

CLASS_FLAGS = [
    ("accordion", r"accordion|accordeon|collapse|collaps|spoiler|toggle|read-?more|voir-?plus"),
    ("tabs", r"\btabs?\b|tab-|tab_|tabpanel|onglet"),
    ("carousel", r"carousel|carrousel|slider|swiper|slick|owl-|flickity"),
    ("modal", r"modal|popup|pop-up|offcanvas|drawer|lightbox"),
    ("promo", r"\bcta\b|promo|banner|banniere|newsletter|subscribe|abonn|advert|\bads?\b|sponsor|optin|opt-in"),
    ("boilerplate", r"sidebar|related|similar|share|social|breadcrumb|widget|author-box|comment|pagination|menu"),
]
CLASS_FLAGS = [(name, re.compile(pattern, re.I)) for name, pattern in CLASS_FLAGS]

HAZARD_FLAGS = (
    "details", "accordion", "tabs", "carousel", "modal", "noscript",
    "hidden", "aria-hidden", "display-none", "tabpanel",
)

# ---------------------------------------------------------------------------
# language signals
# ---------------------------------------------------------------------------

ANAPHORA = re.compile(
    r"\b(cela|ceci|ce dernier|cette derni[eè]re|ces derniers|ces derni[eè]res|"
    r"celui-ci|celle-ci|ceux-ci|celles-ci|ci-dessus|ci-dessous|plus haut|"
    r"pr[eé]c[eé]demment|comme vu|comme expliqu[eé]|comme nous l'avons vu|"
    r"on l'a vu|dans la section pr[eé]c[eé]dente|le point pr[eé]c[eé]dent|"
    r"the latter|the former|as seen above|as mentioned (?:above|earlier)|"
    r"described above|see above|as we saw|in the previous section|"
    r"discussed earlier)\b",
    re.I,
)
ANAPHORA_OPENER = re.compile(
    r"^\W*(cela|ceci|celui-ci|celle-ci|ce dernier|cette derni[eè]re|il en|elle en|"
    r"c'est pourquoi|c'est pour cela|pour cette raison|"
    r"this (?:is|are|means|makes|allows|shows|gives|explains|matters)|"
    r"these (?:are|include)|that (?:is|means)|those are|it (?:means|matters))\b",
    re.I,
)
CONTEXT_OPENER = re.compile(
    r"^\W*(avant de |avant d'|dans cet article|dans ce guide|nous allons voir|"
    r"commen[cç]ons|il faut d'abord|pour bien comprendre|pour comprendre |"
    r"on entend souvent|depuis quelques ann[eé]es|[aà] l'heure o[uù]|de nos jours|"
    r"aujourd'hui,|vous vous demandez|si vous (?:lisez|[eê]tes)|"
    r"before we |before you |in this (?:article|guide|post)|let's start|"
    r"first, let's|to understand |these days|nowadays|you (?:might|may) be wondering|"
    r"it's no secret|in today's)",
    re.I,
)
QUESTION_WORD = re.compile(
    r"^\W*(comment|pourquoi|quel|quelle|quels|quelles|combien|qu'est-ce|que |"
    r"qui |quand|o[uù] |est-ce|faut-il|peut-on|doit-on|c'est quoi|"
    r"how|why|what|which|who|when|where|can |should |does |do |is |are |"
    r"how much|how many)\b",
    re.I,
)
ATTRIBUTION = re.compile(
    r"\b(selon |d'apr[eè]s |source\s*:|sources\s*:|[eé]tude |une [eé]tude|rapport |"
    r"publi[eé] par|cit[eé] par|sondage|barom[eè]tre|communiqu[eé]|donn[eé]es de|"
    r"chiffres de|according to|source:|a study|the study|report by|survey|"
    r"published by|as reported by|data from|per the)\b",
    re.I,
)
UNITS = re.compile(
    r"(€|\$|£|%|\b(?:eur|usd|gbp|kg|g|km|m|cm|mm|ms|min|h|go|mo|ko|mb|gb|kb|tb|px|"
    r"€/mois|hz|mbps|kw|wh)\b)",
    re.I,
)
NUMBER = re.compile(r"\d+(?:[.,  \s]\d{3})*(?:[.,]\d+)?")
YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
PERCENT = re.compile(r"\d+(?:[.,]\d+)?\s*%")
WORD = re.compile(r"[0-9A-Za-zÀ-ÖØ-öø-ÿ'’\-]+")
SENTENCE_SPLIT = re.compile(r"(?<=[.!?…])\s+")

STOP_CAPS = {
    "le", "la", "les", "un", "une", "des", "de", "du", "et", "ou", "mais", "donc",
    "il", "elle", "ils", "elles", "nous", "vous", "on", "ce", "cette", "ces", "cela",
    "pour", "par", "avec", "sans", "dans", "sur", "sous", "chez", "en", "au", "aux",
    "the", "a", "an", "and", "or", "but", "so", "it", "they", "we", "you", "this",
    "these", "that", "those", "for", "with", "without", "in", "on", "at", "to",
    "if", "when", "how", "why", "what", "which", "who", "si", "quand", "comment",
    "pourquoi", "quel", "quelle", "combien", "voici", "voila", "oui", "non",
}


def fold(text):
    """Lowercase, strip accents and collapse whitespace, for text comparison."""
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^0-9a-zA-Z]+", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def words_of(text):
    return WORD.findall(text or "")


def shingles(word_list, size=5):
    if len(word_list) < size:
        return {" ".join(word_list)} if word_list else set()
    return {" ".join(word_list[i:i + size]) for i in range(len(word_list) - size + 1)}


def jaccard(left, right):
    if not left or not right:
        return 0.0
    return len(left & right) / float(len(left | right))


# ---------------------------------------------------------------------------
# parser
# ---------------------------------------------------------------------------

class PageParser(HTMLParser):
    """Flatten an HTML document into text nodes carrying their container flags."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.nodes = []
        self.skip = 0
        self.in_jsonld = False
        self.jsonld_raw = []
        self.metas = {}
        self.times = []
        self.heading = None
        self.has_main = False
        self.table_th = 0
        self.link_href = None

    # -- stack helpers ------------------------------------------------------

    def flags_now(self):
        flags = set()
        for entry in self.stack:
            flags |= entry["flags"]
        return flags

    @staticmethod
    def element_flags(tag, attrs):
        flags = set()
        blob = " ".join(
            [attrs.get("class", ""), attrs.get("id", ""), attrs.get("data-role", "")]
        )
        if tag in CHROME_TAGS:
            flags.add("chrome")
        if tag in ("header", "footer"):
            flags.add("chrome-candidate")
        if tag == "main" or attrs.get("role", "").lower() == "main":
            flags.add("main")
        if tag == "article":
            flags.add("main")
        if tag == "details":
            flags.add("details")
        if tag == "noscript":
            flags.add("noscript")
        if tag == "table":
            flags.add("table")
        if tag == "li":
            flags.add("li")
        if tag == "a":
            flags.add("link")
        if "hidden" in attrs:
            flags.add("hidden")
        if attrs.get("aria-hidden", "").lower() == "true":
            flags.add("aria-hidden")
        style = attrs.get("style", "").replace(" ", "").lower()
        if "display:none" in style or "visibility:hidden" in style:
            flags.add("display-none")
        role = attrs.get("role", "").lower()
        if role in ("tabpanel", "tab"):
            flags.add("tabpanel")
        if role == "dialog":
            flags.add("modal")
        if blob.strip():
            for name, pattern in CLASS_FLAGS:
                if pattern.search(blob):
                    flags.add(name)
        return flags

    # -- events -------------------------------------------------------------

    def handle_starttag(self, tag, attrs):
        attrs = {k.lower(): (v or "") for k, v in attrs}
        if tag == "script":
            if "ld+json" in attrs.get("type", "").lower():
                self.in_jsonld = True
                self.jsonld_raw.append("")
            self.skip += 1
            self.stack.append({"tag": tag, "flags": set()})
            return
        if tag in SKIP_TAGS:
            self.skip += 1
            self.stack.append({"tag": tag, "flags": set()})
            return
        if tag == "meta":
            key = (attrs.get("property") or attrs.get("name") or "").lower()
            if key:
                self.metas[key] = attrs.get("content", "")
            return
        if tag == "time":
            if attrs.get("datetime"):
                self.times.append(attrs["datetime"])
        if tag == "th":
            self.table_th += 1
        if tag == "main" or tag == "article":
            self.has_main = True
        if tag == "a":
            self.link_href = attrs.get("href", "")
        if tag in VOID_TAGS:
            return
        self.stack.append({"tag": tag, "flags": self.element_flags(tag, attrs)})
        if tag in HEADING_TAGS:
            self.heading = {
                "level": int(tag[1]),
                "text": [],
                "id": attrs.get("id", ""),
                "flags": self.flags_now(),
            }
        if tag in BLOCK_TAGS:
            self.nodes.append({"kind": "break"})

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag in VOID_TAGS:
            return
        if tag == "script":
            self.in_jsonld = False
        if tag in SKIP_TAGS:
            self.skip = max(0, self.skip - 1)
        if tag in HEADING_TAGS and self.heading:
            text = re.sub(r"\s+", " ", "".join(self.heading["text"])).strip()
            self.nodes.append(
                {
                    "kind": "heading",
                    "level": self.heading["level"],
                    "text": text,
                    "id": self.heading["id"],
                    "flags": self.heading["flags"],
                }
            )
            self.heading = None
        if tag in BLOCK_TAGS:
            self.nodes.append({"kind": "break"})
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index]["tag"] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        if self.in_jsonld:
            self.jsonld_raw[-1] += data
            return
        if self.skip:
            return
        if not data.strip():
            return
        if self.heading is not None:
            self.heading["text"].append(data)
            return
        flags = self.flags_now()
        if self.link_href and "link" in flags:
            pass
        self.nodes.append(
            {
                "kind": "text",
                "text": re.sub(r"\s+", " ", data),
                "flags": flags,
                "href": self.link_href if "link" in flags else "",
            }
        )


# ---------------------------------------------------------------------------
# passage building
# ---------------------------------------------------------------------------

def slugify(text, fallback):
    slug = fold(text).replace(" ", "-")[:60].strip("-")
    return slug or fallback


def is_chrome(flags, has_main):
    if "chrome" in flags:
        return True
    if "chrome-candidate" in flags and "main" not in flags:
        return True
    if has_main and "main" not in flags:
        return True
    return False


def collect_units(nodes, has_main):
    """Group text nodes into (heading, paragraphs) units in document order."""
    units = []
    current = {
        "heading": "", "level": 0, "anchor": "", "hflags": set(), "paras": [],
    }
    buffer = {"text": [], "flags": set(), "link_words": 0, "words": 0, "hrefs": []}

    def flush_para():
        text = re.sub(r"\s+", " ", " ".join(buffer["text"])).strip()
        if text:
            current["paras"].append(
                {
                    "text": text,
                    "flags": set(buffer["flags"]),
                    "link_words": buffer["link_words"],
                    "words": len(words_of(text)),
                    "hrefs": list(buffer["hrefs"]),
                }
            )
        buffer["text"] = []
        buffer["flags"] = set()
        buffer["link_words"] = 0
        buffer["hrefs"] = []

    for node in nodes:
        if node["kind"] == "break":
            flush_para()
        elif node["kind"] == "heading":
            if is_chrome(node["flags"], has_main):
                continue
            flush_para()
            if current["paras"] or current["heading"]:
                units.append(current)
            current = {
                "heading": node["text"],
                "level": node["level"],
                "anchor": node["id"],
                "hflags": node["flags"],
                "paras": [],
            }
        else:
            if is_chrome(node["flags"], has_main):
                continue
            buffer["text"].append(node["text"])
            buffer["flags"] |= node["flags"]
            count = len(words_of(node["text"]))
            buffer["words"] += count
            if "link" in node["flags"]:
                buffer["link_words"] += count
                if node.get("href"):
                    buffer["hrefs"].append(node["href"])
    flush_para()
    if current["paras"] or current["heading"]:
        units.append(current)
    return units


def split_unit(unit, target, ceiling, floor):
    """Split a long unit at paragraph boundaries into blocks near `target` words."""
    chunks = []
    bucket = []
    size = 0
    for para in unit["paras"]:
        if size >= target and bucket:
            chunks.append(bucket)
            bucket = []
            size = 0
        bucket.append(para)
        size += para["words"]
        if size >= ceiling:
            chunks.append(bucket)
            bucket = []
            size = 0
    if bucket:
        tail = sum(p["words"] for p in bucket)
        if chunks and tail < floor:
            chunks[-1].extend(bucket)
        else:
            chunks.append(bucket)
    return chunks or [[]]


def measure(text, paras, heading, level, anchor, index, part, parts):
    body_words = words_of(text)
    sentences = [s for s in SENTENCE_SPLIT.split(text) if s.strip()]
    first = sentences[0] if sentences else ""
    flags = set()
    link_words = 0
    hrefs = []
    for para in paras:
        flags |= para["flags"]
        link_words += para["link_words"]
        hrefs.extend(para["hrefs"])

    numbers = NUMBER.findall(text)
    years = YEAR.findall(text)
    percents = PERCENT.findall(text)
    units = UNITS.findall(text)
    proper = []
    for sentence in sentences:
        tokens = WORD.findall(sentence)
        for token in tokens[1:]:
            if token[0].isupper() and token.lower() not in STOP_CAPS and len(token) > 2:
                proper.append(token)
    proper_unique = sorted(set(proper))

    anaphora_hits = [m.group(0) for m in ANAPHORA.finditer(text)]
    anaphora_first = [m.group(0) for m in ANAPHORA.finditer(first)]
    opener_anaphora = bool(ANAPHORA_OPENER.match(first))
    opener_context = CONTEXT_OPENER.match(first)
    attribution_hits = [m.group(0).strip() for m in ATTRIBUTION.finditer(text)]

    word_count = len(body_words)
    fact_tokens = len(numbers) + len(proper_unique)
    hazards = sorted(flags & set(HAZARD_FLAGS))
    heading_flat = fold(heading)

    return {
        "id": index,
        "part": part,
        "parts": parts,
        "anchor": anchor,
        "heading": heading,
        "heading_level": level,
        "heading_is_question": bool(
            heading.strip().endswith("?") or QUESTION_WORD.match(heading or "")
        ),
        "heading_words": len(words_of(heading)),
        "words": word_count,
        "sentences": len(sentences),
        "first_sentence": first[:400],
        "first_sentence_words": len(words_of(first)),
        "length_band": (
            "short" if word_count < 90 else "ideal" if word_count <= 200 else "long"
        ),
        "facts": {
            "numbers": len(numbers),
            "years": len(years),
            "percentages": len(percents),
            "units": len(units),
            "proper_nouns": len(proper_unique),
            "proper_noun_sample": proper_unique[:8],
            "fact_tokens": fact_tokens,
            "density_per_100w": round(fact_tokens * 100.0 / word_count, 1) if word_count else 0.0,
        },
        "autonomy": {
            "anaphora_count": len(anaphora_hits),
            "anaphora_terms": sorted(set(h.lower() for h in anaphora_hits))[:8],
            "anaphora_in_first_sentence": len(anaphora_first),
            "opens_on_anaphora": opener_anaphora,
        },
        "direct_answer": {
            "opens_on_context": bool(opener_context),
            "context_opener": opener_context.group(0).strip() if opener_context else "",
            "first_sentence_in_range": 15 <= len(words_of(first)) <= 70,
        },
        "attribution": {
            "markers": sorted(set(a.lower() for a in attribution_hits))[:8],
            "marker_count": len(attribution_hits),
            "external_links": len([h for h in hrefs if h.startswith("http")]),
        },
        "extractability": {
            "in_served_html": True,
            "hazards": hazards,
            "link_word_ratio": round(link_words / float(word_count), 2) if word_count else 0.0,
            "is_link_list": bool(word_count and link_words / float(word_count) > 0.55),
            "in_table": "table" in flags,
            "promo_block": "promo" in flags,
            "boilerplate_block": "boilerplate" in flags,
        },
        "_fold_heading": heading_flat,
        "_fold_text": fold(text),
        "text_head": text[:280],
    }


def build_passages(nodes, has_main, target, ceiling, floor):
    passages = []
    index = 0
    for unit in collect_units(nodes, has_main):
        total = sum(p["words"] for p in unit["paras"])
        if not unit["heading"] and total < 25:
            continue
        chunks = split_unit(unit, target, ceiling, floor) if total > ceiling else [unit["paras"]]
        for position, chunk in enumerate(chunks, start=1):
            text = " ".join(p["text"] for p in chunk).strip()
            heading = unit["heading"] or "(text before the first heading)"
            anchor = unit["anchor"] or slugify(heading, "passage-%d" % (index + 1))
            if len(chunks) > 1 and position > 1:
                anchor = "%s#part-%d" % (anchor, position)
            index += 1
            passages.append(
                measure(
                    text, chunk, heading, unit["level"], anchor, index,
                    position, len(chunks),
                )
            )
    return passages


# ---------------------------------------------------------------------------
# page level checks
# ---------------------------------------------------------------------------

def walk_jsonld(node, out):
    if isinstance(node, dict):
        types = node.get("@type")
        if isinstance(types, str):
            out["types"].append(types)
        elif isinstance(types, list):
            out["types"].extend([t for t in types if isinstance(t, str)])
        for key in ("datePublished", "dateModified", "dateCreated"):
            if isinstance(node.get(key), str):
                out["dates"].setdefault(key, node[key])
        if types == "Question" or (isinstance(types, list) and "Question" in types):
            answer = node.get("acceptedAnswer") or {}
            if isinstance(answer, list) and answer:
                answer = answer[0]
            out["questions"].append(
                {
                    "question": str(node.get("name") or node.get("text") or ""),
                    "answer": str(
                        (answer or {}).get("text", "") if isinstance(answer, dict) else ""
                    ),
                }
            )
        for value in node.values():
            walk_jsonld(value, out)
    elif isinstance(node, list):
        for value in node:
            walk_jsonld(value, out)


def analyse_jsonld(raw_blocks, visible_fold, headings_fold):
    out = {"types": [], "dates": {}, "questions": [], "invalid_blocks": 0}
    for raw in raw_blocks:
        try:
            walk_jsonld(json.loads(raw), out)
        except (ValueError, TypeError):
            out["invalid_blocks"] += 1
    checked = []
    for entry in out["questions"]:
        needle = fold(entry["question"])
        answer_needle = fold(entry["answer"])[:120]
        best = 0.0
        for heading in headings_fold:
            best = max(best, difflib.SequenceMatcher(None, needle, heading).ratio())
        checked.append(
            {
                "question": entry["question"],
                "in_visible_text": bool(needle and needle in visible_fold),
                "best_heading_match": round(best, 2),
                "answer_in_visible_text": bool(
                    answer_needle and answer_needle in visible_fold
                ),
            }
        )
    out["questions"] = checked
    out["types"] = sorted(set(out["types"]))
    return out


def content_words(text):
    """Words long enough to carry topic, used to spot paraphrased duplicates."""
    return {w for w in text.split() if len(w) >= 4 and w not in STOP_CAPS}


def containment(left, right):
    if not left or not right:
        return 0.0
    return len(left & right) / float(min(len(left), len(right)))


def internal_competition(passages, heading_threshold, verbatim_threshold, topic_threshold):
    """Two passages of the same page answering the same question neutralise each other.

    Three signals, any one of them is enough: near-identical headings, near-verbatim
    body (5-gram overlap), or the same topic vocabulary reused (paraphrase).
    The H1 passage is excluded: an H2 that restates the page title is the intended
    structure, not competition.
    """
    pairs = []
    prepared = [
        (p, shingles(p["_fold_text"].split()), content_words(p["_fold_text"]))
        for p in passages
        if p["heading_level"] > 1 and p["words"] >= 30
    ]
    for i in range(len(prepared)):
        for j in range(i + 1, len(prepared)):
            left, left_sh, left_cw = prepared[i]
            right, right_sh, right_cw = prepared[j]
            head_ratio = difflib.SequenceMatcher(
                None, left["_fold_heading"], right["_fold_heading"]
            ).ratio()
            body_ratio = jaccard(left_sh, right_sh)
            topic_ratio = containment(left_cw, right_cw)
            triggers = []
            if head_ratio >= heading_threshold:
                triggers.append("heading")
            if body_ratio >= verbatim_threshold:
                triggers.append("verbatim")
            if topic_ratio >= topic_threshold:
                triggers.append("topic")
            if triggers:
                pairs.append(
                    {
                        "a": left["id"],
                        "a_heading": left["heading"],
                        "b": right["id"],
                        "b_heading": right["heading"],
                        "heading_similarity": round(head_ratio, 2),
                        "body_overlap": round(body_ratio, 2),
                        "topic_overlap": round(topic_ratio, 2),
                        "triggered_by": triggers,
                    }
                )
    return pairs


def parse_file(path):
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        markup = handle.read()
    parser = PageParser()
    parser.feed(markup)
    parser.close()
    return parser, markup


def main(argv=None):
    ap = argparse.ArgumentParser(description="Cut an HTML page into scored passages.")
    ap.add_argument("html", help="the served HTML file, saved with curl")
    ap.add_argument("--rendered", help="optional browser-rendered HTML, to expose JS-only content")
    ap.add_argument("--template", action="append", default=[],
                    help="another page of the same site, to expose template duplication")
    ap.add_argument("--target-words", type=int, default=150)
    ap.add_argument("--ceiling-words", type=int, default=200)
    ap.add_argument("--floor-words", type=int, default=60)
    ap.add_argument("--format", choices=("json", "text"), default="json")
    ap.add_argument("--out", help="write to this file instead of stdout")
    args = ap.parse_args(argv)

    parser, markup = parse_file(args.html)
    passages = build_passages(
        parser.nodes, parser.has_main,
        args.target_words, args.ceiling_words, args.floor_words,
    )
    visible_fold = " ".join(
        p["_fold_heading"] + " " + p["_fold_text"] for p in passages
    )
    headings_fold = [p["_fold_heading"] for p in passages]
    jsonld = analyse_jsonld(parser.jsonld_raw, visible_fold, headings_fold)

    # dates present in the served HTML, compared with the JSON-LD dates
    html_dates = {
        "meta_published": parser.metas.get("article:published_time", ""),
        "meta_modified": parser.metas.get("article:modified_time", ""),
        "time_elements": parser.times[:5],
    }
    ld_pub = jsonld["dates"].get("datePublished", "")
    ld_mod = jsonld["dates"].get("dateModified", "")
    date_check = {
        "html": html_dates,
        "json_ld": {"datePublished": ld_pub, "dateModified": ld_mod},
        "published_agrees": bool(ld_pub) and ld_pub[:10] == html_dates["meta_published"][:10],
        "modified_agrees": bool(ld_mod) and ld_mod[:10] == html_dates["meta_modified"][:10],
        "any_date_found": bool(ld_pub or ld_mod or any(html_dates.values())),
    }

    # JS-only content
    js_delta = None
    if args.rendered:
        rendered_parser, _ = parse_file(args.rendered)
        rendered = build_passages(
            rendered_parser.nodes, rendered_parser.has_main,
            args.target_words, args.ceiling_words, args.floor_words,
        )
        served_keys = {(p["_fold_heading"], p["_fold_text"][:80]) for p in passages}
        served_body = " ".join(p["_fold_text"] for p in passages)
        js_only = []
        for item in rendered:
            key = (item["_fold_heading"], item["_fold_text"][:80])
            if key in served_keys:
                continue
            if item["_fold_text"][:80] and item["_fold_text"][:80] in served_body:
                continue
            item["extractability"]["in_served_html"] = False
            item["id"] = len(passages) + len(js_only) + 1
            js_only.append(item)
        served_words = sum(p["words"] for p in passages)
        js_words = sum(p["words"] for p in js_only)
        passages.extend(js_only)
        js_delta = {
            "served_words": served_words,
            "js_only_words": js_words,
            "js_only_passages": len(js_only),
            "share_invisible_without_js": (
                round(js_words * 100.0 / (served_words + js_words), 1)
                if (served_words + js_words) else 0.0
            ),
            "js_only_headings": [p["heading"] for p in js_only][:20],
        }

    # template duplication against other pages of the same site
    template_hits = []
    if args.template:
        other_shingles = []
        for path in args.template:
            other_parser, _ = parse_file(path)
            for item in build_passages(
                other_parser.nodes, other_parser.has_main,
                args.target_words, args.ceiling_words, args.floor_words,
            ):
                other_shingles.append((path, item["heading"], shingles(item["_fold_text"].split())))
        for passage in passages:
            own = shingles(passage["_fold_text"].split())
            for path, heading, other in other_shingles:
                overlap = jaccard(own, other)
                if overlap >= 0.5:
                    passage["extractability"]["template_duplicate"] = True
                    template_hits.append(
                        {
                            "passage": passage["id"],
                            "heading": passage["heading"],
                            "matches": heading,
                            "file": path,
                            "overlap": round(overlap, 2),
                        }
                    )
                    break

    competition = internal_competition(passages, 0.75, 0.30, 0.60)

    lengths = sorted(p["words"] for p in passages)
    median = lengths[len(lengths) // 2] if lengths else 0
    report = {
        "source": args.html,
        "page": {
            "passage_count": len(passages),
            "body_words": sum(p["words"] for p in passages),
            "median_passage_words": median,
            "has_main_or_article": parser.has_main,
            "title": parser.metas.get("og:title", "") or parser.metas.get("title", ""),
            "html_bytes": len(markup),
            "passages_with_hazards": len(
                [p for p in passages if p["extractability"]["hazards"]]
            ),
            "passages_in_ideal_length": len(
                [p for p in passages if p["length_band"] == "ideal"]
            ),
            "question_headings": len([p for p in passages if p["heading_is_question"]]),
        },
        "dates": date_check,
        "json_ld": jsonld,
        "js_delta": js_delta,
        "template_duplication": template_hits,
        "internal_competition": competition,
        "passages": passages,
    }
    for passage in report["passages"]:
        passage.pop("_fold_heading", None)
        passage.pop("_fold_text", None)

    if args.format == "text":
        out = [
            "%s  passages=%d  body_words=%d  median=%d"
            % (args.html, len(passages), report["page"]["body_words"], median),
            "",
        ]
        for passage in passages:
            out.append(
                "#%-3d h%-1d %-52s w=%-4d facts/100w=%-5s anaphora=%-2d q=%-5s served=%-5s %s"
                % (
                    passage["id"],
                    passage["heading_level"],
                    passage["heading"][:52],
                    passage["words"],
                    passage["facts"]["density_per_100w"],
                    passage["autonomy"]["anaphora_count"],
                    passage["heading_is_question"],
                    passage["extractability"]["in_served_html"],
                    ",".join(passage["extractability"]["hazards"]),
                )
            )
        if competition:
            out.append("")
            out.append("internal competition:")
            for pair in competition:
                out.append(
                    "  #%d vs #%d  heading=%.2f body=%.2f topic=%.2f  (%s)"
                    % (
                        pair["a"], pair["b"], pair["heading_similarity"],
                        pair["body_overlap"], pair["topic_overlap"],
                        ", ".join(pair["triggered_by"]),
                    )
                )
        text = "\n".join(out)
    else:
        text = json.dumps(report, ensure_ascii=False, indent=2)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
        print("wrote %s" % args.out)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
