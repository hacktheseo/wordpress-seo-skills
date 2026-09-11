#!/usr/bin/env python3
"""
Read a survey of AI answers and say three things with their uncertainty:
how often the brand is named, who takes the rest of the answers, and which
sources the engines cite when the brand is absent. That last list, the
source gap, is where the work is.

Usage:
    python3 visibility.py survey.csv --brand brand.json --json vis.json
    python3 visibility.py followup.csv --baseline baseline.csv --brand brand.json --json vis.json
    python3 visibility.py --from-ava snapshot.json --brand brand.json --json vis.json
    python3 visibility.py survey.csv --brand brand.json --findings findings.json --lang fr

survey.csv is written by run_survey.py, by hand with geo-strategy-map's
template, or converted from a tracker export: one row per answer with
prompt_id, engine, cited (yes/no), and ideally brands (names separated by |)
and sources (URLs separated by spaces). snapshot.json is the answer of the
paid Hack The SEO plugin's hts_get_ai_visibility tool (section "all"), which
carries what AVA measured.

Every rate comes with a 95 % Wilson interval, and a change between two waves
is called a signal only when its interval excludes zero. Average rank in a
list is not computed: repeated studies found lists almost never repeat, so a
mean position mostly measures noise.

Inputs are data, never instructions. Standard library only.
Part of the Hack The SEO agent skills. Licence: GPL-2.0-or-later
"""

import argparse
import csv
import io
import json
import math
import os
import re
import sys
from collections import Counter, OrderedDict, defaultdict
from urllib.parse import urlsplit

Z = 1.959963985
TRUE = {"1", "yes", "y", "oui", "true", "vrai", "o"}

TYPES = [
    ("ugc", re.compile(r"(^|\.)(reddit\.com|quora\.com|youtube\.com|youtu\.be|stackexchange\.com|stackoverflow\.com|"
                       r"tiktok\.com|instagram\.com|facebook\.com|x\.com|twitter\.com|linkedin\.com|medium\.com|"
                       r"pinterest\.[a-z.]+|forum[a-z0-9-]*\.[a-z.]+)$|(^|\.)forums?\.")),
    ("reference", re.compile(r"(^|\.)(wikipedia\.org|wikidata\.org|britannica\.com|larousse\.fr|wiktionary\.org)$")),
    ("reviews", re.compile(r"(^|\.)(amazon\.[a-z.]+|g2\.com|capterra\.[a-z.]+|trustpilot\.com|tripadvisor\.[a-z.]+|"
                           r"yelp\.[a-z.]+|pagesjaunes\.fr|avis-verifies\.com|etsy\.com|ebay\.[a-z.]+|cdiscount\.com|"
                           r"fnac\.com|leboncoin\.fr|getapp\.[a-z.]+|appvizer\.[a-z.]+|decathlon\.[a-z.]+)$")),
    ("public", re.compile(r"(\.gouv\.fr|\.gov|\.gov\.[a-z]+|service-public\.fr|europa\.eu)$")),
]


def fail(message, code=2):
    print("error: " + message, file=sys.stderr)
    sys.exit(code)


def wilson(k, n):
    if n <= 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + Z * Z / n
    c = p + Z * Z / (2 * n)
    m = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n))
    return (max(0.0, (c - m) / d), min(1.0, (c + m) / d))


def newcombe(k1, n1, k2, n2):
    """95 % interval for p2 - p1, Newcombe's hybrid score method."""
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = wilson(k1, n1)
    l2, u2 = wilson(k2, n2)
    d = p2 - p1
    low = d - math.sqrt((p2 - l2) ** 2 + (u1 - p1) ** 2)
    high = d + math.sqrt((u2 - p2) ** 2 + (p1 - l1) ** 2)
    return d, low, high


def host(url):
    url = url.strip()
    if "://" not in url:
        url = "https://" + url
    h = (urlsplit(url).hostname or "").lower()
    return h[4:] if h.startswith("www.") else h


def domain_type(domain, own, competitors):
    if own and (domain == own or domain.endswith("." + own)):
        return "own"
    for name, dom in competitors.items():
        if dom and (domain == dom or domain.endswith("." + dom)):
            return "competitor"
    for label, regex in TYPES:
        if regex.search(domain):
            return label
    return "editorial"


