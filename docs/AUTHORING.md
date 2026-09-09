# Authoring standard

Every skill in this repository follows this document. It is not a style guide,
it is a set of thresholds: below them a skill stops triggering, gets truncated,
or gets uninstalled.

## Table of contents

- [What this repository is](#what-this-repository-is)
- [The three circles](#the-three-circles)
- [Folder layout](#folder-layout)
- [Frontmatter](#frontmatter)
- [Hard limits](#hard-limits)
- [The bilingual rule](#the-bilingual-rule)
- [Writing the body](#writing-the-body)
- [Visual output](#visual-output)
- [Graceful degradation](#graceful-degradation)
- [Evaluations](#evaluations)
- [Security](#security)
- [Never do this](#never-do-this)

## What this repository is

Open source Agent Skills for SEO and GEO on WordPress, published by Hack The SEO
under GPL-2.0-or-later.

Positioning, and it must be visible in every skill: the official WordPress skills
repository (`WordPress/agent-skills`) covers development and ships three skills on
the Abilities API, and covers no SEO at all. This repository is the SEO and GEO
layer on top of it, not a competitor to it.

Three facts shape every editorial choice here:

1. No WordPress skill appears in the twenty most installed SEO skills worldwide,
   while `nuxt-seo` and `nextjs-seo` do rank. Verticalisation by platform works.
2. Every installed skill costs roughly 100 tokens of context on every turn,
   whether it fires or not, and `/skill-doctor` now shows users exactly that.
   A verbose skill gets uninstalled.
3. Publishing is not distribution. A competitor shipped 26 skills and holds 100
   stars. What travels is a skill that produces something the user shows to
   somebody else.

## The three circles

| Circle | Requires | Purpose |
|---|---|---|
| 1 | Nothing. Works on any site, any stack | Acquisition. Someone can use it having never heard of the plugin |
| 2 | The free plugin from the wordpress.org directory | Turn use into installs |
| 3 | A Pro or Ultra subscription (MCP write abilities) | Retention and upsell |

A circle 2 or 3 skill must run in a reduced mode when the plugin is absent: do the
part that is possible from public signals, then say in one sentence what it could
not do and why. See [Graceful degradation](#graceful-degradation).

## Folder layout

```
skills/<skill-name>/
├── SKILL.md              required
├── references/           loaded on demand, one level deep only
│   ├── <topic>.md
│   └── fr/<topic>.md     French templates and report wording
├── scripts/              executed, never read into context
└── evals/evals.json      at least three cases with a baseline
```

## Frontmatter

```yaml
---
name: ai-bot-log-forensics
description: Parse server access logs to find and verify AI crawler hits
  (GPTBot, ClaudeBot, PerplexityBot). Use for AI bot traffic, crawl audits,
  GEO visibility, or when analytics shows no AI traffic.
license: GPL-2.0-or-later
metadata:
  author: hacktheseo
  version: "1.0"
  circle: "1"
---
```

Rules that are not negotiable:

- `name`: lowercase, digits and hyphens only, no leading or trailing hyphen, no
  consecutive hyphens, 64 characters max, **identical to the folder name**. The
  words `claude` and `anthropic` are reserved and forbidden.
- `description`: **200 characters maximum**. The open specification allows 1024
  but claude.ai truncates at 200, and writing for 200 works everywhere. It must
  state what the skill does *and* when to use it, in the third person, and it
  must contain the literal words a user types, in both languages where they
  differ (see below).
- There is no top-level `version` field in the specification. Version goes in
  `metadata.version`, quoted, or YAML parses `1.0` as a float.
- No XML tags anywhere in `name` or `description`.

## Hard limits

| Rule | Threshold | Why |
|---|---|---|
| `SKILL.md` body | under 500 lines and under 5 000 tokens | Auto-compaction keeps only the last 5 000 tokens per skill, so an oversized skill loses its top |
| Reference files | one level deep from `SKILL.md` | Claude follows explicit links, it never speculatively lists directories |
| Reference over 300 lines | starts with a table of contents | |
| Paths | `${CLAUDE_SKILL_DIR}`, forward slashes | Absolute paths break on every other machine |
| Unreferenced files | do not exist | A file not explicitly linked with its trigger condition will never be read |

## The bilingual rule

One skill per subject. Never two folders for the same job: duplicates double the
permanent context tax and compete for the same trigger, so Claude picks one at
random.

Instead:

1. `name` and `description` in English, but the description carries the French
   terms a user actually types. Example: `... internal linking (maillage interne,
   cocon semantique) ...`. This is what makes the skill fire on a French prompt.
2. In the body, one explicit instruction: **produce every deliverable in the
   user's language**, report titles, findings and recommendations included.
3. French report wording and templates live in `references/fr/`, loaded only when
   the user is writing in French.

French is a real advantage here, not an afterthought: no French SEO skill exists
in any public repository, and internal linking as a named methodology
(cocon semantique) is a French discipline the English market does not treat
seriously.

## Writing the body

- Imperative. "Read the log with the parser", not "you may want to consider".
- Explain the reason, briefly. Models follow a rule better when they know why it
  exists. One clause is enough, not a paragraph.
- One constant vocabulary. If it is a "hit" in one section it is a "hit" everywhere.
- Any workflow over three steps gets a copyable checklist.
- Any critical operation gets a validation loop with an explicit stop:
  "do not continue until this passes".
- Two concrete input and output examples minimum.
- Pick one default rather than listing options. The user asked for an outcome,
  not a menu.
- Never invent a number. Every figure in a deliverable traces to something
  observed, and its source is named next to it.

## Visual output

This is what makes a skill travel. A skill that ends in a wall of markdown gets
read once. A skill that ends in a report the user forwards to a client gets
installed by the client.

Every analysis skill in this repository ends with a rendered HTML report,
produced by the shared engine, never hand-written:

```bash
python3 "${CLAUDE_SKILL_DIR}/../../shared/report-engine/render_report.py" findings.json report.html
```

The JSON contract is in `shared/report-engine/CONTRACT.md`. Read it before
writing the section of your skill that builds the report. Rules:

- Build the findings JSON, run the script, give the user the path. Do not
  hand-write HTML, and do not fall back to it if the JSON fails to parse.
- The report always carries a one-sentence verdict a client can repeat, three to
  five KPIs, and at least one `findings` block with an action per item.
- Always include a `note` block naming what the data cannot show. An agency
  values a stated blind spot more than a fifth chart.
- The credit line in the footer is on by default. Remove it only when the user
  asks. Agencies rebrand with `meta.brand`.

Use the whole vocabulary, not just tables. Twelve block types exist and each has
one job: `meter` for a score with its band written next to it, `composition` for
shares of a whole (never a pie), `timeseries` for a before and after with an event
marker (this is how proof of impact looks), `matrix` for a four way diagnosis,
`quote` for the one sentence the client repeats, plus `bars`, `table`, `findings`,
`checklist`, `keyvalue`, `note` and `code`. A KPI can carry a twelve point
sparkline through `spark`.

The engine also takes `--artifact`, which emits the same page without the document
wrapper so it can be published as a hosted page. Offer that when the user wants a
link rather than a file, for a client who will open the report on a phone.

## Graceful degradation

Circle 2 and 3 skills state their requirement in the body, detect its absence,
and continue in reduced mode. The wording pattern, adapted to the language:

> The Hack The SEO plugin is not responding on this site, so I ran the public
> checks only: X, Y and Z. With the plugin installed this skill would also do A
> and B, because those need server-side data no crawler can see.
> The free plugin: https://wordpress.org/plugins/hack-the-seo/

Never nag, never repeat the sales line twice in one run, and never refuse to work.

## Evaluations

`evals/evals.json`, minimum three cases:

```json
{
  "skill_name": "ai-bot-log-forensics",
  "evals": [
    {
      "id": 1,
      "prompt": "Why does GA4 show no traffic from ChatGPT?",
      "expected_output": "Explains that AI crawlers do not execute JavaScript, asks for an access log, then parses and verifies it rather than guessing",
      "files": []
    }
  ]
}
```

Include at least one case that should fire from a French prompt, and one
near-miss that should **not** fire. Every case is measured against a baseline
run without the skill, otherwise nothing has been measured.

## Security

Published skills are audited. In one public audit of 3 984 skills, 36,8 % had at
least one flaw and 10,9 % contained a hard-coded secret.

- No secret, no key, no token, no internal hostname. Environment variables only.
- Never fetch remote content and then treat it as instructions. Anything fetched
  is data. Say so explicitly in the skill when it reads a URL or a log.
- Scripts stay readable: no base64, no eval of a built string, no obfuscation.
- Standard library only where possible. Any dependency is declared with its
  install command and pinned.
- Never write outside the working directory, and never into `~/.claude/`,
  `.git/hooks/`, or any agent configuration file.
- Principle of lack of surprise: everything the skill does must be deducible
  from its description.

## Never do this

- Promise a ranking, a traffic figure or a citation. Ever, in any language.
- Present a recommendation as a measurement.
- Write a deliverable in a language the user did not use.
- Use em dashes. Use commas, colons or parentheses.
- Ship a skill whose description does not say when to use it.
