# Report engine contract

`render_report.py` turns a findings JSON file into one self-contained HTML report.
Standard library only, no network, no web fonts, no external assets. The output
opens offline, prints to a clean PDF, reads in light and dark, carries the
agency's own name and colour, and can be published as an artifact as is.

```bash
python3 "${CLAUDE_SKILL_DIR}/../../shared/report-engine/render_report.py" findings.json report.html
```

Write the JSON, run the script, hand the user the HTML path. Never hand-write the HTML.

## Table of contents

- [Top level](#top-level)
- [meta](#meta)
- [headline](#headline)
- [kpis](#kpis)
- [sections and blocks](#sections-and-blocks)
- [Block types](#block-types)
- [Design rules the engine enforces](#design-rules-the-engine-enforces)
- [Rules for you](#rules-for-you)

## Top level

```json
{
  "meta": { },
  "headline": { },
  "kpis": [ ],
  "sections": [ ]
}
```

Only `meta` and `sections` really matter. Everything else is optional.

## meta

| Key | Type | Notes |
|---|---|---|
| `title` | string | Report name. Short noun phrase, no explainer after a colon |
| `subject` | string | The site, folder or portfolio the report is about |
| `prepared_for` | string | The person or team receiving it. Shown on the cover |
| `period` | string | Free text, e.g. `1 au 31 août 2026` |
| `generated` | string | ISO date. Defaults to today |
| `lang` | `"en"` or `"fr"` | Drives the built-in labels. Match the user's language |
| `brand.name` | string | Agency name. Shown on the cover with its initials in a mark |
| `brand.color` | string | Hex like `#1F6F4E`. Any hue works, see below |
| `credit` | bool | Defaults `true`. Set `false` only when the user asks |
| `footer_note` | string | Second footer item, e.g. a confidentiality line |

## headline

```json
{
  "eyebrow": "In short",
  "verdict": "One sentence a client can repeat in a meeting.",
  "detail": "Two or three lines of context."
}
```

The verdict is the single most important sentence of the report. Write it as a
finding, not a description: "AI crawlers read your blog and ignore your catalogue",
not "Analysis of crawler traffic". Keep it under about 15 words: it is set large,
and a long one wraps into a paragraph and stops reading as a headline.

## kpis

Three to five, never more (the engine renders the first five). Each: `label`,
`value`, optional `delta`, `note`, `spark`, and `tone` in `good` / `warn` / `bad` /
`neutral`.

```json
{"label": "AI crawler hits", "value": "1 812", "delta": "+34% vs July",
 "tone": "good", "note": "GPTBot 61%, ClaudeBot 22%",
 "spark": [980, 1042, 1120, 1098, 1240, 1310, 1288, 1402, 1455, 1520, 1690, 1812]}
```

`delta` is a change against a named period, not a description. "+34% vs July" is a
delta, "median of pages" is not: that belongs in `note`.

`spark` is an optional series of at least 3 numbers, last 12 used, drawn as a
sparkline with the final point marked. Give it raw numbers, not formatted strings.

## sections and blocks

```json
{"title": "Who actually crawled", "intro": "One line of context.",
 "blocks": [ {"type": "table", "title": "Optional", "...": "..."} ]}
```

Sections are numbered automatically. Four or more sections produce a table of
contents on the cover page. Every block accepts an optional `title` (a small
heading above it) and `caption` (small type underneath, for the source of the data
and its limits).

## Block types

**table** `columns` (array of strings), `rows` (array of arrays),
`numeric_columns` (zero-based column indexes, rendered tabular and right-aligned).

**bars** Magnitude across items. `items`: `[{"label", "value", "display", "tone"}]`.
Widths are computed against the largest value. `display` is printed, `value` is
measured.

**composition** One horizontal stacked bar plus a legend, for shares of a whole.
Use it instead of a pie or a donut, always. `items`: `[{"label", "value",
"display", "tone"}]`. Without `tone`, segments take steps of a one hue ramp from
the brand colour, largest first. Percentages are computed for you.

**meter** A score on a fixed scale. `value`, `max` (default 100), `display`,
`band` (a short written verdict such as "needs work"), `label` (what the score
means), `tone`, `ticks` (array of scale marks). The band is what stops the colour
from carrying the meaning alone.

**timeseries** A line chart, and the way to show proof of impact.
`series`: `[{"label", "values": [...]}]`. The first series is the treated group in
the accent colour with a light area fill and an end dot; every later series is a
dashed grey line, which is what a control group should look like. `labels`
(first and last x labels), `high_label` and `low_label` (the y scale ends), and
`event`: `{"index": 35, "label": "Fix shipped, 5 Aug"}` drawing a vertical rule at
that point in the series. Put the before and after numbers in the `caption`.

**matrix** A 2x2 diagnostic grid. `quadrants`: exactly four objects with `title`,
`reading` (what being in this quadrant means), `count`, `items`, `tone`. Optional
`axes`: `{"x": "...", "y": "..."}`. Order is top-left, top-right, bottom-left,
bottom-right.

**findings** The spine of any report. `items`: `[{"severity", "title", "evidence",
"action"}]`, numbered automatically. Severity is `high` / `medium` / `low` / `info`.
Always fill `evidence` with an observed fact and `action` with something the reader
can do this week.

**quote** A pulled sentence, set large against a rule. `text`, optional `source`.
Use it once per report at most, for the one line you want repeated.

**checklist** `items`: `[{"label", "done"}]`.

**keyvalue** `items`: `[{"label", "value"}]`. For a settings or parameters snapshot.

**note** `title`, `text`, `tone`. For a caveat, a method note, or a limit.

**code** `text`, optional `label`. A command the reader can copy.

## Design rules the engine enforces

You do not have to think about these, but knowing them explains the output.

- **The brand colour is corrected, never rejected.** A pale brand colour would make
  every mark unreadable, so the engine steps it towards black (light theme) or
  white (dark theme) until it clears 3:1 against the surface for marks and 4.5:1
  for text, keeping the hue. A malformed value falls back to the house green.
- **Status colours are fixed and never themed**, and always sit next to a written
  label, because two of them fall below 3:1 on a light surface and colour must
  never carry meaning alone.
- **Only a genuine problem colours a figure.** A `bad` KPI turns red; `good` and
  `warn` values stay in ink and let the delta chip carry the direction. A report
  where every number is coloured reads as a toy.
- Bars are capped, with a rounded data end and a square baseline. Stacked segments
  are separated by a 2px gap in the surface colour, never by a stroke.
- Both themes are designed, not flipped. Print gets its own stylesheet, with
  sections and findings kept off page breaks.

## Rules for you

1. Every value is escaped by the engine. Never pre-escape, never inject HTML.
2. A report with no `findings` block is a data dump, not a report. Include one.
3. Say what the data cannot show. A `note` with `tone: "warn"` naming the blind
   spot is worth more to an agency than a fifth chart.
4. Never invent a number. Every figure traces to something observed, and its
   source belongs in the `caption` next to it.
5. If the JSON fails to parse, the script exits non-zero and prints the line.
   Fix the JSON, do not fall back to writing HTML by hand.
