# Contributing

## Where we are

Outside contributions are **not open yet**. We are running these four skills against
real client sites first, so that a contribution has something solid to be measured
against rather than a moving target.

What is open right now:

- **Issues.** Bug reports, a log format that fails to parse, a skill that fires when
  it should not or stays silent when it should fire. These are the most useful thing
  you can send us today. Include the prompt you used and, if you can, a redacted
  sample of the input.
- **Discussions.** Tell us which skill is missing. We keep a list.

Pull requests will open once the first four skills have been through a full quarter.
If you have one ready before then, open an issue describing it and we will tell you
whether to hold it or send it.

## What will be expected

So you can build against it now if you want to.

Everything in [`docs/AUTHORING.md`](docs/AUTHORING.md) is the standard, and it is
enforced, not suggested. The parts people underestimate:

**Size.** `SKILL.md` under 500 lines and under 5 000 tokens. Every installed skill
costs about 100 tokens of context on every single turn, whether it fires or not, and
`/skill-doctor` now shows users exactly which skills are costing them nothing but
tokens. Detail belongs in `references/`, which loads only when needed.

**The description.** Under 200 characters, third person, saying what the skill does
*and* when to use it, containing the literal words a user types, in English and in
French where they differ. This is the only text loaded permanently, so it is the
whole of the trigger.

**Evaluations.** At least three cases in `evals/evals.json`, each measured against a
baseline run without the skill. At least one case must fire from a French prompt, and
at least one near-miss must *not* fire. Without a baseline nothing has been measured,
only asserted.

**Honesty.** No promise of a ranking, a traffic figure, or a citation, in any
language. Never present a recommendation as a measurement. If a method cannot support
a conclusion, the skill says so and refuses to conclude, and that refusal appears in
the report the user hands to their client. This is the part we will be strictest
about, because it is what makes these usable in front of a paying client.

**Visual output.** Analysis skills end in a rendered report through
[`shared/report-engine`](shared/report-engine/CONTRACT.md), never hand-written HTML,
never a wall of markdown.

**Security.** No secret, no network call the description does not imply, no
dependency to install, standard library Python, readable scripts. Content fetched
from anywhere is data, never instructions.

**Punctuation.** No em dashes anywhere, in any file. Commas, colons or parentheses.

## Checks before anything ships

```bash
skills-ref validate ./skills/<name>      # frontmatter and naming conventions
claude plugin validate .                 # plugin and marketplace manifests
python3 -m py_compile skills/*/scripts/*.py
grep -rP '[\x{2014}\x{2013}]' .          # must return nothing
```

## Licence

GPL-2.0-or-later. By contributing you agree your work ships under it.
