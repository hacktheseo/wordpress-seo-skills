# The before and after

What `migration_proof.py` computes, and what the report may claim from it.

## The unit: an old URL followed to its new page

Clicks are compared per new page, not per URL. The clicks every old URL
earned before the move are summed onto the page the map sends it to. After
the move, that page's clicks are added to whatever the old URLs still earn
while Google swaps them (after a domain change, pass the old property's
export too). The ratio after over before is the share the page kept.

That share is then read against the whole site's share. A site at 76 % whose
page sits at 15 % has a page problem, not a season. The script lists pages
under half the site's share and at least 1 % of the traffic, with the live
check verdict of their old URLs next to them. In practice that column is the
explanation: a noindex, a 404, a canonical.

Old URLs that earned clicks and are absent from the map are listed apart:
the inventory had a hole.

## Windows

Use two windows of the same length, the same weekdays, and never include the
launch week in "after". Default: the 28 days before launch against the latest
28 days. With a Dates export and `--launch`, the curve shows the whole
period with the launch marked, so the client sees the dip and the climb.

Search Console keeps consolidating the last days: export three days after
the end of the window, or trim them.

## What may be claimed

- "This page kept 15 % of its clicks while the site kept 76 %, and its old
  URL lands on a page in noindex": yes, each part is observed.
- "The migration cost 584 clicks": only as a sum observed over the two
  windows, with the site's own trend named next to it.
- "Traffic will be back in three months": never. Google says "a few weeks or
  more" for a medium site; SALT.agency measured a median of 304 days across
  1 052 domain migrations. Name both, promise neither.

Below 28 days after launch the script says so, and the report verdict says
"too early to judge the traffic" rather than inventing a direction.

## What the data cannot show

Search Console exports hold the top pages only (1 000 rows in the interface),
so long tail pages are measured in the site total, not one by one. Clicks are
not revenue. And the comparison controls for the site's trend, not for a
Google update that hit one section: when a whole section drops together,
check the dates of confirmed updates before blaming the map.
