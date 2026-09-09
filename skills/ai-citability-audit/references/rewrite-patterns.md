# Rewrite patterns

Templates for step 4 of `ai-citability-audit`: turning a low-scoring passage
into a quotable one. English deliverables. For French, use
`references/fr/rewrite-patterns.md`.

## Table of contents

- [The shape](#the-shape)
- [The five moves](#the-five-moves)
- [Patterns by intent](#patterns-by-intent)
- [Before and after](#before-and-after)
- [Rules that override the templates](#rules-that-override-the-templates)
- [Checklist before you hand a rewrite over](#checklist-before-you-hand-a-rewrite-over)

## The shape

Every rewrite has three parts, in this order.

1. **The heading is the question.** The words a person types, not a theme.
2. **The answer, 40 to 60 words, self-contained.** It names its subject in
   full, carries at least one checkable fact, and can be read having read
   nothing else on the page.
3. **The development, 70 to 110 words.** The nuance, the exception, the method,
   the source. This is where conditions and edge cases go, never in the answer.

Target total: 130 to 170 words. That is the band where a passage carries a
complete answer and still fits into one without being condensed.

## The five moves

Apply only the ones the score calls for, and name the move in the report so the
client sees the reason, not just the new text.

| Move | Fires when | What to do |
|---|---|---|
| Retitle | Interrogable form under 10 | Turn the heading into the question the passage answers. Keep the client's vocabulary |
| Front-load | Direct answer under 15 | Move the answer to sentence one. Cut the run-up entirely, do not relocate it |
| De-anaphorise | Autonomy under 15 | Replace every `this`, `the latter`, `as seen above` with the noun it stands for |
| Plant a fact | Fact density under 6 | Add a number, a date, a threshold or a name **the client already published**. Never invent one |
| Name the source | Attribution under 5 | Add `according to <source>, <date>` next to the figure it supports |

## Patterns by intent

Fill the brackets from the client's own content. If a bracket has no source,
leave it as a bracket in the deliverable and say the client has to supply it.

**Definition**
`<Term> is <category> that <function>. <Distinguishing fact with a number or a date>.`

**Price**
`<Product> costs between <low> and <high> <currency> per <unit>, as of <date>.
<What changes the price>, according to <source>.`

**Comparison**
`<A> and <B> differ on <criterion>: <A> <value A>, <B> <value B>. Choose <A>
when <observable condition>, <B> when <observable condition>.`

**How to**
`To <task>, <action 1>, then <action 2>. It takes <duration> on <version or
context>. <Prerequisite>.`

**Eligibility**
`<Who> qualifies if <condition 1> and <condition 2>. <Who> does not qualify.
The threshold is <figure>, set by <authority> in <date>.`

**Deadline or duration**
`<Process> takes <duration>, from <start event> to <end event>. <What extends
it>, according to <source>.`

## Before and after

**Case 1, teaser heading and a context opener.**

Before, 72 words, score 21:

> ## The heart of the matter
> It obviously depends on the context. As seen above, that last point decides
> the trade-off, and it is worth keeping in mind before any decision. Vendors
> know it, which explains how their offers are built.

After, 141 words, expected band `quotable as is`:

> ## Is a free SEO plugin enough for a small business site?
> Yes, a free SEO plugin covers a site of under 20 pages. Titles, meta
> descriptions and the XML sitemap are in the free versions of Yoast SEO, Rank
> Math and All in One SEO. Paid licences buy volume handling, not better SEO.
>
> The threshold sits around 50 pages, where editing tags one by one starts to
> cost more than the licence. Above it, the paid features that pay for
> themselves are bulk redirects and the crawl of the whole site in one pass.
> Below it, the free version leaves nothing on the table, and the vendor
> comparison stops mattering.

What changed: retitle, front-load, de-anaphorise, plant a fact. Four moves, and
the report names all four.

**Case 2, a fact with no owner.**

Before, score 58: `Most sites see a significant improvement after a few months.`

After: `Sites that rewrote their H2 headings as questions gained an average of
14 quoted passages in three months, on a sample of 40 client sites measured
between January and April 2026 (internal count, method described below).`

If the client has no such measurement, the correct rewrite is to delete the
claim, not to soften it. A vague claim scores zero on fact density and zero on
attribution, and it costs the page credibility on both.

## Rules that override the templates

- Never invent a figure, a date, a source, a name or a study. A bracket the
  client has to fill is an acceptable deliverable, a fabricated number is not.
- Keep the meaning. A rewrite that changes what the client asserts is not a
  rewrite, it is a different claim, and the client is the one who answers for it.
- Keep the client's vocabulary and register. Do not translate their product
  names into generic terms.
- Do not add a heading level. Rewrite the H2 as an H2.
- One question per passage. If the passage answers two, split it and say so.
- Never promise the rewrite will get the passage quoted. The rewrite removes
  known obstacles, which is all anyone can honestly claim.

## Checklist before you hand a rewrite over

- [ ] The heading is a question a person would type
- [ ] Sentence one answers it, in 40 to 60 words with the subject named in full
- [ ] No `this`, `that`, `the latter`, `as seen above`, `below`
- [ ] At least one checkable fact, taken from the client's own content
- [ ] Any figure carries its source and its date
- [ ] Total between 130 and 170 words
- [ ] The before and after are both in the report, with the moves named
