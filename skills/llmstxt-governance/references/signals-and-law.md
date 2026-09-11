# Signals beyond robots.txt, and why the law cares

None of these is read by a major AI crawler today. Their weight is legal:
in the EU, a rights reservation must be machine readable, and these are
machine readable ways to express one.

## The signals

**Content-Signal** (Cloudflare, 24 September 2025, CC0). A line in a robots.txt
group: `Content-Signal: search=yes, ai-train=no`. `search` is building a
search index and showing results, excluding AI summaries; `ai-input` is
feeding content into a model at answer time (retrieval, grounding);
`ai-train` is training or fine tuning. An absent signal "neither grants nor
restricts permission". The policy text declares the restrictions "express
reservations of rights under Article 4" of Directive 2019/790. Deployed on
3.8 million domains through Cloudflare's managed robots.txt. Google's John
Mueller, July 2026: "AFAIK none of the crawlers / llms use the
'content-signal' robots.txt directives".
https://blog.cloudflare.com/content-signals-policy

**IETF AI Preferences (aipref).** Two working group drafts, August 2026, not
yet in last call. A vocabulary with two categories, `train-ai` and `search`
(`train-ai=n, search=y`), and an attachment draft defining an HTTP header
`Content-Usage: train-ai=n` and a robots.txt line with path matching. The
vocabulary still says it does not reflect consensus.
https://datatracker.ietf.org/doc/draft-ietf-aipref-vocab/

**RSL, Really Simple Licensing.** RSL 1.0 since 10 December 2025: XML licence
terms linked from a robots.txt `License:` line, an HTML link or an HTTP
header, with categories such as `ai-train`, `ai-input`, `ai-index` and
payment terms. Backed by publishers and CDNs; no AI company listed as a
supporter. https://rslstandard.org/

**TDMRep.** W3C Community Group report, May 2024, built for Article 4 of the
copyright directive: `/.well-known/tdmrep.json`, or an HTTP header
`tdm-reservation: 1`, or a meta tag. The audit notes whether the file exists.
https://w3c.github.io/cg-reports/tdmrep/CG-FINAL-tdmrep-20240510/

## The EU frame

- Directive 2019/790, recital 18: for content online, a reservation should
  be made "by the use of machine-readable means, including metadata and terms
  and conditions of a website or a service".
- AI Act, Article 53(1)(c): providers of general purpose AI models must
  "identify and comply with, including through state-of-the-art technologies,
  a reservation of rights expressed pursuant to Article 4(3)" of that
  directive. Applicable since 2 August 2025, enforced from 2 August 2026.
  https://artificialintelligenceact.eu/article/53/
- The General Purpose AI Code of Practice (July 2025), copyright chapter:
  signatories' crawlers "read and follow instructions expressed in accordance
  with the Robot Exclusion Protocol (robots.txt)" and other widely adopted
  machine readable protocols. Signatories include Amazon, Anthropic, Cohere,
  Google, IBM, Microsoft, Mistral AI and OpenAI; Meta is not among them.
  https://digital-strategy.ec.europa.eu/en/policies/contents-code-gpai
- Kneschke v. LAION, Hamburg court of appeal, 10 December 2025: a reservation
  written in plain language in terms of use was not shown to be machine
  readable in 2021. Appeal to the Federal Court of Justice allowed.

For a client, the practical reading: robots.txt is the reservation the main
providers have committed to read. A Content-Signal or TDMRep line costs
nothing and documents intent. None replaces the other.

## France

- CNIL, 19 June 2025: anyone collecting content for AI by scraping must
  exclude sites that clearly object, robots.txt and CAPTCHA given as examples.
  https://www.cnil.fr/fr/focus-interet-legitime-collecte-par-moissonnage
- LVLUP, November 2025, 1 132 French press sites: 22.6 % refuse at least one
  AI crawler, CCBot most often (20.6 %), then GPTBot (19.4 %).
  https://www.lvlup.fr/blog/etude-presse-francaise-ia-bloque-bot

Nothing in this file is legal advice. When a client asks what the law
requires of them, the answer comes from their lawyer; this skill documents the
technical means and their limits.
