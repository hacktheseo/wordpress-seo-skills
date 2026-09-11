# Testing

Three levels, in order. Each one catches a class of defect the next one cannot.

| Level | Question it answers | Cost |
|---|---|---|
| 1. Verify | Is this a well formed, safe, correctly sized skill? | one command, seconds |
| 2. Run | Do the scripts actually work on real input? | one command per skill, seconds |
| 3. Judge | Does it fire on a natural sentence, and is the output good? | a person, about 20 minutes per skill |

Levels 1 and 2 are automated and belong in CI. Level 3 cannot be automated: a
skill that passes every mechanical check and never fires is worthless, and a
skill that fires perfectly and produces a mediocre report is worse than nothing,
because it costs context on every turn.

## Level 1, what a machine can check

```bash
python3 tools/verify.py            # everything
python3 tools/verify.py --quiet    # only what is not green
python3 tools/verify.py ai-bot-log-forensics
```

Exit code 0 when nothing failed, so it drops into a git hook or CI unchanged.

It checks, per skill: the front matter parses and `name` matches the folder; the
description is under 200 characters and free of XML; there is no top level
`version` field and `metadata.version` is quoted; the body is under 500 lines and
5 000 tokens; every file in `references/` is actually linked from somewhere (an
unlinked reference will never be read, so it may as well not exist); no absolute
paths; scripts are invoked through `${CLAUDE_SKILL_DIR}`; no em dashes; nothing
that promises a ranking or a citation; no hard coded secrets, no obfuscation, no
writes near the agent config; every script compiles and fails cleanly with no
arguments rather than printing a traceback; at least three eval cases, each with
an explicit `should_trigger`, at least one near miss, at least one French prompt,
a described baseline, and fixtures that exist.

It also checks the repository itself (required files, both manifests parse and
carry their required keys) and the report engine (compiles, renders the example
in both document and artifact mode, and fails loudly on malformed JSON instead of
writing a broken page).

**A FAIL blocks publication. A WARN is fixed or justified in writing.**

Two more checks that live outside this repository, run them before publishing:

```bash
skills-ref validate ./skills/<name>    # the open specification's own linter
claude plugin validate .               # the plugin and marketplace manifests
```

## Level 2, do the scripts work

Every skill ships fixtures so its scripts can be exercised without needing a real
client site. Run these from the repository root.

```bash
# ai-bot-log-forensics: parse a log, verify user agents, separate spoofed traffic
cd skills/ai-bot-log-forensics/evals/fixtures
python3 ../../scripts/parse_logs.py access-sample.log \
    --ip-ranges ranges-sample.json --out /tmp/bots.json
```

Expect: verified, spoofed and unverifiable counted separately, spoofed hits
excluded from every other total, and three ClaudeBot hits answered 403 in ten
milliseconds (a firewall signature the report is supposed to surface).

```bash
# geo-strategy-map: two surveys, three months apart
cd skills/geo-strategy-map/evals/fixtures
python3 ../../scripts/geo_measure.py baseline.csv followup.csv --domain exemple.fr
```

Expect a noise floor printed **before** any delta, then one family marked
`signal` (how-to, +55.6 points, p 0.001) and every other family marked `noise`
with its own floor. That mix is the point of the fixture: a tool that called all
seven of those moves progress would be lying, and this one refuses to.

```bash
# seo-portfolio-report: a four site agency portfolio, one command
cd skills/seo-portfolio-report/evals/fixtures
python3 ../../scripts/portfolio_rollup.py --config portfolio.json \
    --view all --out-dir /tmp/pf
for f in /tmp/pf/*.findings.json; do
  python3 ../../../../shared/report-engine/render_report.py "$f" "${f%.findings.json}.html"
done
open /tmp/pf/portfolio.html    # xdg-open on Linux
```

Expect five findings files (one portfolio view plus one per client) and five
rendered reports. Then test the degraded path, which is the one that matters on a
real Monday morning:

