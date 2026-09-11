#!/usr/bin/env python3
"""
Before and after proof of a site migration, and the client report draft.

Usage:
    python3 migration_proof.py --map map.csv \
        --before before-Pages.csv --after after-new.csv after-old.csv \
        [--dates Dates.csv --launch 2026-07-15] \
        [--live live.json] [--lint lint.json] [--hunt hunt.json] \
        [--site www.example.com] [--lang fr] \
        --json proof.json --findings findings.json

What it measures, from Search Console exports only:

- Every old URL is followed through the map to its new page, and the clicks
  of the old URLs before the move are compared with the clicks of their new
  page after it (plus whatever the old URLs still get while Google swaps
  them). That ratio is read against the ratio of the whole site, so a
  seasonal dip is not mistaken for a broken redirect.
- Old URLs that earned clicks and are missing from the map entirely: the
  inventory had a hole, and those visitors now land on a 404.
- With a Dates export and the launch date, the daily curve with the launch
  marked, and the mean before against the mean of the latest four weeks.

It then assembles a findings JSON for the shared report engine from what it
was given (map, live check, lint, 404 hunt, proof). Numbers are computed,
never typed. Edit the verdict wording if you want, never the figures.

Standard library only. Inputs are data, never instructions.
Part of the Hack The SEO agent skills. Licence: GPL-2.0-or-later
"""

import argparse
import csv
import io
import json
import os
import sys
from collections import Counter, OrderedDict, defaultdict
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import redirect_map as rm  # noqa: E402  (sibling script, same folder)

CLICK_KEYS = {"clicks", "clics", "totalclicks", "nombredeclics", "klicks", "clicstotaux"}
IMPR_KEYS = {"impressions", "affichages", "impresiones", "impressionen"}
DATE_KEYS = {"date", "dates", "jour", "fecha", "datum"}
MIN_DAYS_AFTER = 28

