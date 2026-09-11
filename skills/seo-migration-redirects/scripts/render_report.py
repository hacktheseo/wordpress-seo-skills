#!/usr/bin/env python3
"""
Render a self-contained HTML report from a findings JSON file.

Usage:
    python3 render_report.py findings.json report.html

Standard library only. No network. No external assets, no web fonts, no
tracking. The output is one HTML file: it opens offline, prints to a clean
PDF, reads in light and dark, carries an agency's own name and colour, and
can be published as an artifact as is.

The JSON contract is documented in CONTRACT.md next to this file.
Backwards compatible with contract v1.

Part of the Hack The SEO agent skills.
Licence: GPL-2.0-or-later
"""

import html
import json
import os
import re
import sys
from datetime import date

# --------------------------------------------------------------------------
# palette
# --------------------------------------------------------------------------
# Status colours are fixed and never themed. They are always paired with a
# written label, because two of them sit below 3:1 on a light surface and a
# colour must never carry meaning on its own.

CREDIT_URL = "https://hacktheseo.com/skills?utm_source=report&utm_medium=skills"
PLUGIN_URL = "https://wordpress.org/plugins/hack-the-seo/"

STATUS = {
    "good": "#0CA30C",
    "warning": "#FAB219",
    "serious": "#EC835A",
    "critical": "#D03B3B",
}

# Contract v1 tone names, kept so existing skills do not need changing.
# The status names are accepted too, because that is what an author writes
# naturally and silently downgrading them to neutral loses the meaning.
TONE_TO_STATUS = {
    "good": "good",
    "warn": "warning",
    "warning": "warning",
    "bad": "critical",
    "critical": "critical",
    "serious": "serious",
    "neutral": "neutral",
}

SEVERITY_TO_STATUS = {
    "high": "critical",
    "medium": "serious",
    "low": "neutral",
    "info": "good",
}

TONES = tuple(TONE_TO_STATUS.keys())

STRINGS = {
    "en": {
        "generated": "Generated",
        "period": "Period",
        "prepared": "Prepared for",
        "credit": "Report produced with the Hack The SEO agent skills",
        "contents": "Contents",
        "severity": {"high": "High", "medium": "Medium", "low": "Low", "info": "Note"},
        "evidence": "Evidence",
        "action": "What to do",
        "total": "Total",
        "of": "of",
        "source_note": (
            "AI crawler hits are recorded server side, on the site itself, "
            "because these crawlers run no JavaScript and leave no trace in "
            "analytics. The free Hack The SEO plugin performs that measurement: "
            "wordpress.org/plugins/hack-the-seo/"
        ),
    },
    "fr": {
        "generated": "Généré le",
        "period": "Période",
        "prepared": "Préparé pour",
        "credit": "Rapport produit avec les skills Hack The SEO",
        "contents": "Sommaire",
        "severity": {"high": "Élevé", "medium": "Moyen", "low": "Faible", "info": "Note"},
        "evidence": "Constat",
        "action": "Ce qu'il faut faire",
        "total": "Total",
        "of": "sur",
        "source_note": (
            "Les passages de robots IA sont relevés côté serveur, sur le site "
            "lui-même, parce que ces robots n'exécutent pas JavaScript et ne "
            "laissent aucune trace dans un outil analytics. L'extension gratuite "
            "Hack The SEO fait cette mesure : wordpress.org/plugins/hack-the-seo/"
        ),
    },
}


# --------------------------------------------------------------------------
# colour helpers
# --------------------------------------------------------------------------

def parse_hex(value, fallback="#1F6F4E"):
    """Return a normalised #rrggbb string, or the fallback."""
    if not isinstance(value, str):
        return fallback
    value = value.strip()
    if not re.fullmatch(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})", value):
        return fallback
    if len(value) == 4:
        value = "#" + "".join(c * 2 for c in value[1:])
    return value.lower()


def to_rgb(hexstr):
    hexstr = hexstr.lstrip("#")
    return tuple(int(hexstr[i:i + 2], 16) for i in (0, 2, 4))


def to_hex(rgb):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(round(c)))) for c in rgb)


def _channel(value):
    value = value / 255.0
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def luminance(hexstr):
    r, g, b = to_rgb(hexstr)
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def contrast(a, b):
    la, lb = luminance(a), luminance(b)
    if la < lb:
        la, lb = lb, la
    return (la + 0.05) / (lb + 0.05)


def mix(a, b, amount):
    """Blend a towards b. amount 0 keeps a, 1 returns b."""
    ra, ga, ba = to_rgb(a)
    rb, gb, bb = to_rgb(b)
    return to_hex((
        ra + (rb - ra) * amount,
        ga + (gb - ga) * amount,
        ba + (bb - ba) * amount,
    ))


def ensure_contrast(colour, surface, target, towards):
    """Step a colour towards black or white until it clears the target ratio.

    An agency picks its own brand colour and a pale one would make every mark
    unreadable. Rather than refuse the colour, the engine steps it just far
    enough to be legible and leaves the hue alone.
    """
    if contrast(colour, surface) >= target:
        return colour
    for step in range(1, 21):
        candidate = mix(colour, towards, step * 0.05)
        if contrast(candidate, surface) >= target:
            return candidate
    return towards


# --------------------------------------------------------------------------
# small utilities
# --------------------------------------------------------------------------

def safe_url(value):
    """Return the URL only if it is a plain absolute http or https URL.

    A link is the one place where text from the contract lands inside an
    attribute, so the scheme is checked here rather than trusted. javascript:,
    data: and protocol relative // are refused outright, and so is anything
    carrying a newline or a quote, which is how attribute injection starts.
    """
    if not isinstance(value, str):
        return ""
    url = value.strip()
    if not url or url.startswith("//"):
        return ""
    if not url.lower().startswith(("http://", "https://")):
        return ""
    if any(ch in url for ch in "\r\n\t<>\'\""):
        return ""
    return url


def link(url, label):
    """Render an anchor, or the bare label when the URL is refused.

    The href is built here, never passed through esc() as a whole: escaping the
    tag would emit inert text. The URL and the label are each escaped for their
    own position, and href comes first so the markup stays greppable.
    """
    href = safe_url(url)
    if not href:
        return esc(label)
    return f'<a href="{esc(href)}" rel="noopener">{esc(label)}</a>'


def esc(value):
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def tone_of(value):
    value = (value or "neutral").lower()
    return value if value in TONES else "neutral"


def numbers(items, key="value"):
    out = []
    for item in items:
        try:
            out.append(float(item.get(key, 0) if isinstance(item, dict) else item))
        except (TypeError, ValueError):
            out.append(0.0)
    return out


def pct(value, maximum):
    if maximum <= 0:
        return 0.0
    return max(0.0, min(100.0, (value / maximum) * 100.0))


def svg_points(values, width, height, pad=0):
    """Map a series to polyline points inside a box."""
    if not values:
        return [], 0.0, 0.0
    low, high = min(values), max(values)
    if high == low:
        high = low + 1.0
    span = high - low
    inner_h = height - pad * 2
    step = width / (len(values) - 1) if len(values) > 1 else 0.0
    pts = []
    for index, value in enumerate(values):
        x = index * step
        y = pad + inner_h - ((value - low) / span) * inner_h
        pts.append((x, y))
    return pts, low, high


# --------------------------------------------------------------------------
# block renderers
# --------------------------------------------------------------------------

