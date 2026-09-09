#!/usr/bin/env python3
"""
Compute GEO presence metrics from a manual survey CSV, and compare two surveys.

Usage:
    python3 geo_measure.py survey.csv --domain example.com
    python3 geo_measure.py baseline.csv followup.csv --domain example.com
    python3 geo_measure.py survey.csv --domain example.com --json metrics.json

Input is a CSV recorded by hand while running a frozen prompt set against AI
answer engines. One row per observation, meaning one prompt run once on one
engine. Required columns:

    prompt_id, family, engine, run, cited

Optional columns:

    prompt, date, position, sentiment, cited_url, note

    cited      1 / 0, yes / no, oui / non, true / false
    position   first / passing / footnote / none
    sentiment  positive / neutral / negative / none
    cited_url  the URL the engine actually pointed to, third party included

The script never fetches anything. It reads the CSV you give it and nothing
else. Every figure it prints is a count taken from that file.

Standard library only. Part of the Hack The SEO agent skills.
Licence: GPL-2.0-or-later
"""

import argparse
import csv
import json
import math
import sys
from collections import Counter, OrderedDict

REQUIRED = ("prompt_id", "family", "engine", "run", "cited")
TRUE_WORDS = {"1", "y", "yes", "true", "oui", "vrai", "o"}
FALSE_WORDS = {"0", "n", "no", "false", "non", "faux", ""}
POSITIONS = ("first", "passing", "footnote", "none")
SENTIMENTS = ("positive", "neutral", "negative", "none")
Z95 = 1.959963985


# ---------------------------------------------------------------------------
# statistics, kept deliberately small and readable
# ---------------------------------------------------------------------------

def wilson(successes, total, z=Z95):
    """95 % Wilson score interval for a proportion. Returns (low, high)."""
    if total <= 0:
        return (0.0, 0.0)
    phat = successes / total
    denom = 1.0 + (z * z) / total
    centre = phat + (z * z) / (2 * total)
    margin = z * math.sqrt((phat * (1 - phat) + (z * z) / (4 * total)) / total)
    return (max(0.0, (centre - margin) / denom), min(1.0, (centre + margin) / denom))


def two_proportion_z(s1, n1, s2, n2):
    """Pooled two proportion z statistic. Returns (z, p_value) or (None, None)."""
    if n1 <= 0 or n2 <= 0:
        return (None, None)
    p1, p2 = s1 / n1, s2 / n2
    pooled = (s1 + s2) / (n1 + n2)
    se = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    if se == 0:
        return (0.0, 1.0)
    z = (p2 - p1) / se
    p_value = math.erfc(abs(z) / math.sqrt(2))
    return (z, p_value)


def noise_floor(n1, n2=None, rate=0.5):
    """
    Smallest difference in presence rate that could reach significance with
    these sample sizes. Uses rate 0.5 by default, the least favourable case,
    so the number printed is a floor and not an optimistic estimate.
    """
    n2 = n1 if n2 is None else n2
    if n1 <= 0 or n2 <= 0:
        return 1.0
    se = math.sqrt(rate * (1 - rate) * (1 / n1 + 1 / n2))
    return min(1.0, Z95 * se)


# ---------------------------------------------------------------------------
# reading
# ---------------------------------------------------------------------------

def to_bool(value):
    text = (value or "").strip().lower()
    if text in TRUE_WORDS:
        return True
    if text in FALSE_WORDS:
        return False
    raise ValueError("value %r is not a yes or a no" % value)