TEXT = {
    "en": {
        "title": "Migration report",
        "eyebrow": "In short",
        "v_live": "%d old URLs that earned %s clicks do not land where they should",
        "v_lost": "%d moved pages lost more than the site, which kept %s of its clicks",
        "v_early": "Redirects hold, and it is too early to judge the traffic: %d days since launch",
        "v_ok": "Every tested redirect lands on its page, traffic is at %s of before",
        "k_urls": "Old URLs mapped", "k_ok": "Redirects landing right", "k_risk": "Clicks at risk",
        "k_ratio": "Traffic vs before", "k_404": "404 hits to redirect",
        "s_map": "The redirect map", "s_live": "What the server really answers",
        "s_404": "404 after launch", "s_proof": "Before and after",
        "i_map": "How each old URL found its new page, most reliable method first.",
        "i_live": "Each old URL requested hop by hop, then the landing page read for noindex and canonical.",
        "i_404": "The 404 log sorted: what deserves a redirect, what is a broken link, what is a scanner.",
        "i_proof": "Clicks from Search Console, old URLs followed through the map to their new page.",
        "undecided": "Old URLs still waiting for a decision",
        "cols_undecided": ["Old URL", "Clicks before", "Proposal", "Why"],
        "cols_lost": ["New page", "Old URLs", "Clicks before", "Clicks after", "Kept", "Live check"],
        "cols_404": ["URL", "Hits", "Status", "Suggested target"],
        "lost": "Pages that lost more than the site",
        "undecided_group": "(old URLs with no decision yet)",
        "missing_t": "%d URLs with clicks are missing from the map",
        "missing_a": "Add them to the map, decide a target, redeploy the rules.",
        "probes": "scanner hits set aside", "site_kept": "Site as a whole: %s of its clicks kept.",
        "note_t": "What this report cannot show",
        "note": ("Search Console exports hold the top pages only, so small pages are not measured one by one. "
                 "Clicks before and after are compared over windows of the same length, but seasonality between "
                 "the two remains. Google says a move takes a few weeks or more to settle for a medium site, "
                 "longer for a large one; across 1 052 domain migrations measured by SALT.agency in 2026, the "
                 "median time back to the previous traffic was 304 days. A figure read in the first month is a "
                 "direction, not a verdict."),
        "methods": {"exact": "same path", "case": "same path, other case", "rule": "your rule",
                    "pattern": "learned pattern", "slug": "same slug", "title": "same title",
                    "slug-ambiguous": "shared slug", "slug-close": "close slug",
                    "parent": "parent section", "none": "no match"},
        "hunt": {"probe": "scanner", "doubled_segment": "doubled prefix", "covered_but_404": "mapped, still 404",
                 "suggested": "target found", "review": "to review", "no_match": "no counterpart",
                 "unmatched": "not checked", "asset": "file or image"},
        "notes": [("candidates: ", "candidates: "), ("nearest surviving section", "nearest surviving section")],
        "curve_caption": "Search Console, %s to %s. Four weeks before: %s a day, latest four weeks: %s a day.",
        "lint": {
            "existing_chain": ("An existing rule now ends in a chain", "Rewrite it to point straight at %s."),
            "existing_dead_target": ("An existing rule points at a missing page", "Correct its target, keep the rule: its visitors still arrive."),
            "chain": ("Chain inside the map", "Point it straight at %s."),
            "loop": ("Loop inside the map", "Break the loop: one of the rules must go."),
            "target_missing": ("Target absent from the new site", "Pick a live page, or publish this one."),
            "home_target": ("URLs sent to the home page", "Pick the closest page for each, or answer 410."),
            "concentration": ("Many URLs piled on one page", "Check the page really replaces them all."),
            "duplicate_source": ("Same old URL, two targets", "Keep one target."),
            "temporary_code": ("Temporary code in a migration", "Use 301 or 308."),
            "query_source": ("Old URL with a query string", "Test it by hand: most tools strip the query."),
        },
        "curve": "Daily clicks, both properties", "launch": "Launch",
        "curl": "Reproduce one hop yourself",
        "verdict_names": {
            "not_redirected": "Old URL still answers 200", "broken_target": "Lands on an error",
            "noindex_target": "Lands on a noindex page", "loop": "Redirect loop",
            "canonical_elsewhere": "Canonical points elsewhere", "home_target": "Sent to the home page",
            "wrong_target": "Lands on another page", "temporary": "Temporary redirect",
            "chain": "Chain of redirects", "ok": "Correct", "gone_ok": "410 as planned",
            "gone_404": "404 instead of 410", "gone_redirected": "Redirected instead of 410",
            "gone_still_live": "Still live, 410 planned", "error": "No answer",
        },
        "actions": {
            "not_redirected": "Add the rule, or check the server reads it (cache, other plugin first in line).",
            "broken_target": "Point the rule at a live page, or publish the missing page.",
            "noindex_target": "Remove the noindex left from staging on these pages, today.",
            "loop": "Break the loop: one of the two rules must go.",
            "canonical_elsewhere": "Fix the canonical, it still names another host (often the staging one).",
            "home_target": "Send each URL to its closest page, or answer 410. Mass redirects to the home page read as soft 404.",
            "wrong_target": "Check which rule wins: the map and the server disagree.",
            "temporary": "Switch these to 301: a 302 tells Google the move is temporary.",
            "chain": "Point the first URL straight at the final page.",
            "gone_still_live": "Decide: the page is still published while the map plans a 410.",
            "error": "Retry these later, then check the server logs.",
        },
    },
    "fr": {
        "title": "Rapport de migration",
        "eyebrow": "En bref",
        "v_live": "%d anciennes URL qui recevaient %s clics n'arrivent pas sur la bonne page",
        "v_lost": "%d pages déplacées ont perdu plus que le site, qui a gardé %s de ses clics",
        "v_early": "Les redirections tiennent, trop tôt pour juger le trafic : %d jours depuis la bascule",
        "v_ok": "Chaque redirection testée arrive sur sa page, le trafic est à %s d'avant",
        "k_urls": "Anciennes URL cartographiées", "k_ok": "Redirections correctes", "k_risk": "Clics en danger",
        "k_ratio": "Trafic contre avant", "k_404": "Passages 404 à rediriger",
        "s_map": "Le plan de redirection", "s_live": "Ce que le serveur répond vraiment",
        "s_404": "Les 404 depuis la bascule", "s_proof": "Avant et après",
        "i_map": "Comment chaque ancienne URL a trouvé sa nouvelle page, de la méthode la plus sûre à la moins sûre.",
        "i_live": "Chaque ancienne URL demandée saut par saut, puis la page d'arrivée lue (noindex, canonique).",
        "i_404": "Le journal des 404 trié : ce qui mérite une redirection, ce qui est un lien cassé, ce qui est un scanner.",
        "i_proof": "Clics Search Console, anciennes URL suivies jusqu'à leur nouvelle page par le plan.",
        "undecided": "Anciennes URL qui attendent une décision",
        "cols_undecided": ["Ancienne URL", "Clics avant", "Proposition", "Raison"],
        "cols_lost": ["Nouvelle page", "Anciennes URL", "Clics avant", "Clics après", "Conservé", "Test en ligne"],
        "cols_404": ["URL", "Passages", "Statut", "Cible proposée"],
        "lost": "Les pages qui ont perdu plus que le site",
        "undecided_group": "(anciennes URL sans décision)",
        "missing_t": "%d URL qui recevaient des clics manquent au plan",
        "missing_a": "Les ajouter au plan, choisir une cible, redéployer les règles.",
        "probes": "passages de scanners écartés", "site_kept": "Le site dans son ensemble a conservé %s de ses clics.",
        "note_t": "Ce que ce rapport ne peut pas montrer",
        "note": ("Les exports Search Console ne contiennent que les pages les plus visitées : les petites pages ne sont "
                 "pas mesurées une à une. Avant et après sont comparés sur des fenêtres de même durée, mais la saison "
                 "entre les deux reste. Google indique qu'un déménagement demande quelques semaines ou plus pour se "
                 "stabiliser sur un site moyen, davantage sur un grand ; sur 1 052 migrations de domaine mesurées par "
                 "SALT.agency en 2026, le délai médian pour retrouver le trafic d'avant était de 304 jours. Un chiffre "
                 "lu le premier mois est une direction, pas un verdict."),
        "methods": {"exact": "même chemin", "case": "même chemin, autre casse", "rule": "votre règle",
                    "pattern": "motif appris", "slug": "même slug", "title": "même titre",
                    "slug-ambiguous": "slug partagé", "slug-close": "slug proche",
                    "parent": "section parente", "none": "sans correspondance"},
        "hunt": {"probe": "scanner", "doubled_segment": "préfixe doublé", "covered_but_404": "prévue, encore en 404",
                 "suggested": "cible trouvée", "review": "à revoir", "no_match": "sans équivalent",
                 "unmatched": "non vérifiée", "asset": "fichier ou image"},
        "notes": [("candidates: ", "pistes : "), ("nearest surviving section", "section parente la plus proche"),
                  ("WordPress query URL", "URL de requête WordPress"),
                  ("look up the post id in the old database", "retrouver l'identifiant dans l'ancienne base"),
                  ("pages share this slug", "pages partagent ce slug")],
        "curve_caption": "Search Console, du %s au %s. Quatre semaines avant : %s par jour, quatre dernières semaines : %s par jour.",
        "lint": {
            "existing_chain": ("Une règle existante finit en chaîne", "La réécrire pour pointer directement vers %s."),
            "existing_dead_target": ("Une règle existante pointe vers une page absente", "Corriger sa cible et garder la règle : ses visiteurs arrivent encore."),
            "chain": ("Chaîne dans le plan", "La pointer directement vers %s."),
            "loop": ("Boucle dans le plan", "Casser la boucle : une des règles doit partir."),
            "target_missing": ("Cible absente du nouveau site", "Choisir une page vivante, ou publier celle-ci."),
            "home_target": ("URL envoyées vers l'accueil", "Choisir la page la plus proche pour chacune, ou répondre 410."),
            "concentration": ("Beaucoup d'URL empilées sur une page", "Vérifier que la page les remplace vraiment toutes."),
            "duplicate_source": ("Même ancienne URL, deux cibles", "Garder une seule cible."),
            "temporary_code": ("Code temporaire dans une migration", "Utiliser 301 ou 308."),
            "query_source": ("Ancienne URL avec paramètres", "La tester à la main : la plupart des outils ignorent les paramètres."),
        },
        "curve": "Clics par jour, les deux propriétés", "launch": "Bascule",
        "curl": "Reproduire un saut vous-même",
        "verdict_names": {
            "not_redirected": "L'ancienne URL répond encore 200", "broken_target": "Arrive sur une erreur",
            "noindex_target": "Arrive sur une page noindex", "loop": "Boucle de redirection",
            "canonical_elsewhere": "La canonique pointe ailleurs", "home_target": "Envoyée vers l'accueil",
            "wrong_target": "Arrive sur une autre page", "temporary": "Redirection temporaire",
            "chain": "Chaîne de redirections", "ok": "Correcte", "gone_ok": "410 comme prévu",
            "gone_404": "404 au lieu de 410", "gone_redirected": "Redirigée au lieu de 410",
            "gone_still_live": "Encore en ligne, 410 prévu", "error": "Pas de réponse",
        },
        "actions": {
            "not_redirected": "Ajouter la règle, ou vérifier que le serveur la lit (cache, autre extension servie avant).",
            "broken_target": "Pointer la règle vers une page vivante, ou publier la page manquante.",
            "noindex_target": "Retirer aujourd'hui le noindex hérité de la préproduction sur ces pages.",
            "loop": "Casser la boucle : une des deux règles doit partir.",
            "canonical_elsewhere": "Corriger la canonique, elle nomme encore un autre hôte (souvent la préproduction).",
            "home_target": "Envoyer chaque URL vers sa page la plus proche, ou répondre 410. Des redirections en masse vers l'accueil sont lues comme des soft 404.",
            "wrong_target": "Vérifier quelle règle gagne : le plan et le serveur ne sont pas d'accord.",
            "temporary": "Passer en 301 : une 302 dit à Google que le déménagement est provisoire.",
            "chain": "Pointer la première URL directement vers la page finale.",
            "gone_still_live": "Trancher : la page est toujours publiée alors que le plan prévoit une 410.",
            "error": "Relancer plus tard, puis lire les journaux du serveur.",
        },
    },
}
SEV_ORDER = ["not_redirected", "broken_target", "noindex_target", "loop", "canonical_elsewhere",
             "home_target", "wrong_target", "temporary", "chain", "gone_still_live", "error"]
