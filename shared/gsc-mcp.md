# Search Console, read live

The single step that loses people is "send me your Search Console exports".
A Search Console MCP removes it. Prefer it over a CSV every time it is present.

## The server

[mcp-gsc](https://github.com/AminForou/mcp-gsc) by Amin Forou. MIT, Python 3.11
or newer, twenty tools. Installed with `uvx mcp-search-console`.

**It is not ours.** Never assume it is connected, never tell a user to install it
as though it were part of this repository, and never break a run because it is
absent. It is one input among several.

## Detect it in one call

Look for `list_properties` or `get_capabilities` in your tool list. If neither is
there, drop to CSV exports and say so once, in the user's language, then keep
working. Do not ask twice.

## The twenty tools

**Properties**

| Tool | What it does |
|---|---|
| `list_properties` | Every property the credential can read. Start here |
| `get_site_details` | Details of one property |
| `add_site`, `delete_site` | **Write.** Off by default. Never call them |

**Search analytics**

| Tool | What it returns |
|---|---|
| `get_search_analytics` | Queries, clicks, impressions, CTR, position |
| `get_performance_overview` | The site's summary over a period |
| `compare_search_periods` | Two ranges against each other, which is the whole before and after |
| `get_search_by_page_query` | The queries that drive traffic to one page |
| `get_advanced_search_analytics` | The same, filtered by country, device, query or page |

**Indexing**, which no CSV export can give you

| Tool | What it returns |
|---|---|
| `inspect_url_enhanced` | Crawl and index status of one URL |
| `batch_url_inspection` | The same for up to **10 URLs per call** |
| `check_indexing_issues` | Indexing problems across several URLs |

**Sitemaps**

| Tool | What it does |
|---|---|
| `get_sitemaps`, `list_sitemaps_enhanced` | Status of the declared sitemaps |
| `manage_sitemaps` | **Write.** Submits or removes. Only on an explicit request |

**Utility**: `get_capabilities` (tools plus auth state, the fastest diagnosis),
`reauthenticate` (switch Google account).

## The agency setup, which is the whole point

Two ways to authenticate, and the choice is not a detail.

**OAuth** signs in as one person, in a browser, once. Right for someone auditing
their own site.

**A service account** is what makes a portfolio work. One account created once in
Google Cloud, then its address added as a user on each client's Search Console
property. From then on the agency's agent reads **every client property from one
credential**, with no client ever touching a config file.

That is the setup `seo-portfolio-report` assumes when it runs across a portfolio.

## Be honest about the cost

Fifteen to twenty minutes the first time, and it goes through a Google Cloud
project: enable the Search Console API, create the credential, download a JSON
file, install `uv`, find the full path of `uvx`, edit the client config by hand,
and fully quit the desktop app so it reloads.

**This is agency work, not client work.** Never present it to a site owner as a
two minute setup. Done once by the agency with a service account, it is then
invisible to every client, which is exactly why the service account path is the
one to recommend.

## Rules that do not bend

- **Read only in practice.** `add_site`, `delete_site` and `manage_sitemaps`
  write. Never call one unless the user asked for that exact action in this
  conversation.
- **The last three days are incomplete.** Live reading does not change this.
  Drop them, as with an export.
- **A property is a domain property or a URL prefix property**, and they do not
  return the same rows. Call `list_properties` and match rather than guessing.
- **Live data is not a licence to skip the noise floor.** Reading faster does not
  make fourteen days of data conclusive.
- Search Console is Google. It says nothing about who a generative engine cites,
  and nothing about which AI crawler came. Those need the other skills here.