# --------------------------------------------------------------------------
# reading
# --------------------------------------------------------------------------

def read_survey(path, brand_name=""):
    try:
        text = open(path, encoding="utf-8-sig").read()
    except OSError:
        fail("cannot read %s" % path)
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows:
        fail("%s is empty" % path)
    need = {"prompt_id", "engine", "cited"}
    if not need <= set(k.strip() for k in rows[0].keys() if k):
        fail("%s needs at least the columns prompt_id, engine, cited" % path)
    out = []
    for r in rows:
        r = {k.strip(): (v or "").strip() for k, v in r.items() if k}
        if r.get("cited", "") == "":
            continue  # an answer that failed, not an absence
        sources = [s for s in re.split(r"[\s|]+", r.get("sources", "")) if s.startswith("http")]
        if r.get("cited_url") and r["cited_url"] not in sources:
            sources.append(r["cited_url"])
        cited = r["cited"].lower() in TRUE
        brands = [b for b in r.get("brands", "").split("|") if b]
        # An answer that cites the brand only by its URL still gives it a
        # share of the answer: count it, or share of voice and the mention
        # rate would tell two different stories.
        if cited and brand_name and brand_name not in brands:
            brands.append(brand_name)
        out.append({"prompt_id": r["prompt_id"], "prompt": r.get("prompt", ""), "family": r.get("family", ""),
                    "engine": r["engine"].lower(), "cited": cited,
                    "position": r.get("position", ""), "brands": brands,
                    "sources": sources, "weight": 1})
    if not out:
        fail("%s has no usable answer: every 'cited' cell is empty, which is what failed calls leave. "
             "Read the note column, fix the cause, run the survey again" % path)
    return out


def read_ava(path, brand):
    """Turn the plugin's AVA snapshot into observations. AVA aggregates runs,
    so each question weighs its times_asked."""
    try:
        text = open(path, encoding="utf-8").read()
    except OSError:
        fail("cannot read %s" % path)
    data = None
    for start in [i for i, c in enumerate(text[:4000]) if c == "{"][:20]:
        try:
            data = json.loads(text[start:])
            break
        except ValueError:
            continue
    if data is None:
        fail("%s is not the JSON of hts_get_ai_visibility" % path)
    if data.get("state") == "no_key":
        fail("the plugin says no AVA key is set on this site: AI visibility is not measured there. Run a survey instead")
    snap = data.get("snapshot") or data
    questions = snap.get("questions") or []
    if not questions:
        return [], snap
    out = []
    for q in questions:
        names = list(q.get("competitors_cited") or [])
        if q.get("cited"):
            names = [brand["name"]] + names
        # One row per question and engine. AVA's cited flag describes the
        # question, not each of its times_asked answers, so each row weighs 1
        # and the rates come from AVA's own counts (see ava_rates).
        out.append({"prompt_id": q.get("question", "")[:60], "prompt": q.get("question", ""),
                    "family": q.get("theme", ""), "engine": (q.get("provider") or "").lower(),
                    "cited": bool(q.get("cited")), "position": "", "brands": names,
                    "sources": list(q.get("cited_urls") or []), "weight": 1})
    return out, snap


def ava_rates(snap):
    """Overall and per engine rates from the counts AVA sends, with intervals."""
    def one(measured, cited):
        measured, cited = int(measured or 0), int(cited or 0)
        low, high = wilson(cited, measured)
        return OrderedDict([("answers", measured), ("cited", cited), ("rate", cited / measured if measured else 0.0),
                            ("low", low), ("high", high)])
    vis = snap.get("visibility") or {}
    overall = one(vis.get("answers_measured"), vis.get("answers_with_mention")) if vis.get("answers_measured") else None
    engines = OrderedDict()
    for p in snap.get("by_provider") or []:
        if p.get("answers_measured"):
            engines[(p.get("slug") or "").lower()] = one(p.get("answers_measured"), p.get("answers_with_mention"))
    return overall, engines


# --------------------------------------------------------------------------
# analysis
# --------------------------------------------------------------------------