def render_table(block):
    columns = block.get("columns") or []
    rows = block.get("rows") or []
    if not isinstance(rows, list):
        print("warning: table rows is not a list, table skipped", file=sys.stderr)
        rows = []
    numeric = set(block.get("numeric_columns") or [])
    head_cells = []
    for i, column in enumerate(columns):
        cls = ' class="num"' if i in numeric else ""
        head_cells.append(f"<th{cls}>{esc(column)}</th>")
    head = "".join(head_cells)
    body = []
    for row in rows:
        cells = []
        for index, cell in enumerate(row):
            cls = ' class="num"' if index in numeric else ""
            cells.append(f"<td{cls}>{esc(cell)}</td>")
        body.append("<tr>" + "".join(cells) + "</tr>")
    return (
        '<div class="tablewrap"><table><thead><tr>'
        + head
        + "</tr></thead><tbody>"
        + "".join(body)
        + "</tbody></table></div>"
    )


def render_bars(block):
    items = block.get("items") or []
    values = numbers(items)
    top = max(values) if values else 0.0
    rows = []
    for item, value in zip(items, values):
        width = pct(value, top)
        status = TONE_TO_STATUS.get(tone_of(item.get("tone")), "neutral")
        label = esc(item.get("label"))
        display = esc(item.get("display", item.get("value")))
        title = esc(f'{item.get("label")}: {item.get("display", item.get("value"))}')
        rows.append(
            f'<div class="bar-row" title="{title}">'
            f'<span class="bar-name">{label}</span>'
            f'<span class="bar-track"><span class="bar-fill s-{status}" '
            f'style="width:{width:.1f}%"></span></span>'
            f'<span class="bar-val">{display}</span></div>'
        )
    return '<div class="bars">' + "".join(rows) + "</div>"


def render_composition(block):
    """One horizontal stacked bar plus a legend. Beats a donut on every count."""
    items = block.get("items") or []
    values = numbers(items)
    total = sum(values)
    if total <= 0:
        return ""
    segments, legend = [], []
    for index, (item, value) in enumerate(zip(items, values)):
        share = value / total * 100.0
        status = item.get("tone")
        colour_var = (
            f"var(--st-{TONE_TO_STATUS[tone_of(status)]})"
            if status
            else f"var(--seq-{min(index, 5) + 1})"
        )
        display = item.get("display", item.get("value"))
        title = esc(f'{item.get("label")}: {display} ({share:.1f}%)')
        inline = ""
        if share >= 14:
            inline = f'<span class="seg-label">{share:.0f}%</span>'
        segments.append(
            f'<span class="seg" style="flex:0 0 {share:.3f}%;background:{colour_var}" '
            f'title="{title}">{inline}</span>'
        )
        legend.append(
            f'<span class="lg-item"><span class="lg-dot" style="background:{colour_var}">'
            f"</span>{esc(item.get('label'))} "
            f'<b class="num">{esc(display)}</b></span>'
        )
    return (
        '<div class="stackbar">' + "".join(segments) + "</div>"
        '<div class="legend">' + "".join(legend) + "</div>"
    )


def render_meter(block):
    """A score on a fixed scale, with the band written next to the number."""
    try:
        value = float(block.get("value", 0))
    except (TypeError, ValueError):
        value = 0.0
    maximum = float(block.get("max", 100) or 100)
    share = pct(value, maximum)
    status = TONE_TO_STATUS.get(tone_of(block.get("tone")), "neutral")
    band = block.get("band")
    label = block.get("label")
    ticks = block.get("ticks") or [0, maximum / 2, maximum]
    tick_html = "".join(
        f'<span style="left:{pct(float(t), maximum):.1f}%">{esc(int(t) if float(t) == int(float(t)) else t)}</span>'
        for t in ticks
    )
    band_html = f'<span class="meter-band s-{status}">{esc(band)}</span>' if band else ""
    return (
        '<div class="meter">'
        f'<div class="meter-head"><span class="meter-num">{esc(block.get("display", value))}'
        f'<span class="meter-max">/{esc(int(maximum) if maximum == int(maximum) else maximum)}</span></span>'
        f"{band_html}</div>"
        + (f'<p class="meter-label">{esc(label)}</p>' if label else "")
        + f'<div class="meter-track"><span class="meter-fill s-{status}" style="width:{share:.1f}%"></span></div>'
        f'<div class="meter-ticks">{tick_html}</div>'
        "</div>"
    )


def render_timeseries(block):
    """A line with an optional event marker. This is the impact proof visual."""
    series = block.get("series") or []
    if not series:
        return ""
    labels = block.get("labels") or []
    width, height, pad = 640.0, 150.0, 10.0
    all_values = [v for s in series for v in numbers(s.get("values") or [])]
    if not all_values:
        return ""
    low, high = min(all_values), max(all_values)
    if high == low:
        high = low + 1.0
    span = high - low

    def project(values):
        step = width / (len(values) - 1) if len(values) > 1 else 0.0
        inner = height - pad * 2
        return [
            (i * step, pad + inner - ((v - low) / span) * inner)
            for i, v in enumerate(values)
        ]

    parts = []
    legend = []
    for index, entry in enumerate(series):
        values = numbers(entry.get("values") or [])
        if not values:
            continue
        pts = project(values)
        colour = (
            "var(--accent)" if index == 0 else "var(--muted)"
        )
        dash = ' stroke-dasharray="5 4"' if index > 0 else ""
        path = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        if index == 0:
            area = f"0,{height} " + path + f" {pts[-1][0]:.1f},{height}"
            parts.append(
                f'<polygon points="{area}" fill="var(--accent)" opacity="0.10"></polygon>'
            )
        parts.append(
            f'<polyline points="{path}" fill="none" stroke="{colour}" stroke-width="2" '
            f'stroke-linejoin="round" stroke-linecap="round"{dash}></polyline>'
        )
        if index == 0:
            ex, ey = pts[-1]
            parts.append(
                f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="4" fill="var(--accent)" '
                f'stroke="var(--surface)" stroke-width="2"></circle>'
            )
        legend.append(
            f'<span class="lg-item"><span class="lg-line" '
            f'style="background:{colour};{"opacity:.9" if index == 0 else ""}"></span>'
            f"{esc(entry.get('label'))}</span>"
        )

    marker = block.get("event")
    if marker and isinstance(marker, dict):
        try:
            at = int(marker.get("index", -1))
        except (TypeError, ValueError):
            at = -1
        count = len(numbers(series[0].get("values") or []))
        if 0 <= at < count and count > 1:
            x = at * (width / (count - 1))
            anchor = "start" if x < width * 0.6 else "end"
            offset = 6 if anchor == "start" else -6
            parts.append(
                f'<line x1="{x:.1f}" y1="0" x2="{x:.1f}" y2="{height}" '
                f'stroke="var(--baseline)" stroke-width="1"></line>'
                f'<text x="{x + offset:.1f}" y="12" text-anchor="{anchor}" '
                f'class="svg-tick">{esc(marker.get("label"))}</text>'
            )

    axis = ""
    if labels:
        axis = (
            '<div class="ts-axis"><span>' + esc(labels[0]) + "</span>"
            "<span>" + esc(labels[-1]) + "</span></div>"
        )
    scale = (
        f'<div class="ts-scale"><span>{esc(block.get("high_label", int(high)))}</span>'
        f'<span>{esc(block.get("low_label", int(low)))}</span></div>'
    )
    legend_html = '<div class="legend">' + "".join(legend) + "</div>" if len(legend) > 1 else ""
    return (
        '<div class="ts">' + scale
        + f'<svg viewBox="0 -2 {width:.0f} {height + 4:.0f}" preserveAspectRatio="none" '
        f'role="img" aria-label="{esc(block.get("caption") or "time series")}">'
        + "".join(parts)
        + "</svg></div>"
        + axis
        + legend_html
    )