def read_survey(path):
    """Read one survey CSV into a list of dicts. Exits on a malformed file."""
    rows = []
    try:
        handle = open(path, newline="", encoding="utf-8-sig")
    except OSError as error:
        sys.exit("cannot open %s: %s" % (path, error))
    with handle:
        reader = csv.DictReader(handle)
        headers = [h.strip() for h in (reader.fieldnames or [])]
        missing = [c for c in REQUIRED if c not in headers]
        if missing:
            sys.exit(
                "%s is missing required column(s): %s\nexpected at least: %s"
                % (path, ", ".join(missing), ", ".join(REQUIRED))
            )
        for number, raw in enumerate(reader, start=2):
            clean = {(k or "").strip(): (v or "").strip() for k, v in raw.items()}
            if not clean.get("prompt_id"):
                continue
            try:
                cited = to_bool(clean.get("cited"))
            except ValueError as error:
                sys.exit("%s line %d: column cited, %s" % (path, number, error))
            position = (clean.get("position") or "").lower() or ("none" if not cited else "")
            if position and position not in POSITIONS:
                sys.exit(
                    "%s line %d: position %r is not one of %s"
                    % (path, number, position, "/".join(POSITIONS))
                )
            sentiment = (clean.get("sentiment") or "").lower() or "none"
            if sentiment not in SENTIMENTS:
                sys.exit(
                    "%s line %d: sentiment %r is not one of %s"
                    % (path, number, sentiment, "/".join(SENTIMENTS))
                )
            rows.append(
                {
                    "prompt_id": clean["prompt_id"],
                    "family": clean.get("family") or "unclassified",
                    "engine": clean.get("engine") or "unknown",
                    "run": clean.get("run") or "1",
                    "cited": cited,
                    "position": position or "none",
                    "sentiment": sentiment,
                    "cited_url": clean.get("cited_url") or "",
                    "date": clean.get("date") or "",
                    "prompt": clean.get("prompt") or "",
                }
            )
    if not rows:
        sys.exit("%s contains no usable row" % path)
    return rows


# ---------------------------------------------------------------------------
# aggregation
# ---------------------------------------------------------------------------

def group_rate(rows, key):
    """Presence rate per value of key, ordered by descending observation count."""
    buckets = OrderedDict()
    for row in rows:
        bucket = buckets.setdefault(row[key], {"n": 0, "cited": 0})
        bucket["n"] += 1
        bucket["cited"] += 1 if row["cited"] else 0
    out = OrderedDict()
    for name in sorted(buckets, key=lambda k: (-buckets[k]["n"], k)):
        bucket = buckets[name]
        low, high = wilson(bucket["cited"], bucket["n"])
        out[name] = {
            "observations": bucket["n"],
            "cited": bucket["cited"],
            "rate": bucket["cited"] / bucket["n"],
            "ci_low": low,
            "ci_high": high,
        }
    return out


