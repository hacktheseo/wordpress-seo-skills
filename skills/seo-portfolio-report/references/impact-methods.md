# Impact methods

How to show that the work of the month did something, without a statistics
package and without lying. Three methods, ordered by what they cost and what
they can support. Then the traps, which matter more than the methods.

## Table of contents

- [Why this exists](#why-this-exists)
- [Method 1: before and after with a control group](#method-1-before-and-after-with-a-control-group)
- [Method 2: changepoint detection](#method-2-changepoint-detection)
- [Method 3: difference in differences](#method-3-difference-in-differences)
- [Running the script](#running-the-script)
- [Traps, and the answer to each](#traps-and-the-answer-to-each)
- [Wording that is allowed](#wording-that-is-allowed)

## Why this exists

Every SEO skill on the market recommends. None of them measures. The gap between
"we optimised 24 titles" and "the pages we touched moved 47 points more than the
ones we did not" is the gap between an invoice and a renewal.

None of these methods proves causality. They make one alternative explanation at
a time less plausible. That is the honest ceiling, and stating it is what makes
the rest credible.

## Method 1: before and after with a control group

**The minimum defensible measurement. Never ship a before and after without it.**

Take the pages you modified: that is the treated group. Take pages you did not
touch on the same site, comparable in template, topic and traffic level: that is
the control group. Compare the change of the treated group with the change of the
control group over the same calendar days.

Why the control group is not optional: seasonality, an algorithm update, a
Christmas peak, a competitor launch and a tracking change all hit both groups.
Whatever moved both is not your work. What is left over is the only part you can
discuss.

Choosing a control group, in order of preference:

1. Pages of the same template and same topic cluster, untouched, similar traffic.
2. Pages of the same template, any topic, untouched.
3. The rest of the site minus the treated pages. Weak, but better than nothing.

Rules:

- At least 28 days on each side of the action. 14 is the hard floor below which
  the script refuses to run.
- At least 10 pages in each group, or one page with real volume. Two pages at
  three clicks a day measure nothing.
- The control group must be frozen: if you touched it during the period, it is
  not a control any more, it is a second treatment.

## Method 2: changepoint detection

**Use it to date a movement, and to find out whether the date is yours.**

A series changes regime on a date. The question is whether that date is your
deployment date or something else. The script scans every possible split of the
series, keeps the one where the two halves differ most (a Welch statistic on the
means, minimum seven days per segment), and reports the date.

Then the reading, which is the whole point:

- The changepoint falls within a few days of your action: the timing is
  consistent with your action. Consistent, not caused.
- The changepoint falls three weeks before your action: something else happened.
  Go and find it before writing anything.
- **The same changepoint appears in the control series**: it is external.
  Seasonality, an algorithm update, a Search Console reporting change. The script
  flags this and downgrades its own verdict to a market wide movement.

A changepoint with no known cause is a finding worth writing down. It is the
starting point of next month's investigation, not a hole in the report.

## Method 3: difference in differences

**The next step, once the control group is clean.**

Difference in differences is the control group method with the arithmetic made
explicit:

```
DiD = (treated_after - treated_before) - (control_after - control_before)
```

Expressed in percentage points, which is what an agency can read: the treated
group moved X percent, the control moved Y percent, the difference is X minus Y
points. That difference is the estimate of the effect.

The script also runs a permutation test: it reshuffles which days count as
before and which count as after, five thousand times with a fixed seed, and
reports how often chance alone produces a gap as large as the observed one. It
declares an effect only when the difference is at least 5 points **and** that
p value is under 0.05.

The assumption that makes it work, and that you must state: without the action,
the two groups would have moved in parallel. Check it by eye on the period before
the action. If the two curves were already diverging, difference in differences
is not usable and the honest answer is that this month cannot be measured.

The permutation p value assumes days are independent. Search traffic is
correlated from one day to the next, so the true p value is higher than the one
printed. The script says this in every run. Treat 0.04 as borderline, not as a
result.

## Running the script

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/impact.py" \
  --treated treated.csv --control control.csv \
  --action 2026-08-05 --lang fr --json impact.json
```

Series come from Search Console exports filtered by page, or from
`gsc_parse.py --emit-series`. The output carries a `blocks` array ready to splice
into the report findings JSON, in the report language.

Verdicts the script can return, and what each means:

| Verdict | Meaning | What to write |
|---|---|---|
| `insufficient_data` | Under 14 days on a side, or under 50 clicks | No measurement this month, say why |
| `no_control` | No control series given | Describe the movement, attribute nothing |
| `no_detectable_effect` | Under 5 points, or p at or above 0.05 | The data cannot separate an effect from noise |
| `market_wide_movement` | The control moved the same way | Not the work, name the external cause |
| `consistent_with_the_action` | Over 5 points and p under 0.05 | Compatible with the action, not proof |

A refusal is a correct answer. A wrong attribution costs the account the month
the client checks it.

## Traps, and the answer to each

**Concluding on 7 days.** A week contains one weekend and no reindexing cycle.
Google may not have recrawled the changed pages yet. Answer: 28 days each side,
14 as a hard floor, and the script refuses below it.

**Confusing seasonality with an effect.** A ski shop always climbs in November.
Answer: a control group on the same site absorbs it, because seasonality hits
both groups. Year over year comparison is a fallback, not a replacement: the site
was a different site last year.

**Attributing a sector wide move.** A core update lifts or sinks a whole vertical
in a week. Answer: the control group again, plus the changepoint check on the
control series. If the control has the same changepoint, it is not your work.
Before publishing an unusually good month, check whether an update landed on that
date.

**Ignoring a Search Console data window change.** Google changes what it counts,
and Search Console has had multiple reporting changes that move numbers without
anything moving on the site. Answer: a sharp step on the same date across every
site of the portfolio is a reporting artefact, not fifteen simultaneous SEO wins.
The portfolio view exists partly to make that visible.

**Forgetting the last three days.** Search Console has not finished counting the
most recent days when you export. Counting them makes every end of month look
like a collapse and every start of month look like a recovery. Answer: the
scripts drop the last 3 days by default and say so in the caption.

**Reading an average position as a ranking.** Average position mixes queries of
very different volumes, and a new query entering at position 40 lowers the
average while adding traffic. Answer: report it as context, never as an outcome,
and never as a promise.

**Measuring a page the client also changed.** The client redesigned the template
the same week. Answer: ask what changed on their side before running anything.
The action log is where that question stops being asked twice.

## Wording that is allowed

Allowed, because it describes what was observed:

- "Les pages modifiées ont progressé de 18 points de plus que les pages non
  modifiées du même site sur la même période."
- "Un changement de régime est détecté le 5 août, le jour de la mise en ligne."
- "Le mouvement touche aussi les pages non modifiées, il vient donc de
  l'extérieur."
- "Nous ne pouvons pas mesurer l'effet de cette action ce mois-ci : 12 jours de
  recul, il en faut 28."

Never, in any language:

- "Cette action a généré 340 clics." (attribution presented as a fact)
- "Nous atteindrons la première page en octobre." (promise)
- "L'optimisation des titres améliorera le CTR." (recommendation written as a
  measurement, in the section that reports results)