def render_matrix(block):
    quadrants = block.get("quadrants") or []
    cells = []
    for quadrant in quadrants[:4]:
        status = TONE_TO_STATUS.get(tone_of(quadrant.get("tone")), "neutral")
        items = quadrant.get("items") or []
        listing = "".join(f"<li>{esc(i)}</li>" for i in items)
        count = quadrant.get("count")
        badge = f'<span class="q-count num">{esc(count)}</span>' if count is not None else ""
        cells.append(
            f'<div class="quad s-{status}"><div class="q-head">'
            f'<h5>{esc(quadrant.get("title"))}</h5>{badge}</div>'
            f'<p class="q-read">{esc(quadrant.get("reading"))}</p>'
            + (f"<ul>{listing}</ul>" if listing else "")
            + "</div>"
        )
    axes = block.get("axes") or {}
    legend = ""
    if axes:
        bits = [esc(axes.get("x", "")), esc(axes.get("y", ""))]
        legend = '<p class="axes">' + " &middot; ".join(b for b in bits if b) + "</p>"
    return '<div class="matrix">' + "".join(cells) + "</div>" + legend


def render_findings(block):
    items = block.get("items") or []
    lang = block.get("_lang", "en")
    words = STRINGS.get(lang, STRINGS["en"])
    out = []
    for index, item in enumerate(items, start=1):
        severity = (item.get("severity") or "info").lower()
        if severity not in words["severity"]:
            severity = "info"
        status = SEVERITY_TO_STATUS[severity]
        evidence = item.get("evidence")
        action = item.get("action")
        parts = [
            f'<div class="finding s-{status}">',
            '<div class="f-rail">',
            f'<span class="f-index num">{index:02d}</span>',
            f'<span class="sev">{esc(words["severity"][severity])}</span>',
            "</div>",
            f'<div class="f-body"><p class="f-title">{esc(item.get("title"))}</p>',
        ]
        if evidence:
            parts.append(
                f'<p class="f-line"><b>{esc(words["evidence"])}</b>{esc(evidence)}</p>'
            )
        if action:
            parts.append(
                f'<p class="f-line f-do"><b>{esc(words["action"])}</b>{esc(action)}</p>'
            )
        parts.append("</div></div>")
        out.append("".join(parts))
    return '<div class="findings">' + "".join(out) + "</div>"


def render_checklist(block):
    items = block.get("items") or []
    out = []
    for item in items:
        done = bool(item.get("done"))
        mark = "&#10003;" if done else ""
        cls = "done" if done else "todo"
        out.append(
            f'<li class="{cls}"><span class="mark">{mark}</span>'
            f"<span>{esc(item.get('label'))}</span></li>"
        )
    return '<ul class="checklist">' + "".join(out) + "</ul>"


def render_keyvalue(block):
    pairs = block.get("items") or []
    out = []
    for pair in pairs:
        out.append(
            f'<div class="kv"><dt>{esc(pair.get("label"))}</dt>'
            f'<dd>{esc(pair.get("value"))}</dd></div>'
        )
    return '<dl class="kvlist">' + "".join(out) + "</dl>"


def render_note(block):
    status = TONE_TO_STATUS.get(tone_of(block.get("tone")), "neutral")
    title = block.get("title")
    head = f"<h5>{esc(title)}</h5>" if title else ""
    return f'<div class="note s-{status}">{head}<p>{esc(block.get("text"))}</p></div>'


def render_code(block):
    label = block.get("label")
    head = f'<span class="code-label">{esc(label)}</span>' if label else ""
    return f'<div class="codewrap">{head}<pre>{esc(block.get("text"))}</pre></div>'


def render_cta(block):
    """A short closing note carrying at most two links.

    Deliberately limited. This block says where the measurement came from and
    how to reproduce it. It is not a sales slot, see CONTRACT.md.
    """
    links = [
        i for i in (block.get("links") or [])
        if isinstance(i, dict) and safe_url(i.get("url"))
    ][:2]
    rendered = " &middot; ".join(link(i.get("url"), i.get("label")) for i in links)
    title = block.get("title")
    head = f"<h5>{esc(title)}</h5>" if title else ""
    text = f'<p>{esc(block.get("text"))}</p>' if block.get("text") else ""
    tail = f'<p class="cta-links">{rendered}</p>' if rendered else ""
    return f'<div class="cta">{head}{text}{tail}</div>'


def render_quote(block):
    """A pulled sentence. Used for the one line a client repeats in a meeting."""
    source = block.get("source")
    cite = f'<cite>{esc(source)}</cite>' if source else ""
    return f'<blockquote class="pull"><p>{esc(block.get("text"))}</p>{cite}</blockquote>'


RENDERERS = {
    "table": render_table,
    "bars": render_bars,
    "composition": render_composition,
    "meter": render_meter,
    "timeseries": render_timeseries,
    "matrix": render_matrix,
    "findings": render_findings,
    "checklist": render_checklist,
    "keyvalue": render_keyvalue,
    "note": render_note,
    "code": render_code,
    "quote": render_quote,
    "cta": render_cta,
}


def render_block(block, lang):
    if not isinstance(block, dict):
        print("warning: skipped a block that is not an object", file=sys.stderr)
        return ""
    kind = block.get("type")
    renderer = RENDERERS.get(kind)
    if renderer is None:
        print("warning: unknown block type %r, skipped" % (kind,), file=sys.stderr)
        return f'<div class="note s-warning"><p>Unknown block type: {esc(kind)}</p></div>'
    block = dict(block)
    block["_lang"] = lang
    title = block.get("title") if kind not in ("note",) else None
    body = renderer(block)
    caption = block.get("caption")
    head = f'<h4 class="block-title">{esc(title)}</h4>' if title else ""
    if caption:
        body += f'<p class="caption">{esc(caption)}</p>'
    return f'<div class="block">{head}{body}</div>'


# --------------------------------------------------------------------------
# stylesheet
# --------------------------------------------------------------------------

