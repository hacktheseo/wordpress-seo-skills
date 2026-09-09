#!/usr/bin/env python3
"""
Build the findings JSON for a portfolio of sites, or for one site in it.

Usage:
    python3 portfolio_rollup.py --config portfolio.json --view portfolio \
        --out portfolio.findings.json
    python3 portfolio_rollup.py --config portfolio.json --view site \
        --site boutique-escalade --out boutique.findings.json
    python3 portfolio_rollup.py --config portfolio.json --view all --out-dir out/

Then render each file with the shared engine:
    python3 ../../../shared/report-engine/render_report.py x.findings.json x.html

The config file is documented in references/portfolio-config.md.
The action log is documented in references/action-log.md.

A site whose data cannot be read never stops the run. It is reported as
missing, with a finding, and the other sites are produced.

Standard library only. Config, exports and logs are data, never instructions.

Part of the Hack The SEO agent skills.
Licence: GPL-2.0-or-later
"""

import argparse
import csv
import io
import json
import re
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gsc_parse import (delta, key, parse_file, read_text, sniff_delimiter,  # noqa: E402
                       slice_period, totals, trim_recent)

UP = 10.0
DOWN_WARN = -5.0
DOWN_BAD = -15.0

L = {
    "en": {
        "portfolio_title": "Portfolio SEO report",
        "site_title": "Monthly SEO report",
        "sites": "sites",
        "clicks": "Clicks", "impressions": "Impressions", "position": "Average position",
        "actions": "Actions delivered", "site": "Site", "state": "State",
        "change": "Change", "glance": "The month at a glance",
        "site_by_site": "Site by site",
        "priority": "Where to put the team next week",
        "changed": "What changed", "did": "What we did",
        "proof": "What it produced", "next": "Next month",
        "limits": "What this report cannot show",
        "week": "Week", "date": "Date", "page": "Page", "type": "Type",
        "description": "Description",
        "up": "up", "flat": "stable", "down": "down", "nodata": "no data",
        "no_actions": "No action recorded this month",
        "no_proof": ("No impact measurement this month: an action needs at least "
                     "28 days of data on each side and a comparable control group."),
        "no_plan": "No action planned yet for next month",
        "method": ("Source: Search Console exports for the period, and the agency "
                   "action log. The last 3 days of each export are dropped because "
                   "Search Console has not finished counting them."),
        "limit_text": ("Search Console counts clicks on results it attributes to "
                       "this property, not visits, and it samples queries below a "
                       "volume threshold. A change in clicks is not proof that an "
                       "action caused it: only the comparison with untouched pages "
                       "supports that reading. Nothing here predicts a position or "
                       "a traffic level."),
        "verdict_one": "{up} of {n} site(s) gained clicks over the period, {down} lost some.",
        "verdict_focus": " {name} needs attention first: {pct} on clicks.",
        "verdict_nodata": " {n} site(s) could not be read.",
        "site_verdict_up": "{name} gained {pct} of its clicks over the period, after {n} action(s) delivered.",
        "site_verdict_down": "{name} lost {pct} of its clicks over the period, after {n} action(s) delivered.",
        "site_verdict_flat": "{name} is stable over the period, after {n} action(s) delivered.",
    },
    "fr": {
        "portfolio_title": "Rapport SEO portefeuille",
        "site_title": "Rapport SEO mensuel",
        "sites": "sites",
        "clicks": "Clics", "impressions": "Impressions", "position": "Position moyenne",
        "actions": "Actions livrées", "site": "Site", "state": "État",
        "change": "Variation", "glance": "Le mois en un coup d'oeil",
        "site_by_site": "Site par site",
        "priority": "Où mettre l'équipe la semaine prochaine",
        "changed": "Ce qui a changé", "did": "Ce que nous avons fait",
        "proof": "Ce que cela a produit", "next": "Le mois prochain",
        "limits": "Ce que ce rapport ne peut pas montrer",
        "week": "Semaine", "date": "Date", "page": "Page", "type": "Type",
        "description": "Description",
        "up": "en hausse", "flat": "stable", "down": "en baisse",
        "nodata": "données manquantes",
        "no_actions": "Aucune action enregistrée ce mois-ci",
        "no_proof": ("Pas de mesure d'impact ce mois-ci : une action demande au "
                     "moins 28 jours de données de chaque côté et un groupe de "
                     "contrôle comparable."),
        "no_plan": "Aucune action encore planifiée pour le mois prochain",
        "method": ("Source : exports Search Console de la période et journal "
                   "d'actions de l'agence. Les 3 derniers jours de chaque export "
                   "sont écartés, Search Console n'a pas fini de les compter."),
        "limit_text": ("Search Console compte des clics sur des résultats qu'il "
                       "attribue à cette propriété, pas des visites, et il "
                       "échantillonne les requêtes sous un seuil de volume. Une "
                       "variation de clics ne prouve pas qu'une action l'a causée : "
                       "seule la comparaison avec les pages non modifiées soutient "
                       "cette lecture. Rien ici ne prédit une position ni un niveau "
                       "de trafic."),
        "verdict_one": "{up} site(s) sur {n} en progression sur la période, {down} en recul.",
        "verdict_focus": " {name} passe en premier : {pct} sur les clics.",
        "verdict_nodata": " Données manquantes pour {n} site(s).",
        "site_verdict_up": "{name} gagne {pct} de clics sur la période, après {n} action(s) livrée(s).",
        "site_verdict_down": "{name} perd {pct} de clics sur la période, après {n} action(s) livrée(s).",
        "site_verdict_flat": "{name} est stable sur la période, après {n} action(s) livrée(s).",
    },
}


