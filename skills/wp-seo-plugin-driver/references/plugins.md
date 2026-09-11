# The four plugins, field by field

Read in September 2026 from each plugin's documentation, changelog and
source on plugins.svn.wordpress.org. Versions move: when a behaviour depends
on a version, `detect` tells you which one the site runs (Yoast and AIOSEO
print it; Rank Math and SEOPress do not).

## Table of contents

- [At a glance](#at-a-glance)
- [Yoast SEO](#yoast-seo)
- [Rank Math](#rank-math)
- [All in One SEO](#all-in-one-seo)
- [SEOPress](#seopress)
- [Abilities API and MCP](#abilities-api-and-mcp)
- [Fingerprints](#fingerprints)

## At a glance

| | Yoast SEO | Rank Math | AIOSEO | SEOPress |
|---|---|---|---|---|
| Version read | 28.4 | 1.0.278 | 5.0.1.1 | 10.2 |
| Requires WordPress | 6.9 | 6.7 | 5.7 | 6.5 |
| Active installs | 10M+ | 4M+ | 2M+ | 300k+ |
| REST write of title and description | core route, posts only, 27.7+ | `rankmath/v1/updateMeta` | `aioseo_meta_data`, 4.9.8+ | `seopress/v1` PUT routes |
| Abilities (WordPress 6.9+) | 3, read only | about 25, settings and audits, no per post write | 13 in Lite, write included | on a toggle, write included |
| Where the data lives | post meta, mirrored in `wp_yoast_indexable` | post meta | its own table `wp_aioseo_posts` | post meta |

Sources: https://wordpress.org/plugins/wordpress-seo/ ,
https://wordpress.org/plugins/seo-by-rank-math/ ,
https://wordpress.org/plugins/all-in-one-seo-pack/ ,
https://wordpress.org/plugins/wp-seopress/

## Yoast SEO

| Field | Post meta key | Values |
|---|---|---|
| SEO title | `_yoast_wpseo_title` | REST writable 27.7+, `post` type only |
| Meta description | `_yoast_wpseo_metadesc` | REST writable 27.7+, `post` type only |
| Focus keyphrase | `_yoast_wpseo_focuskw` | REST writable 27.7+, `post` type only |
| Canonical | `_yoast_wpseo_canonical` | WP-CLI only |
| Noindex | `_yoast_wpseo_meta-robots-noindex` | `0` post type default, `1` noindex, `2` index |
| Nofollow | `_yoast_wpseo_meta-robots-nofollow` | `0` follow, `1` nofollow |
| Open Graph | `_yoast_wpseo_opengraph-title`, `-description` | WP-CLI only |
| Primary category | `_yoast_wpseo_primary_category` | term id |
| Cornerstone | `_yoast_wpseo_is_cornerstone` | `1` |

- **Reading**: `yoast_head_json` on every core REST object, and
  `GET /wp-json/yoast/v1/get_head?url=` (can be switched off in Site features).
- **Writing**: Yoast's own API is read only (Yoast support, August 2025). From
  27.7 (27 May 2026), three keys are registered with `show_in_rest` for the
  `post` subtype only, so `POST /wp-json/wp/v2/posts/{id}` with
  `{"meta": {"_yoast_wpseo_metadesc": "..."}}` works on posts. On a page or a
  custom type the key is not registered, the core API drops it and still
  answers 200. That is why the canary exists.
- **Everything else**: `wp post meta update <id> <key> <value>` over SSH.
  Yoast's watcher rebuilds the indexable on every meta add, update or delete,
  so WP-CLI and the REST route keep `wp_yoast_indexable` in sync. Raw SQL
  does not: repair with `wp yoast index --reindex`.
- Source: https://plugins.svn.wordpress.org/wordpress-seo/trunk/inc/class-wpseo-meta.php

## Rank Math

| Field | Post meta key | Values |
|---|---|---|
| SEO title | `rank_math_title` | |
| Meta description | `rank_math_description` | |
| Focus keyword | `rank_math_focus_keyword` | comma separated, the first is primary |
| Canonical | `rank_math_canonical_url` | |
| Robots | `rank_math_robots` | array of directives, stored serialized |
| Open Graph | `rank_math_facebook_title`, `rank_math_facebook_description` | |
| Primary category | `rank_math_primary_category` | term id |
| Pillar content | `rank_math_pillar_content` | `on` |

- **Writing**: `POST /wp-json/rankmath/v1/updateMeta` with
  `{"objectType": "post", "objectID": 123, "meta": {"rank_math_description": "..."}}`.
  Needs `edit_post` on that post. Only keys starting with `rank_math_` are
  accepted; an empty value deletes the key. Terms work with
  `"objectType": "term"`. Source: `includes/rest/class-shared.php`.
- The `rank_math_*` keys are not registered with `show_in_rest`: the core
  route ignores them.
- **Reading**: `GET /wp-json/rankmath/v1/getHead?url=` exists only when
  "Headless CMS Support" is on, and is public when it is.
- The robots array accepted by `updateMeta` is not documented: send it to one
  page, read the rendered robots tag, then the rest.
- WP-CLI: only `wp rankmath sitemap generate`.
- Some Cloudflare rules block `rankmath/v1/updateMeta`: see [access.md](access.md).

## All in One SEO

| Field | Column in `wp_aioseo_posts` | Values |
|---|---|---|
| SEO title | `title` | |
| Meta description | `description` | |
| Focus keyphrase | `keyphrases` | JSON, `{"focus": {"keyphrase": ""}, "additional": []}` |
| Canonical | `canonical_url` | |
| Noindex | `robots_noindex` | only applies when `robots_default` is false |
| Open Graph | `og_title`, `og_description` | |
| Cornerstone | `pillar_content` | bool |

- **Writing**: `POST /wp-json/wp/v2/{type}/{id}` with
  `{"aioseo_meta_data": {"description": "..."}}`. AIOSEO merges it with the
  existing row and saves through its own model. Free in every plan since
  4.9.8 (June 2026); before that it was a paid add-on.
  https://aioseo.com/docs/fetching-updating-aioseo-data-via-the-wordpress-rest-api/
- **The trap**: AIOSEO also writes `_aioseo_title`, `_aioseo_description`
  and similar post meta, one way, from its table. It never reads them back.
  Writing them changes nothing on the page. WP-CLI `wp post meta update` is
  therefore useless for AIOSEO.
- **Abilities** (4.9.8+, Lite): `aioseo-posts/seo-data-get`,
  `aioseo-posts/seo-data-update`, `aioseo-posts/list-missing-seo`,
  `aioseo-robots/rules-*`, `aioseo-audit/site-get` and others, 13 in Lite,
  more in Pro. The newsroom says free for all plans, the docs page says Basic
  or above for Pro features: probe the site rather than assume.

## SEOPress

| Field | Post meta key | Values |
|---|---|---|
| SEO title | `_seopress_titles_title` | |
| Meta description | `_seopress_titles_desc` | |
| Target keywords | `_seopress_analysis_target_kw` | comma separated |
| Canonical | `_seopress_robots_canonical` | |
| Noindex | `_seopress_robots_index` | `yes` means **noindex** |
| Nofollow | `_seopress_robots_follow` | `yes` means nofollow |
| Open Graph | `_seopress_social_fb_title`, `_seopress_social_fb_desc` | |
| Primary category | `_seopress_robots_primary_cat` | term id |

- **Writing**: `PUT /wp-json/seopress/v1/posts/{id}/title-description-metas`
  with `{"title": "...", "description": "..."}`, and
  `.../meta-robot-settings` for robots and canonical. Needs `edit_post`.
  Application passwords supported since 6.8.
  https://www.seopress.org/support/guides/get-started-with-the-seopress-rest-api/
- `plan` sends one field per call. Check on the canary that the other field
  was not emptied.
- **Reading**: `GET /wp-json/seopress/v1/posts/{id}` and `.../posts/by-url?url=`.
- **Abilities** (10.0, June 2026): off by default, one toggle in Advanced.
  Free: get and update title and description, robots, social. PRO: redirects,
  schemas, target keywords, AI generation (uses credits).
- WP-CLI: `wp seopress settings export|import`; metas through `wp post meta`.

## Abilities API and MCP

WordPress 6.9 shipped the Abilities API (`/wp-json/wp-abilities/v1/abilities`,
authenticated). An ability is visible over REST only when registered with
`show_in_rest`, and reachable by the MCP Adapter only with `mcp.public`. Run
an ability with `GET` when it is read only, `POST` otherwise, input as JSON.
The MCP Adapter is a plugin (or bundled by a plugin, as Rank Math does), not
core; it turns `plugin/ability` into the tool `plugin-ability`.
https://make.wordpress.org/core/2025/11/10/abilities-api-in-wordpress-6-9/
https://github.com/WordPress/mcp-adapter

Rank Math bundles the adapter and, since 1.0.278 (8 September 2026), offers
OAuth at `/wp-json/mcp/mcp-oauth-server`. Its tools cover settings, audits and
redirections, not per post meta.

## Fingerprints

| Plugin | In the page head | Sitemap |
|---|---|---|
| Yoast | `<!-- This site is optimized with the Yoast SEO plugin v28.4 ...`, schema class `yoast-schema-graph` | `/sitemap_index.xml` |
| Rank Math | `<!-- Search Engine Optimization by Rank Math ...` (or PRO), schema class `rank-math-schema` | `/sitemap_index.xml` |
| AIOSEO | `<!-- All in One SEO 5.0.1.1 - aioseo.com -->`, generator meta, schema class `aioseo-schema` | `/sitemap.xml` |
| SEOPress | no documented comment: `detect` relies on the `seopress/v1` namespace | `/sitemaps.xml` |

The comments can be removed by a filter (`wpseo_debug_markers`,
`rank_math/frontend/remove_credit_notice`), which is why `detect` also reads
the REST namespaces.