CSS = """
*{box-sizing:border-box}
:root{
  color-scheme:light;
  --plane:#F7F7F5; --surface:#FCFCFB; --surface-2:#F1F1EE;
  --ink:#0B0B0B; --ink-2:#52514E; --muted:#898781;
  --grid:#E1E0D9; --baseline:#C3C2B7; --hair:rgba(11,11,11,.10);
  --accent:__ACCENT__; --accent-text:__ACCENT_TEXT__; --accent-wash:__ACCENT_WASH__;
  --accent-line:__ACCENT_LINE__;
  --st-good:#0CA30C; --st-warning:#FAB219; --st-serious:#EC835A; --st-critical:#D03B3B;
  --st-neutral:#898781;
  --wash-good:rgba(12,163,12,.10); --wash-warning:rgba(250,178,25,.14);
  --wash-serious:rgba(236,131,90,.14); --wash-critical:rgba(208,59,59,.10);
  --wash-neutral:rgba(137,135,129,.10);
  --seq-1:__ACCENT__; --seq-2:__SEQ2__; --seq-3:__SEQ3__; --seq-4:__SEQ4__;
  --seq-5:__SEQ5__; --seq-6:__SEQ6__;
  --sans:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  --mono:ui-monospace,"SF Mono",SFMono-Regular,Menlo,Consolas,monospace;
  --measure:38rem; --page:52rem;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  color-scheme:dark;
  --plane:#0D0D0D; --surface:#1A1A19; --surface-2:#232321;
  --ink:#FFFFFF; --ink-2:#C3C2B7; --muted:#898781;
  --grid:#2C2C2A; --baseline:#383835; --hair:rgba(255,255,255,.10);
  --accent:__ACCENT_D__; --accent-text:__ACCENT_TEXT_D__; --accent-wash:__ACCENT_WASH_D__;
  --accent-line:__ACCENT_LINE_D__;
  --wash-good:rgba(12,163,12,.16); --wash-warning:rgba(250,178,25,.16);
  --wash-serious:rgba(236,131,90,.16); --wash-critical:rgba(208,59,59,.18);
  --wash-neutral:rgba(137,135,129,.16);
  --seq-1:__ACCENT_D__; --seq-2:__SEQ2D__; --seq-3:__SEQ3D__; --seq-4:__SEQ4D__;
  --seq-5:__SEQ5D__; --seq-6:__SEQ6D__;
}}
:root[data-theme="dark"]{
  color-scheme:dark;
  --plane:#0D0D0D; --surface:#1A1A19; --surface-2:#232321;
  --ink:#FFFFFF; --ink-2:#C3C2B7; --muted:#898781;
  --grid:#2C2C2A; --baseline:#383835; --hair:rgba(255,255,255,.10);
  --accent:__ACCENT_D__; --accent-text:__ACCENT_TEXT_D__; --accent-wash:__ACCENT_WASH_D__;
  --accent-line:__ACCENT_LINE_D__;
  --wash-good:rgba(12,163,12,.16); --wash-warning:rgba(250,178,25,.16);
  --wash-serious:rgba(236,131,90,.16); --wash-critical:rgba(208,59,59,.18);
  --wash-neutral:rgba(137,135,129,.16);
  --seq-1:__ACCENT_D__; --seq-2:__SEQ2D__; --seq-3:__SEQ3D__; --seq-4:__SEQ4D__;
  --seq-5:__SEQ5D__; --seq-6:__SEQ6D__;
}

body{margin:0;background:var(--plane);color:var(--ink);font-family:var(--sans);
 font-size:15.5px;line-height:1.62;-webkit-font-smoothing:antialiased;
 text-rendering:optimizeLegibility}
.sheet{max-width:var(--page);margin:0 auto;background:var(--surface);
 border-left:1px solid var(--hair);border-right:1px solid var(--hair);min-height:100vh}
.pad{padding:0 clamp(1.25rem,5vw,3.5rem)}

/* ---------- cover ---------- */
.rule-top{height:4px;background:var(--accent)}
.cover{padding-top:clamp(2.5rem,7vw,4.5rem);padding-bottom:1.75rem}
.brandline{display:flex;align-items:center;gap:.6rem;margin:0 0 clamp(2rem,6vw,3.25rem)}
.brandmark{width:22px;height:22px;border-radius:3px;background:var(--accent);flex:none;
 display:grid;place-items:center;color:#fff;font-size:.62rem;font-weight:700;letter-spacing:.02em}
.brandname{font-size:.78rem;font-weight:600;letter-spacing:.11em;text-transform:uppercase;
 color:var(--ink-2);margin:0}
h1{font-size:clamp(2rem,5.6vw,3.1rem);line-height:1.02;letter-spacing:-.032em;
 font-weight:700;margin:0 0 1rem;text-wrap:balance;max-width:20ch}
.subject{font-size:1.05rem;color:var(--ink-2);margin:0 0 1.75rem;max-width:var(--measure)}
.subject b{color:var(--ink);font-weight:600}
.covermeta{display:flex;flex-wrap:wrap;gap:.35rem 2.5rem;padding-top:1.1rem;
 border-top:1px solid var(--grid)}
.cm{display:flex;flex-direction:column;gap:.15rem}
.cm dt{font-size:.66rem;font-weight:600;letter-spacing:.1em;text-transform:uppercase;
 color:var(--muted)}
.cm dd{margin:0;font-size:.9rem;color:var(--ink-2);font-variant-numeric:tabular-nums}

/* ---------- verdict ---------- */
.verdict{padding:2.25rem 0 .5rem}
.eyebrow{font-size:.66rem;font-weight:700;letter-spacing:.13em;text-transform:uppercase;
 color:var(--accent-text);margin:0 0 .7rem}
.v-main{font-size:clamp(1.15rem,2.7vw,1.45rem);line-height:1.38;letter-spacing:-.017em;
 font-weight:600;margin:0 0 .8rem;max-width:34ch;text-wrap:balance}
.v-detail{font-size:1rem;color:var(--ink-2);margin:0;max-width:var(--measure)}

/* ---------- kpis ---------- */
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(10.5rem,1fr));
 gap:0;margin:2.25rem 0 0;border-top:1px solid var(--grid)}
.kpi{padding:1.1rem 1.25rem 1.15rem;border-bottom:1px solid var(--grid);
 border-right:1px solid var(--grid);display:flex;flex-direction:column;gap:.1rem}
.kpi:last-child{border-right:none}
.k-l{font-size:.72rem;font-weight:600;letter-spacing:.02em;color:var(--muted);
 margin:0 0 .45rem}
.k-v{font-size:1.95rem;font-weight:700;line-height:1;letter-spacing:-.035em;margin:0}
.k-row{display:flex;align-items:center;gap:.45rem;margin-top:.45rem;min-height:1.1rem}
.k-d{font-size:.74rem;font-weight:600;padding:.08rem .34rem;border-radius:3px;
 font-variant-numeric:tabular-nums}
.k-n{font-size:.78rem;color:var(--ink-2);margin:.5rem 0 0;line-height:1.45}
.k-spark{display:block;width:100%;height:22px;margin-top:.5rem;overflow:visible}
/* Only a genuine problem colours the figure. A report where every number is
   coloured reads as a toy; one where only the problem is red reads as a finding. */
.k-critical .k-v{color:var(--st-critical)}
.k-good .k-d{background:var(--wash-good);color:var(--st-good)}
.k-critical .k-d{background:var(--wash-critical);color:var(--st-critical)}
.k-serious .k-d{background:var(--wash-serious);color:var(--st-serious)}
.k-warning .k-d{background:var(--wash-warning);color:var(--ink)}
.k-neutral .k-d{background:var(--surface-2);color:var(--ink-2)}

/* ---------- contents ---------- */
.toc{margin:3rem 0 0;padding:1.25rem 0 0;border-top:1px solid var(--grid)}
.toc h2{font-size:.66rem;font-weight:700;letter-spacing:.13em;text-transform:uppercase;
 color:var(--muted);margin:0 0 .8rem}
.toc ol{list-style:none;margin:0;padding:0;
 columns:2;column-gap:2.5rem}
.toc li{margin:0 0 .38rem;font-size:.9rem;break-inside:avoid}
.toc a{color:var(--ink-2);text-decoration:none;display:flex;gap:.7rem}
.toc a:hover{color:var(--accent-text)}
.toc .n{color:var(--muted);font-variant-numeric:tabular-nums;font-size:.8rem;
 padding-top:.1rem}

/* ---------- sections ---------- */
.body{padding-top:1rem;padding-bottom:3rem}
section{padding:2.75rem 0 0;scroll-margin-top:1rem}
.s-head{display:flex;gap:.9rem;align-items:baseline;border-top:1px solid var(--ink);
 padding-top:.75rem;margin:0 0 .6rem}
.s-num{font-size:.72rem;font-weight:700;color:var(--accent-text);flex:none;
 font-variant-numeric:tabular-nums;padding-top:.3rem}
h2.s-title{font-size:1.3rem;font-weight:650;letter-spacing:-.02em;line-height:1.2;
 margin:0;text-wrap:balance}
.intro{color:var(--ink-2);margin:0 0 1.4rem;max-width:var(--measure);font-size:.98rem}
.block{margin:0 0 1.6rem}
.block:last-child{margin-bottom:0}
.block-title{font-size:.86rem;font-weight:650;letter-spacing:-.005em;margin:0 0 .7rem;
 color:var(--ink)}
.caption{font-size:.8rem;color:var(--muted);margin:.65rem 0 0;max-width:var(--measure);
 line-height:1.5}

/* ---------- tables ---------- */
.tablewrap{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:.88rem;min-width:26rem}
th,td{text-align:left;padding:.6rem .85rem .6rem 0;border-bottom:1px solid var(--grid);
 vertical-align:top}
th:last-child,td:last-child{padding-right:0}
thead th{font-size:.68rem;font-weight:600;letter-spacing:.06em;text-transform:uppercase;
 color:var(--muted);border-bottom:1px solid var(--baseline);padding-bottom:.5rem;
 white-space:nowrap}
tbody tr:last-child td{border-bottom:none}
.num,td.num,th.num{font-variant-numeric:tabular-nums}
td.num,th.num{text-align:right;white-space:nowrap}
tbody tr:hover{background:var(--surface-2)}

/* ---------- bars ---------- */
.bars{display:grid;gap:.55rem}
.bar-row{display:grid;grid-template-columns:minmax(5.5rem,11rem) 1fr auto;gap:.85rem;
 align-items:center}
.bar-name{font-size:.82rem;color:var(--ink-2);overflow:hidden;text-overflow:ellipsis;
 white-space:nowrap}
.bar-track{height:16px;background:var(--surface-2);border-radius:2px}
.bar-fill{display:block;height:100%;background:var(--accent);border-radius:0 4px 4px 0;
 min-width:2px}
.bar-fill.s-good{background:var(--st-good)} .bar-fill.s-warning{background:var(--st-warning)}
.bar-fill.s-critical{background:var(--st-critical)} .bar-fill.s-serious{background:var(--st-serious)}
.bar-fill.s-neutral{background:var(--baseline)}
.bar-val{font-size:.82rem;font-weight:600;font-variant-numeric:tabular-nums;
 color:var(--ink);min-width:2.5rem;text-align:right}

/* ---------- stacked composition ---------- */
.stackbar{display:flex;height:34px;border-radius:3px;overflow:hidden;gap:2px;
 background:var(--surface-2)}
.seg{position:relative;display:grid;place-items:center;min-width:2px}
.seg-label{font-size:.7rem;font-weight:700;color:#fff;
 text-shadow:0 1px 2px rgba(0,0,0,.25)}
.legend{display:flex;flex-wrap:wrap;gap:.4rem 1.4rem;margin-top:.75rem}
.lg-item{display:flex;align-items:center;gap:.42rem;font-size:.82rem;color:var(--ink-2)}
.lg-dot{width:9px;height:9px;border-radius:2px;flex:none}
.lg-line{width:14px;height:2px;border-radius:1px;flex:none}
.lg-item b{color:var(--ink);font-weight:600}

/* ---------- meter ---------- */
.meter-head{display:flex;align-items:baseline;gap:.7rem;flex-wrap:wrap}
.meter-num{font-size:3rem;font-weight:700;line-height:1;letter-spacing:-.04em}
.meter-max{font-size:1.1rem;font-weight:600;color:var(--muted);letter-spacing:-.02em}
.meter-band{font-size:.72rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;
 padding:.18rem .45rem;border-radius:3px}
.meter-band.s-good{background:var(--wash-good);color:var(--st-good)}
.meter-band.s-warning{background:var(--wash-warning);color:var(--ink)}
.meter-band.s-serious{background:var(--wash-serious);color:var(--st-serious)}
.meter-band.s-critical{background:var(--wash-critical);color:var(--st-critical)}
.meter-band.s-neutral{background:var(--surface-2);color:var(--ink-2)}
.meter-label{font-size:.88rem;color:var(--ink-2);margin:.45rem 0 0;max-width:var(--measure)}
.meter-track{height:10px;background:var(--accent-wash);border-radius:2px;margin:.9rem 0 .4rem}
.meter-fill{display:block;height:100%;background:var(--accent);border-radius:0 4px 4px 0}
.meter-fill.s-good{background:var(--st-good)} .meter-fill.s-warning{background:var(--st-warning)}
.meter-fill.s-serious{background:var(--st-serious)} .meter-fill.s-critical{background:var(--st-critical)}
.meter-ticks{position:relative;height:1rem}
.meter-ticks span{position:absolute;transform:translateX(-50%);font-size:.7rem;
 color:var(--muted);font-variant-numeric:tabular-nums}
.meter-ticks span:first-child{transform:none}
.meter-ticks span:last-child{transform:translateX(-100%)}

/* ---------- timeseries ---------- */
.ts{display:grid;grid-template-columns:auto 1fr;gap:.7rem;align-items:stretch}
.ts svg{width:100%;height:150px;display:block;border-left:1px solid var(--grid);
 border-bottom:1px solid var(--baseline)}
.ts-scale{display:flex;flex-direction:column;justify-content:space-between;
 font-size:.7rem;color:var(--muted);font-variant-numeric:tabular-nums;padding:2px 0}
.svg-tick{font-size:10px;fill:var(--muted);font-family:var(--sans)}
.ts-axis{display:flex;justify-content:space-between;font-size:.72rem;color:var(--muted);
 margin-top:.3rem;padding-left:2.5rem;font-variant-numeric:tabular-nums}

/* ---------- matrix ---------- */
.matrix{display:grid;grid-template-columns:repeat(2,1fr);gap:2px;background:var(--grid);
 border:1px solid var(--grid);border-radius:3px;overflow:hidden}
.quad{background:var(--surface);padding:1rem 1.05rem}
.q-head{display:flex;align-items:baseline;justify-content:space-between;gap:.6rem;
 margin-bottom:.3rem}
.quad h5{font-size:.92rem;font-weight:650;margin:0;letter-spacing:-.01em}
.q-count{font-size:1.05rem;font-weight:700;letter-spacing:-.02em}
.quad.s-good h5,.quad.s-good .q-count{color:var(--st-good)}
.quad.s-critical h5,.quad.s-critical .q-count{color:var(--st-critical)}
.quad.s-serious h5,.quad.s-serious .q-count{color:var(--st-serious)}
.quad.s-warning h5,.quad.s-warning .q-count{color:var(--ink)}
.q-read{font-size:.83rem;color:var(--ink-2);margin:0 0 .55rem;line-height:1.5}
.quad ul{margin:0;padding-left:1rem;font-size:.8rem;color:var(--muted)}
.quad li{margin-bottom:.18rem;word-break:break-word}
.axes{font-size:.72rem;color:var(--muted);margin:.55rem 0 0}

/* ---------- findings ---------- */
.findings{display:grid;gap:0;border-top:1px solid var(--grid)}
.finding{display:grid;grid-template-columns:5.2rem 1fr;gap:1rem;padding:1rem 0;
 border-bottom:1px solid var(--grid)}
.f-rail{display:flex;flex-direction:column;gap:.4rem;align-items:flex-start}
.f-index{font-size:.75rem;font-weight:700;color:var(--muted)}
.sev{font-size:.63rem;font-weight:700;letter-spacing:.07em;text-transform:uppercase;
 padding:.16rem .4rem;border-radius:3px;white-space:nowrap}
.s-critical .sev{background:var(--wash-critical);color:var(--st-critical)}
.s-serious .sev{background:var(--wash-serious);color:var(--st-serious)}
.s-neutral .sev{background:var(--surface-2);color:var(--ink-2)}
.s-good .sev{background:var(--wash-good);color:var(--st-good)}
.f-title{font-weight:650;margin:0 0 .45rem;font-size:1rem;letter-spacing:-.01em;
 line-height:1.35;max-width:44ch}
.f-line{font-size:.87rem;color:var(--ink-2);margin:0 0 .3rem;max-width:var(--measure);
 line-height:1.5}
.f-line b{font-size:.64rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;
 color:var(--muted);display:block;margin-bottom:.05rem}
.f-do b{color:var(--accent-text)}
.f-body p:last-child{margin-bottom:0}

/* ---------- checklist, kv, note, code, quote ---------- */
.checklist{list-style:none;padding:0;margin:0;display:grid;gap:.05rem}
.checklist li{display:grid;grid-template-columns:1.25rem 1fr;gap:.6rem;font-size:.92rem;
 padding:.42rem 0;border-bottom:1px solid var(--grid);align-items:baseline}
.checklist li:last-child{border-bottom:none}
.checklist .mark{width:1rem;height:1rem;border-radius:3px;display:grid;place-items:center;
 font-size:.66rem;line-height:1;border:1px solid var(--baseline)}
.checklist .done .mark{background:var(--st-good);border-color:var(--st-good);color:#fff}
.checklist .done{color:var(--muted)}
.kvlist{display:grid;grid-template-columns:repeat(auto-fit,minmax(11rem,1fr));
 gap:1px;background:var(--grid);border:1px solid var(--grid);border-radius:3px;margin:0}
.kv{background:var(--surface);padding:.7rem .85rem}
.kv dt{font-size:.66rem;font-weight:600;letter-spacing:.08em;text-transform:uppercase;
 color:var(--muted);margin-bottom:.2rem}
.kv dd{margin:0;font-size:.9rem;word-break:break-word}
.note{border-left:2px solid var(--baseline);background:var(--surface-2);
 padding:.9rem 1.1rem;border-radius:0 3px 3px 0}
.note.s-good{border-left-color:var(--st-good);background:var(--wash-good)}
.note.s-warning{border-left-color:var(--st-warning);background:var(--wash-warning)}
.note.s-serious{border-left-color:var(--st-serious);background:var(--wash-serious)}
.note.s-critical{border-left-color:var(--st-critical);background:var(--wash-critical)}
.note h5{font-size:.86rem;font-weight:650;margin:0 0 .25rem}
.note p{margin:0;font-size:.88rem;color:var(--ink-2);max-width:var(--measure)}
.codewrap{border:1px solid var(--grid);border-radius:3px;overflow:hidden}
.code-label{display:block;font-size:.66rem;font-weight:600;letter-spacing:.08em;
 text-transform:uppercase;color:var(--muted);padding:.5rem .9rem;
 background:var(--surface-2);border-bottom:1px solid var(--grid)}
pre{font-family:var(--mono);font-size:.79rem;line-height:1.6;margin:0;
 padding:.85rem .9rem;overflow-x:auto;color:var(--ink-2)}
.pull{margin:0;padding:0 0 0 1.1rem;border-left:2px solid var(--accent)}
.pull p{font-size:1.08rem;line-height:1.45;font-weight:500;margin:0;letter-spacing:-.012em;
 max-width:34ch}
.pull cite{display:block;font-size:.78rem;color:var(--muted);font-style:normal;
 margin-top:.5rem}

/* ---------- cta and provenance ---------- */
.cta{border:1px solid var(--grid);border-left:2px solid var(--accent);border-radius:0 3px 3px 0;
 padding:.9rem 1.1rem;background:var(--surface)}
.cta h5{font-size:.86rem;font-weight:650;margin:0 0 .25rem}
.cta p{margin:0;font-size:.88rem;color:var(--ink-2);max-width:var(--measure)}
.cta-links{margin-top:.55rem!important;font-size:.85rem}
.cta-links a{color:var(--accent-text);text-underline-offset:2px}
.provenance{font-size:.78rem;color:var(--muted);line-height:1.55;margin:2.5rem 0 0;
 max-width:var(--measure);padding-top:1rem;border-top:1px solid var(--grid)}

/* ---------- footer ---------- */
footer{border-top:1px solid var(--grid);padding:1.1rem 0 2.5rem;margin-top:3rem;
 display:flex;flex-wrap:wrap;gap:.4rem 1.5rem;justify-content:space-between;
 font-size:.72rem;color:var(--muted)}
footer .fmark{display:flex;align-items:center;gap:.45rem}
footer .fdot{width:7px;height:7px;border-radius:2px;background:var(--accent);flex:none}

@media (max-width:680px){
  body{font-size:15px}
  .matrix{grid-template-columns:1fr}
  .finding{grid-template-columns:1fr;gap:.5rem}
  .f-rail{flex-direction:row;align-items:center;gap:.6rem}
  .toc ol{columns:1}
  .kpi{border-right:none}
  .bar-row{grid-template-columns:minmax(4.5rem,8rem) 1fr auto;gap:.6rem}
}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}

@media print{
  @page{margin:14mm 13mm}
  body{background:#fff;font-size:10pt;line-height:1.5}
  .sheet{max-width:none;border:none;background:#fff;min-height:0}
  .pad{padding:0}
  .rule-top{height:3px}
  .cover{padding-top:0}
  h1{font-size:24pt} .k-v{font-size:16pt} .meter-num{font-size:22pt}
  section{padding-top:1.4rem;break-inside:auto}
  .s-head{break-after:avoid} .block-title{break-after:avoid}
  .finding,.quad,.kpi,.note,.codewrap,.meter,.ts{break-inside:avoid}
  .toc{break-after:page}
  tbody tr:hover{background:none}
  a{color:inherit;text-decoration:none}
  footer{break-inside:avoid}
}
"""