```bash
python3 ../../scripts/portfolio_rollup.py --config portfolio-degraded.json \
    --view portfolio --out /tmp/deg.json
```

Expect a warning on stderr naming the missing export, the site dropped from the
totals rather than counted as zero, and a report still produced on the other
three.

```bash
# ai-citability-audit: segment a page into passages
cd skills/ai-citability-audit
python3 scripts/segment_passages.py --help
```

This one needs a page, so point it at any URL you control.

```bash
# seo-migration-redirects: a redesign with a domain change, end to end
cd skills/seo-migration-redirects/evals/fixtures
S=../../scripts
python3 $S/redirect_map.py build --old gsc-before-Pages.csv --new new-sitemap.xml \
    --out /tmp/map.csv --json /tmp/build.json
python3 $S/redirect_map.py lint /tmp/map.csv --new new-sitemap.xml \
    --existing existing-rules.json --json /tmp/lint.json
python3 $S/redirect_map.py hunt notfound-log.json --map /tmp/map.csv \
    --new new-sitemap.xml --json /tmp/hunt.json
python3 mock_site.py 8765 &
python3 $S/check_live.py /tmp/map.csv --old-base http://127.0.0.1:8765 \
    --expect-base http://localhost:8765 --rate 0 --out /tmp/live.json
kill %1
python3 $S/migration_proof.py --map /tmp/map.csv --before gsc-before-Pages.csv \
    --after gsc-after-Pages-new.csv gsc-after-Pages-old.csv --dates gsc-Dates.csv \
    --launch 2026-07-15 --live /tmp/live.json --lint /tmp/lint.json --hunt /tmp/hunt.json \
    --lang fr --findings /tmp/migration.json
```

Expect 28 old URLs: 20 redirect, 3 review, 4 manual, 1 gone, and two learned
patterns (`/produit/*` to `/boutique/*`, `/category/*` to `/blog/*`) each with one
exception. The lint finds one existing rule turned into a chain. The hunt sets
aside 4 scanner probes and groups two `/en/en/` URLs. The live check on the mock
site returns 12 ok, 1 gone_ok and 8 defects, one of each kind the mock plants:
the one that matters is a correct redirect landing on a page still in noindex.

```bash
# wp-seo-plugin-driver: a Yoast to Rank Math switch, six pages
cd skills/wp-seo-plugin-driver/evals/fixtures
S=../../scripts/seo_driver.py
python3 $S snapshot before --out /tmp/before.json
python3 $S snapshot after --out /tmp/after.json
python3 $S diff /tmp/before.json /tmp/after.json --json /tmp/diff.json
python3 $S detect https://www.cabinet-vandel.exemple.fr --html after/accueil.html \
    --index wp-json-rankmath.json --json /tmp/detect.json
python3 $S plan changes.csv --detect /tmp/detect.json --snapshot /tmp/after.json --out-dir /tmp/plan
```

Expect five differences: one page became noindex, one canonical moved to the
preproduction host, one description lost, one Article schema lost, one title
separator changed. The plan writes five `rankmath/v1/updateMeta` calls with the
post ids read from the page heads, and sends nothing.

```bash
# llmstxt-governance: a shop whose robots.txt and llms.txt disagree
cd skills/llmstxt-governance/evals/fixtures
S=../../scripts/ai_access.py
python3 $S audit --robots robots.txt --llms llms.txt --sitemap sitemap.xml \
    --site https://www.boutique.exemple.fr --log access.log --shop --json /tmp/audit.json
python3 $S policy --preset open --site https://www.boutique.exemple.fr --shop --out /tmp/robots.txt
```

