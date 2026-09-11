#!/usr/bin/env python3
"""
A two host fake site for testing check_live.py without touching a real server.

    python3 mock_site.py 8765 &
    python3 ../../scripts/check_live.py map.csv \
        --old-base http://127.0.0.1:8765 --expect-base http://localhost:8765

Requests sent to 127.0.0.1 play the old site, requests sent to localhost play
the new one. Nine of the old URLs carry a planted defect, one per verdict the
checker knows: a noindex left on a target, a canonical still pointing at the
staging host, a 302, a chain, a loop, a target that answers 404, a category
dumped on the home page, a page that was never redirected, and a 410 that
works. Everything else redirects correctly.

Listens on 127.0.0.1 only. Standard library only.
Licence: GPL-2.0-or-later
"""

import os
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))

OLD_TO_NEW = {
    "/": "/",
    "/2021/03/choisir-un-velo-electrique/": "/blog/choisir-un-velo-electrique/",
    "/2021/06/regler-ses-freins-a-disque/": "/blog/regler-ses-freins-a-disque/",
    "/2023/04/nettoyer-sa-chaine/": "/blog/nettoyer-sa-chaine/",
    "/conseils-securite-route/": "/blog/conseils-securite-route/",
    "/a-propos/": "/a-propos/",
    "/contact/": "/contact/",
    "/guide-achat-casque/": "/blog/guide-achat-casque/",
    "/category/entretien/": "/blog/entretien/",
    "/category/velotaf/": "/blog/velotaf/",
    "/produit/casque-urbain/": "/boutique/casque-urbain/",
    "/produit/antivol-u/": "/boutique/antivol-u/",
    "/produit/sacoche-velo/": "/boutique/sacoche-velo/",
    "/produit/eclairage-led/": "/boutique/eclairage-led/",
    "/lexique-velo/": "/blog/lexique-velo/",
    "/en/": "/",
}

# planted defects on the old host
OLD_SPECIAL = {
    "/2022/09/pression-pneus-velo-route/": (302, "/blog/pression-pneus-velo-route/"),
    "/2022/01/velotaf-hiver-equipement/": (301, "/velotaf-hiver-equipement/"),
    "/category/conseils/": (301, "/"),
    "/atelier.html": (200, None),
    "/promo-noel-2021/": (410, None),
}

# planted defects on the new host
NEW_SPECIAL = {
    "/velotaf-hiver-equipement/": (301, "/blog/velotaf-hiver-equipement/"),
    "/boutique/antivol-u/": (404, None),
    "/boutique/sacoche-velo/": (301, "OLD:/produit/sacoche-velo/"),
}
NOINDEX = {"/blog/regler-ses-freins-a-disque/"}
STAGING_CANONICAL = {"/boutique/casque-urbain/"}


def new_paths():
    text = open(os.path.join(HERE, "new-sitemap.xml"), encoding="utf-8").read()
    return {re.sub(r"^https?://[^/]+", "", u) for u in re.findall(r"<loc>([^<]+)</loc>", text)}


LIVE = new_paths()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send(self, status, location=None, body=b""):
        self.send_response(status)
        if location:
            self.send_header("Location", location)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def page(self, base, path):
        robots = '<meta name="robots" content="noindex, follow">' if path in NOINDEX else ""
        canonical = ("https://staging.exemple.fr" + path) if path in STAGING_CANONICAL else base + path
        html = ('<!doctype html><html><head><title>%s</title>%s'
                '<link rel="canonical" href="%s"></head><body>ok</body></html>' % (path, robots, canonical))
        self.send(200, body=html.encode("utf-8"))

    def do_GET(self):
        host = (self.headers.get("Host") or "").split(":")[0]
        port = self.server.server_address[1]
        old_base = "http://127.0.0.1:%d" % port
        new_base = "http://localhost:%d" % port
        path = self.path.split("?")[0]
        if host == "localhost":
            if path in NEW_SPECIAL:
                status, target = NEW_SPECIAL[path]
                if target and target.startswith("OLD:"):
                    return self.send(status, old_base + target[4:])
                return self.send(status, new_base + target if target else None)
            if path in LIVE:
                return self.page(new_base, path)
            return self.send(404)
        if path in OLD_SPECIAL:
            status, target = OLD_SPECIAL[path]
            if status == 200:
                return self.page(old_base, path)
            return self.send(status, new_base + target if target else None)
        if path in OLD_TO_NEW:
            return self.send(301, new_base + OLD_TO_NEW[path])
        return self.send(404)


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print("mock site on port %d (old host 127.0.0.1, new host localhost)" % port, file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
