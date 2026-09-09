# The 90 day plan

The main deliverable. Three waves, twelve actions maximum, one control survey per
wave, and a priority rule the client can argue with.

## Table of contents

- [The priority rule](#the-priority-rule)
- [The 2x2 and its four strategies](#the-2x2-and-its-four-strategies)
- [The three waves](#the-three-waves)
- [Writing an objective](#writing-an-objective)
- [The action table](#the-action-table)
- [The twelve action ceiling](#the-twelve-action-ceiling)

## The priority rule

```
score = (prompts_in_family x volume_weight x (1 - presence_rate)) / effort_days
```

- `prompts_in_family`: counted in the map.
- `volume_weight`: 1 to 3, justified by a counted source (see
  `prompt-taxonomy.md`).
- `presence_rate`: from the baseline survey, as a fraction.
- `effort_days`: estimated by the team that will do the work, in whole days.
  Not by the consultant alone, or the plan will not be executed.

Worked example, one line: the replacement family holds 5 prompts, weight 3
(15 recurring pre-sales questions), presence 0.09, a migration page costs 3 days.
Score = (5 x 3 x 0.91) / 3 = 4.55. The implementation family holds 6 prompts,
weight 2, presence 0.65, 2 days per guide. Score = (6 x 2 x 0.35) / 2 = 2.10.
Replacement is done first, and the report states both numbers so the arbitration
is visible.

Print the score column in the plan table. A priority without an arithmetic is an
opinion.

## The 2x2 and its four strategies

Axes: horizontal, family volume (prompts x weight). Vertical, current presence
rate. Cut both axes at the median across families, and say in the report that the
cut is the median, not an absolute threshold.

| Quadrant | Strategy | What it means |
|---|---|---|
| High volume, high presence | **Defend** | It works. Keep the pages fresh and dated, watch for a competitor taking the slot. No new production |
| High volume, low presence | **Attack** | Where the 90 days are spent. Highest scores land here by construction |
| Low volume, high presence | **Monitor** | Cheap to hold. One check per wave, zero investment |
| Low volume, low presence | **Ignore** | Explicitly out of scope this quarter. Write it in the report so nobody spends a day on it by accident |

The matrix block in the report carries the meaning of each quadrant in its
`reading` field, so the page is readable without the consultant in the room.

## The three waves

### Wave 1, days 1 to 30. Foundation.

- Entity repairs in the order given by `entity-audit.md`, priorities 1 and 2 at
  minimum.
- One or two contents from the highest scoring attack family, so the wave is not
  purely technical.
- Control survey at day 30, same frozen prompt file, same engines, same runs.
- Objective: the facts the model got wrong are corrected at the source, and the
  baseline exists.

Entity work goes first because it is cheap, one time, and everything published
before it lands on a broken foundation.

### Wave 2, days 31 to 60. Attack.

- The attack quadrant, typically named-comparison and replacement.
- Comparison pages that name competitors, migration pages that state what breaks.
- Third party placement when the baseline showed citations pointing at forums and
  comparison blogs rather than the site.
- Control survey at day 60.
- Objective: the pages exist, are indexed, are reachable by AI crawlers, and the
  cited URL split has been re-measured.

### Wave 3, days 61 to 90. Consolidation and decision.

- Implementation and objection families, the objection work being evidence
  (pricing page, status page, security page, third party reviews) rather than
  writing.
- Final control survey, compared with the baseline with
  `scripts/geo_measure.py`.
- Objective: a keep or drop decision per action, written, with the noise floor
  next to every reported movement.

## Writing an objective

Never write a rate to be reached, a position or a traffic figure. Nobody controls
what a model answers, and a promise like that ends a client relationship in
90 days.

Write objectives as work delivered and facts corrected:

- Good: "the founding year and the country are correct in the three engines'
  answers to who is X, verified on a dated survey".
- Good: "the migration page exists, states the five things that break, and is
  cited or not cited on the next survey, which we will read against the noise
  floor".
- Bad: "reach 50 % presence on comparison prompts".
- Bad: "be cited by ChatGPT on the category prompts".

## The action table

One row per action, in the report as a `table` block:

| Column | Content |
|---|---|
| Wave | 1, 2 or 3 |
| Action | One verb, one object. "Write the migration page from X" |
| Family | The prompt family it serves, or `entity` |
| Why now | The score, or the entity priority |
| Effort | Days |
| Owner | A name, not a team |
| Proof | What will exist at the end: a URL, a corrected record, a dated survey |

The `Proof` column is what makes the plan auditable. An action with no proof is a
line item, not a commitment.

## The twelve action ceiling

Twelve is the ceiling, not the target. Eight to ten is a plan that gets executed.

If the sorted list is longer, cut from the bottom and write in the report which
actions were cut and their score. The cut list is a finding: it tells the client
what the next quarter holds, and it proves the arbitration was done rather than
avoided.

If a single family absorbs more than half the actions, check that the map is not
unbalanced before accepting it. A plan that is 70 % one family usually means the
prompt map was built from one source.
