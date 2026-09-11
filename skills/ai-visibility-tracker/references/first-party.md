# First party AI data, and referral traffic

Surveys measure what engines answer. These sources measure what the engines'
owners report, for the site itself. Add them to the report when the client
has them; they are the only figures no survey can dispute.

## Google Search Console

A "Generative AI performance" report since June 2026: **impressions only** for
AI Overviews and AI Mode, by page, country, date and device. No clicks, no
queries, no position. Two results of the same site in one AI feature count as
one impression. The same impressions are also inside the main Web search
report: never add the two. Google says the rollout reached all sites on
31 August 2026, while the same page says not every property has it yet.
https://support.google.com/webmasters/answer/16984139

## Bing Webmaster Tools

"AI Performance", public preview since 10 February 2026: total citations,
cited pages, grounding queries and trends across Copilot, Bing AI summaries
and some partners. Intents, topics and a citation share added in June 2026.
No clicks, no competitors.
https://blogs.bing.com/webmaster/February-2026/Introducing-AI-Performance-in-Bing-Webmaster-Tools-Public-Preview

## Analytics

- GA4 has a default "AI Assistant" channel since May 2026 (ChatGPT, Gemini,
  Claude among its examples; the full list is unpublished; older data is not
  reclassified).
- ChatGPT adds `utm_source=chatgpt.com` to the links it shows; check the exact
  value in the site's own data. Perplexity, Gemini, Claude and Copilot arrive
  as referrers without UTM; links opened in apps often land in Direct.
- AI Overviews and AI Mode clicks arrive as Google organic.
- Scale, to keep the conversation grounded: Conductor measured AI referrals
  at 1.08 % of visits across 13 770 domains (May to September 2025), 87.4 %
  of them from ChatGPT; Ahrefs measured ChatGPT at about 0.21 % of traffic
  against Google near 40 % across 76 000 sites (2026).
  https://searchengineland.com/ai-1-traffic-mostly-chatgpt-464653

A visit from an AI answer is a human who clicked. A crawler hit is not a
visit: that is `ai-bot-log-forensics`.