# --------------------------------------------------------------------------
# page
# --------------------------------------------------------------------------

def build_tokens(accent_raw):
    light_surface, dark_surface = "#FCFCFB", "#1A1A19"
    accent_l = ensure_contrast(accent_raw, light_surface, 3.0, "#000000")
    accent_text_l = ensure_contrast(accent_l, light_surface, 4.5, "#000000")
    accent_d = ensure_contrast(accent_raw, dark_surface, 3.0, "#FFFFFF")
    accent_text_d = ensure_contrast(accent_d, dark_surface, 4.5, "#FFFFFF")

    # A one hue sequential ramp for composition segments, light to dark.
    seq_l = [mix(accent_l, "#FFFFFF", f) for f in (0.0, 0.16, 0.32, 0.45, 0.55, 0.62)]
    seq_d = [mix(accent_d, "#000000", f) for f in (0.0, 0.15, 0.30, 0.42, 0.52, 0.60)]

    return {
        "__ACCENT__": accent_l,
        "__ACCENT_TEXT__": accent_text_l,
        "__ACCENT_WASH__": mix(accent_l, light_surface, 0.86),
        "__ACCENT_LINE__": mix(accent_l, light_surface, 0.62),
        "__ACCENT_D__": accent_d,
        "__ACCENT_TEXT_D__": accent_text_d,
        "__ACCENT_WASH_D__": mix(accent_d, dark_surface, 0.84),
        "__ACCENT_LINE_D__": mix(accent_d, dark_surface, 0.6),
        "__SEQ2__": seq_l[1], "__SEQ3__": seq_l[2], "__SEQ4__": seq_l[3],
        "__SEQ5__": seq_l[4], "__SEQ6__": seq_l[5],
        "__SEQ2D__": seq_d[1], "__SEQ3D__": seq_d[2], "__SEQ4D__": seq_d[3],
        "__SEQ5D__": seq_d[4], "__SEQ6D__": seq_d[5],
    }