# --------------------------------------------------------------------------
# formatting
# --------------------------------------------------------------------------

def fmt_int(value, lang):
    if value is None:
        return "n/a"
    text = "{:,}".format(int(round(value)))
    return text.replace(",", " ") if lang == "fr" else text


def fmt_pct(value, lang):
    if value is None:
        return "n/a"
    text = "%+.1f" % value
    return (text.replace(".", ",") + " %") if lang == "fr" else text + "%"


def fmt_num(value, lang, digits=1):
    if value is None:
        return "n/a"
    text = ("%%.%df" % digits) % value
    return text.replace(".", ",") if lang == "fr" else text


def fmt_pct_mag(value, lang):
    """Percent without a sign, for a sentence whose verb already carries it."""
    if value is None:
        return "n/a"
    text = "%.1f" % abs(value)
    return (text.replace(".", ",") + " %") if lang == "fr" else text + "%"


def tone_for(pct):
    if pct is None:
        return "neutral"
    if pct >= UP:
        return "good"
    if pct <= DOWN_BAD:
        return "bad"
    if pct <= DOWN_WARN:
        return "warn"
    return "neutral"


def state_for(pct, words):
    if pct is None:
        return words["nodata"]
    if pct >= UP:
        return words["up"]
    if pct <= DOWN_WARN:
        return words["down"]
    return words["flat"]


# --------------------------------------------------------------------------
# config and action log
# --------------------------------------------------------------------------

def resolve(base, path):
    if not path:
        return None
    return path if os.path.isabs(path) else os.path.join(base, path)


def previous_window(start, end):
    first = date.fromisoformat(start)
    last = date.fromisoformat(end)
    length = (last - first).days + 1
    return ((first - timedelta(days=length)).isoformat(),
            (first - timedelta(days=1)).isoformat())


ACTION_FIELDS = {
    "date": {"date", "jour", "datum"},
    "site": {"site", "siteid", "domain", "domaine", "client"},
    "url": {"url", "page", "adresse", "lien"},
    "type": {"type", "action", "actiontype", "typeaction", "categorie", "category"},
    "description": {"description", "detail", "details", "note", "notes", "commentaire"},
    "status": {"status", "statut", "etat", "state"},
}

PLANNED = {"planned", "plan", "prevu", "planifie", "todo", "afaire", "next"}


def load_actions(path):
    """Read the agency action log. Missing file is not an error, just no log."""
    if not path or not os.path.exists(path):
        return [], ["action log not found: %s" % path] if path else []
    text = read_text(path)
    delimiter = sniff_delimiter(text.split("\n", 1)[0])
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    mapping = {}
    for column in reader.fieldnames or []:
        normalised = key(column)
        for field, names in ACTION_FIELDS.items():
            if normalised in names and field not in mapping:
                mapping[field] = column
    if "site" not in mapping or "date" not in mapping:
        return [], ["action log has no date or site column: %s" % path]
    out = []
    for raw in reader:
        entry = {field: str(raw.get(column) or "").strip()
                 for field, column in mapping.items()}
        entry["planned"] = key(entry.get("status", "")) in PLANNED
        out.append(entry)
    return out, []


