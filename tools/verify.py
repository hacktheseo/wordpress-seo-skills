#!/usr/bin/env python3
"""
Verify every skill in this repository against the authoring standard.

    python3 tools/verify.py                 # check everything
    python3 tools/verify.py ai-bot-log-forensics
    python3 tools/verify.py --quiet         # only failures and the summary
    python3 tools/verify.py --no-urls       # skip the link check, for offline runs
    python3 tools/verify.py --sheet         # print the manual test sheet

Standard library only. Exit code 0 when nothing failed, 1 otherwise, so it
drops straight into a git hook or CI.

This checks what a machine can check: format, size, links, security, and that
the scripts actually run. It cannot check whether a skill fires on a natural
sentence or whether its output is any good. Run `--sheet` for that part.

Licence: GPL-2.0-or-later
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, "skills")

MAX_LINES = 500
MAX_TOKENS = 5000
MAX_DESC = 200
RESERVED = ("claude", "anthropic")

SECRET_PATTERNS = [
    (r"\bsk-[A-Za-z0-9]{16,}", "OpenAI style key"),
    (r"\bghp_[A-Za-z0-9]{20,}", "GitHub token"),
    (r"\bAKIA[0-9A-Z]{12,}", "AWS key id"),
    (r"(?i)\b(api[_-]?key|secret|password|passwd|token)\s*[:=]\s*['\"][^'\"]{8,}", "inline credential"),
]
DANGEROUS = [
    (r"\beval\s*\(", "eval()"),
    (r"\bexec\s*\(", "exec()"),
    (r"\bbase64\b", "base64"),
    (r"__import__", "__import__"),
    (r"os\.system\s*\(", "os.system()"),
    (r"shell\s*=\s*True", "shell=True"),
]
FORBIDDEN_WRITES = [
    (r"~/\.claude", "writes near the agent config"),
    (r"\.git/hooks", "writes to git hooks"),
    (r"\.bashrc|\.zshrc|\.profile", "writes to a shell profile"),
]
OVERPROMISE = [
    (r"(?i)\bguarantee(s|d)?\b", "promises a result"),
    (r"(?i)\bgaranti(e|s)?\b", "promises a result"),
    (r"(?i)will rank\b", "promises a ranking"),
    (r"(?i)\bva ranker\b", "promises a ranking"),
]
DASHES = re.compile("[\u2014\u2013]")
FRENCH = re.compile(r"[àâçéèêëîïôûùüÿœ]|\b(le|la|les|des|pour|est|sur|mon|mes|nos)\b", re.I)

GREEN, RED, YELLOW, GREY, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[0m"
if not sys.stdout.isatty() or os.environ.get("NO_COLOR"):
    GREEN = RED = YELLOW = GREY = RESET = ""


class Report:
    def __init__(self):
        self.rows = []

    def add(self, skill, level, check, detail=""):
        self.rows.append((skill, level, check, detail))

    def ok(self, skill, check, detail=""):
        self.add(skill, "PASS", check, detail)

    def warn(self, skill, check, detail=""):
        self.add(skill, "WARN", check, detail)

    def fail(self, skill, check, detail=""):
        self.add(skill, "FAIL", check, detail)

    def counts(self):
        out = {"PASS": 0, "WARN": 0, "FAIL": 0}
        for _, level, _, _ in self.rows:
            out[level] += 1
        return out


# --------------------------------------------------------------------------
# a very small YAML front matter reader, enough for the fields we allow
# --------------------------------------------------------------------------

def read_frontmatter(text):
    match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", text, re.S)
    if not match:
        return None, text
    raw, body = match.group(1), text[match.end():]
    data, key, indent_key = {}, None, None
    for line in raw.split("\n"):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if re.match(r"^\s", line) and indent_key:
            sub = line.strip()
            if ":" in sub and not data[indent_key].get("__folded__"):
                k, _, v = sub.partition(":")
                data[indent_key][k.strip()] = v.strip()
            else:
                data[indent_key]["__folded__"] = (
                    data[indent_key].get("__folded__", "") + " " + sub
                )
            continue
        key, _, value = line.partition(":")
        key, value = key.strip(), value.strip()
        if value == "":
            data[key] = {}
            indent_key = key
        else:
            data[key] = value
            indent_key = key if value == "" else None
    # a folded scalar (description spanning lines) lands in __folded__
    for k, v in list(data.items()):
        if isinstance(v, dict) and "__folded__" in v and len(v) == 1:
            data[k] = v["__folded__"].strip()
        elif isinstance(v, str) and k in data and isinstance(data.get(k), str):
            pass
    return data, body


def folded_value(text, key):
    """Read a possibly multi-line scalar out of the raw front matter."""
    match = re.search(
        r"^" + key + r":\s*(.*(?:\n[ \t]+\S.*)*)", text, re.M
    )
    if not match:
        return None
    return " ".join(match.group(1).split()).strip("\"'")


# --------------------------------------------------------------------------
# checks
# --------------------------------------------------------------------------

def check_skill(name, report):
    path = os.path.join(SKILLS, name)
    skill_md = os.path.join(path, "SKILL.md")
    if not os.path.isfile(skill_md):
        report.fail(name, "SKILL.md exists")
        return

    text = open(skill_md, encoding="utf-8").read()
    front, body = read_frontmatter(text)

    # --- front matter -----------------------------------------------------
    if front is None:
        report.fail(name, "front matter parses")
        return
    report.ok(name, "front matter parses")

    fm_raw = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", text, re.S).group(1)

    declared = front.get("name", "")
    if declared != name:
        report.fail(name, "name matches folder", f"front matter says {declared!r}")
    elif not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) or len(name) > 64:
        report.fail(name, "name is a valid slug")
    elif any(word in name for word in RESERVED):
        report.fail(name, "name avoids reserved words")
    else:
        report.ok(name, "name matches folder and is a valid slug")

    desc = folded_value(fm_raw, "description") or ""
    if not desc:
        report.fail(name, "description present")
    elif len(desc) > MAX_DESC:
        report.fail(name, "description under 200 chars", f"{len(desc)} chars")
    elif "<" in desc and ">" in desc:
        report.fail(name, "description has no XML tags")
    else:
        report.ok(name, "description", f"{len(desc)} chars")

    if re.search(r"^version:", fm_raw, re.M):
        report.fail(name, "no top level version field", "move it to metadata.version")
    else:
        version = re.search(r"version:\s*(\S+)", fm_raw)
        if version and not version.group(1).startswith(('"', "'")):
            report.fail(name, "metadata.version is quoted", "YAML reads 1.0 as a float")
        else:
            report.ok(name, "version lives in metadata and is quoted")

    if "license:" not in fm_raw:
        report.warn(name, "license declared")
    else:
        report.ok(name, "license declared")

    # --- size -------------------------------------------------------------
    lines = body.count("\n") + 1
    approx_tokens = len(body) // 4
    if lines > MAX_LINES:
        report.fail(name, "body under 500 lines", f"{lines} lines")
    elif approx_tokens > MAX_TOKENS:
        report.fail(name, "body under 5000 tokens", f"about {approx_tokens}")
    else:
        report.ok(name, "size", f"{lines} lines, about {approx_tokens} tokens")

    # --- references -------------------------------------------------------
    ref_dir = os.path.join(path, "references")
    referenced, orphans = set(), []
    corpus = text
    for root, _, files in os.walk(ref_dir):
        for f in files:
            corpus += "\n" + open(os.path.join(root, f), encoding="utf-8", errors="replace").read()
    if os.path.isdir(ref_dir):
        for root, _, files in os.walk(ref_dir):
            for f in files:
                rel = os.path.relpath(os.path.join(root, f), path)
                if f in text or rel in text:
                    referenced.add(rel)
                elif f in corpus or rel in corpus:
                    referenced.add(rel)
                else:
                    orphans.append(rel)
                full = os.path.join(root, f)
                if f.endswith(".md"):
                    ref_lines = open(full, encoding="utf-8").read().count("\n")
                    if ref_lines > 300:
                        head = "\n".join(
                            open(full, encoding="utf-8").read().split("\n")[:40]
                        ).lower()
                        if "table of contents" not in head and "sommaire" not in head:
                            report.warn(
                                name, "long reference has a table of contents",
                                f"{rel}, {ref_lines} lines",
                            )
    if orphans:
        report.fail(
            name, "no orphan reference files",
            "never linked: " + ", ".join(orphans),
        )
    elif referenced:
        report.ok(name, "references are all linked", f"{len(referenced)} files")

    # --- paths ------------------------------------------------------------
    bad_paths = re.findall(r"(?:/Users/|/home/|C:\\\\|[A-Z]:\\)[^\s\)\"']*", text)
    if bad_paths:
        report.fail(name, "no absolute paths", bad_paths[0][:60])
    else:
        report.ok(name, "no absolute paths")

    scripts_dir = os.path.join(path, "scripts")
    if os.path.isdir(scripts_dir) and os.listdir(scripts_dir):
        if "${CLAUDE_SKILL_DIR}" in text:
            report.ok(name, "scripts invoked through CLAUDE_SKILL_DIR")
        else:
            report.fail(name, "scripts invoked through CLAUDE_SKILL_DIR")

    # --- house style ------------------------------------------------------
    dashed = [f for f in walk_files(path) if DASHES.search(read(f))]
    if dashed:
        report.fail(name, "no em or en dashes", os.path.relpath(dashed[0], path))
    else:
        report.ok(name, "no em or en dashes")

    for pattern, label in OVERPROMISE:
        hit = re.search(pattern, corpus)
        if hit:
            line = context(corpus, hit.start())
            if "never" in line.lower() or "jamais" in line.lower() or "no " in line.lower():
                continue
            report.warn(name, "no promised outcome", f"{label}: {line[:70]}")
            break
    else:
        report.ok(name, "promises no ranking or citation")

    # --- security ---------------------------------------------------------
    findings = []
    for f in walk_files(path):
        content = read(f)
        rel = os.path.relpath(f, path)
        for pattern, label in SECRET_PATTERNS:
            if re.search(pattern, content):
                findings.append(f"{label} in {rel}")
        if f.endswith(".py"):
            for pattern, label in DANGEROUS:
                if re.search(pattern, content):
                    findings.append(f"{label} in {rel}")
        for pattern, label in FORBIDDEN_WRITES:
            if re.search(pattern, content):
                findings.append(f"{label} in {rel}")
    if findings:
        report.fail(name, "security scan", "; ".join(findings[:3]))
    else:
        report.ok(name, "security scan", "no secrets, no obfuscation, no stray writes")

    # --- scripts ----------------------------------------------------------
    if os.path.isdir(scripts_dir):
        for f in sorted(os.listdir(scripts_dir)):
            if not f.endswith(".py"):
                continue
            full = os.path.join(scripts_dir, f)
            compiled = subprocess.run(
                [sys.executable, "-m", "py_compile", full],
                capture_output=True, text=True,
            )
            if compiled.returncode != 0:
                report.fail(name, f"{f} compiles", compiled.stderr.strip().split("\n")[-1][:80])
                continue
            run = subprocess.run(
                [sys.executable, full], capture_output=True, text=True, timeout=60
            )
            if "Traceback" in run.stderr:
                report.fail(name, f"{f} fails cleanly with no args", "raw traceback shown to the user")
            elif run.returncode == 0 and not run.stdout.strip():
                report.warn(name, f"{f} with no args", "exits 0 and prints nothing")
            else:
                report.ok(name, f"{f} compiles and fails cleanly", f"exit {run.returncode}")

    # --- evals ------------------------------------------------------------
    evals_path = os.path.join(path, "evals", "evals.json")
    if not os.path.isfile(evals_path):
        report.fail(name, "evals/evals.json exists")
        return
    try:
        data = json.load(open(evals_path, encoding="utf-8"))
    except json.JSONDecodeError as error:
        report.fail(name, "evals.json parses", str(error)[:60])
        return

    cases = data.get("evals") or []
    if len(cases) < 3:
        report.fail(name, "at least 3 eval cases", f"{len(cases)} found")
    else:
        report.ok(name, "eval cases", f"{len(cases)}")

    missing = [c.get("id") for c in cases if "should_trigger" not in c]
    if missing:
        report.fail(name, "every case declares should_trigger", f"missing on {missing}")
    else:
        report.ok(name, "every case declares should_trigger")

    negatives = [c for c in cases if c.get("should_trigger") is False]
    if not negatives:
        report.fail(name, "at least one near miss", "nothing tests that it stays quiet")
    else:
        report.ok(name, "near miss cases", f"{len(negatives)}")

    if not any(FRENCH.search(c.get("prompt", "")) for c in cases):
        report.fail(name, "at least one French prompt")
    else:
        report.ok(name, "French prompt covered")

    if not data.get("baseline"):
        report.warn(name, "baseline described", "without one, nothing is measured")
    else:
        report.ok(name, "baseline described")

    for case in cases:
        for fixture in case.get("files") or []:
            # a fixture may be a folder of files (saved pages, a site tree)
            found = any(
                os.path.exists(os.path.join(path, "evals", d, fixture))
                for d in ("", "fixtures")
            )
            if not found:
                report.warn(name, "fixture present", f"case {case.get('id')}: {fixture}")


def check_engine(report):
    name = "shared/report-engine"
    engine = os.path.join(ROOT, "shared", "report-engine", "render_report.py")
    if not os.path.isfile(engine):
        report.fail(name, "engine present")
        return
    compiled = subprocess.run(
        [sys.executable, "-m", "py_compile", engine], capture_output=True, text=True
    )
    if compiled.returncode != 0:
        report.fail(name, "engine compiles", compiled.stderr.strip()[:80])
        return
    report.ok(name, "engine compiles")

    sample = os.path.join(ROOT, "examples", "ai-crawler-forensics.findings.json")
    if not os.path.isfile(sample):
        return

    # Temporary files go to the system temp dir, never into the repository.
    # A checkout can sit on a read only mount or a sandboxed folder where
    # deleting is not permitted, and a verifier must not need write access
    # to the thing it is verifying.
    workdir = tempfile.mkdtemp(prefix="verify-report-")
    out = os.path.join(workdir, "out.html")
    try:
        for flag in ([], ["--artifact"]):
            run = subprocess.run(
                [sys.executable, engine] + flag + [sample, out],
                capture_output=True, text=True, timeout=60,
            )
            label = "artifact mode" if flag else "document mode"
            if run.returncode != 0 or not os.path.isfile(out):
                report.fail(name, f"renders the example, {label}", run.stderr.strip()[:70])
                continue
            html = read(out)
            if flag and re.search(r"<!doctype|<body\b", html, re.I):
                report.fail(name, "artifact mode drops the document wrapper")
            elif not flag and "<!doctype" not in html.lower():
                report.fail(name, "document mode emits a full document")
            elif "findings" not in html:
                report.warn(name, f"renders the example, {label}", "no findings block")
            else:
                report.ok(name, f"renders the example, {label}", f"{len(html) // 1024} KB")

        bad = os.path.join(workdir, "bad.json")
        with open(bad, "w", encoding="utf-8") as handle:
            handle.write("{ not json")
        run = subprocess.run(
            [sys.executable, engine, bad, out], capture_output=True, text=True
        )
        if run.returncode == 0 or "Traceback" in run.stderr:
            report.fail(name, "bad JSON fails loudly", "should exit non zero with a message")
        else:
            report.ok(name, "bad JSON fails loudly", run.stderr.strip()[:50])
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


# The numbers below are not decoration. They are the whole point of the skill:
# a hit counted as verified that was forged, or the reverse, is a false statement
# in a document an agency sends to a client. If this assertion ever goes red,
# stop and find out why before shipping.
FIXTURE_TOTALS = {
    "ai_claimed": 17,
    "ai_verified": 13,
    "ai_spoofed": 2,
    "ai_unverifiable": 2,
}


def check_fixture_numbers(report):
    name = "assertions"
    skill = os.path.join(SKILLS, "ai-bot-log-forensics")
    parser = os.path.join(skill, "scripts", "parse_logs.py")
    log = os.path.join(skill, "evals", "fixtures", "access-sample.log")
    ranges = os.path.join(skill, "evals", "fixtures", "ranges-sample.json")
    if not all(os.path.isfile(f) for f in (parser, log, ranges)):
        report.fail(name, "log fixture present")
        return
    workdir = tempfile.mkdtemp(prefix="verify-fixture-")
    out = os.path.join(workdir, "bots.json")
    try:
        run = subprocess.run(
            [sys.executable, parser, log, "--ip-ranges", ranges,
             "--no-dns", "--quiet", "--out", out],
            capture_output=True, text=True, timeout=120,
        )
        if run.returncode != 0 or not os.path.isfile(out):
            report.fail(name, "parse_logs runs on the fixture",
                        run.stderr.strip()[:70])
            return
        totals = json.load(open(out, encoding="utf-8")).get("totals") or {}
        wrong = {k: (v, totals.get(k)) for k, v in FIXTURE_TOTALS.items()
                 if totals.get(k) != v}
        if wrong:
            detail = ", ".join("%s expected %s got %s" % (k, a, b)
                               for k, (a, b) in wrong.items())
            report.fail(name, "fixture verification counts", detail)
        else:
            report.ok(name, "fixture verification counts",
                      ", ".join("%s %s" % (k, v) for k, v in FIXTURE_TOTALS.items()))
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    engine = os.path.join(ROOT, "shared", "report-engine", "render_report.py")
    sample = os.path.join(ROOT, "examples", "ai-crawler-forensics.findings.json")
    shipped = os.path.join(ROOT, "examples", "ai-crawler-forensics.report.html")
    if not all(os.path.isfile(f) for f in (engine, sample, shipped)):
        report.fail(name, "shipped example present")
        return
    workdir = tempfile.mkdtemp(prefix="verify-bytes-")
    out = os.path.join(workdir, "again.html")
    try:
        subprocess.run([sys.executable, engine, sample, out],
                       capture_output=True, text=True, timeout=60)
        if not os.path.isfile(out):
            report.fail(name, "example re-renders")
        elif read(out) != read(shipped):
            report.fail(name, "example is byte for byte the shipped file",
                        "regenerate examples/ai-crawler-forensics.report.html")
        else:
            report.ok(name, "example is byte for byte the shipped file",
                      "%d bytes" % os.path.getsize(shipped))
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


# Regression figures for the fixtures of the second lot of skills. Same idea
# as FIXTURE_TOTALS: each number is a statement a client report would make.
# If one changes, find out why before shipping.
MIGRATION_DECISIONS = {"redirect": 20, "review": 3, "manual": 4, "gone": 1}
MIGRATION_LIVE = {"ok": 12, "gone_ok": 1, "noindex_target": 1, "canonical_elsewhere": 1,
                  "broken_target": 1, "loop": 1, "home_target": 1, "not_redirected": 1,
                  "temporary": 1, "chain": 1}
DRIVER_DIFF = {"became_noindex": 1, "canonical_changed": 1, "description_lost": 1,
               "schema_lost": 1, "title_changed": 1}
TRACKER = {"answers": 180, "cited": 54, "core": 7, "signal": ["family:implementation"]}


def free_port():
    import socket
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def run_json(cmd, out):
    run = subprocess.run([sys.executable] + cmd, capture_output=True, text=True, timeout=180)
    if run.returncode != 0 or not os.path.isfile(out):
        return None, (run.stderr.strip() or run.stdout.strip())[-90:]
    return json.load(open(out, encoding="utf-8")), ""


def check_new_fixtures(report):
    name = "assertions"
    work = tempfile.mkdtemp(prefix="verify-lot2-")
    try:
        # seo-migration-redirects
        skill = os.path.join(SKILLS, "seo-migration-redirects")
        if os.path.isdir(skill):
            fx = os.path.join(skill, "evals", "fixtures")
            rm = os.path.join(skill, "scripts", "redirect_map.py")
            mp = os.path.join(work, "map.csv")
            build, err = run_json([rm, "build", "--old", os.path.join(fx, "gsc-before-Pages.csv"),
                                   "--new", os.path.join(fx, "new-sitemap.xml"), "--out", mp,
                                   "--json", os.path.join(work, "build.json"), "--quiet"],
                                  os.path.join(work, "build.json"))
            if build is None:
                report.fail(name, "migration map builds on the fixture", err)
            elif build.get("decisions") != MIGRATION_DECISIONS:
                report.fail(name, "migration map decisions", "got %s" % build.get("decisions"))
            else:
                report.ok(name, "migration map decisions", ", ".join("%s %d" % kv for kv in MIGRATION_DECISIONS.items()))
            if build is not None:
                lint, err = run_json([rm, "lint", mp, "--new", os.path.join(fx, "new-sitemap.xml"),
                                      "--existing", os.path.join(fx, "existing-rules.json"),
                                      "--json", os.path.join(work, "lint.json"), "--quiet"],
                                     os.path.join(work, "lint.json"))
                types = (lint or {}).get("issues_by_type", {})
                if types.get("existing_chain") == 1 and types.get("existing_dead_target") == 1:
                    report.ok(name, "migration lint sees the old rules", "1 chain, 1 dead target")
                else:
                    report.fail(name, "migration lint sees the old rules", err or str(types))
                mock = os.path.join(fx, "mock_site.py")
                port = free_port()
                server = subprocess.Popen([sys.executable, mock, str(port)],
                                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                try:
                    import socket
                    import time
                    for _ in range(50):
                        try:
                            socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
                            break
                        except OSError:
                            time.sleep(0.1)
                    live, err = run_json([os.path.join(skill, "scripts", "check_live.py"), mp,
                                          "--old-base", "http://127.0.0.1:%d" % port,
                                          "--expect-base", "http://localhost:%d" % port,
                                          "--rate", "0", "--out", os.path.join(work, "live.json"), "--quiet"],
                                         os.path.join(work, "live.json"))
                finally:
                    server.terminate()
                    server.wait(timeout=10)
                verdicts = (live or {}).get("verdicts", {})
                if verdicts == MIGRATION_LIVE:
                    report.ok(name, "live check finds every planted defect", "12 ok, 8 defects, 1 gone")
                else:
                    report.fail(name, "live check finds every planted defect", err or str(verdicts))

        # wp-seo-plugin-driver
        skill = os.path.join(SKILLS, "wp-seo-plugin-driver")
        if os.path.isdir(skill):
            fx = os.path.join(skill, "evals", "fixtures")
            drv = os.path.join(skill, "scripts", "seo_driver.py")
            snaps = []
            for side in ("before", "after"):
                out = os.path.join(work, side + ".json")
                subprocess.run([sys.executable, drv, "snapshot", os.path.join(fx, side), "--out", out, "--quiet"],
                               capture_output=True, text=True, timeout=60)
                snaps.append(out)
            diff, err = run_json([drv, "diff", snaps[0], snaps[1], "--json", os.path.join(work, "diff.json"),
                                  "--quiet"], os.path.join(work, "diff.json"))
            if diff and diff.get("by_type") == DRIVER_DIFF:
                report.ok(name, "plugin switch diff", "5 changes, 3 serious")
            else:
                report.fail(name, "plugin switch diff", err or str((diff or {}).get("by_type")))

        # llmstxt-governance
        skill = os.path.join(SKILLS, "llmstxt-governance")
        if os.path.isdir(skill):
            fx = os.path.join(skill, "evals", "fixtures")
            audit, err = run_json([os.path.join(skill, "scripts", "ai_access.py"), "audit",
                                   "--robots", os.path.join(fx, "robots.txt"), "--llms", os.path.join(fx, "llms.txt"),
                                   "--sitemap", os.path.join(fx, "sitemap.xml"), "--site", "https://www.boutique.exemple.fr",
                                   "--log", os.path.join(fx, "access.log"), "--shop",
                                   "--json", os.path.join(work, "audit.json"), "--quiet"],
                                  os.path.join(work, "audit.json"))
            checks = {c["type"]: c for c in (audit or {}).get("checks", [])}
            wanted = ("chatgpt_search_blocked", "llms_offhost", "llms_contradiction", "user_fetcher_rule",
                      "transactional_open", "llms_too_long")
            missing = [w for w in wanted if w not in checks]
            if audit and not missing and checks["llms_contradiction"]["count"] == 1:
                report.ok(name, "AI access audit finds the contradictions", "%d checks" % len(checks))
            else:
                report.fail(name, "AI access audit finds the contradictions", err or "missing %s" % missing)
            for preset in ("open", "cite-not-train", "closed"):
                out = os.path.join(work, "robots-%s.txt" % preset)
                run = subprocess.run([sys.executable, os.path.join(skill, "scripts", "ai_access.py"), "policy",
                                      "--preset", preset, "--shop", "--signal", "--out", out, "--quiet"],
                                     capture_output=True, text=True, timeout=60)
                if run.returncode != 0:
                    report.fail(name, "policy %s proves itself" % preset, run.stderr.strip()[-80:])
                    break
            else:
                report.ok(name, "every policy preset proves itself", "open, cite-not-train, closed")

        # ai-visibility-tracker
        skill = os.path.join(SKILLS, "ai-visibility-tracker")
        if os.path.isdir(skill):
            fx = os.path.join(skill, "evals", "fixtures")
            vis, err = run_json([os.path.join(skill, "scripts", "visibility.py"),
                                 os.path.join(fx, "survey-september.csv"), "--baseline", os.path.join(fx, "survey-june.csv"),
                                 "--brand", os.path.join(fx, "brand.json"), "--json", os.path.join(work, "vis.json"),
                                 "--quiet"], os.path.join(work, "vis.json"))
            if vis is None:
                report.fail(name, "visibility fixture", err)
            else:
                r = vis["result"]
                core = sum(1 for g in r["source_gap"] if g["stability"] == "core")
                signals = [k for k, c in (vis.get("comparison") or {}).items() if c and c["verdict"] == "signal"]
                if (r["overall"]["answers"], r["overall"]["cited"], core, signals) == (
                        TRACKER["answers"], TRACKER["cited"], TRACKER["core"], TRACKER["signal"]):
                    report.ok(name, "visibility rates, source gap and signal", "54 of 180, 7 core, 1 signal")
                else:
                    report.fail(name, "visibility rates, source gap and signal",
                                "got %s of %s, %d core, signals %s" % (r["overall"]["cited"], r["overall"]["answers"], core, signals))
    finally:
        shutil.rmtree(work, ignore_errors=True)


URL_RE = re.compile(r"https?://[^\s\)\"'`<>\]]+")
URL_SKIP = ("example.com", "exemple.fr", "example.org", "localhost", "127.0.0.1",
            "mon-site.fr", "a.fr", "b.fr", "site-one.com", "boutique-escalade.fr")


def check_urls(report):
    """HEAD every absolute URL that ships in the documentation.

    urllib does not do HTTPS on every machine this runs on, so curl is the
    portable choice here. A dead link in a README is a broken promise, and six
    of them pointed at a repository that did not exist yet.
    """
    name = "links"
    if not shutil.which("curl"):
        report.fail(name, "curl available for the link check")
        return
    urls = set()
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
        for f in files:
            if not f.endswith((".md", ".json")):
                continue
            text = read(os.path.join(root, f))
            for match in URL_RE.finditer(text):
                # "+https://..." inside a user agent string is a convention,
                # not a link anyone is meant to open. Do not probe it.
                if match.start() and text[match.start() - 1] == "+":
                    continue
                url = match.group(0).rstrip(".,;:")
                if not any(bad in url for bad in URL_SKIP):
                    urls.add(url)
    bad, refused = [], []
    for url in sorted(urls):
        run = subprocess.run(
            ["curl", "-sS", "-o", "/dev/null", "-w", "%{http_code}",
             "-L", "--max-time", "15", "-A", "hacktheseo-verify/1.0", "-I", url],
            capture_output=True, text=True,
        )
        code = (run.stdout or "").strip()
        if code in ("405", "404", "403", "000"):  # HEAD refused or mishandled, retry with a ranged GET
            run = subprocess.run(
                ["curl", "-sS", "-o", "/dev/null", "-w", "%{http_code}",
                 "-L", "--max-time", "15", "-A", "hacktheseo-verify/1.0",
                 "-r", "0-0", url],
                capture_output=True, text=True,
            )
            code = (run.stdout or "").strip()
        try:
            status = int(code)
        except ValueError:
            status = 0
        # 401, 403 and 429 mean the host is up and refuses a script: many
        # documentation sites sit behind bot protection. That is not a dead
        # link, which is what this check exists to catch (404, 410, 5xx, no
        # answer at all). They are counted and named, never hidden.
        if status in (401, 403, 429):
            refused.append(urlsplit_host(url))
        elif status == 0 or status >= 400:
            bad.append("%s -> %s" % (url, code or "no answer"))
    if bad:
        report.fail(name, "every documented URL answers", "; ".join(bad[:4]))
    else:
        detail = "%d checked" % len(urls)
        if refused:
            detail += ", %d refused a script (%s)" % (len(refused), ", ".join(sorted(set(refused))[:4]))
        report.ok(name, "every documented URL answers", detail)


def urlsplit_host(url):
    match = re.match(r"https?://([^/]+)", url)
    return match.group(1) if match else url


def check_repo(report):
    name = "repo"
    for required in ("README.md", "LICENSE", "SECURITY.md", "CONTRIBUTING.md",
                     ".claude-plugin/marketplace.json", ".claude-plugin/plugin.json",
                     "docs/AUTHORING.md"):
        if os.path.isfile(os.path.join(ROOT, required)):
            report.ok(name, f"{required} present")
        else:
            report.fail(name, f"{required} present")

    for manifest in (".claude-plugin/marketplace.json", ".claude-plugin/plugin.json"):
        full = os.path.join(ROOT, manifest)
        if not os.path.isfile(full):
            continue
        try:
            data = json.load(open(full, encoding="utf-8"))
        except json.JSONDecodeError as error:
            report.fail(name, f"{manifest} parses", str(error)[:60])
            continue
        if manifest.endswith("marketplace.json"):
            missing = [k for k in ("name", "owner", "plugins") if k not in data]
            if missing:
                report.fail(name, "marketplace.json has required keys", str(missing))
            elif not isinstance(data.get("owner"), dict) or "name" not in data["owner"]:
                report.fail(name, "marketplace owner has a name")
            else:
                report.ok(name, "marketplace.json is well formed",
                          f"{len(data['plugins'])} plugin(s)")
        else:
            if "name" not in data:
                report.fail(name, "plugin.json has a name")
            else:
                report.ok(name, "plugin.json is well formed")


def walk_files(path):
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            if f.endswith((".png", ".jpg", ".gz", ".zip", ".pyc")):
                continue
            yield os.path.join(root, f)


def read(path):
    try:
        return open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return ""


def context(text, index):
    start = text.rfind("\n", 0, index) + 1
    end = text.find("\n", index)
    return text[start:end if end != -1 else len(text)].strip()


# --------------------------------------------------------------------------
# the manual test sheet
# --------------------------------------------------------------------------

def print_sheet(names):
    print("\nMANUAL TEST SHEET")
    print("=" * 72)
    print("""