def initials(name):
    if not name:
        return ""
    parts = [p for p in re.split(r"[\s\-_.]+", str(name)) if p]
    return "".join(p[0] for p in parts[:2]).upper()


def render_spark(values):
    """A 12 point sparkline for a stat tile, current point in the accent."""
    values = numbers(values)
    if len(values) < 3:
        return ""
    values = values[-12:]
    width, height = 100.0, 22.0
    pts, _, _ = svg_points(values, width, height, pad=3.0)
    path = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    ex, ey = pts[-1]
    return (
        f'<svg class="k-spark" viewBox="0 0 {width:.0f} {height:.0f}" '
        'preserveAspectRatio="none" aria-hidden="true">'
        f'<polyline points="{path}" fill="none" stroke="var(--baseline)" stroke-width="1.5" '
        'stroke-linejoin="round" stroke-linecap="round"></polyline>'
        f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="2.6" fill="var(--accent)" '
        'stroke="var(--surface)" stroke-width="1.5"></circle></svg>'
    )


# --------------------------------------------------------------------------
# the agency profile
# --------------------------------------------------------------------------
#
# A freelance sets their identity once and every report from every skill wears
# it, instead of retyping the brand into each findings file. The findings file
# always wins: explicit beats ambient, so a per client override still works.
#
# Read from disk, so treated like any other untrusted input. Values are escaped
# by the same esc() as everything else, the colour goes through the same
# contrast correction, and no key here can inject markup. A missing or broken
# profile degrades to no profile and never stops a run.