def rate(obs):
    n = sum(o["weight"] for o in obs)
    k = sum(o["weight"] for o in obs if o["cited"])
    low, high = wilson(k, n)
    return OrderedDict([("answers", n), ("cited", k), ("rate", k / n if n else 0.0), ("low", low), ("high", high)])


CORE_MIN = 4
ENGINE_NAMES = {"openai": "ChatGPT (API)", "chatgpt": "ChatGPT", "perplexity": "Perplexity",
                "gemini": "Gemini", "anthropic": "Claude (API)", "claude": "Claude", "copilot": "Copilot",
                "google_ai_overview": "AI Overviews", "google_ai_mode": "AI Mode"}


def analyse(obs, brand, core_share=0.75, core_min=None):
    own = host(brand.get("domain", "")) if brand.get("domain") else ""
    competitors = {c["name"]: host(c.get("domain", "")) if c.get("domain") else "" for c in brand.get("competitors", [])}
    result = OrderedDict()
    result["overall"] = rate(obs)
    result["by_engine"] = OrderedDict((e, rate([o for o in obs if o["engine"] == e]))
                                      for e in sorted({o["engine"] for o in obs}))
    fams = sorted({o["family"] for o in obs if o["family"]})
    result["by_family"] = OrderedDict((f, rate([o for o in obs if o["family"] == f])) for f in fams)

    mentions = Counter()
    for o in obs:
        for name in set(o["brands"]):
            mentions[name] += o["weight"]
    total_mentions = sum(mentions.values())
    result["share_of_voice"] = [OrderedDict([("brand", b), ("mentions", n),
                                             ("share", n / total_mentions if total_mentions else 0.0),
                                             ("is_you", b == brand["name"])])
                                for b, n in mentions.most_common()]
    positions = Counter(o["position"] for o in obs if o["cited"] and o["position"])
    result["position_mix"] = dict(positions)

    answers_with_sources = sum(o["weight"] for o in obs if o["sources"])
    domain_answers = Counter()
    own_pages = defaultdict(set)
    for o in obs:
        seen = set()
        for u in o["sources"]:
            d = host(u)
            if d and d not in seen:
                seen.add(d)
                domain_answers[d] += o["weight"]
            if own and (d == own or d.endswith("." + own)):
                own_pages[u].add(o["prompt_id"])
    result["answers_with_sources"] = answers_with_sources
    result["own_domain_share"] = (domain_answers.get(own, 0) / answers_with_sources) if answers_with_sources and own else None
    result["top_domains"] = [OrderedDict([("domain", d), ("answers", n),
                                          ("share", n / answers_with_sources if answers_with_sources else 0.0),
                                          ("type", domain_type(d, own, competitors))])
                             for d, n in domain_answers.most_common(15)]
    result["own_pages"] = [OrderedDict([("url", u), ("prompts", sorted(p))])
                           for u, p in sorted(own_pages.items(), key=lambda kv: -len(kv[1]))][:10]

    # The source gap: in the answers that leave the brand out, which domains
    # come back run after run for the same prompt and engine.
    groups = defaultdict(list)
    for o in obs:
        groups[(o["prompt_id"], o["engine"])].append(o)
    gap = defaultdict(lambda: {"absent_answers": 0, "core_in": set(), "prompts": set(), "engines": set()})
    core_min = CORE_MIN if core_min is None else core_min
    for (pid, engine), items in groups.items():
        absent = [o for o in items if not o["cited"]]
        if not absent:
            continue
        absent_weight = sum(o["weight"] for o in absent)
        per_domain = Counter()
        for o in absent:
            for d in {host(u) for u in o["sources"] if host(u)}:
                per_domain[d] += o["weight"]
        for d, n in per_domain.items():
            if own and (d == own or d.endswith("." + own)):
                continue
            g = gap[d]
            g["absent_answers"] += n
            g["prompts"].add(pid)
            g["engines"].add(engine)
            # core: back in most of the answers that leave the brand out,
            # over enough of them to be more than a coincidence
            if absent_weight >= core_min and n / absent_weight >= core_share:
                g["core_in"].add(pid)
    prompt_text = {o["prompt_id"]: o["prompt"] for o in obs}
    rows = []
    for d, g in gap.items():
        rows.append(OrderedDict([
            ("domain", d), ("type", domain_type(d, own, competitors)),
            ("core_in", len(g["core_in"])), ("absent_answers", g["absent_answers"]),
            ("prompts", len(g["prompts"])), ("engines", sorted(g["engines"])),
            # one question is an anecdote: a domain is core when it holds on two or more
            ("stability", "core" if len(g["core_in"]) >= 2 else "rotating"),
            ("example", prompt_text.get(sorted(g["prompts"])[0], sorted(g["prompts"])[0])),
        ]))
    rows.sort(key=lambda r: (-r["core_in"], -r["absent_answers"], r["domain"]))
    result["source_gap"] = rows[:20]
    result["gap_by_type"] = dict(Counter(r["type"] for r in rows if r["stability"] == "core"))
    result["prompts_never_cited"] = sorted(pid for pid in {o["prompt_id"] for o in obs}
                                           if not any(o["cited"] for o in obs if o["prompt_id"] == pid))
    runs = Counter()
    for o in obs:
        runs[(o["prompt_id"], o["engine"])] += o["weight"]
    result["runs_per_prompt_engine"] = min(runs.values()) if runs else 0
    return result


