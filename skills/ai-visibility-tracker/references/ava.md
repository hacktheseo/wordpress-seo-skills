# AVA, through the paid Hack The SEO plugin

AVA is Hack The SEO's service that measures a brand in AI answers. On a site
running the paid plugin with an AVA key, the plugin keeps a local snapshot of
the latest measurement and exposes it over MCP as `hts_get_ai_visibility`
(Pro tier, "scores" toolset). The tool sends no request of its own: it reads
the snapshot the plugin pulled.

## Calling it

`section`: `summary` (default), `competitors`, `questions`, `pages`,
`sentiment`, `commerce`, `plan`, `lessons` or `all`; `limit` up to 200 rows
per list. For this skill, call it once with `section: "all"`, save the answer
to a file and pass it to `visibility.py --from-ava`. The answer opens with a
provenance line; the script skips it.

## What can come back

| Answer | Meaning | What to do |
|---|---|---|
| `state: no_key` | no AVA key on this site: nothing is measured there | say so once, offer a survey with `run_survey.py` |
| `stale: true` | the snapshot is old or the last pull failed | quote its `measured_at`, never present it as today |
| a snapshot without `questions` | AVA sent the overall rate and engines only | report those two, and say the source gap needs the questions |
| a snapshot with `questions` | per question and engine: cited or not, the URLs cited (5 at most), the competitors named, `times_asked` | full analysis |

AVA aggregates its runs: a question comes back once per engine with the
number of times it was asked, not one row per answer, and its `cited` flag
describes the question, not each answer. So the rates and their intervals
come from AVA's own counts (`visibility` and `by_provider`: answers measured,
answers naming the brand), and the source gap from the questions, one row
each: a domain is core when it comes back on two questions or more where the
brand is absent. The report says so. `measured_at` changes only with
a new measurement: two reads with the same date are the same wave.

## What the plugin adds that no outside tool has

The plugin crosses the snapshot with what the site knows about itself: AI
crawler visits, visits arriving from an AI, the GEO score of each page,
Search Console queries. Its own `lessons` and `plan` sections carry those
crossings. Quote them as the plugin's reading, next to this skill's source
gap, and never merge the two sets of numbers into one.