AGENCY_KEYS = ("name", "color", "lang", "credit", "footer_note", "prepared_by")

AGENCY_TEMPLATE = {
    "_comment": "Agency profile for the Hack The SEO report engine. "
                "Put this file next to your reports, or at "
                "~/.config/hacktheseo/agency.json, and every report you build "
                "wears it. Anything you set in a findings file overrides it.",
    "name": "Your agency name",
    "color": "#1F4B99",
    "lang": "fr",
    "credit": True,
    "footer_note": "you@example.com",
    "prepared_by": "Your agency name",
}


def agency_profile_path(explicit=None):
    """Where the profile lives, most specific first. Returns a path or None."""
    candidates = []
    if explicit:
        candidates.append(explicit)
    env = os.environ.get("HTS_AGENCY_PROFILE")
    if env:
        candidates.append(env)
    candidates.append(os.path.join(os.getcwd(), "agency.json"))
    home = os.path.expanduser("~")
    if home and home != "~":
        candidates.append(os.path.join(home, ".config", "hacktheseo", "agency.json"))
    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            return candidate
    return None


def load_agency_profile(path):
    """
    Read the profile, or return an empty one.

    Never raises. A profile that cannot be read is a profile that is not
    applied, and the caller says so on stderr. A report that fails to build
    because of a branding file would be the worst possible trade.
    """
    if not path:
        return {}, ""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, ValueError) as error:
        return {}, "ignored the agency profile %s: %s" % (path, error)
    if not isinstance(payload, dict):
        return {}, "ignored the agency profile %s: the top level must be an object" % path
    profile = {}
    for key in AGENCY_KEYS:
        if key in payload and payload[key] is not None:
            profile[key] = payload[key]
    return profile, ""


def apply_agency_profile(data, profile):
    """Fill only what the findings file left empty."""
    if not profile:
        return data
    meta = data.setdefault("meta", {})
    if not isinstance(meta, dict):
        return data
    brand = meta.setdefault("brand", {})
    if isinstance(brand, dict):
        if not brand.get("name") and profile.get("name"):
            brand["name"] = profile["name"]
        if not brand.get("color") and profile.get("color"):
            brand["color"] = profile["color"]
    for key in ("lang", "footer_note", "prepared_by"):
        if not meta.get(key) and profile.get(key):
            meta[key] = profile[key]
    # credit is a boolean, so "not set" has to be tested by absence. Removing
    # our name is free and complete, and the profile is allowed to do it once
    # for every report rather than per file.
    if "credit" not in meta and "credit" in profile:
        meta["credit"] = bool(profile["credit"])
    return data


