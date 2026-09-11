# WordPress traps during a migration

What WordPress core and the common plugins do on their own, read from the
code and the developer reference in September 2026. Each one explains a
symptom that looks random until you know it.

## Core

**Old slugs redirect, but only for posts.** When a published post changes
slug, WordPress stores the old one in `_wp_old_slug` (and the old date in
`_wp_old_date`, since 4.9.3), and `wp_old_slug_redirect()` answers a 301 when
a request would otherwise 404. It skips hierarchical post types: **a Page
whose slug changed gets no redirect at all.** It also runs only while the old
database is in place: an import into a fresh install loses the meta.
https://developer.wordpress.org/reference/functions/wp_old_slug_redirect/

**The 404 guess is loose.** On a 404, `redirect_canonical()` calls
`redirect_guess_404_permalink()`, which looks for a post whose slug *starts
with* the requested one (`post_name LIKE 'slug%'`), with no ordering. So
`/velo/` can land on `/velo-cargo-occasion-2019/`. That is the "wrong target"
nobody configured. Since 5.5, a filter restricts it to exact slugs:

```php
add_filter( 'strict_redirect_guess_404_permalink', '__return_true' );
```

and `do_redirect_guess_404_permalink` returning false turns it off.
https://developer.wordpress.org/reference/functions/redirect_guess_404_permalink/

**Changing Settings, Permalinks redirects nothing.** Core keeps no record of
the previous structure. An old URL survives only if the new rewrite rules
happen to parse it into a slug, then goes through the loose guess above.
Test each structure, never assume. WordPress.com says it plainly: "posts may
not automatically redirect from the old links."

**"Discourage search engines" leaks a noindex, not a robots.txt rule.** Since
5.3 the virtual robots.txt no longer writes `Disallow: /`; since 5.7 the
setting adds a `noindex` robots meta tag instead. A staging copy pushed live
with the box ticked is indexable by robots.txt and invisible by meta: exactly
what `check_live.py` reports as `noindex_target`.
https://developer.wordpress.org/reference/functions/wp_robots_noindex/

**Attachment pages.** Since 6.4, new installs redirect attachment pages to
the file (`wp_attachment_pages_enabled` = 0), upgraded sites keep them. A
migration into a fresh install silently changes this.
https://make.wordpress.org/core/2023/10/16/changes-to-attachment-pages/

**The core sitemap** lives at `/wp-sitemap.xml` (since 5.5), 2 000 URLs per
file, and is off when the site discourages search engines. Yoast replaces it
with `/sitemap_index.xml`, Rank Math too, AIOSEO uses `/sitemap.xml`, SEOPress
`/sitemaps.xml`. Pass the right one to `--new`.

## Plugins and setups

**Two redirect engines at once.** A site running Redirection and a SEO
plugin's redirect module answers with whichever hooks first. `check_live.py`
reports it as `wrong_target`: the map and the server disagree. Keep one.

**Cache in front.** A page cache or a CDN can keep serving the old page with
a 200 after the rule is added: `not_redirected`. Purge, then test again.

**Multilingual prefixes.** Removing a language (WPML, Polylang, TranslatePress)
leaves `/en/` URLs everywhere, and a relative link in a language switcher
produces `/en/en/...`. `hunt` groups those as `doubled_segment`: fix the link
in the theme or the menu, a redirect would only hide it. Measured on one real
WooCommerce site in September 2026: the doubled prefix URLs held four of its
ten most frequent 404s.

**WooCommerce bases.** `/product/` and `/produit/`, `/product-category/`,
`/product-tag/` and `/etiquette-produit/` change with the shop language and
the permalink settings. `build` learns the swap from the inventories; check
the exceptions it lists (discontinued products).

**Media.** Uploads keep their `/wp-content/uploads/YYYY/MM/` path only if
the files were copied. A 404 on images after launch (`asset` in `hunt`) means
the files, not the rules.

**Query URLs.** `?p=123`, `?page_id=45`, `?cat=7` name content by database id.
Nothing in a URL list says which post that was: look it up in the old
database, then add a rule that matches the query string (Redirection can,
`.htaccess` needs mod_rewrite).