Expect OAI-SearchBot refused (it shares GPTBot's group), one llms.txt link on
another host, one llms.txt page refused by robots.txt, and llms.txt requested
once by an AI user agent in a month against 105 requests for robots.txt. The
policy command re-reads its own file and confirms every token lands where the
preset says.

```bash
# ai-visibility-tracker: two waves, 180 answers each
cd skills/ai-visibility-tracker/evals/fixtures
python3 ../../scripts/visibility.py survey-september.csv --baseline survey-june.csv \
    --brand brand.json --json /tmp/vis.json
for e in openai perplexity gemini anthropic; do
  python3 ../../scripts/run_survey.py --parse $e-response.json --engine $e --brand brand.json
done
```

Expect 54 of 180 answers, 30 % with an interval of 23.8 to 37.1 %, every change
marked noise except the implementation family (+31 points, interval +11 to +48,
signal), and seven core domains in the source gap. Each of the four saved API
answers parses with a search detected and its sources extracted.

## Level 3, what only a person can judge

### Install first

Pick one. The first works with any agent, the second is Claude Code specific.

```bash
npx skills add hacktheseo/wordpress-seo-skills
```

```
/plugin marketplace add hacktheseo/wordpress-seo-skills
/plugin install wordpress-seo-skills@hacktheseo
```

To test a local checkout before anything is published, symlink it instead of
copying, so edits take effect without reinstalling:

```bash
ln -s "$(pwd)/skills/ai-bot-log-forensics" ~/.claude/skills/ai-bot-log-forensics
```

Project skills and personal skills reload automatically. Plugin skills do not:
run `/reload-plugins` after an edit.

### Then print the sheet

```bash
python3 tools/verify.py --sheet                        # all skills
python3 tools/verify.py --sheet seo-portfolio-report   # one
```

It prints every eval case as a checklist row: the prompt to paste, whether the
skill must fire or must stay quiet, what the output should contain, and a box to
tick.

### The four rules that make the test valid

1. **Fresh session every time.** A skill already loaded in context will appear to
   fire brilliantly. Test it cold or you are testing nothing.
2. **Never name the skill.** Paste the prompt as written. If it only works when
   the user says "use the citability skill", the description is the bug, not the
   body.
3. **Run the baseline.** Ask the same question with the skill uninstalled. Each
   `evals.json` describes what that unaided answer looks like. If the two answers
   are equally good, the skill is not earning the context it costs, and the right
   fix is to delete it.
4. **Test the near misses hardest.** A skill that fires on everything is worse
   than one that fires on nothing: it hijacks unrelated questions and burns
   tokens. Every skill here has at least one prompt it must ignore.

### Then check the cost

```
/skill-doctor
```

Available in Claude Code 2.1.252 and later. It reports which skills were loaded
in the session, which were never invoked, and what each one cost in context.
Run it after a normal working day, not after a test session. A skill that never
fires in real use gets removed, however good it looks.

### Test across models

Run at least the first eval case of each skill on Haiku, Sonnet and Opus. Skills
that lean on a strong model to fill gaps in their instructions pass on Opus and
fall apart on Haiku, and that shows up nowhere else.

## When something fails

| Symptom | Where the bug usually is |
|---|---|
| Never fires | The `description`: it lacks the literal words a user types, in the language they type them |
| Fires on everything | The description claims too broad a domain, or has no exclusion clause |
| Fires but ignores its own instructions | The body is too long, or the rule is buried below 300 lines |
| Works on Opus, fails on Haiku | The instructions imply a step instead of stating it |
| Reads a reference file, never the others | The file is not linked with an explicit condition saying when to read it |
| Output is right but ugly | The findings JSON, not the engine. Check `shared/report-engine/CONTRACT.md` |

## Before publishing

```bash
python3 tools/verify.py && echo "level 1 green"
skills-ref validate ./skills/<name>
claude plugin validate .
python3 tools/verify.py --sheet > /tmp/sheet.txt   # then work through it
```

Publish when level 1 is green, level 2 runs on every fixture, and every level 3
case has a ticked box, including the near misses and the baseline comparison.