def build_html(data, artifact=False):
    meta = data.get("meta") or {}
    lang = (meta.get("lang") or "en").lower()
    if lang not in STRINGS:
        lang = "en"
    words = STRINGS[lang]
    brand = meta.get("brand") or {}
    tokens = build_tokens(parse_hex(brand.get("color")))

    title = meta.get("title") or "SEO report"
    generated = meta.get("generated") or date.today().isoformat()

    # cover
    mark = esc(initials(brand.get("name")) or "")
    brandline = ""
    if brand.get("name"):
        brandline = (
            f'<div class="brandline"><span class="brandmark">{mark}</span>'
            f'<p class="brandname">{esc(brand["name"])}</p></div>'
        )
    else:
        brandline = '<div class="brandline"><span class="brandmark"></span></div>'

    subject = ""
    if meta.get("subject"):
        subject = f'<p class="subject"><b>{esc(meta["subject"])}</b></p>'

    cover_meta = [(words["generated"], generated)]
    if meta.get("period"):
        cover_meta.insert(0, (words["period"], meta["period"]))
    if meta.get("prepared_for"):
        cover_meta.append((words["prepared"], meta["prepared_for"]))
    covermeta = '<dl class="covermeta">' + "".join(
        f'<div class="cm"><dt>{esc(k)}</dt><dd>{esc(v)}</dd></div>' for k, v in cover_meta
    ) + "</dl>"

    # verdict
    headline = data.get("headline") or {}
    verdict = ""
    if headline.get("verdict"):
        detail = (
            f'<p class="v-detail">{esc(headline["detail"])}</p>'
            if headline.get("detail")
            else ""
        )
        eyebrow = headline.get("eyebrow") or (
            "En résumé" if lang == "fr" else "In short"
        )
        verdict = (
            '<div class="verdict">'
            f'<p class="eyebrow">{esc(eyebrow)}</p>'
            f'<p class="v-main">{esc(headline["verdict"])}</p>{detail}</div>'
        )

    # kpis
    kpis = data.get("kpis") or []
    kpi_html = ""
    if kpis:
        cells = []
        for kpi in kpis[:5]:
            status = TONE_TO_STATUS.get(tone_of(kpi.get("tone")), "neutral")
            delta = (
                f'<span class="k-d">{esc(kpi["delta"])}</span>' if kpi.get("delta") else ""
            )
            spark = render_spark(kpi.get("spark") or [])
            row = f'<div class="k-row">{delta}</div>' if delta else ""
            note = f'<p class="k-n">{esc(kpi["note"])}</p>' if kpi.get("note") else ""
            cells.append(
                f'<div class="kpi k-{status}"><p class="k-l">{esc(kpi.get("label"))}</p>'
                f'<p class="k-v">{esc(kpi.get("value"))}</p>{row}{spark}{note}</div>'
            )
        kpi_html = '<div class="kpis">' + "".join(cells) + "</div>"

    # sections
    section_list = data.get("sections") or []
    if not isinstance(section_list, list):
        raise ValueError(
            "\"sections\" must be a list of objects, got %s"
            % type(section_list).__name__
        )
    sections, toc_items = [], []
    for index, section in enumerate(section_list, start=1):
        if not isinstance(section, dict):
            print("warning: skipped a section that is not an object", file=sys.stderr)
            continue
        anchor = f"s{index}"
        toc_items.append(
            f'<li><a href="#{anchor}"><span class="n">{index:02d}</span>'
            f'<span>{esc(section.get("title"))}</span></a></li>'
        )
        intro = (
            f'<p class="intro">{esc(section["intro"])}</p>' if section.get("intro") else ""
        )
        blocks = "".join(
            render_block(block, lang) for block in (section.get("blocks") or [])
        )
        sections.append(
            f'<section id="{anchor}"><div class="s-head">'
            f'<span class="s-num">{index:02d}</span>'
            f'<h2 class="s-title">{esc(section.get("title"))}</h2></div>'
            f"{intro}{blocks}</section>"
        )

    toc = ""
    if len(section_list) >= 4:
        toc = (
            f'<nav class="toc"><h2>{esc(words["contents"])}</h2><ol>'
            + "".join(toc_items)
            + "</ol></nav>"
        )

    # footer
    foot = []
    if meta.get("credit", True):
        foot.append(
            '<span class="fmark"><span class="fdot"></span>'
            + link(CREDIT_URL, words["credit"])
            + "</span>"
        )
    if meta.get("footer_note"):
        foot.append(f"<span>{esc(meta['footer_note'])}</span>")
    footer = "<footer>" + "".join(foot) + "</footer>" if foot else ""

    # The provenance line says where the measurement comes from. It survives
    # meta.credit=false on purpose: removing our name from a white label report
    # is fair, removing the source of the numbers is not.
    note = meta.get("source_note")
    if note is False:
        provenance = ""
    else:
        if not isinstance(note, str) or not note.strip():
            note = words["source_note"]
        provenance = f'<p class="provenance">{esc(note)}</p>' 

    # The visible h1 stays the report title. The document title, which lands in
    # the browser tab, the bookmark and any share card, also carries the subject
    # and the period, because an agency ends the month with a dozen of these
    # open at once and "SEO report" on every tab helps nobody.
    doc_title = ", ".join(
        part for part in (title, meta.get("subject"), meta.get("period")) if part
    )
    summary = (headline.get("verdict") or meta.get("subject") or title or "").strip()
    if len(summary) > 300:
        summary = summary[:297].rstrip() + "..."

    css = CSS
    for key, value in tokens.items():
        css = css.replace(key, value)

    page = (
        '<div class="sheet"><div class="rule-top"></div>'
        f'<header class="cover pad">{brandline}<h1>{esc(title)}</h1>{subject}{covermeta}</header>'
        f'<div class="pad">{verdict}{kpi_html}{toc}</div>'
        f'<main class="body pad">{"".join(sections)}{provenance}{footer}</main>'
        "</div>"
    )
    if artifact:
        # No doctype, html, head or body: the artifact host supplies those.
        return f"<title>{esc(title)}</title>\n<style>{css}</style>\n{page}"
    return (
        "<!doctype html>\n"
        f'<html lang="{esc(lang)}"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{esc(doc_title)}</title>"
        f'<meta name="description" content="{esc(summary)}">'
        '<meta name="generator" content="Hack The SEO agent skills, hacktheseo.com">'
        f'<meta property="og:title" content="{esc(doc_title)}">'
        f'<meta property="og:description" content="{esc(summary)}">'
        '<meta property="og:type" content="article">'
        f"<style>{css}</style></head><body>"
        + page
        + "</body></html>"
    )


def slug(text):
    text = re.sub(r"[^A-Za-z0-9]+", "-", str(text or "")).strip("-").lower()
    return text[:48] or "report"


def suggested_name(data):
    """<domain>-<subject>-<YYYY-MM>.html, the name an agency can file."""
    meta = data.get("meta") or {}
    domain = slug(meta.get("subject"))
    subject = slug(meta.get("title"))
    stamp = ""
    for field in (meta.get("period"), meta.get("generated")):
        found = re.search(r"(\d{4})[-/ ]?(\d{2})", str(field or ""))
        if found:
            stamp = "%s-%s" % (found.group(1), found.group(2))
            break
    parts = [p for p in (domain, subject, stamp) if p]
    return "-".join(parts) + ".html"


def main(argv):
    if "--print-brand-template" in argv:
        print(json.dumps(AGENCY_TEMPLATE, indent=2, ensure_ascii=False))
        return 0

    artifact = "--artifact" in argv
    argv = [a for a in argv if a != "--artifact"]

    brand_path = None
    if "--brand" in argv:
        index = argv.index("--brand")
        if index + 1 >= len(argv):
            print("--brand needs a path to an agency profile", file=sys.stderr)
            return 2
        brand_path = argv[index + 1]
        del argv[index:index + 2]

    if len(argv) != 3:
        print(
            "usage: render_report.py [--artifact] [--brand agency.json] "
            "<findings.json> <output.html>",
            file=sys.stderr,
        )
        print("       render_report.py --print-brand-template", file=sys.stderr)
        return 2
    try:
        with open(argv[1], "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        print(f"input not found: {argv[1]}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as error:
        print(f"invalid JSON in {argv[1]}: {error}", file=sys.stderr)
        return 1

    if not isinstance(data, dict):
        print("the top level of the findings file must be an object", file=sys.stderr)
        return 1

    if brand_path and not os.path.isfile(brand_path):
        print("agency profile not found: %s" % brand_path, file=sys.stderr)
        return 1
    found = agency_profile_path(brand_path)
    profile, complaint = load_agency_profile(found)
    if complaint:
        print(complaint, file=sys.stderr)
    data = apply_agency_profile(data, profile)

    try:
        page = build_html(data, artifact=artifact)
    except Exception as error:
        # A contract mistake must read as a contract mistake, not as a Python
        # traceback the user has to decode.
        print("invalid contract: %s: %s" % (type(error).__name__, error),
              file=sys.stderr)
        print("see CONTRACT.md next to this script", file=sys.stderr)
        return 1

    try:
        with open(argv[2], "w", encoding="utf-8") as handle:
            handle.write(page)
    except OSError as error:
        print(f"cannot write {argv[2]}: {error}", file=sys.stderr)
        return 1

    print(f"wrote {argv[2]}")
    if os.path.basename(argv[2]) in ("report.html", "page.html", "out.html",
                                     "output.html", "rapport.html"):
        print("suggested name: %s" % suggested_name(data), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