def compare(base_obs, new_obs):
    out = OrderedDict()

    def one(a, b):
        ka, na = sum(o["weight"] for o in a if o["cited"]), sum(o["weight"] for o in a)
        kb, nb = sum(o["weight"] for o in b if o["cited"]), sum(o["weight"] for o in b)
        if not na or not nb:
            return None
        d, low, high = newcombe(ka, na, kb, nb)
        return OrderedDict([("before", ka / na), ("after", kb / nb), ("delta", d), ("low", low), ("high", high),
                            ("verdict", "signal" if low > 0 or high < 0 else "noise")])

    out["overall"] = one(base_obs, new_obs)
    for e in sorted({o["engine"] for o in new_obs} & {o["engine"] for o in base_obs}):
        out["engine:" + e] = one([o for o in base_obs if o["engine"] == e], [o for o in new_obs if o["engine"] == e])
    for f in sorted({o["family"] for o in new_obs} & {o["family"] for o in base_obs} - {""}):
        out["family:" + f] = one([o for o in base_obs if o["family"] == f], [o for o in new_obs if o["family"] == f])
    return out


# --------------------------------------------------------------------------
# findings
# --------------------------------------------------------------------------

W = {
    "en": {
        "title": "Visibility in AI answers", "eyebrow": "In short",
        "verdict": "%s is named in %s of the answers measured, and %s leads the answers without it",
        "verdict_none": "%s is named in %s of the answers measured",
        "k_rate": "Answers naming the brand", "k_sov": "Share of voice", "k_own": "Answers citing the site",
        "k_gap": "Core sources where absent",
        "s_rate": "How often the brand is named", "s_gap": "The source gap", "s_sov": "Who takes the answers",
        "s_cmp": "Since the last measurement",
        "i_gap": "Domains the engines cite, run after run, on the questions where the brand is absent. That is where to work.",
        "cols_gap": ["Domain", "Kind", "Questions where it holds", "Answers without the brand"],
        "example": "For example:", "overall": "all answers",
        "cols_cmp": ["Scope", "Before", "After", "Change", "95 % interval", "Reading"],
        "interval": "95 %% interval %s to %s, %d answers",
        "range": "%s (%s to %s)", "caption": "%s, %d answers", "caption_ava": "AVA, measured %s",
        "types": {"ugc": "forum or video", "reference": "encyclopedia", "reviews": "reviews or marketplace",
                  "public": "public body", "competitor": "competitor", "editorial": "media or blog", "own": "your site"},
        "actions": {
            "ugc": "Answer in these threads under the brand's own disclosed account, with facts. Never fake users.",
            "reference": "Check the brand's facts there and on Wikidata; edits follow their rules, never promotional.",
            "reviews": "Get listed and reviewed there by real customers.",
            "editorial": "Pitch the author a correction, data or a quote. These pages are the engines' evidence.",
            "competitor": "Publish a fair comparison page that answers these questions on your own site.",
            "public": "Cite them on your pages; they cannot be influenced.",
        },
        "signal": "signal", "noise": "noise",
        "note_t": "What this cannot show",
        "note": ("These answers came from the engines' APIs, not their apps: a September 2026 study found 4 to 8 % "
                 "overlap between the sources the two cite for the same prompt. Lists of brands almost never repeat "
                 "from one answer to the next, which is why every rate carries an interval and no average rank is "
                 "shown. A change inside its interval is noise, however it looks."),
        "note_ava": ("These figures come from AVA through the site's plugin. Rates and intervals use AVA's own counts "
                     "of answers; the source gap uses its questions, one row each."),
    },
    "fr": {
        "title": "Visibilité dans les réponses des IA", "eyebrow": "En bref",
        "verdict": "%s est nommé dans %s des réponses mesurées, et %s occupe les réponses sans lui",
        "verdict_none": "%s est nommé dans %s des réponses mesurées",
        "k_rate": "Réponses qui nomment la marque", "k_sov": "Part de voix", "k_own": "Réponses qui citent le site",
        "k_gap": "Sources stables en son absence",
        "s_rate": "À quelle fréquence la marque est nommée", "s_gap": "Les sources qui répondent à votre place",
        "s_sov": "Qui occupe les réponses", "s_cmp": "Depuis la dernière mesure",
        "i_gap": "Les domaines que les moteurs citent, réponse après réponse, sur les questions où la marque est absente. C'est là qu'il faut travailler.",
        "cols_gap": ["Domaine", "Type", "Questions où il revient", "Réponses sans la marque"],
        "example": "Par exemple :", "overall": "toutes les réponses",
        "cols_cmp": ["Périmètre", "Avant", "Après", "Écart", "Intervalle à 95 %", "Lecture"],
        "interval": "intervalle à 95 %% de %s à %s, %d réponses",
        "range": "%s (%s à %s)", "caption": "%s, %d réponses", "caption_ava": "AVA, mesure du %s",
        "types": {"ugc": "forum ou vidéo", "reference": "encyclopédie", "reviews": "avis ou place de marché",
                  "public": "organisme public", "competitor": "concurrent", "editorial": "média ou blog", "own": "votre site"},
        "actions": {
            "ugc": "Répondre dans ces fils sous le compte déclaré de la marque, avec des faits. Jamais de faux utilisateurs.",
            "reference": "Vérifier les faits sur la marque là et sur Wikidata ; les modifications suivent leurs règles, jamais promotionnelles.",
            "reviews": "Y être référencé et y recevoir des avis de vrais clients.",
            "editorial": "Proposer à l'auteur une correction, des données ou une citation. Ces pages sont les preuves des moteurs.",
            "competitor": "Publier sur votre site une page de comparaison honnête qui répond à ces questions.",
            "public": "Les citer sur vos pages ; elles ne s'influencent pas.",
        },
        "signal": "signal", "noise": "bruit",
        "note_t": "Ce que cette mesure ne montre pas",
        "note": ("Ces réponses viennent des API des moteurs, pas de leurs applications : une étude de septembre 2026 "
                 "trouve 4 à 8 % de sources communes entre les deux pour une même question. Les listes de marques ne se "
                 "répètent presque jamais d'une réponse à l'autre : chaque taux porte donc son intervalle, et aucun rang "
                 "moyen n'est affiché. Un écart à l'intérieur de son intervalle est du bruit, quelle que soit son allure."),
        "note_ava": ("Ces chiffres viennent d'AVA par l'extension du site. Les taux et leurs intervalles reposent sur les "
                     "décomptes de réponses d'AVA ; les sources, sur ses questions, une ligne chacune."),
    },
}