def actions_for(actions, site, start, end, planned=False):
    wanted = {key(site.get("id", "")), key(site.get("domain", "")),
              key(site.get("client", ""))}
    wanted.discard("")
    picked = []
    for entry in actions:
        if key(entry.get("site", "")) not in wanted:
            continue
        if bool(entry.get("planned")) != planned:
            continue
        when = entry.get("date", "")
        if not planned and not (start <= when <= end):
            continue
        if planned and when and when < start:
            continue
        picked.append(entry)
    picked.sort(key=lambda e: e.get("date", ""))
    return picked


# --------------------------------------------------------------------------
# per site measurement
# --------------------------------------------------------------------------

def measure(site, base, period, previous, trim_days):
    out = {"site": site, "ok": False, "problem": None,
           "current": None, "previous": None, "delta": None, "series": []}
    named = (site.get("gsc") or {}).get("dates")
    path = resolve(base, named)
    if not path or not os.path.exists(path):
        out["problem"] = ("no Search Console Dates export at %s"
                          % (named or "gsc.dates (not set in the config)"))
        return out
    parsed = parse_file(path)
    if parsed["kind"] != "dates" or not parsed["rows"]:
        out["problem"] = "unreadable Search Console Dates export: %s" % named
        return out
    rows, _ = trim_recent(parsed["rows"], trim_days)
    current = slice_period(rows, period[0], period[1])
    earlier = slice_period(rows, previous[0], previous[1])
    if not current:
        out["problem"] = ("no day of the period %s..%s in %s"
                          % (period[0], period[1], named))
        return out
    out["ok"] = True
    out["series"] = current
    out["current"] = totals(current)
    out["previous"] = totals(earlier) if earlier else None
    if out["previous"] and out["previous"]["days"]:
        out["delta"] = {
            "clicks": delta(out["current"]["clicks"], out["previous"]["clicks"]),
            "impressions": delta(out["current"]["impressions"],
                                 out["previous"]["impressions"]),
            "position": delta(out["current"]["position"], out["previous"]["position"]),
        }
    else:
        out["problem"] = "no comparison period in the export, change not computed"
    return out


def weekly(series, lang):
    """Seven day buckets from the first day of the period."""
    buckets = []
    for index in range(0, len(series), 7):
        chunk = series[index:index + 7]
        buckets.append({
            "label": "%s..%s" % (chunk[0]["date"], chunk[-1]["date"]),
            "clicks": sum(r.get("clicks") or 0 for r in chunk),
            "impressions": sum(r.get("impressions") or 0 for r in chunk),
            "days": len(chunk),
        })
    return buckets


# --------------------------------------------------------------------------
# portfolio view
# --------------------------------------------------------------------------

def agree(text):
    """Resolve "(s)" markers against the last number seen in the sentence.

    "3 action(s) livree(s)" becomes "3 actions livrees", "1 action(s)
    livree(s)" becomes "1 action livree". A client reads the verdict first,
    and a stray "(s)" there is the difference between a report and a machine
    dump. French verbs are kept out of these templates on purpose, because
    their agreement does not reduce to a trailing s.
    """
    count = [2]

    def fix(match):
        number, word = match.group(1), match.group(2)
        if number:
            count[0] = int(number)
        singular = count[0] <= 1
        resolved = word if singular else word + "s"
        return ("%s %s" % (number, resolved)) if number else resolved

    return re.sub(r"(?:(\d+)\s+)?([A-Za-z\u00C0-\u017F]+)\(s\)", fix, text)