def repetitions(rows):
    """Observation count per prompt and engine pair, to expose thin sampling."""
    counts = Counter((row["prompt_id"], row["engine"]) for row in rows)
    values = sorted(counts.values())
    return {
        "min": values[0],
        "max": values[-1],
        "median": values[len(values) // 2],
        "pairs": len(values),
    }


def url_split(rows, domain):
    """Count the URLs actually cited, split between own domain and third party."""
    own, third, counter = 0, 0, Counter()
    for row in rows:
        url = row["cited_url"]
        if not row["cited"] or not url:
            continue
        counter[url] += 1
        if domain and domain.lower() in url.lower():
            own += 1
        else:
            third += 1
    return {"own": own, "third_party": third, "top": counter.most_common(10)}


def analyse(rows, domain):
    cited = sum(1 for row in rows if row["cited"])
    low, high = wilson(cited, len(rows))
    reps = repetitions(rows)
    return {
        "observations": len(rows),
        "prompts": len({row["prompt_id"] for row in rows}),
        "families": len({row["family"] for row in rows}),
        "engines": sorted({row["engine"] for row in rows}),
        "dates": sorted({row["date"] for row in rows if row["date"]}),
        "cited": cited,
        "rate": cited / len(rows),
        "ci_low": low,
        "ci_high": high,
        "repetitions": reps,
        "by_family": group_rate(rows, "family"),
        "by_engine": group_rate(rows, "engine"),
        "positions": Counter(row["position"] for row in rows if row["cited"]),
        "sentiments": Counter(row["sentiment"] for row in rows if row["cited"]),
        "urls": url_split(rows, domain),
        "noise_floor": noise_floor(len(rows)),
    }


def compare(before, after):
    """Family by family and overall comparison, with a signal or noise verdict."""
    out = OrderedDict()
    names = list(before["by_family"].keys())
    names += [n for n in after["by_family"] if n not in names]
    for name in names:
        b = before["by_family"].get(name, {"observations": 0, "cited": 0, "rate": 0.0})
        a = after["by_family"].get(name, {"observations": 0, "cited": 0, "rate": 0.0})
        z, p_value = two_proportion_z(
            b["cited"], b["observations"], a["cited"], a["observations"]
        )
        floor = noise_floor(b["observations"], a["observations"])
        out[name] = {
            "before_rate": b["rate"],
            "after_rate": a["rate"],
            "delta": a["rate"] - b["rate"],
            "before_n": b["observations"],
            "after_n": a["observations"],
            "z": z,
            "p_value": p_value,
            "noise_floor": floor,
            "significant": bool(p_value is not None and p_value < 0.05),
        }
    z, p_value = two_proportion_z(
        before["cited"], before["observations"], after["cited"], after["observations"]
    )
    out["__overall__"] = {
        "before_rate": before["rate"],
        "after_rate": after["rate"],
        "delta": after["rate"] - before["rate"],
        "before_n": before["observations"],
        "after_n": after["observations"],
        "z": z,
        "p_value": p_value,
        "noise_floor": noise_floor(before["observations"], after["observations"]),
        "significant": bool(p_value is not None and p_value < 0.05),
    }
    return out


# ---------------------------------------------------------------------------
# printing
# ---------------------------------------------------------------------------

def percent(value):
    return "%5.1f %%" % (value * 100)


def line(char="-", width=72):
    return char * width


def print_survey(name, data):
    reps = data["repetitions"]
    print(line("="))
    print("SURVEY %s" % name)
    print(line("="))
    print(
        "observations %d, prompts %d, families %d, engines %s"
        % (data["observations"], data["prompts"], data["families"], ", ".join(data["engines"]))
    )
    if data["dates"]:
        print("dates recorded: %s" % ", ".join(data["dates"][:5]))
    print(
        "repetitions per prompt and engine: min %d, median %d, max %d"
        % (reps["min"], reps["median"], reps["max"])
    )
    print(
        "overall presence %s  (%d / %d, 95 %% interval %s to %s)"
        % (
            percent(data["rate"]),
            data["cited"],
            data["observations"],
            percent(data["ci_low"]),
            percent(data["ci_high"]),
        )
    )
    print()
    print("PRESENCE BY PROMPT FAMILY")
    print("%-28s %6s %6s %9s   %s" % ("family", "obs", "cited", "presence", "95 % interval"))
    for name, row in data["by_family"].items():
        print(
            "%-28s %6d %6d %9s   %s to %s"
            % (
                name[:28],
                row["observations"],
                row["cited"],
                percent(row["rate"]),
                percent(row["ci_low"]),
                percent(row["ci_high"]),
            )
        )
    print()
    print("PRESENCE BY ENGINE")
    for name, row in data["by_engine"].items():
        print(
            "%-28s %6d %6d %9s"
            % (name[:28], row["observations"], row["cited"], percent(row["rate"]))
        )
    print()
    print("POSITION IN THE ANSWER (cited observations only)")
    total_cited = max(1, data["cited"])
    for key in POSITIONS:
        count = data["positions"].get(key, 0)
        if count:
            print("%-28s %6d %9s" % (key, count, percent(count / total_cited)))
    print()
    print("SENTIMENT OF THE MENTION (cited observations only)")
    for key in SENTIMENTS:
        count = data["sentiments"].get(key, 0)
        if count:
            print("%-28s %6d %9s" % (key, count, percent(count / total_cited)))
    print()
    urls = data["urls"]
    print(
        "URL ACTUALLY CITED: own domain %d, third party %d"
        % (urls["own"], urls["third_party"])
    )
    for url, count in urls["top"]:
        print("%6d  %s" % (count, url))
    print()
    print(line())
    print("NOISE FLOOR")
    print(
        "With %d observation(s) per survey, no change smaller than %s can be called\n"
        "a result. Repetitions of the same prompt are correlated, so the real\n"
        "floor is wider than this number, never narrower."
        % (data["observations"], percent(data["noise_floor"]))
    )
    if reps["min"] < 3:
        print(
            "WARNING: at least one prompt and engine pair was run %d time(s).\n"
            "Answers vary between runs. Below 3 runs a rate is an anecdote."
            % reps["min"]
        )
    print(line())
    print()


def print_comparison(result):
    print(line("="))
    print("EVOLUTION, BASELINE VERSUS FOLLOW UP")
    print(line("="))
    print(
        "%-24s %9s %9s %8s %9s  %s"
        % ("family", "before", "after", "delta", "p value", "verdict")
    )
    for name, row in result.items():
        label = "OVERALL" if name == "__overall__" else name[:24]
        p_text = "n/a" if row["p_value"] is None else "%8.3f" % row["p_value"]
        if row["p_value"] is None:
            verdict = "no data"
        elif row["significant"]:
            verdict = "signal"
        else:
            verdict = "noise, floor %s" % percent(row["noise_floor"]).strip()
        print(
            "%-24s %9s %9s %+7.1f %9s  %s"
            % (
                label,
                percent(row["before_rate"]).strip(),
                percent(row["after_rate"]).strip(),
                (row["delta"] * 100),
                p_text,
                verdict,
            )
        )
    print()
    print(line())
    print(
        "Read this as a consultant, not as a dashboard. A line marked noise means\n"
        "the two surveys are compatible with no change at all. Report it as such,\n"
        "and raise the number of prompts or repetitions before the next survey."
    )
    print(line())
    print()


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Compute GEO presence metrics from a manual survey CSV."
    )
    parser.add_argument("csv", nargs="+", help="one survey, or baseline then follow up")
    parser.add_argument("--domain", default="", help="own domain, to split cited URLs")
    parser.add_argument("--json", dest="json_path", default="", help="write metrics to this JSON file")
    args = parser.parse_args(argv)

    if len(args.csv) > 2:
        sys.exit("pass one survey, or two surveys to compare")

    surveys = [(path, analyse(read_survey(path), args.domain)) for path in args.csv]
    for path, data in surveys:
        print_survey(path, data)

    comparison = None
    if len(surveys) == 2:
        comparison = compare(surveys[0][1], surveys[1][1])
        print_comparison(comparison)

    if args.json_path:
        payload = {
            "surveys": [
                {
                    "file": path,
                    "observations": data["observations"],
                    "prompts": data["prompts"],
                    "engines": data["engines"],
                    "dates": data["dates"],
                    "repetitions": data["repetitions"],
                    "presence_rate": round(data["rate"], 4),
                    "presence_ci": [round(data["ci_low"], 4), round(data["ci_high"], 4)],
                    "noise_floor": round(data["noise_floor"], 4),
                    "by_family": {
                        k: {
                            "observations": v["observations"],
                            "cited": v["cited"],
                            "rate": round(v["rate"], 4),
                            "ci": [round(v["ci_low"], 4), round(v["ci_high"], 4)],
                        }
                        for k, v in data["by_family"].items()
                    },
                    "by_engine": {
                        k: {"observations": v["observations"], "rate": round(v["rate"], 4)}
                        for k, v in data["by_engine"].items()
                    },
                    "positions": dict(data["positions"]),
                    "sentiments": dict(data["sentiments"]),
                    "urls": {
                        "own": data["urls"]["own"],
                        "third_party": data["urls"]["third_party"],
                        "top": data["urls"]["top"],
                    },
                }
                for path, data in surveys
            ],
            "comparison": (
                {
                    k: {
                        "before_rate": round(v["before_rate"], 4),
                        "after_rate": round(v["after_rate"], 4),
                        "delta": round(v["delta"], 4),
                        "p_value": None if v["p_value"] is None else round(v["p_value"], 4),
                        "noise_floor": round(v["noise_floor"], 4),
                        "significant": v["significant"],
                    }
                    for k, v in comparison.items()
                }
                if comparison
                else None
            ),
        }
        with open(args.json_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        print("metrics written to %s" % args.json_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