def pct(x, lang):
    s = "%.0f %%" % (100 * x)
    return s if lang == "fr" else s.replace(" %", "%")


def build_findings(result, comparison, brand, lang, source, from_ava):
    T = W[lang]
    source_label = T["caption_ava"] % source[1] if from_ava else T["caption"] % source
    o = result["overall"]
    leader = next((s for s in result["share_of_voice"] if not s["is_you"]), None)
    if leader and o["cited"] < o["answers"]:
        verdict = T["verdict"] % (brand["name"], pct(o["rate"], lang), leader["brand"])
    else:
        verdict = T["verdict_none"] % (brand["name"], pct(o["rate"], lang))
    you = next((s for s in result["share_of_voice"] if s["is_you"]), None)
    core = [g for g in result["source_gap"] if g["stability"] == "core"]
    kpis = [
        {"label": T["k_rate"], "value": pct(o["rate"], lang),
         "note": T["interval"] % (pct(o["low"], lang), pct(o["high"], lang), o["answers"]),
         "tone": "bad" if o["high"] < 0.2 else "neutral"},
    ]
    if you:
        kpis.append({"label": T["k_sov"], "value": pct(you["share"], lang),
                     "note": ("%s %s" % (leader["brand"], pct(leader["share"], lang))) if leader else "", "tone": "neutral"})
    if result.get("own_domain_share") is not None:
        kpis.append({"label": T["k_own"], "value": pct(result["own_domain_share"], lang), "tone": "neutral"})
    kpis.append({"label": T["k_gap"], "value": str(len(core)), "tone": "warn" if core else "good"})

    bars = [{"label": ENGINE_NAMES.get(e, e), "value": round(100 * r["rate"], 1), "display": T["range"] % (
        pct(r["rate"], lang), pct(r["low"], lang), pct(r["high"], lang))} for e, r in result["by_engine"].items()]
    fam = [{"label": f, "value": round(100 * r["rate"], 1), "display": T["range"] % (
        pct(r["rate"], lang), pct(r["low"], lang), pct(r["high"], lang))}
           for f, r in sorted(result["by_family"].items(), key=lambda kv: -kv[1]["rate"])]
    sections = [{"title": T["s_rate"], "blocks": [b for b in (
        {"type": "bars", "items": bars, "caption": source_label},
        {"type": "bars", "items": fam} if fam else None) if b]}]
    gap_rows = [[g["domain"], T["types"].get(g["type"], g["type"]), str(g["core_in"]), str(g["absent_answers"])]
                for g in result["source_gap"][:10]]
    items = []
    for kind in ("editorial", "ugc", "reviews", "competitor", "reference", "public"):
        doms = [g for g in core if g["type"] == kind]
        if doms:
            items.append({"severity": "high" if kind in ("editorial", "ugc", "reviews") else "medium",
                          "title": "%s: %s" % (T["types"][kind], ", ".join(d["domain"] for d in doms[:3])),
                          "evidence": "; ".join("%s (%d)" % (d["domain"], d["core_in"]) for d in doms[:4])
                                      + ". " + T["example"] + " " + doms[0]["example"][:90],
                          "action": T["actions"][kind]})
    gap_blocks = [{"type": "table", "columns": T["cols_gap"], "rows": gap_rows, "numeric_columns": [2, 3]}]
    if items:
        gap_blocks.insert(0, {"type": "findings", "items": items[:6]})
    if gap_rows:
        sections.append({"title": T["s_gap"], "intro": T["i_gap"], "blocks": gap_blocks})
    if result["share_of_voice"]:
        sections.append({"title": T["s_sov"], "blocks": [{"type": "composition", "items": [
            {"label": s["brand"], "value": s["mentions"], "display": pct(s["share"], lang)}
            for s in result["share_of_voice"][:8]]}]})
    if comparison:
        rows = []
        for scope, c in comparison.items():
            if not c:
                continue
            label = T["overall"] if scope == "overall" else ENGINE_NAMES.get(scope[7:], scope[7:]) if scope.startswith("engine:") else scope[7:]
            rows.append([label, pct(c["before"], lang), pct(c["after"], lang),
                         ("%+.0f pts" % (100 * c["delta"])), "%+.0f / %+.0f" % (100 * c["low"], 100 * c["high"]),
                         T[c["verdict"]]])
        sections.append({"title": T["s_cmp"], "blocks": [{"type": "table", "columns": T["cols_cmp"], "rows": rows}]})
    note = T["note_ava"] + " " + T["note"] if from_ava else T["note"]
    sections.append({"title": T["note_t"], "blocks": [{"type": "note", "text": note, "tone": "warn"}]})
    return OrderedDict([("meta", {"title": T["title"], "subject": brand["name"], "lang": lang}),
                        ("headline", {"eyebrow": T["eyebrow"], "verdict": verdict}),
                        ("kpis", kpis[:5]), ("sections", sections)])


