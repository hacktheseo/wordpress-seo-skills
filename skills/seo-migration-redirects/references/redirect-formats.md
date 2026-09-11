# Redirect formats: what each tool imports

`redirect_map.py export` writes the formats below. Read the row of the tool
that will serve the rules before importing, because each has one trap.

## The table

| `--format` | Tool | Columns, in order | Regex | Codes | Trap |
|---|---|---|---|---|---|
| `redirection` | Redirection plugin | `source,target,regex,code,type` | yes, `regex=1` | 301 to 308, and 4xx as `type=error` | none known, the most forgiving importer |
| `yoast` | Yoast SEO Premium | `Origin,Target,Type,Format`, header required | yes, `Format=regex` | 301, 302, 307, 410, 451 | 410 and 451 rows must have an empty target |
| `rankmath` | Rank Math PRO | `id,source,matching,destination,type,category,status,ignore`, lowercase header | `matching=regex` | 301, 302, 307, 410, 451 | CSV import is PRO only; sources written without slashes |
| `seopress` | SEOPress PRO | 9 columns, no header | column 8 `yes` | 301, 302, 307, 410, 451 | source without leading slash, target absolute: pass `--host` |
| `generic` | anything else | `source,target,code` | no | as in the map | paste into the tool's own sample file |
| `htaccess` | Apache | `RedirectMatch` lines | yes | any | place it above `# BEGIN WordPress` |
| `nginx` | Nginx | a `map` include file | yes, `~` prefix | 301 via `return` | raise `map_hash_max_size` first if nginx asks |

No format needs a code the tool does not support: the map uses 301 and 410
only, unless you edit it.

## Details and sources

**Redirection** (John Godley). The first row is skipped when it is a header.
A missing code defaults to 301. Imports CSV, Apache and JSON, and imports
directly from Rank Math, Yoast and WordPress old slugs. Its import page says
"301-307" only, while the parser in the current source accepts 4xx codes.
https://redirection.me/support/import-export-redirects/

**Yoast SEO Premium.** UTF-8, Unix line endings, comma delimited, existing
redirects skipped, case sensitive. Origins start with `/`. Example rows from
Yoast's own help: `"/four-ten","",410,"plain"` and
`"^/([0-9]{4})/([0-9]{2})/(?!page/)(.+)$","/$4",301,"regex"`.
https://yoast.com/help/import-redirects/

**Rank Math PRO.** Minimum columns are `source` and `destination`. Leave `id`
empty to create, set `destination` to `DELETE` to delete. Rank Math compares a
stored source against the request path with its slashes trimmed
(`includes/modules/redirections/class-redirector.php`), so the export writes
`blog/old-post` rather than `/blog/old-post/`. Its regex conventions are not
documented publicly, so learned patterns are not exported for it: add them by
hand from `build.json`, then test with `check_live.py`.
https://rankmath.com/kb/how-to-manage-redirects-via-csv/

**SEOPress PRO.** Columns: URL to match without the domain
(`category/my-post`), absolute target, type, enabled (`yes`), query handling
(`exact_match`, `without_param`, `with_ignored_param`), counter, category ids,
regex (`yes`), logged in status (`both`). Comma or semicolon, detected since
9.7. The home page row is never written for it or for Rank Math: an empty
source would match everything.
https://www.seopress.org/support/guides/import-redirects-from-a-csv-file/

**AIOSEO** publishes a downloadable sample file but documents neither the
values of its `Ignore Slash`, `Ignore Case` and `Regex` columns nor whether a
header is required. This skill does not write that format blind. Download the
sample from AIOSEO's import screen, export `generic`, and paste the three
columns in. https://aioseo.com/docs/exporting-and-importing-redirects/

**Hack The SEO, free plugin.** It serves redirects in PHP, never in
`.htaccess`, with 301, 302, 307 and 410 in its form (308 only through an
import), regex rules, and a CSV import and export on its Redirections screen.
Its column order is not documented here: export once from the screen and use
that file as the template for `generic`. Its migration wizard also imports
redirects straight from Yoast, Rank Math, AIOSEO and SEOPress.

**Apache.** `Redirect` matches a path prefix and appends the rest, and passes
the query string through; it cannot match on a query string. The export uses
`RedirectMatch` anchored with `^` and `/?$`, so `/old` never catches
`/old-and-more`. A source with a query string needs mod_rewrite with a
`RewriteCond %{QUERY_STRING}` and is left as a comment for a person.
https://httpd.apache.org/docs/2.4/mod/mod_alias.html

**Nginx.** `map` lives in the `http` block. Plain keys are case insensitive,
`~` starts a case sensitive regex. `$uri` is decoded and has no arguments,
`$request_uri` keeps them. Include the generated file, then
`if ($hts_redirect) { return 301 $hts_redirect; }` in the `server` block.
If nginx refuses to start and names a hash size, increase `map_hash_max_size`
first. https://nginx.org/en/docs/http/ngx_http_map_module.html

## Learned patterns

`--patterns build.json` appends the patterns `build` learned as regex rules,
for the formats that document their regex (`redirection`, `yoast`, `htaccess`,
`nginx`). They catch the long tail the inventory never saw. Each pattern lists
its exceptions: URLs under the prefix whose new page does not exist. Those
must be decided in the map, and the tool must evaluate plain rules before
regex ones, or the pattern sends them to a 404. When in doubt, export without
`--patterns`: explicit lines are slower to maintain and never surprising.