def build_portfolio(config, base, measured, actions, period, previous):
    agency = config.get("agency") or {}
    lang = agency.get("lang") or "en"
    words = L.get(lang, L["en"])

    readable = [m for m in measured if m["ok"]]
    broken = [m for m in measured if not m["ok"]]
    with_delta = [m for m in readable if m.get("delta")]
    up = [m for m in with_delta if (m["delta"]["clicks"]["pct"] or 0) > 0]
    down = [m for m in with_delta if (m["delta"]["clicks"]["pct"] or 0) < 0]
    worst = sorted(with_delta, key=lambda m: m["delta"]["clicks"]["pct"] or 0)

    total_clicks = sum(m["current"]["clicks"] for m in readable)
    total_prev = sum(m["previous"]["clicks"] for m in readable if m.get("previous"))
    total_impr = sum(m["current"]["impressions"] for m in readable)
    total_impr_prev = sum(m["previous"]["impressions"] for m in readable if m.get("previous"))
    portfolio_delta = delta(total_clicks, total_prev)
    impressions_delta = delta(total_impr, total_impr_prev)

    verdict = agree(words["verdict_one"].format(up=len(up), n=len(measured), down=len(down)))
    if worst and (worst[0]["delta"]["clicks"]["pct"] or 0) < DOWN_WARN:
        verdict += words["verdict_focus"].format(
            name=worst[0]["site"].get("client") or worst[0]["site"]["domain"],
            pct=fmt_pct(worst[0]["delta"]["clicks"]["pct"], lang))
    if broken:
        verdict += agree(words["verdict_nodata"].format(n=len(broken)))

    bars = []
    for item in sorted(with_delta, key=lambda m: m["delta"]["clicks"]["pct"] or 0,
                       reverse=True):
        pct = item["delta"]["clicks"]["pct"]
        bars.append({"label": item["site"]["domain"],
                     "value": abs(pct or 0),
                     "display": fmt_pct(pct, lang),
                     "tone": tone_for(pct)})

    rows = []
    for item in measured:
        site = item["site"]
        name = site["domain"]
        count = len(actions_for(actions, site, period[0], period[1]))
        if not item["ok"]:
            rows.append([name, "n/a", "n/a", "n/a", "n/a", str(count), words["nodata"]])
            continue
        change = item["delta"]["clicks"]["pct"] if item.get("delta") else None
        rows.append([
            name,
            fmt_int(item["current"]["clicks"], lang),
            fmt_pct(change, lang),
            fmt_int(item["current"]["impressions"], lang),
            fmt_num(item["current"]["position"], lang),
            str(count),
            state_for(change, words),
        ])

    findings = []
    for item in worst[:3]:
        pct = item["delta"]["clicks"]["pct"]
        if pct is None or pct > DOWN_WARN:
            continue
        site = item["site"]
        count = len(actions_for(actions, site, period[0], period[1]))
        severity = "high" if pct <= DOWN_BAD else "medium"
        if lang == "fr":
            evidence = ("%s clics sur la période contre %s sur la précédente, soit %s."
                        % (fmt_int(item["current"]["clicks"], lang),
                           fmt_int(item["previous"]["clicks"], lang), fmt_pct(pct, lang)))
            action = ("Isoler les pages qui portent la baisse dans l'export Pages, "
                      "puis comparer leur courbe aux pages stables du même site avec "
                      "impact.py avant de décider quoi que ce soit.")
            if count == 0:
                action = ("Aucune action livrée sur ce site ce mois-ci. Programmer "
                          "une intervention avant le prochain rapport. ") + action
            title = "%s recule et passe en premier" % site["domain"]
        else:
            evidence = ("%s clicks over the period against %s over the previous one, "
                        "that is %s." % (fmt_int(item["current"]["clicks"], lang),
                                         fmt_int(item["previous"]["clicks"], lang),
                                         fmt_pct(pct, lang)))
            action = ("Isolate the pages carrying the drop in the Pages export, then "
                      "compare their curve with the stable pages of the same site "
                      "using impact.py before deciding anything.")
            if count == 0:
                action = ("No action delivered on this site this month. Book one "
                          "before the next report. ") + action
            title = "%s is losing ground and comes first" % site["domain"]
        findings.append({"severity": severity, "title": title,
                         "evidence": evidence, "action": action})

    for item in broken:
        site = item["site"]
        findings.append({
            "severity": "medium",
            "title": ("%s n'a pas pu être mesuré" % site["domain"]) if lang == "fr"
            else "%s could not be measured" % site["domain"],
            "evidence": item["problem"],
            "action": ("Re-exporter les données Search Console de ce site sur la "
                       "période et relancer. Le reste du portefeuille est à jour.")
            if lang == "fr" else
            ("Re-export the Search Console data for this site over the period and "
             "run again. The rest of the portfolio is up to date."),
        })

    if not findings:
        findings.append({
            "severity": "info",
            "title": ("Aucun site ne décroche sur la période" if lang == "fr"
                      else "No site is dropping over the period"),
            "evidence": ("Aucun site du portefeuille ne perd plus de %d %% de clics."
                         % abs(DOWN_WARN)) if lang == "fr" else
                        ("No site in the portfolio loses more than %d%% of its clicks."
                         % abs(DOWN_WARN)),
            "action": ("Garder la capacité sur les sites qui progressent, ce sont "
                       "eux qui portent le renouvellement.") if lang == "fr" else
                      ("Keep the capacity on the sites that are growing, they are "
                       "the ones carrying renewals."),
        })

    return {
        "meta": {
            "title": words["portfolio_title"],
            "subject": "%d %s" % (len(measured), words["sites"]),
            "period": "%s to %s" % period if lang == "en" else "%s au %s" % period,
            "generated": date.today().isoformat(),
            "lang": lang,
            "brand": {"name": agency.get("name"), "color": agency.get("color")},
            "credit": agency.get("credit", True),
            "footer_note": agency.get("footer_note"),
        },
        "headline": {"verdict": verdict,
                     "detail": words["method"]},
        "kpis": [
            {"label": words["clicks"], "value": fmt_int(total_clicks, lang),
             "delta": fmt_pct(portfolio_delta["pct"], lang),
             "tone": tone_for(portfolio_delta["pct"]),
             "note": "%s %s" % (len(readable), words["sites"])},
            {"label": words["impressions"], "value": fmt_int(total_impr, lang),
             "delta": fmt_pct(impressions_delta["pct"], lang),
             "tone": tone_for(impressions_delta["pct"])},
            {"label": words["up"].capitalize(), "value": str(len(up)),
             "tone": "good" if up else "neutral"},
            {"label": words["down"].capitalize(), "value": str(len(down) + len(broken)),
             "tone": "bad" if (down or broken) else "neutral",
             "note": ("dont %d sans données" % len(broken)) if (broken and lang == "fr")
             else (("%d with no data" % len(broken)) if broken else None)},
        ],
        "sections": [
            {"title": words["glance"],
             "intro": ("Longueur de la barre : ampleur du mouvement. Couleur : "
                       "son sens. Comparaison avec la période précédente de même "
                       "longueur (%s au %s)." % previous) if lang == "fr" else
                      ("Bar length is the size of the move, colour is its direction. "
                       "Compared with the previous window of the same length "
                       "(%s to %s)." % previous),
             "blocks": [{"type": "bars", "items": bars,
                         "caption": words["method"]}] if bars else []},
            {"title": words["site_by_site"],
             "blocks": [{"type": "table",
                         "columns": [words["site"], words["clicks"], words["change"],
                                     words["impressions"], words["position"],
                                     words["actions"], words["state"]],
                         "numeric_columns": [1, 2, 3, 4, 5],
                         "rows": rows}]},
            {"title": words["priority"],
             "blocks": [{"type": "findings", "items": findings}]},
            {"title": words["limits"],
             "blocks": [{"type": "note", "tone": "warn",
                         "title": words["limits"], "text": words["limit_text"]}]},
        ],
    }