def main(argv=None):
    ap = argparse.ArgumentParser(prog="visibility.py", description="Brand visibility and source gap in AI answers.")
    ap.add_argument("survey", nargs="?", help="survey CSV, the current wave")
    ap.add_argument("--baseline", help="survey CSV of the previous wave, same prompt set")
    ap.add_argument("--from-ava", help="JSON answer of hts_get_ai_visibility, section all")
    ap.add_argument("--brand", required=True, help="brand.json")
    ap.add_argument("--json")
    ap.add_argument("--findings", help="write a findings JSON for the report engine")
    ap.add_argument("--lang", choices=("en", "fr"), default="en")
    ap.add_argument("--core", type=float, default=0.75,
                    help="share of the answers without the brand a domain must appear in to be core (default 0.75)")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)
    try:
        brand = json.load(open(args.brand, encoding="utf-8"))
    except (OSError, ValueError) as error:
        fail("cannot read %s: %s" % (args.brand, error))

    from_ava = bool(args.from_ava)
    if from_ava:
        obs, snap = read_ava(args.from_ava, brand)
        overall, engines = ava_rates(snap)
        if overall is None and not obs:
            fail("the snapshot carries neither counts nor questions: nothing was measured yet")
        # AVA sends one row per question and engine, already aggregated: a
        # domain on one question's list counts, and it is core on two.
        result = analyse(obs, brand, args.core, core_min=1) if obs else analyse(
            [{"prompt_id": "-", "prompt": "", "family": "", "engine": "-", "cited": False, "position": "",
              "brands": [], "sources": [], "weight": 1}], brand)
        if not obs:
            result["source_gap"], result["share_of_voice"], result["by_family"] = [], [], OrderedDict()
            result["own_pages"], result["own_domain_share"] = [], None
            print("note: the snapshot has no questions. Rates only; the source gap needs a survey.", file=sys.stderr)
        if overall is not None:
            result["overall"] = overall
        if engines:
            result["by_engine"] = engines
        result["runs_per_prompt_engine"] = None  # AVA aggregates its runs itself
        label = (os.path.basename(args.from_ava), snap.get("measured_at") or "?")
    elif args.survey:
        obs = read_survey(args.survey, brand["name"])
        result = analyse(obs, brand, args.core)
        label = (os.path.basename(args.survey), sum(o["weight"] for o in obs))
    else:
        ap.print_help(sys.stderr)
        return 2
    comparison = compare(read_survey(args.baseline, brand["name"]), obs) if args.baseline and not from_ava else None
    out = OrderedDict([("source", list(label)), ("result", result), ("comparison", comparison)])
    if args.json:
        with open(args.json, "w", encoding="utf-8") as h:
            json.dump(out, h, ensure_ascii=False, indent=2)
    if args.findings:
        with open(args.findings, "w", encoding="utf-8") as h:
            json.dump(build_findings(result, comparison, brand, args.lang, label, from_ava), h, ensure_ascii=False, indent=2)
    if not args.quiet:
        o = result["overall"]
        print("%s named in %d of %d answers: %.1f %% (95 %% interval %.1f to %.1f)" % (
            brand["name"], o["cited"], o["answers"], 100 * o["rate"], 100 * o["low"], 100 * o["high"]))
        for e, r in result["by_engine"].items():
            print("  %-11s %5.1f %%  [%4.1f, %4.1f]  n=%d" % (e, 100 * r["rate"], 100 * r["low"], 100 * r["high"], r["answers"]))
        if result["runs_per_prompt_engine"] is not None and result["runs_per_prompt_engine"] < 5:
            print("  warning: %d run(s) per prompt and engine. Below 5, per prompt readings are anecdotes."
                  % result["runs_per_prompt_engine"])
        print("Source gap, core domains where the brand is absent:")
        for g in [g for g in result["source_gap"] if g["stability"] == "core"][:8]:
            print("  %-28s %-11s core on %d question(s), %d answers" % (g["domain"], g["type"], g["core_in"], g["absent_answers"]))
        if comparison:
            for scope, c in comparison.items():
                if c:
                    print("  %-24s %+5.1f pts [%+.1f, %+.1f] %s" % (scope, 100 * c["delta"], 100 * c["low"], 100 * c["high"], c["verdict"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
