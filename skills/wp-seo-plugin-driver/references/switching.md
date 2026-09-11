# Switching from one SEO plugin to another

The switch itself takes ten minutes. What costs traffic is what the importer
did not carry, noticed three weeks later in Search Console.

## Who imports what

| Moving to | Imports from | Source |
|---|---|---|
| Yoast SEO | AIOSEO, Rank Math, SEO Framework, SmartCrawl, Squirrly, WP Meta SEO. **Not SEOPress** | https://yoast.com/features/migrate-from-other-plugins/ |
| Rank Math | Yoast, AIOSEO, SEOPress, All In One Schema, Redirection | https://wordpress.org/plugins/seo-by-rank-math/ |
| AIOSEO | Yoast, Rank Math, SEOPress | https://aioseo.com/docs/importing-settings-from-other-plugins/ |
| SEOPress | Yoast, AIOSEO, Rank Math, Squirrly, SEO Framework, SmartCrawl and others | https://www.seopress.org/support/faq/can-i-import-my-posts-and-terms-metadata-from-other-seo-plugins-like-yoast-or-aio-seo/ |
| Hack The SEO (free) | Yoast, Rank Math, AIOSEO, SEOPress: titles, descriptions, robots, canonicals, keywords, cornerstone, redirects, Open Graph. Never deletes the source data | https://wordpress.org/plugins/hack-the-seo/ |

## The procedure

1. `snapshot` every indexable URL (the sitemap is enough) on the old plugin.
2. Install the new plugin, run its importer. Keep the old one installed.
   Some importers need it active, and every importer needs its data.
3. Deactivate the old one only for the `snapshot` after, then compare:
   `diff before.json after.json`.
4. Fix what the diff shows, with `plan` on the new plugin.
5. Snapshot and diff again until nothing `high` is left. Then deactivate the
   old plugin for good. Delete its data weeks later, never on the same day.

Also compare, by hand, what the snapshot does not see: the sitemap URL (change
it in Search Console if it moved), the redirects module, the robots.txt
editor, the breadcrumbs in the theme, the organisation schema on the home page.

## What importers usually miss

Descriptions built from variables rather than typed, per page robots set on
old posts, schema types chosen per post, the title separator, the primary
category, and archive settings (tag, author, date archives indexed or not).
Every one of those is visible in a `diff` of the rendered pages, which is why
the diff, not the importer's success message, decides.

## Title variables

`vars` translates a template. The table it uses:

| Meaning | Yoast | Rank Math | AIOSEO | SEOPress |
|---|---|---|---|---|
| Post title | `%%title%%` | `%title%` | `#post_title` | `%%post_title%%` |
| Separator | `%%sep%%` | `%sep%` | `#separator_sa` | `%%sep%%` |
| Site title | `%%sitename%%` | `%sitename%` | `#site_title` | `%%sitetitle%%` |
| Tagline | `%%sitedesc%%` | `%sitedesc%` | `#tagline` | `%%tagline%%` |
| Excerpt | `%%excerpt%%` | `%excerpt%` | `#post_excerpt` | `%%post_excerpt%%` |
| Primary category | `%%primary_category%%` | `%category%` | `#categories` | `%%post_category%%` |
| Page number | `%%page%%` | `%pagenumber%` | `#page_number` | `%%page%%` |
| Current year | `%%currentyear%%` | `%currentyear%` | `#current_year` | `%%currentyear%%` |
| Term title | `%%term_title%%` | `%term%` | `#taxonomy_title` | `%%term_title%%` |
| Author | `%%name%%` | `%name%` | `#author_name` | `%%post_author%%` |
| Date | `%%date%%` | `%date%` | `#post_date` | `%%post_date%%` |
| Focus keyword | `%%focuskw%%` | `%focuskw%` | none | `%%target_keyword%%` |

AIOSEO has no "primary category" tag: `#categories` lists them all. Yoast's
`%%page%%` renders "page 2 of 4", Rank Math's `%pagenumber%` only the number.
Anything `vars` does not know is printed on stderr: rewrite it by hand.