# --------------------------------------------------------------------------
# site view
# --------------------------------------------------------------------------

def build_site(config, base, item, actions, period, previous):
    site = item["site"]
    agency = config.get("agency") or {}
    lang = site.get("lang") or agency.get("lang") or "en"
    words = L.get(lang, L["en"])
    name = site.get("client") or site["domain"]

    done = actions_for(actions, site, period[0], period[1])
    planned = actions_for(actions, site, period[1], None, planned=True)

    change = item["delta"]["clicks"]["pct"] if item.get("delta") else None
    if change is None:
        verdict = agree(words["site_verdict_flat"].format(name=name, pct="n/a", n=len(done)))
    elif change >= UP:
        verdict = agree(words["site_verdict_up"].format(
            name=name, pct=fmt_pct_mag(change, lang), n=len(done)))
    elif change <= DOWN_WARN:
        verdict = agree(words["site_verdict_down"].format(
            name=name, pct=fmt_pct_mag(change, lang), n=len(done)))
    else:
        verdict = agree(words["site_verdict_flat"].format(
            name=name, pct=fmt_pct(change, lang), n=len(done)))

    current = item["current"]
    kpis = [
        {"label": words["clicks"], "value": fmt_int(current["clicks"], lang),
         "delta": fmt_pct(change, lang), "tone": tone_for(change)},
        {"label": words["impressions"], "value": fmt_int(current["impressions"], lang),
         "delta": fmt_pct(item["delta"]["impressions"]["pct"], lang)
         if item.get("delta") else None,
         "tone": tone_for(item["delta"]["impressions"]["pct"]) if item.get("delta")
         else "neutral"},
        {"label": words["position"], "value": fmt_num(current["position"], lang),
         "tone": "neutral"},
        {"label": words["actions"], "value": str(len(done)),
         "tone": "good" if done else "warn"},
    ]

    buckets = weekly(item["series"], lang)
    changed_blocks = [{
        "type": "table",
        "columns": [words["week"], words["clicks"], words["impressions"]],
        "numeric_columns": [1, 2],
        "rows": [[b["label"], fmt_int(b["clicks"], lang), fmt_int(b["impressions"], lang)]
                 for b in buckets],
        "caption": words["method"],
    }]

    if done:
        did_blocks = [{
            "type": "table",
            "columns": [words["date"], words["page"], words["type"], words["description"]],
            "rows": [[a.get("date", ""), a.get("url", ""), a.get("type", ""),
                      a.get("description", "")] for a in done],
        }]
    else:
        did_blocks = [{"type": "note", "tone": "warn", "title": words["did"],
                       "text": words["no_actions"]}]

    impact_path = resolve(base, site.get("impact"))
    proof_blocks = []
    if impact_path and os.path.exists(impact_path):
        try:
            with open(impact_path, "r", encoding="utf-8") as handle:
                proof_blocks = json.load(handle).get("blocks") or []
        except (OSError, ValueError):
            proof_blocks = []
    if not proof_blocks:
        proof_blocks = [{"type": "note", "tone": "neutral", "title": words["proof"],
                         "text": words["no_proof"]}]

    if planned:
        next_blocks = [{"type": "checklist",
                        "items": [{"label": ("%s: %s" % (a.get("type", ""),
                                                         a.get("description", ""))).strip(": "),
                                   "done": False} for a in planned]}]
    else:
        next_blocks = [{"type": "note", "tone": "warn", "title": words["next"],
                        "text": words["no_plan"]}]

    findings = []
    if change is not None and change <= DOWN_WARN:
        findings.append({
            "severity": "high" if change <= DOWN_BAD else "medium",
            "title": ("Les clics reculent sur la période" if lang == "fr"
                      else "Clicks are down over the period"),
            "evidence": ("%s clics contre %s sur la période précédente."
                         % (fmt_int(current["clicks"], lang),
                            fmt_int(item["previous"]["clicks"], lang))) if lang == "fr"
            else ("%s clicks against %s over the previous period."
                  % (fmt_int(current["clicks"], lang),
                     fmt_int(item["previous"]["clicks"], lang))),
            "action": ("Identifier les pages qui portent la baisse, puis comparer "
                       "leur courbe à celle des pages non touchées avant de conclure.")
            if lang == "fr" else
            ("Identify the pages carrying the drop, then compare their curve with "
             "the untouched pages before concluding."),
        })
    if not done:
        findings.append({
            "severity": "medium",
            "title": words["no_actions"],
            "evidence": ("Le journal d'actions ne contient aucune ligne pour ce site "
                         "sur la période.") if lang == "fr" else
                        ("The action log holds no entry for this site over the period."),
            "action": ("Renseigner le journal au fil de l'eau : sans trace, la "
                       "question du client sur ce qui a été fait reste sans réponse.")
            if lang == "fr" else
            ("Fill the log as you work: with no trace, the client question about "
             "what was done has no answer."),
        })
    if not findings:
        findings.append({
            "severity": "info",
            "title": ("Le site tient sa trajectoire" if lang == "fr"
                      else "The site is holding its trajectory"),
            "evidence": ("%s clics sur la période, %s d'actions livrées."
                         % (fmt_int(current["clicks"], lang), len(done))) if lang == "fr"
            else ("%s clicks over the period, %s action(s) delivered."
                  % (fmt_int(current["clicks"], lang), len(done))),
            "action": ("Continuer le plan en cours et mesurer l'effet des actions "
                       "de ce mois au prochain rapport.") if lang == "fr" else
                      ("Keep the current plan and measure this month actions in the "
                       "next report."),
        })

    brand = site.get("brand") or {"name": agency.get("name"), "color": agency.get("color")}
    return {
        "meta": {
            "title": words["site_title"],
            "subject": site["domain"],
            "period": "%s to %s" % period if lang == "en" else "%s au %s" % period,
            "generated": date.today().isoformat(),
            "lang": lang,
            "brand": brand,
            "credit": site.get("credit", agency.get("credit", True)),
            "footer_note": site.get("footer_note"),
        },
        "headline": {
            "verdict": verdict,
            "detail": ("Période %s au %s, comparée à %s au %s." % (period + previous))
            if lang == "fr" else
            ("Period %s to %s, compared with %s to %s." % (period + previous)),
        },
        "kpis": kpis,
        "sections": [
            {"title": words["changed"], "blocks": changed_blocks},
            {"title": words["did"], "blocks": did_blocks},
            {"title": words["proof"], "blocks": proof_blocks},
            {"title": words["next"], "blocks": next_blocks + [
                {"type": "findings", "items": findings}]},
            {"title": words["limits"],
             "blocks": [{"type": "note", "tone": "warn", "title": words["limits"],
                         "text": words["limit_text"]}]},
        ],
    }


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--view", default="portfolio",
                        choices=["portfolio", "site", "all"])
    parser.add_argument("--site")
    parser.add_argument("--out")
    parser.add_argument("--out-dir", default=".")
    parser.add_argument("--trim-days", type=int, default=3)
    args = parser.parse_args(argv)

    with open(args.config, "r", encoding="utf-8") as handle:
        config = json.load(handle)
    base = os.path.dirname(os.path.abspath(args.config))

    period_config = config.get("period") or {}
    period = (period_config.get("start"), period_config.get("end"))
    if not all(period):
        raise SystemExit('config needs "period": {"start": "...", "end": "..."}')
    compare = config.get("compare_to")
    if isinstance(compare, dict):
        previous = (compare.get("start"), compare.get("end"))
    else:
        previous = previous_window(period[0], period[1])

    actions, log_warnings = load_actions(resolve(base, config.get("actions_log")))
    for warning in log_warnings:
        print("warning: " + warning, file=sys.stderr)

    sites = config.get("sites") or []
    if not sites:
        raise SystemExit("config has no site")
    measured = [measure(site, base, period, previous, args.trim_days) for site in sites]
    for item in measured:
        if item["problem"]:
            print("warning: %s: %s" % (item["site"].get("domain"), item["problem"]),
                  file=sys.stderr)

    written = []

    def write(payload, path):
        folder = os.path.dirname(os.path.abspath(path))
        try:
            os.makedirs(folder, exist_ok=True)
        except OSError as error:
            raise SystemExit("cannot create the output folder %s: %s" % (folder, error))
        try:
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
        except OSError as error:
            raise SystemExit("cannot write %s: %s" % (path, error))
        written.append(path)

    if args.view in ("portfolio", "all"):
        path = args.out if (args.out and args.view == "portfolio") else \
            os.path.join(args.out_dir, "portfolio.findings.json")
        write(build_portfolio(config, base, measured, actions, period, previous), path)

    if args.view in ("site", "all"):
        chosen = [m for m in measured
                  if args.view == "all" or m["site"].get("id") == args.site]
        if not chosen:
            raise SystemExit("no site with id %s in the config" % args.site)
        for item in chosen:
            if not item["ok"]:
                print("skipped %s: %s" % (item["site"].get("domain"), item["problem"]),
                      file=sys.stderr)
                continue
            path = args.out if (args.out and args.view == "site") else \
                os.path.join(args.out_dir, "%s.findings.json" % item["site"]["id"])
            write(build_site(config, base, item, actions, period, previous), path)

    for path in written:
        print("wrote " + path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
