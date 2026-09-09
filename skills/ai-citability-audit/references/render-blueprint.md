# Render blueprint

The JSON skeleton for step 8 of `ai-citability-audit`. The full contract is in
`shared/report-engine/CONTRACT.md`. This file is the copyable shape, already
filled with the blocks this skill must always produce.

## Table of contents

- [Required blocks](#required-blocks)
- [Skeleton](#skeleton)
- [Filling the citability map](#filling-the-citability-map)
- [Filling the criterion table](#filling-the-criterion-table)
- [Filling the rewrites](#filling-the-rewrites)
- [Render and check](#render-and-check)

## Required blocks

| Order | Section | Block | Never omit because |
|---|---|---|---|
| 1 | Citability map | `bars`, one bar per passage | This is the image the client forwards. It is the whole point of scoring passages instead of pages |
| 2 | Criterion detail | `table`, one row per passage | Turns the score into something a writer can act on |
| 3 | What drags the page | `findings` | A file without a findings block is a data dump |
| 4 | Rewrites | `findings` plus `code` pairs | Five worst passages, before and after |
| 5 | Schema alignment | `keyvalue` or `table` | The FAQPage check |
| 6 | Method and limits | `note` with `tone: "warn"` | The scale is a heuristic, and that has to be written down |

## Skeleton

```json
{
  "meta": {
    "title": "AI citability audit",
    "subject": "https://example.com/page/",
    "period": "Served HTML fetched 2026-09-09",
    "lang": "en",
    "credit": true
  },
  "headline": {
    "verdict": "Six of the page's 14 passages are quotable as is, and the four that open on a run-up carry every figure on the page.",
    "detail": "Median passage score 61. The page is not short of facts, it buries them under context sentences."
  },
  "kpis": [
    {"label": "Median passage score", "value": "61 / 100", "tone": "warn",
     "note": "Median of 14 passages"},
    {"label": "Quotable as is", "value": "6 / 14", "tone": "neutral",
     "note": "Score 80 and above"},
    {"label": "To rewrite or cut", "value": "5", "tone": "bad",
     "note": "Score under 60"},
    {"label": "Invisible without JavaScript", "value": "12.7 %", "tone": "bad",
     "note": "93 body words absent from the served HTML"}
  ],
  "sections": [
    {"title": "Citability map", "intro": "One bar per passage, in page order.",
     "blocks": [{"type": "bars", "items": [], "caption": "Score out of 100. Green: quotable as is. Grey: one edit away. Amber: rewrite. Red: filler."}]},
    {"title": "Criterion detail", "blocks": [{"type": "table", "columns": [], "rows": [], "numeric_columns": []}]},
    {"title": "What drags the page down", "blocks": [{"type": "findings", "items": []}]},
    {"title": "Five rewritten passages", "blocks": []},
    {"title": "Schema markup against visible content", "blocks": [{"type": "keyvalue", "items": []}]},
    {"title": "Method and limits", "blocks": [{"type": "note", "tone": "warn", "title": "What this cannot show", "text": ""}]}
  ]
}
```

## Filling the citability map

One item per passage, in page order, so the reader sees where the page collapses.

```json
{"label": "H2 How much does an SEO plugin cost?", "value": 90, "display": "90", "tone": "good"}
```

- `label`: heading level and heading text, truncated at about 55 characters.
- `value` and `display`: the score out of 100.
- `tone`: `good` at 80 and above, `neutral` 60 to 79, `warn` 40 to 59, `bad` under 40.
- A passage absent from the served HTML gets `bad` and its label ends with
  `(JS only)`.

## Filling the criterion table

Columns: `Passage`, `Extract.`, `Autonomy`, `Answer`, `Facts`, `Form`,
`Length`, `Attrib.`, `Total`, `Band`. Set `numeric_columns` to
`[1, 2, 3, 4, 5, 6, 7, 8]`. One row per passage, points not comments. Put the
cap in the `Band` cell when one fired, for example `Filler (JS cap 25)`.

Caption: name the source of every number, for example
`Measured by scripts/segment_passages.py on the served HTML, 9 September 2026. Scale: references/scoring.md.`

## Filling the rewrites

For each of the five lowest passages, one `findings` item followed by two
`code` blocks.

```json
{"type": "findings", "items": [
  {"severity": "high", "title": "Passage 3: The heart of the matter",
   "evidence": "72 words, 5 anaphora including one in the first sentence, no figure, heading not interrogable. Score 21.",
   "action": "Retitle as a question, front-load the answer, de-anaphorise, plant a fact already published on the site."}]},
{"type": "code", "text": "BEFORE\n\n## The heart of the matter\nIt obviously depends on the context...",
 "caption": "Current text, copied from the served HTML."},
{"type": "code", "text": "AFTER\n\n## Is a free SEO plugin enough for a small business site?\nYes, a free SEO plugin covers a site of under 20 pages...",
 "caption": "Proposed rewrite, 148 words. Every figure comes from the page itself."}
```

Severity: `high` under 40, `medium` 40 to 59, `low` 60 to 79.

## Render and check

```bash
python3 "${CLAUDE_SKILL_DIR}/../../shared/report-engine/render_report.py" findings.json citability.html
```

The script exits non-zero and prints the offending line when the JSON is bad.
Fix the JSON. Never hand-write the HTML, and never fall back to it.

Then check three things before handing over the path: the bars section has one
item per passage, every score in the table appears in the map with the same
value, and the limits note is present.
