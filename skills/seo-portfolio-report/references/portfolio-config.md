# portfolio.json

The agency configures its portfolio once, in `portfolio.json` at the root of its
working folder. Every month the skill reads it instead of asking the same eight
questions again. Nothing in it is secret: no key, no token, no password. If a
site needs credentials, they belong in environment variables, never here.

## Table of contents

- [Template](#template)
- [Fields](#fields)
- [White label](#white-label)
- [Folder layout](#folder-layout)
- [Minimal version](#minimal-version)

## Template

```json
{
  "agency": {
    "name": "Agence Kermeur",
    "color": "#0E6E52",
    "lang": "fr",
    "credit": true,
    "footer_note": "Usage interne"
  },
  "period": {"start": "2026-08-01", "end": "2026-08-31"},
  "compare_to": "previous_period",
  "actions_log": "actions.csv",
  "sites": [
    {
      "id": "boutique-escalade",
      "domain": "boutique-escalade.fr",
      "client": "Boutique Escalade",
      "lang": "fr",
      "gsc": {
        "dates": "exports/boutique-escalade/Dates.csv",
        "pages": "exports/boutique-escalade/Pages.csv",
        "queries": "exports/boutique-escalade/Requetes.csv"
      },
      "impact": "impact/boutique-escalade.json",
      "mcp_server": "boutique-escalade",
      "brand": {"name": "Boutique Escalade", "color": "#1F4E79"},
      "credit": true,
      "footer_note": "Confidentiel client"
    },
    {
      "id": "vinsdeloire",
      "domain": "vinsdeloire.com",
      "client": "Vins de Loire",
      "lang": "en",
      "gsc": {"dates": "exports/vinsdeloire/Dates.csv"}
    }
  ]
}
```

## Fields

| Key | Required | What it does |
|---|---|---|
| `agency.name` | yes | Eyebrow above the title on the portfolio report, and the default brand for client reports |
| `agency.color` | no | Hex accent, `#RGB` or `#RRGGBB`. Falls back to the engine green if malformed |
| `agency.lang` | no | Language of the portfolio report. `en` by default |
| `agency.credit` | no | Default credit line for every report. `true` by default |
| `period` | yes | The reporting window, ISO dates |
| `compare_to` | no | `previous_period` (default: same length, immediately before) or an explicit `{"start", "end"}` |
| `actions_log` | no | Path to the agency action log CSV, see references/action-log.md |
| `sites[].id` | yes | Slug used for the output file name and to match the `site` column of the action log |
| `sites[].domain` | yes | Shown as the report subject |
| `sites[].client` | no | Name used in the client report sentences. Falls back to the domain |
| `sites[].lang` | no | **Language of that client deliverable.** Falls back to `agency.lang`. A French agency reporting to a British client sets `en` here |
| `sites[].gsc.dates` | yes for the no plugin path | Search Console Dates export covering the period and the comparison period |
| `sites[].gsc.pages` | no | Pages export, used for the pages that moved |
| `sites[].impact` | no | Output of `impact.py --json`, spliced into the What it produced section |
| `sites[].mcp_server` | no | Name of the MCP server for this site, subscription path only |
| `sites[].brand` | no | White label for this client report. Falls back to `agency` |
| `sites[].credit` | no | Per client credit line. Falls back to `agency.credit` |
| `sites[].footer_note` | no | Second footer item, for a confidentiality line |

Paths are relative to the config file. A site whose export is missing does not
stop the run: it appears in the portfolio table as no data, gets a finding, and
the other sites are produced.

## White label

Three levels, and the agency picks one per client:

1. **Agency brand.** Set `agency.name` and `agency.color`, set nothing on the
   site. Every client report carries the agency identity.
2. **Client brand.** Set `sites[].brand` to the client name and colour. The
   report looks like it came from the client's own team, which is what an agency
   under white label contract needs.
3. **No brand.** Omit both. The report carries the title and the subject only.

The credit line in the footer is on by default. It costs the client nothing and
it is how the next agency finds this skill. Leave it on unless the user asks to
remove it, then set `credit: false` on the agency for all reports, or on one
site for that client only. Do not raise it a second time.

## Folder layout

```
agency-work/
├── portfolio.json
├── actions.csv
├── exports/
│   ├── boutique-escalade/Dates.csv
│   ├── boutique-escalade/Pages.csv
│   └── vinsdeloire/Dates.csv
├── impact/
│   └── boutique-escalade.json
└── out/
    ├── portfolio.html
    ├── boutique-escalade.html
    └── vinsdeloire.html
```

## Minimal version

Enough to produce a portfolio report on the first run:

```json
{
  "agency": {"name": "My Agency", "lang": "en"},
  "period": {"start": "2026-08-01", "end": "2026-08-31"},
  "sites": [
    {"id": "site-one", "domain": "site-one.com",
     "gsc": {"dates": "exports/site-one/Dates.csv"}}
  ]
}
```