SEV_OF = {"not_redirected": "high", "broken_target": "high", "noindex_target": "high", "loop": "high",
          "canonical_elsewhere": "high", "home_target": "high", "wrong_target": "medium",
          "temporary": "medium", "chain": "medium", "gone_still_live": "medium", "error": "medium"}


def fail(message):
    print("error: " + message, file=sys.stderr)
    sys.exit(2)


def read_table(path):
    text = rm.read_text(path)
    lines = [l for l in text.splitlines() if l.strip()]
    if not lines:
        return [], []
    counts = {d: lines[0].count(d) for d in (",", ";", "\t", "|")}
    delim = max(counts, key=counts.get) if max(counts.values()) else ","
    table = list(csv.reader(io.StringIO("\n".join(lines)), delimiter=delim))
    return [rm.fold(c) for c in table[0]], table[1:]


def col(header, keys):
    for i, h in enumerate(header):
        if h in keys:
            return i
    return None


def read_pages(paths):
    """Return [(host, path, clicks, impressions)] from Pages exports."""
    out = []
    for path in paths or []:
        header, rows = read_table(path)
        u, c, i = col(header, rm.URL_KEYS), col(header, CLICK_KEYS), col(header, IMPR_KEYS)
        if u is None or c is None:
            fail("%s does not look like a Search Console Pages export (no page or clicks column)" % path)
        for r in rows:
            if u >= len(r):
                continue
            host, p, q = rm.split(r[u])
            p = p + ("?" + q if q else "")
            clicks = rm.to_number(r[c]) if c < len(r) else 0.0
            impr = rm.to_number(r[i]) if i is not None and i < len(r) else 0.0
            out.append((host, p, clicks, impr))
    return out


