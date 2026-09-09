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
