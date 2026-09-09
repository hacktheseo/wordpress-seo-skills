# Render skeleton

The exact `findings.json` shape for this skill. Fill it from `metrics.json`
produced by `scripts/geo_measure.py`, never from memory. The full contract lives
in `shared/report-engine/CONTRACT.md`.

```bash
python3 "${CLAUDE_SKILL_DIR}/../../shared/report-engine/render_report.py" \
  findings.json geo-strategy.html
```

## Order of the sections

1. Prompt map, `bars` of presence per family.
2. Where to fight, the `matrix` of volume against presence.
3. The 90 day plan, a `table`.
4. Entity, a `findings` block.
5. Method and limits, a `checklist` plus a `note` on variance.

## Skeleton

```json
{
  "meta": {
    "title": "GEO strategy map",
    "subject": "example.com",
    "period": "Baseline 2026-09-08, plan to 2026-12-07",
    "lang": "en",
    "brand": {"name": "", "color": "#0E6E52"},
    "credit": true
  },
  "headline": {
    "verdict": "One sentence stating presence, the families at zero, and who is cited instead.",
    "detail": "Two lines: sample size, engines, runs, and what the plan attacks first."
  },
  "kpis": [
    {"label": "Prompts mapped", "value": "34", "tone": "neutral",
     "note": "6 families, 3 engines, 3 runs, 306 observations"},
    {"label": "Overall presence", "value": "28.1 %", "tone": "warn",
     "note": "86 cited observations out of 306"},
    {"label": "Most favourable engine", "value": "Perplexity 33.3 %", "tone": "good",
     "note": "ChatGPT 25.5 %, Gemini 25.5 %"},
    {"label": "Families with no presence", "value": "1 of 6", "tone": "bad",
     "note": "objection, 1 cited observation out of 36"}
  ],
  "sections": [
    {
      "title": "Presence by prompt family",
      "intro": "One line naming the survey date and the sample size.",
      "blocks": [
        {"type": "bars",
         "items": [
           {"label": "implementation (18 prompts)", "value": 64.8,
            "display": "64.8 %", "tone": "good"},
           {"label": "objection (12 prompts)", "value": 2.8,
            "display": "2.8 %", "tone": "bad"}
         ],
         "caption": "Source: survey of DATE, N observations. Rate = cited observations / observations."}
      ]
    },
    {
      "title": "Where to fight",
      "blocks": [
        {"type": "matrix",
         "axes": {"x": "Horizontal: family volume (prompts x weight)",
                  "y": "Vertical: presence measured on the baseline"},
         "quadrants": [
           {"title": "Monitor", "count": 1, "tone": "good",
            "reading": "Low volume, presence already held. One check per wave, no investment.",
            "items": ["qualification"]},
           {"title": "Defend", "count": 1, "tone": "good",
            "reading": "It works. Keep the pages dated and fresh, watch for displacement.",
            "items": ["implementation"]},
           {"title": "Ignore", "count": 1, "tone": "neutral",
            "reading": "Out of scope this quarter, and said so on purpose.",
            "items": ["objection, evidence gap, not a content gap"]},
           {"title": "Attack", "count": 2, "tone": "bad",
            "reading": "High volume, low presence. This is where the 90 days go.",
            "items": ["replacement", "named-comparison"]}
         ],
         "caption": "Axes cut at the median across families, not at an absolute threshold."}
      ]
    },
    {
      "title": "The 90 day plan",
      "blocks": [
        {"type": "table",
         "columns": ["Wave", "Action", "Family", "Why now", "Days", "Owner", "Proof"],
         "numeric_columns": [4],
         "rows": [["1", "Correct the founding year on Wikidata", "entity",
                   "Priority 2, 3 engines answer wrong", "1", "NAME",
                   "Wikidata revision id"]],
         "caption": "Score = (prompts x weight x (1 - presence)) / days. Sorted by score."}
      ]
    },
    {
      "title": "Entity",
      "blocks": [
        {"type": "findings",
         "items": [
           {"severity": "high", "title": "The model states the wrong founding country",
            "evidence": "Quote the model answer verbatim, with engine and date.",
            "action": "One thing doable this week."}
         ]}
      ]
    },
    {
      "title": "Method and limits",
      "blocks": [
        {"type": "checklist",
         "items": [
           {"label": "Prompt set frozen and versioned (prompts-v1.csv)", "done": true},
           {"label": "3 runs per prompt and per engine", "done": true},
           {"label": "Fresh sessions, no memory, no personalisation", "done": true},
           {"label": "Raw answers kept, one file per run", "done": true},
           {"label": "Control survey scheduled at day 30", "done": false}
         ]},
        {"type": "note", "tone": "warn", "title": "What these figures cannot show",
         "text": "State the noise floor printed by the script, the fact that repetitions of the same prompt are correlated so the real floor is wider, and that a survey measures what the engines answered on that date from that country, not a ranking."}
      ]
    }
  ]
}
```

## Rules specific to this deliverable

- Every rate carries its denominator, in the value or in the `note`.
- A family with fewer than 5 prompts is presented as an observation, not a
  percentage. Put the count in `display`, for example `1 / 36 observations`.
- The `note` on variance is mandatory. Remove any other block before removing it.
- Never write a target rate, a position or a traffic figure anywhere in the plan
  table. Objectives are work delivered and facts corrected.
- French deliverables: wording, KPI labels and quadrant names come from
  `references/fr/rapport.md`.