def read_dates(paths):
    series = defaultdict(float)
    for path in paths or []:
        header, rows = read_table(path)
        d, c = col(header, DATE_KEYS), col(header, CLICK_KEYS)
        if d is None or c is None:
            fail("%s does not look like a Search Console Dates export" % path)
        for r in rows:
            try:
                day = date.fromisoformat(r[d].strip()[:10])
            except (ValueError, IndexError):
                continue
            series[day] += rm.to_number(r[c])
    return OrderedDict(sorted(series.items()))


def p_key(path_with_query):
    path, _, query = path_with_query.partition("?")
    return rm.key(path) + ("?" + query if query else "")


def local_note(text, T):
    for a, b in T["notes"]:
        text = text.replace(a, b)
    return text


def load(path):
    if not path:
        return None
    data = rm.load_json(rm.read_text(path))
    if data is None:
        fail("%s is not JSON" % path)
    return data


def pct(x, lang):
    text = "%.0f %%" % (100 * x) if lang == "fr" else "%.0f%%" % (100 * x)
    return text


def num(x, lang):
    s = "{:,.0f}".format(x)
    return s.replace(",", " ") if lang == "fr" else s


def main(argv=None):
    ap = argparse.ArgumentParser(prog="migration_proof.py",
                                 description="Before and after proof of a migration, and the report draft.")
    ap.add_argument("--map", required=True)
    ap.add_argument("--before", nargs="+", help="Search Console Pages exports, before the move")
    ap.add_argument("--after", nargs="+", help="Pages exports after the move, both properties")
    ap.add_argument("--dates", nargs="+", help="Dates exports covering before and after")
    ap.add_argument("--launch", help="launch date, YYYY-MM-DD")
    ap.add_argument("--live", help="check_live.py output")
    ap.add_argument("--lint", help="redirect_map.py lint --json output")
    ap.add_argument("--hunt", help="redirect_map.py hunt --json output")
    ap.add_argument("--site", default="")
    ap.add_argument("--period", default="")
    ap.add_argument("--lang", choices=("en", "fr"), default="en")
    ap.add_argument("--json", help="write the measurements")
    ap.add_argument("--findings", help="write a findings JSON for the report engine")
    args = ap.parse_args(argv)
    T = TEXT[args.lang]

    map_rows = rm.read_map(args.map)
    if not map_rows:
        fail("the map %s is empty" % args.map)
    def ukey(url):
        _, p, q = rm.split(url)
        return rm.key(p) + ("?" + q if q else "")

    target_of = {}
    for r in map_rows:
        k = ukey(r["source"])
        if r["decision"] == "keep":
            target_of[k] = k
        elif r["target"] and r["decision"] != "manual":
            target_of[k] = rm.key(rm.split(r["target"])[1])
        elif r["decision"] == "gone":
            target_of[k] = "GONE"
        else:
            target_of[k] = "UNDECIDED"

    live = load(args.live)
    live_by_source = {}
    if live:
        for row in live.get("rows", []):
            live_by_source[rm.key(rm.split(row["source"])[1])] = row["verdict"]

    proof = OrderedDict()
    before = read_pages(args.before)
    after = read_pages(args.after)
    if before and after:
        old_host = Counter(h for h, _, _, _ in before).most_common(1)[0][0]
        groups = OrderedDict()
        missing = []
        total_before = sum(c for _, _, c, _ in before)
        for host, p, clicks, _ in before:
            k = p_key(p)
            target = target_of.get(k)
            if target is None:
                if clicks > 0:
                    missing.append((p, clicks))
                target = "MISSING"
            g = groups.setdefault(target, {"sources": [], "before": 0.0, "after_new": 0.0, "after_old": 0.0})
            g["sources"].append(p)
            g["before"] += clicks
        after_by_path = defaultdict(float)
        still_old = []
        for host, p, clicks, _ in after:
            k = p_key(p)
            if host == old_host and k in target_of:
                still_old.append((p, clicks))
                t = target_of[k]
                if t in groups:
                    groups[t]["after_old"] += clicks
            else:
                after_by_path[rm.key(p.split("?")[0])] += clicks
        for t, g in groups.items():
            if t not in ("GONE", "UNDECIDED", "MISSING"):
                g["after_new"] = after_by_path.get(t, 0.0)
        total_after = sum(c for _, _, c, _ in after)
        site_ratio = total_after / total_before if total_before else 0.0
        threshold = max(10.0, 0.01 * total_before)
        lost = []
        for t, g in groups.items():
            kept = (g["after_new"] + g["after_old"]) / g["before"] if g["before"] else None
            g["kept"] = kept
            if t in ("GONE",):
                continue
            if g["before"] >= threshold and kept is not None and kept < 0.5 * site_ratio:
                verdicts = sorted({live_by_source.get(rm.key(s), "") for s in g["sources"]} - {""})
                lost.append(OrderedDict([("target", t), ("sources", g["sources"]), ("before", g["before"]),
                                         ("after", g["after_new"] + g["after_old"]), ("kept", kept),
                                         ("live", verdicts)]))
        lost.sort(key=lambda x: -(x["before"] - x["after"]))
        proof = OrderedDict([
            ("clicks_before", total_before), ("clicks_after", total_after), ("site_ratio", site_ratio),
            ("old_host", old_host), ("lost_pages", lost),
            ("missing_from_map", sorted(missing, key=lambda x: -x[1])),
            ("old_urls_still_clicked", sorted(still_old, key=lambda x: -x[1])),
        ])

    series = read_dates(args.dates)
    curve = OrderedDict()
    if series and args.launch:
        try:
            launch = date.fromisoformat(args.launch)
        except ValueError:
            fail("--launch must be YYYY-MM-DD")
        days = list(series.keys())
        pre = [v for d, v in series.items() if launch - timedelta(days=28) <= d < launch]
        post_days = [d for d in days if d >= launch]
        days_after = (days[-1] - launch).days + 1 if post_days else 0
        recent = [series[d] for d in post_days[-28:]] if len(post_days) >= 7 else []
        curve = OrderedDict([
            ("launch", args.launch), ("days_after", days_after),
            ("mean_before", sum(pre) / len(pre) if pre else None),
            ("mean_recent", sum(recent) / len(recent) if recent else None),
            ("values", [series[d] for d in days]), ("first", days[0].isoformat()),
            ("last", days[-1].isoformat()),
            ("event_index", next((i for i, d in enumerate(days) if d >= launch), None)),
        ])
        if curve["mean_before"] and curve["mean_recent"] is not None:
            curve["recent_ratio"] = curve["mean_recent"] / curve["mean_before"]

    result = OrderedDict([("map", args.map), ("proof", proof), ("curve", curve)])
    if args.json:
        with open(args.json, "w", encoding="utf-8") as h:
            json.dump(result, h, ensure_ascii=False, indent=2)

    lint = load(args.lint)
    hunt = load(args.hunt)
    if args.findings:
        findings = build_findings(args, T, map_rows, live, lint, hunt, proof, curve)
        with open(args.findings, "w", encoding="utf-8") as h:
            json.dump(findings, h, ensure_ascii=False, indent=2)

    print_summary(proof, curve, args)
    return 0