A machine cannot judge two things: whether a skill fires on a natural
sentence, and whether what it produces is any good. Here is the procedure.

For every prompt below:
  1. Open a FRESH session. A skill already loaded in context invalidates the test.
  2. Paste the prompt as written. Never name the skill.
  3. Note whether it fired, then compare the output against what is expected.
  4. On MUST NOT FIRE cases the skill has to stay out of the way.
  5. Run the same prompt once with the skill removed. That is the baseline: if
     the answers are equally good, the skill is not earning its context.
""")
    for name in names:
        path = os.path.join(SKILLS, name, "evals", "evals.json")
        if not os.path.isfile(path):
            continue
        data = json.load(open(path, encoding="utf-8"))
        print("\n" + "-" * 72)
        print(name.upper())
        print("-" * 72)
        if data.get("baseline"):
            print(f"Baseline without the skill: {data['baseline']}\n")
        for case in data.get("evals") or []:
            flag = "MUST FIRE" if case.get("should_trigger") else "MUST NOT FIRE"
            print(f"[{case.get('id')}] {flag}")
            print(f"    Prompt   : {case.get('prompt')}")
            expected = " ".join((case.get("expected_output") or "").split())
            print(f"    Expected : {expected}")
            if case.get("files"):
                print(f"    Files    : {', '.join(case['files'])}")
            print("    Result   : [ ] as expected   [ ] partial   [ ] failed")
            print()


# --------------------------------------------------------------------------

def main(argv):
    quiet = "--quiet" in argv
    sheet = "--sheet" in argv
    args = [a for a in argv[1:] if not a.startswith("--")]

    if not os.path.isdir(SKILLS):
        print("no skills/ directory found next to tools/", file=sys.stderr)
        return 2

    names = args or sorted(
        d for d in os.listdir(SKILLS) if os.path.isdir(os.path.join(SKILLS, d))
    )
    unknown = [n for n in names if not os.path.isdir(os.path.join(SKILLS, n))]
    if unknown:
        print(f"unknown skill: {', '.join(unknown)}", file=sys.stderr)
        return 2

    if sheet:
        print_sheet(names)
        return 0

    report = Report()
    check_repo(report)
    check_engine(report)
    check_fixture_numbers(report)
    check_new_fixtures(report)
    if "--no-urls" not in argv:
        check_urls(report)
    for name in names:
        check_skill(name, report)

    current = None
    for skill, level, check, detail in report.rows:
        if level == "PASS" and quiet:
            continue
        if skill != current:
            print(f"\n{skill}")
            current = skill
        colour = {"PASS": GREEN, "WARN": YELLOW, "FAIL": RED}[level]
        tail = f" {GREY}{detail}{RESET}" if detail else ""
        print(f"  {colour}{level}{RESET}  {check}{tail}")

    counts = report.counts()
    print(
        f"\n{'-' * 60}\n"
        f"{GREEN}{counts['PASS']} pass{RESET}  "
        f"{YELLOW}{counts['WARN']} warn{RESET}  "
        f"{RED}{counts['FAIL']} fail{RESET}"
        f"   across {len(names)} skill(s)"
    )
    if counts["FAIL"]:
        print("\nA FAIL blocks publication. A WARN is fixed or justified in writing.")
    else:
        print("\nEverything a machine can check is green.")
        print("Run `python3 tools/verify.py --sheet` for the part only a human can do.")
    return 1 if counts["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