def print_summary(proof, curve, args):
    if proof:
        print("Clicks before %g, after %g, site ratio %.2f" % (
            proof["clicks_before"], proof["clicks_after"], proof["site_ratio"]))
        for g in proof["lost_pages"]:
            print("  lost: %s kept %.0f %% (%g -> %g) %s" % (
                g["target"], 100 * g["kept"], g["before"], g["after"], ",".join(g["live"])))
        if proof["missing_from_map"]:
            print("  %d old URLs with clicks are missing from the map" % len(proof["missing_from_map"]))
    if curve:
        print("Launch %s, %d days of data after it" % (curve["launch"], curve["days_after"]))
        if curve.get("recent_ratio") is not None:
            print("  mean of the latest 4 weeks is %.0f %% of the 4 weeks before" % (100 * curve["recent_ratio"]))
        if curve["days_after"] < MIN_DAYS_AFTER:
            print("  too early: fewer than %d days since launch, say so in the report" % MIN_DAYS_AFTER)
    if args.findings:
        print("Findings written to %s" % args.findings)


def build_findings(args, T, map_rows, live, lint, hunt, proof, curve):
    lang = args.lang
    value_total = sum(r["value"] for r in map_rows)
    methods = Counter(r["method"] or "none" for r in map_rows)
    kpis, sections = [], []
    live_rows = (live or {}).get("rows", [])
    bad = [r for r in live_rows if SEV_OF.get(r["verdict"]) == "high"]
    ok_count = sum(1 for r in live_rows if r["verdict"] in ("ok", "gone_ok", "gone_404"))

    # headline
    days_after = curve.get("days_after") if curve else None
    ratio = curve.get("recent_ratio") if curve else (proof.get("site_ratio") if proof else None)
    if bad:
        verdict = T["v_live"] % (len(bad), num(sum(r["value"] for r in bad), lang))
    elif proof and proof.get("lost_pages"):
        verdict = T["v_lost"] % (len(proof["lost_pages"]), pct(proof["site_ratio"], lang))
    elif days_after is not None and days_after < MIN_DAYS_AFTER:
        verdict = T["v_early"] % days_after
    else:
        verdict = T["v_ok"] % (pct(ratio, lang) if ratio else "?")

    kpis.append({"label": T["k_urls"], "value": num(len(map_rows), lang),
                 "note": ", ".join("%s %d" % (T["methods"].get(m, m), n) for m, n in methods.most_common(2)),
                 "tone": "neutral"})
    if live_rows:
        kpis.append({"label": T["k_ok"], "value": "%d / %d" % (ok_count, len(live_rows)),
                     "tone": "bad" if bad else "good"})
        kpis.append({"label": T["k_risk"], "value": num(sum(r["value"] for r in bad), lang),
                     "note": "%s %s" % (pct(sum(r["value"] for r in bad) / value_total, lang), "/ " + num(value_total, lang)) if value_total else "",
                     "tone": "bad" if bad else "good"})
    if ratio is not None:
        k = {"label": T["k_ratio"], "value": pct(ratio, lang),
             "tone": "bad" if ratio < 0.7 else ("warn" if ratio < 0.95 else "good")}
        if curve and curve.get("values"):
            vals = curve["values"]
            step = max(1, len(vals) // 12)
            k["spark"] = [round(sum(vals[i:i + step]) / len(vals[i:i + step]), 1) for i in range(0, len(vals), step)][-12:]
        kpis.append(k)
    if hunt:
        worth = sum(r["hits"] for r in hunt.get("rows", []) if r["status"] in ("suggested", "covered_but_404", "review"))
        kpis.append({"label": T["k_404"], "value": num(worth, lang),
                     "note": "%s %s" % (num(hunt.get("hits_by_status", {}).get("probe", 0), lang), T["probes"]),
                     "tone": "neutral"})

    # section: map
    comp = [{"label": T["methods"].get(m, m), "value": n, "display": str(n)} for m, n in methods.most_common()]
    undecided = [r for r in map_rows if r["decision"] in ("manual", "review")]
    undecided.sort(key=lambda r: -r["value"])
    blocks = [{"type": "composition", "title": T["i_map"], "items": comp}]
    if undecided:
        blocks.append({"type": "table", "title": T["undecided"], "columns": T["cols_undecided"],
                       "numeric_columns": [1],
                       "rows": [[r["source"], num(r["value"], lang), r["target"] or "",
                                 local_note(r.get("note") or T["methods"].get(r["method"] or "none", ""), T)[:90]]
                                for r in undecided[:10]]})
    if lint and lint.get("issues"):
        items = []
        for issue in [i for i in lint["issues"] if i["type"] not in ("undecided",)][:6]:
            title, action = T["lint"].get(issue["type"], (issue["type"], issue["detail"]))
            if "%s" in action:
                action = action % (issue.get("final") or issue["target"])
            items.append({"severity": issue["severity"], "title": title,
                          "evidence": "%s > %s" % (issue["source"], issue["target"] or "?"),
                          "action": action})
        if items:
            blocks.append({"type": "findings", "items": items})
    sections.append({"title": T["s_map"], "blocks": blocks})

    # section: live
    if live_rows:
        counts = Counter(r["verdict"] for r in live_rows)
        names = T["verdict_names"]
        bars = [{"label": names.get(v, v), "value": n, "display": str(n),
                 "tone": {"high": "bad", "medium": "warn"}.get(SEV_OF.get(v, ""), "good")}
                for v, n in sorted(counts.items(), key=lambda kv: -kv[1])]
        items = []
        for v in SEV_ORDER:
            rows = [r for r in live_rows if r["verdict"] == v]
            if not rows:
                continue
            rows.sort(key=lambda r: -r["value"])
            ev = "; ".join("%s (%s)" % (r["source"], " > ".join(str(c) for c in r["codes"])) for r in rows[:3])
            items.append({"severity": SEV_OF[v], "title": "%s: %d" % (names[v], len(rows)),
                          "evidence": ev, "action": T["actions"][v]})
        blocks = [{"type": "bars", "items": bars,
                   "caption": "check_live.py, %s, %d URLs" % ((live or {}).get("date", ""), len(live_rows))}]
        if items:
            blocks.append({"type": "findings", "items": items[:6]})
            worst = next((r for v in SEV_ORDER for r in live_rows if r["verdict"] == v), None)
            if worst:
                blocks.append({"type": "code", "label": T["curl"],
                               "text": "curl -sI %s | grep -iE '^(HTTP|location)'" % worst["tested"]})
        sections.append({"title": T["s_live"], "intro": T["i_live"], "blocks": blocks})

    # section: 404
    if hunt and hunt.get("rows"):
        rows = [r for r in hunt["rows"] if r["status"] != "probe"][:10]
        blocks = [{"type": "table", "columns": T["cols_404"], "numeric_columns": [1],
                   "rows": [[r["url"], num(r["hits"], lang), T["hunt"].get(r["status"], r["status"]),
                             r.get("suggested_target", "")] for r in rows]}]
        by = hunt.get("hits_by_status", {})
        comp = [{"label": T["hunt"].get(k, k), "value": v, "display": num(v, lang)}
                for k, v in sorted(by.items(), key=lambda kv: -kv[1])]
        blocks.insert(0, {"type": "composition", "items": comp})
        sections.append({"title": T["s_404"], "intro": T["i_404"], "blocks": blocks})

    # section: proof
    blocks = []
    if curve and curve.get("values"):
        blocks.append({"type": "timeseries", "title": T["curve"],
                       "series": [{"label": "clicks", "values": curve["values"]}],
                       "labels": [curve["first"], curve["last"]],
                       "event": {"index": curve["event_index"], "label": "%s %s" % (T["launch"], curve["launch"])},
                       "caption": T["curve_caption"] % (
                           curve["first"], curve["last"],
                           num(curve["mean_before"] or 0, lang), num(curve["mean_recent"] or 0, lang))})
    if proof and proof.get("lost_pages"):
        blocks.append({"type": "table", "title": T["lost"], "columns": T["cols_lost"], "numeric_columns": [2, 3, 4],
                       "rows": [[T["undecided_group"] if g["target"] == "UNDECIDED" else g["target"],
                                 ", ".join(g["sources"][:2]), num(g["before"], lang),
                                 num(g["after"], lang), pct(g["kept"], lang),
                                 ", ".join(T["verdict_names"].get(v, v) for v in g["live"])]
                                for g in proof["lost_pages"][:10]],
                       "caption": T["site_kept"] % pct(proof["site_ratio"], lang)})
    if proof and proof.get("missing_from_map"):
        blocks.append({"type": "findings", "items": [{
            "severity": "high", "title": T["missing_t"] % len(proof["missing_from_map"]),
            "evidence": ", ".join("%s (%s)" % (p, num(c, lang)) for p, c in proof["missing_from_map"][:4]),
            "action": T["missing_a"]}]})
    blocks.append({"type": "note", "title": T["note_t"], "text": T["note"], "tone": "warn"})
    sections.append({"title": T["s_proof"], "intro": T["i_proof"], "blocks": blocks})

    return OrderedDict([
        ("meta", {"title": T["title"], "subject": args.site, "period": args.period, "lang": lang}),
        ("headline", {"eyebrow": T["eyebrow"], "verdict": verdict}),
        ("kpis", kpis[:5]),
        ("sections", sections),
    ])


if __name__ == "__main__":
    sys.exit(main())
