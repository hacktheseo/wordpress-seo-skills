#!/usr/bin/env python3
"""
parse_logs.py, AI crawler forensics on server access logs.

Reads one or more access logs (Apache combined, Nginx combined or custom,
Cloudflare Logpush JSON lines, host CSV exports), finds requests that claim to
come from an AI crawler, verifies that claim, and prints one aggregated JSON
document on stdout.

Design constraints, on purpose:
  - Python standard library only.
  - Streaming: one line at a time, counters updated on the fly. A 500 MB log
    never lands in memory.
  - Tolerant: a malformed line is counted and skipped, never fatal.
  - Honest: a hit whose origin cannot be verified is reported as unverifiable,
    never as verified. A hit proven not to come from the provider it claims is
    reported as spoofed and is excluded from every other counter.

Usage:
    python3 parse_logs.py access.log [more.log.gz ...] [options] > bots.json

Run with --help for the full option list.

Part of the Hack The SEO agent skills.
Licence: GPL-2.0-or-later
"""

import argparse
import bz2
import gzip
import io
import ipaddress
import json
import lzma
import os
import random
import re
import socket
import sys
from collections import Counter
from datetime import datetime, timezone

SCHEMA = "hts.ai-bot-log-forensics/1"

# --------------------------------------------------------------------------
# Bot table. Survey date below. This list moves, re-check it before quoting it.
# The human readable version lives in references/user-agents.md.
# purpose values:
#   training   : corpus collection for model training
#   user_fetch : real time fetch triggered by one user question
#   search     : building or refreshing a search index used at answer time
#   preview    : link unfurling, not an AI signal
# --------------------------------------------------------------------------

BOT_SURVEY_DATE = "2026-09-08"

BOTS = [
    # OpenAI
    {"pat": "gptbot", "name": "GPTBot", "provider": "OpenAI", "purpose": "training",
     "ranges": "openai", "rdns": []},
    {"pat": "chatgpt-user", "name": "ChatGPT-User", "provider": "OpenAI", "purpose": "user_fetch",
     "ranges": "openai", "rdns": []},
    {"pat": "oai-searchbot", "name": "OAI-SearchBot", "provider": "OpenAI", "purpose": "search",
     "ranges": "openai", "rdns": []},
    # Anthropic
    {"pat": "claudebot", "name": "ClaudeBot", "provider": "Anthropic", "purpose": "training",
     "ranges": "anthropic", "rdns": []},
    {"pat": "claude-user", "name": "Claude-User", "provider": "Anthropic", "purpose": "user_fetch",
     "ranges": "anthropic", "rdns": []},
    {"pat": "claude-searchbot", "name": "Claude-SearchBot", "provider": "Anthropic", "purpose": "search",
     "ranges": "anthropic", "rdns": []},
    {"pat": "anthropic-ai", "name": "anthropic-ai (legacy)", "provider": "Anthropic", "purpose": "training",
     "ranges": "anthropic", "rdns": []},
    {"pat": "claude-web", "name": "claude-web (legacy)", "provider": "Anthropic", "purpose": "user_fetch",
     "ranges": "anthropic", "rdns": []},
    # Perplexity
    {"pat": "perplexitybot", "name": "PerplexityBot", "provider": "Perplexity", "purpose": "search",
     "ranges": "perplexity", "rdns": []},
    {"pat": "perplexity-user", "name": "Perplexity-User", "provider": "Perplexity", "purpose": "user_fetch",
     "ranges": "perplexity", "rdns": []},
    # Google
    {"pat": "google-cloudvertexbot", "name": "Google-CloudVertexBot", "provider": "Google", "purpose": "user_fetch",
     "ranges": "google", "rdns": [".google.com", ".googlebot.com", ".googleusercontent.com"]},
    {"pat": "google-extended", "name": "Google-Extended", "provider": "Google", "purpose": "training",
     "ranges": "google", "rdns": [".google.com", ".googlebot.com"]},
    {"pat": "googleother", "name": "GoogleOther", "provider": "Google", "purpose": "training",
     "ranges": "google", "rdns": [".google.com", ".googlebot.com", ".googleusercontent.com"]},
    {"pat": "googlebot", "name": "Googlebot", "provider": "Google", "purpose": "search",
     "ranges": "google", "rdns": [".googlebot.com", ".google.com"]},
    # Microsoft
    {"pat": "bingbot", "name": "Bingbot", "provider": "Microsoft", "purpose": "search",
     "ranges": "microsoft", "rdns": [".search.msn.com"]},
    # Common Crawl
    {"pat": "ccbot", "name": "CCBot", "provider": "Common Crawl", "purpose": "training",
     "ranges": "commoncrawl", "rdns": []},
    # Amazon
    {"pat": "amazonbot", "name": "Amazonbot", "provider": "Amazon", "purpose": "search",
     "ranges": "amazon", "rdns": [".crawl.amazonbot.amazon"]},
    # Meta
    {"pat": "meta-externalagent", "name": "meta-externalagent", "provider": "Meta", "purpose": "training",
     "ranges": "meta", "rdns": [".fbsv.net", ".facebook.com"]},
    {"pat": "meta-externalfetcher", "name": "meta-externalfetcher", "provider": "Meta", "purpose": "user_fetch",
     "ranges": "meta", "rdns": [".fbsv.net", ".facebook.com"]},
    {"pat": "facebookbot", "name": "FacebookBot", "provider": "Meta", "purpose": "training",
     "ranges": "meta", "rdns": [".fbsv.net", ".facebook.com"]},
    {"pat": "facebookexternalhit", "name": "facebookexternalhit", "provider": "Meta", "purpose": "preview",
     "ranges": "meta", "rdns": [".fbsv.net", ".facebook.com"]},
    # Apple
    {"pat": "applebot-extended", "name": "Applebot-Extended", "provider": "Apple", "purpose": "training",
     "ranges": "apple", "rdns": [".applebot.apple.com"]},
    {"pat": "applebot", "name": "Applebot", "provider": "Apple", "purpose": "search",
     "ranges": "apple", "rdns": [".applebot.apple.com"]},
    # ByteDance
    {"pat": "bytespider", "name": "Bytespider", "provider": "ByteDance", "purpose": "training",
     "ranges": "bytedance", "rdns": []},
    {"pat": "tiktokspider", "name": "TikTokSpider", "provider": "ByteDance", "purpose": "training",
     "ranges": "bytedance", "rdns": []},
    # Cohere
    {"pat": "cohere-training-data-crawler", "name": "cohere-training-data-crawler", "provider": "Cohere",
     "purpose": "training", "ranges": "cohere", "rdns": []},
    {"pat": "cohere-ai", "name": "cohere-ai", "provider": "Cohere", "purpose": "user_fetch",
     "ranges": "cohere", "rdns": []},
    # Mistral
    {"pat": "mistralai-user", "name": "MistralAI-User", "provider": "Mistral AI", "purpose": "user_fetch",
     "ranges": "mistral", "rdns": []},
    {"pat": "mistralai", "name": "MistralAI (other)", "provider": "Mistral AI", "purpose": "training",
     "ranges": "mistral", "rdns": []},
    # xAI
    {"pat": "xai-bot", "name": "xAI-Bot", "provider": "xAI", "purpose": "training",
     "ranges": "xai", "rdns": []},
    {"pat": "grokbot", "name": "GrokBot", "provider": "xAI", "purpose": "user_fetch",
     "ranges": "xai", "rdns": []},
    # DeepSeek. No crawler documented at survey date, so any hit claiming it is
    # unverifiable by construction. Kept in the table so it gets surfaced.
    {"pat": "deepseek", "name": "DeepSeek (undocumented)", "provider": "DeepSeek", "purpose": "training",
     "ranges": "deepseek", "rdns": []},
    # Answer engines and data brokers that feed model corpora
    {"pat": "youbot", "name": "YouBot", "provider": "You.com", "purpose": "search",
     "ranges": "youcom", "rdns": []},
    {"pat": "diffbot", "name": "Diffbot", "provider": "Diffbot", "purpose": "training",
     "ranges": "diffbot", "rdns": []},
    {"pat": "omgilibot", "name": "Omgilibot", "provider": "Webz.io", "purpose": "training",
     "ranges": "webzio", "rdns": []},
    {"pat": "webzio-extended", "name": "Webzio-Extended", "provider": "Webz.io", "purpose": "training",
     "ranges": "webzio", "rdns": []},
    {"pat": "timpibot", "name": "Timpibot", "provider": "Timpi", "purpose": "training",
     "ranges": "timpi", "rdns": []},
    {"pat": "imagesiftbot", "name": "ImagesiftBot", "provider": "Hive", "purpose": "training",
     "ranges": "imagesift", "rdns": []},
    {"pat": "petalbot", "name": "PetalBot", "provider": "Huawei", "purpose": "search",
     "ranges": "huawei", "rdns": [".petalsearch.com"]},
]

# Longest pattern first so chatgpt-user never gets swallowed by a shorter token.
BOTS.sort(key=lambda b: len(b["pat"]), reverse=True)

AI_PURPOSES = ("training", "user_fetch", "search")

# Used only to keep the human baseline honest, never reported as AI traffic.
GENERIC_BOT_HINTS = (
    "bot", "crawler", "spider", "slurp", "crawl", "fetch", "scrapy", "curl",
    "wget", "python-requests", "python-urllib", "go-http-client", "java/",
    "headlesschrome", "libwww", "okhttp", "axios", "monitoring", "uptime",
    "pingdom", "ahrefs", "semrush", "dataforseo", "screaming frog",
)

MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

TS_RE = re.compile(
    r"\[(\d{1,2})/([A-Za-z]{3})/(\d{4}):(\d{2}):(\d{2}):(\d{2})(?:\s*([+-]\d{4}))?\]"
)
QUOTED_RE = re.compile(r'"((?:[^"\\]|\\.)*)"')
FLOAT_RE = re.compile(r"^\d+(?:\.\d+)?$")
PAGINATION_RE = re.compile(r"/(?:page|p)/\d+|[?&](?:page|paged|p)=\d+", re.I)


class SkillError(Exception):
    """An error the operator can act on. Printed as a message, never a traceback."""


# --------------------------------------------------------------------------
# input handling
# --------------------------------------------------------------------------

def open_log(path):
    """Open a log file as text, transparently handling gzip, bzip2 and xz."""
    try:
        raw = open(path, "rb")
    except OSError as exc:
        raise SkillError(
            "cannot open %s (%s). Check the path and the read permission."
            % (path, exc.strerror or exc)
        )
    head = raw.read(6)
    raw.seek(0)
    if head[:2] == b"\x1f\x8b":
        stream = gzip.open(raw, "rb")
    elif head[:3] == b"BZh":
        stream = bz2.open(raw, "rb")
    elif head[:6] == b"\xfd7zXZ\x00":
        stream = lzma.open(raw, "rb")
    else:
        stream = raw
    return io.TextIOWrapper(stream, encoding="utf-8", errors="replace", newline="")


def expand_inputs(paths):
    """Accept files and directories. Directories are scanned one level deep."""
    out = []
    for path in paths:
        if os.path.isdir(path):
            for name in sorted(os.listdir(path)):
                full = os.path.join(path, name)
                if os.path.isfile(full):
                    out.append(full)
        elif os.path.isfile(path):
            out.append(path)
        else:
            raise SkillError(
                "no such file or directory: %s. Pass the access log path, or the "
                "folder that holds the rotated logs." % path
            )
    if not out:
        raise SkillError("no readable log file found in the paths given.")
    return out


# --------------------------------------------------------------------------
# line parsers
# --------------------------------------------------------------------------

def parse_ip(token):
    """Return a clean IP string, or None. Handles comma lists from proxies."""
    if not token:
        return None
    for candidate in token.split(","):
        candidate = candidate.strip().strip('"')
        if candidate.startswith("[") and "]" in candidate:
            candidate = candidate[1:candidate.index("]")]
        if ":" in candidate and candidate.count(":") == 1 and "." in candidate:
            candidate = candidate.split(":")[0]
        try:
            ipaddress.ip_address(candidate)
            return candidate
        except ValueError:
            continue
    return None


def parse_apache_ts(day, mon, year, hh, mm, ss):
    month = MONTHS.get(mon.lower())
    if not month:
        return None
    try:
        return datetime(int(year), month, int(day), int(hh), int(mm), int(ss))
    except ValueError:
        return None


def read_response_time(tokens):
    """
    Find a request time in the trailing fields of a custom log line.
    Heuristic, stated in the output: a value with a decimal point is seconds
    (Nginx $request_time, Apache %T), a bare integer above 1000 is microseconds
    (Apache %D). Anything else is ignored.
    """
    for token in tokens:
        token = token.strip()
        if not FLOAT_RE.match(token):
            continue
        value = float(token)
        if "." in token:
            if 0 <= value <= 900:
                return value * 1000.0
        elif value > 1000:
            return value / 1000.0
    return None


def parse_combined(line):
    """
    Tolerant parser for combined style lines. Covers Apache combined, Nginx
    combined, the vhost prefixed variants used by OVH and cPanel hosts
    (o2switch), and custom formats that append extra fields.
    """
    match = TS_RE.search(line)
    if not match:
        return None
    left = line[:match.start()]
    right = line[match.end():]

    ip = None
    for token in reversed(left.split()):
        ip = parse_ip(token)
        if ip:
            break
    if not ip:
        return None

    stamp = parse_apache_ts(*match.group(1, 2, 3, 4, 5, 6))
    if stamp is None:
        return None

    quoted = QUOTED_RE.findall(right)
    if not quoted:
        return None
    request = quoted[0]
    if len(quoted) >= 3:
        agent = quoted[2]
    elif len(quoted) == 2:
        agent = quoted[1]
    else:
        agent = ""

    parts = request.split()
    if len(parts) >= 2:
        method, url = parts[0], parts[1]
    elif len(parts) == 1:
        method, url = "", parts[0]
    else:
        method, url = "", ""

    tail_start = right.rfind('"')
    tail = right[tail_start + 1:] if tail_start >= 0 else ""
    after_request = right[right.find('"', right.find('"') + 1) + 1:].split()
    status = 0
    size = 0
    if after_request:
        if after_request[0].isdigit():
            status = int(after_request[0])
        if len(after_request) > 1 and after_request[1].isdigit():
            size = int(after_request[1])
    rt_ms = read_response_time(tail.split())

    return {
        "ip": ip, "ts": stamp, "method": method, "url": url,
        "status": status, "bytes": size, "agent": agent, "rt_ms": rt_ms,
    }


JSON_KEYS = {
    "ip": ("ClientIP", "clientIp", "client_ip", "remote_addr", "RemoteIP", "ip", "c_ip", "src_ip"),
    "agent": ("ClientRequestUserAgent", "http_user_agent", "user_agent", "userAgent", "ua", "agent"),
    "url": ("ClientRequestURI", "ClientRequestPath", "request_uri", "uri", "url", "path",
            "cs_uri_stem", "request"),
    "status": ("EdgeResponseStatus", "OriginResponseStatus", "status", "response_status",
               "sc_status", "http_status"),
    "ts": ("EdgeStartTimestamp", "EdgeEndTimestamp", "time_local", "timestamp", "time",
           "@timestamp", "datetime", "date"),
    "method": ("ClientRequestMethod", "request_method", "method", "verb"),
    "bytes": ("EdgeResponseBytes", "body_bytes_sent", "bytes_sent", "bytes", "size"),
    "rt": ("OriginResponseDurationMs", "request_time", "upstream_response_time",
           "response_time", "duration", "time_taken"),
}


def pick(record, names):
    for name in names:
        if name in record and record[name] not in (None, ""):
            return record[name]
    return None


def parse_json_ts(value):
    """Handle RFC3339, epoch seconds, milliseconds and nanoseconds, and Apache style."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        for divisor in (1e9, 1e6, 1e3, 1.0):
            seconds = number / divisor
            if 946684800 < seconds < 4102444800:  # year 2000 to 2100
                try:
                    return datetime.fromtimestamp(seconds, tz=timezone.utc).replace(tzinfo=None)
                except (OverflowError, OSError, ValueError):
                    return None
        return None
    text = str(value).strip()
    if text.isdigit():
        return parse_json_ts(int(text))
    match = TS_RE.search("[" + text + "]") or TS_RE.search(text)
    if match:
        return parse_apache_ts(*match.group(1, 2, 3, 4, 5, 6))
    cleaned = text.replace("Z", "+00:00")
    try:
        stamp = datetime.fromisoformat(cleaned)
        return stamp.replace(tzinfo=None)
    except ValueError:
        return None


def parse_jsonline(line):
    """Cloudflare Logpush and any JSON access log, including Nginx json format."""
    try:
        record = json.loads(line)
    except ValueError:
        return None
    if not isinstance(record, dict):
        return None
    ip = parse_ip(pick(record, JSON_KEYS["ip"]))
    if not ip:
        return None
    agent = pick(record, JSON_KEYS["agent"]) or ""
    url = pick(record, JSON_KEYS["url"]) or ""
    if isinstance(url, str) and url[:4].upper() in ("GET ", "POST", "HEAD", "PUT ") and " " in url:
        pieces = url.split()
        url = pieces[1] if len(pieces) > 1 else url
    status = pick(record, JSON_KEYS["status"]) or 0
    try:
        status = int(status)
    except (TypeError, ValueError):
        status = 0
    size = pick(record, JSON_KEYS["bytes"]) or 0
    try:
        size = int(size)
    except (TypeError, ValueError):
        size = 0
    stamp = parse_json_ts(pick(record, JSON_KEYS["ts"]))
    if stamp is None:
        return None
    rt_ms = None
    raw_rt = pick(record, JSON_KEYS["rt"])
    if raw_rt is not None:
        try:
            value = float(str(raw_rt).split(",")[0])
            rt_ms = value if value > 50 else value * 1000.0
        except ValueError:
            rt_ms = None
    return {
        "ip": ip, "ts": stamp, "method": str(pick(record, JSON_KEYS["method"]) or ""),
        "url": str(url), "status": status, "bytes": size,
        "agent": str(agent), "rt_ms": rt_ms,
    }


CSV_ALIASES = {
    "ip": ("ip", "client_ip", "clientip", "remote_addr", "remote_host", "host_ip", "adresse_ip", "visitor_ip"),
    "agent": ("user_agent", "useragent", "ua", "agent", "http_user_agent", "navigateur"),
    "url": ("url", "uri", "path", "request", "request_uri", "page", "chemin"),
    "status": ("status", "code", "status_code", "http_code", "response_code", "statut"),
    "ts": ("date", "time", "datetime", "timestamp", "time_local", "date_heure"),
    "bytes": ("bytes", "size", "bytes_sent", "taille"),
    "rt": ("response_time", "request_time", "duration", "time_taken", "temps"),
}


def sniff_csv(first_line):
    """Return (delimiter, column map) when the first line looks like a header."""
    best = None
    for delimiter in ("\t", ";", ",", "|"):
        fields = [f.strip().strip('"').lower().replace(" ", "_") for f in first_line.split(delimiter)]
        if len(fields) < 3:
            continue
        mapping = {}
        for index, field in enumerate(fields):
            for key, aliases in CSV_ALIASES.items():
                if field in aliases and key not in mapping:
                    mapping[key] = index
        if "ip" in mapping and "agent" in mapping and "url" in mapping:
            if best is None or len(mapping) > len(best[1]):
                best = (delimiter, mapping)
    return best


def parse_csvline(line, delimiter, mapping):
    fields = [f.strip().strip('"') for f in line.split(delimiter)]
    try:
        ip = parse_ip(fields[mapping["ip"]])
        agent = fields[mapping["agent"]]
        url = fields[mapping["url"]]
    except IndexError:
        return None
    if not ip:
        return None
    stamp = parse_json_ts(fields[mapping["ts"]]) if "ts" in mapping and mapping["ts"] < len(fields) else None
    if stamp is None:
        return None
    status = 0
    if "status" in mapping and mapping["status"] < len(fields):
        raw = fields[mapping["status"]]
        status = int(raw) if raw.isdigit() else 0
    size = 0
    if "bytes" in mapping and mapping["bytes"] < len(fields):
        raw = fields[mapping["bytes"]]
        size = int(raw) if raw.isdigit() else 0
    rt_ms = None
    if "rt" in mapping and mapping["rt"] < len(fields):
        rt_ms = read_response_time([fields[mapping["rt"]]])
    return {"ip": ip, "ts": stamp, "method": "", "url": url, "status": status,
            "bytes": size, "agent": agent, "rt_ms": rt_ms}


# --------------------------------------------------------------------------
# verification
# --------------------------------------------------------------------------

class Verifier:
    """
    Answers one question per (IP, claimed provider): verified, spoofed or
    unverifiable.

    Two methods, in this order:
      1. Published IP ranges. Conclusive both ways when the provider publishes
         a complete list.
      2. Reverse DNS then forward DNS. The method Google documents for
         Googlebot: the PTR record must end in a provider domain, and the
         forward lookup of that hostname must return the same IP.

    Absence of evidence is never treated as spoofing. No PTR record and no
    published range means unverifiable, which is a different fact.
    """

    def __init__(self, ranges_path=None, use_dns=True, max_lookups=800, timeout=3.0):
        self.networks = {}
        self.sources = {}
        self.use_dns = use_dns
        self.max_lookups = max_lookups
        self.lookups = 0
        self.cache = {}
        self.notes = []
        self.dns_failures = 0
        socket.setdefaulttimeout(timeout)
        if ranges_path:
            self._load_ranges(ranges_path)

    def _load_ranges(self, path):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except OSError as exc:
            raise SkillError(
                "cannot read the IP ranges file %s (%s). Drop the flag to run "
                "without range verification." % (path, exc.strerror or exc)
            )
        except ValueError as exc:
            raise SkillError(
                "the IP ranges file %s is not valid JSON (%s). Expected an object "
                'like {"openai": ["1.2.3.0/24"], "anthropic": [...]}.' % (path, exc)
            )
        if not isinstance(payload, dict):
            raise SkillError(
                'the IP ranges file must be a JSON object keyed by provider, for '
                'example {"openai": ["1.2.3.0/24"]}.'
            )
        for key, value in payload.items():
            if key.startswith("_"):
                if key == "_sources" and isinstance(value, dict):
                    self.sources = value
                continue
            nets = []
            for cidr in self._flatten(value):
                try:
                    nets.append(ipaddress.ip_network(cidr, strict=False))
                except ValueError:
                    continue
            if nets:
                self.networks[key.lower()] = nets

    @staticmethod
    def _flatten(value):
        """Accept a plain list, or a vendor payload pasted as is."""
        if isinstance(value, dict):
            value = value.get("prefixes") or value.get("ranges") or value.get("ips") or []
        if isinstance(value, str):
            value = [value]
        out = []
        for item in value or []:
            if isinstance(item, str):
                out.append(item.strip())
            elif isinstance(item, dict):
                for field in ("ipv4Prefix", "ipv6Prefix", "ip_prefix", "ipv6_prefix",
                              "prefix", "cidr", "ip"):
                    if item.get(field):
                        out.append(str(item[field]).strip())
        return out

    def range_count(self):
        return {key: len(nets) for key, nets in self.networks.items()}

    def verify(self, ip, bot):
        key = (ip, bot["ranges"])
        cached = self.cache.get(key)
        if cached:
            return cached
        result = self._verify_uncached(ip, bot)
        self.cache[key] = result
        return result

    def _verify_uncached(self, ip, bot):
        nets = self.networks.get((bot["ranges"] or "").lower())
        if nets:
            try:
                address = ipaddress.ip_address(ip)
            except ValueError:
                return ("unverifiable", "unparsable address")
            for net in nets:
                if address.version == net.version and address in net:
                    return ("verified", "published IP range")
            if not bot["rdns"]:
                return ("spoofed", "outside every published range of the provider")
        if bot["rdns"] and self.use_dns:
            if self.lookups >= self.max_lookups:
                return ("unverifiable", "DNS lookup budget exhausted")
            self.lookups += 1
            try:
                hostname = socket.gethostbyaddr(ip)[0].lower().rstrip(".")
            except (socket.herror, socket.gaierror, socket.timeout, OSError):
                self.dns_failures += 1
                return ("unverifiable", "no PTR record")
            if not any(hostname.endswith(suffix) for suffix in bot["rdns"]):
                return ("spoofed", "PTR %s does not belong to the provider" % hostname)
            try:
                infos = socket.getaddrinfo(hostname, None)
            except (socket.gaierror, socket.timeout, OSError):
                return ("unverifiable", "PTR %s does not resolve forward" % hostname)
            addresses = {info[4][0] for info in infos}
            if ip in addresses:
                return ("verified", "rDNS then fDNS on %s" % hostname)
            return ("spoofed", "forward lookup of %s does not return this IP" % hostname)
        if nets:
            return ("spoofed", "outside every published range of the provider")
        return ("unverifiable", "no published range and no documented rDNS domain")


RANGES_TEMPLATE = {
    "_comment": "Paste each provider payload as is, or a plain list of CIDR strings. "
                "Re-check every URL before use, they move.",
    "_sources": {
        "openai": "https://openai.com/gptbot.json, /chatgpt-user.json, /searchbot.json",
        "anthropic": "https://claude.com/crawling/bots.json",
        "perplexity": "https://www.perplexity.ai/perplexitybot.json, /perplexity-user.json",
        "google": "https://developers.google.com/static/search/apis/ipranges/googlebot.json "
                  "plus special-crawlers.json and user-triggered-fetchers.json",
        "microsoft": "https://www.bing.com/toolbox/bingbot.json",
        "amazon": "rDNS under crawl.amazonbot.amazon, no CIDR list published",
        "meta": "https://developers.facebook.com/docs/sharing/webmasters/crawler (AS32934)",
        "apple": "https://search.developer.apple.com/applebot.json",
        "commoncrawl": "no list published, runs on AWS us-east-1",
        "bytedance": "no stable list published",
        "mistral": "IP list inside the Mistral AI documentation, no stable JSON",
        "xai": "no list published at survey date",
        "cohere": "no list published at survey date",
        "deepseek": "no crawler documented at survey date",
    },
    "openai": [], "anthropic": [], "perplexity": [], "google": [], "microsoft": [],
    "amazon": [], "meta": [], "apple": [], "commoncrawl": [], "bytedance": [],
    "mistral": [], "xai": [], "cohere": [], "deepseek": [],
}


# --------------------------------------------------------------------------
# aggregation
# --------------------------------------------------------------------------

class Reservoir:
    """Bounded sample of response times, so percentiles cost no memory growth."""

    def __init__(self, cap=5000, seed=0):
        self.cap = cap
        self.values = []
        self.count = 0
        self.total = 0.0
        self.rng = random.Random(seed)

    def add(self, value):
        self.count += 1
        self.total += value
        if len(self.values) < self.cap:
            self.values.append(value)
        else:
            index = self.rng.randrange(self.count)
            if index < self.cap:
                self.values[index] = value

    def summary(self):
        if not self.count:
            return None
        ordered = sorted(self.values)

        def at(fraction):
            if not ordered:
                return None
            position = min(len(ordered) - 1, int(fraction * len(ordered)))
            return round(ordered[position], 1)

        return {
            "samples": self.count,
            "avg_ms": round(self.total / self.count, 1),
            "p50_ms": at(0.50),
            "p90_ms": at(0.90),
            "p99_ms": at(0.99),
        }


class BotBucket:
    def __init__(self, meta):
        self.meta = meta
        self.hits = 0
        self.verified = 0
        self.spoofed = 0
        self.unverifiable = 0
        self.bytes = 0
        self.ips = Counter()
        self.status = Counter()
        self.urls = Counter()
        self.sections = Counter()
        self.daily = Counter()
        self.monthly = Counter()
        self.spoofed_targets = Counter()
        self.reasons = Counter()
        self.rt = Reservoir()
        self.first = None
        self.last = None
        self.url_cap_hit = False


def section_of(url):
    path = url.split("?")[0]
    if not path.startswith("/"):
        path = "/" + path
    parts = [p for p in path.split("/") if p]
    if not parts:
        return "/ (root)"
    if len(parts) == 1 and "." in parts[0]:
        return "/ (root)"
    return "/" + parts[0] + "/"


def normalise_url(url):
    """Reduce a URL to a comparable path, query kept, fragment and host dropped."""
    if not url:
        return "/"
    url = url.strip()
    if "://" in url:
        after_scheme = url.split("://", 1)[1]
        url = "/" + after_scheme.split("/", 1)[1] if "/" in after_scheme else "/"
    url = url.split("#")[0]
    if not url.startswith("/"):
        url = "/" + url
    if len(url) > 1 and url.endswith("/") and "?" not in url:
        url = url[:-1]
    return url or "/"


def strip_query(url):
    """Matrix and sitemap comparison happen on the path, query strings aside."""
    path = normalise_url(url).split("?")[0]
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    return path or "/"


def match_bot(agent_lower):
    for bot in BOTS:
        if bot["pat"] in agent_lower:
            return bot
    return None


def looks_human(agent_lower):
    if not agent_lower:
        return False
    if "mozilla" not in agent_lower:
        return False
    return not any(hint in agent_lower for hint in GENERIC_BOT_HINTS)


# --------------------------------------------------------------------------
# side inputs
# --------------------------------------------------------------------------

LOC_RE = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>", re.I)


def load_sitemap(path):
    urls = set()
    index_detected = False
    with open_log(path) as handle:
        for line in handle:
            if "<sitemapindex" in line.lower():
                index_detected = True
            for found in LOC_RE.findall(line):
                urls.add(strip_query(found))
            stripped = line.strip()
            if stripped.startswith("http") and "<" not in stripped:
                urls.add(strip_query(stripped))
    return urls, index_detected


def load_citations(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            text = handle.read()
    except OSError as exc:
        raise SkillError("cannot read the citations file %s (%s)." % (path, exc.strerror or exc))
    stripped = text.lstrip()
    urls = []
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            payload = json.loads(text)
        except ValueError as exc:
            raise SkillError(
                "the citations file %s starts like JSON but does not parse (%s). "
                "Use a JSON list of URLs, or one URL per line." % (path, exc)
            )
        if isinstance(payload, dict):
            payload = payload.get("cited") or payload.get("urls") or payload.get("citations") or []
        for item in payload:
            if isinstance(item, str):
                urls.append(item)
            elif isinstance(item, dict):
                value = item.get("url") or item.get("uri") or item.get("page")
                if value:
                    urls.append(value)
    else:
        for line in text.splitlines():
            line = line.split(",")[0].strip()
            if line and not line.startswith("#"):
                urls.append(line)
    return {strip_query(u) for u in urls if u}


# --------------------------------------------------------------------------
# main run
# --------------------------------------------------------------------------

def run(args):
    files = expand_inputs(args.logs)
    verifier = Verifier(
        ranges_path=args.ip_ranges,
        use_dns=not args.no_dns,
        max_lookups=args.max_lookups,
        timeout=args.dns_timeout,
    )

    since = parse_day(args.since, "since")
    until = parse_day(args.until, "until")

    buckets = {}
    formats = Counter()
    malformed_samples = []
    lines_read = 0
    lines_parsed = 0
    lines_malformed = 0
    out_of_range = 0
    all_requests = 0
    human_requests = 0
    human_status = Counter()
    human_rt = Reservoir(seed=1)
    other_bot_requests = 0
    first_seen = None
    last_seen = None
    status_to_bots = Counter()
    query_hits = 0
    param_names = Counter()
    pagination_hits = 0
    redirect_hits = 0
    redirect_urls = Counter()

    for path in files:
        csv_mode = None
        with open_log(path) as handle:
            for index, line in enumerate(handle):
                line = line.rstrip("\n").rstrip("\r")
                if not line.strip():
                    continue
                lines_read += 1
                if not args.quiet and lines_read % 2000000 == 0:
                    sys.stderr.write("  %d million lines read\n" % (lines_read // 1000000))
                    sys.stderr.flush()

                if index == 0 and not line.lstrip().startswith("{") and not TS_RE.search(line):
                    sniffed = sniff_csv(line)
                    if sniffed:
                        csv_mode = sniffed
                        formats["csv"] += 1
                        continue

                if line.lstrip().startswith("{"):
                    record = parse_jsonline(line)
                    if record:
                        formats["json"] += 1
                elif csv_mode:
                    record = parse_csvline(line, csv_mode[0], csv_mode[1])
                else:
                    record = parse_combined(line)
                    if record:
                        formats["combined"] += 1

                if not record:
                    lines_malformed += 1
                    if len(malformed_samples) < 3:
                        malformed_samples.append(line[:200])
                    continue

                stamp = record["ts"]
                day = stamp.date()
                if since and day < since:
                    out_of_range += 1
                    continue
                if until and day > until:
                    out_of_range += 1
                    continue

                lines_parsed += 1
                all_requests += 1
                if first_seen is None or stamp < first_seen:
                    first_seen = stamp
                if last_seen is None or stamp > last_seen:
                    last_seen = stamp

                agent_lower = record["agent"].lower()
                bot = match_bot(agent_lower)
                if bot is None:
                    if looks_human(agent_lower):
                        human_requests += 1
                        human_status[str(record["status"])] += 1
                        if record["rt_ms"] is not None:
                            human_rt.add(record["rt_ms"])
                    else:
                        other_bot_requests += 1
                    continue

                bucket = buckets.get(bot["name"])
                if bucket is None:
                    bucket = BotBucket(bot)
                    buckets[bot["name"]] = bucket

                url = normalise_url(record["url"])
                status, reason = verifier.verify(record["ip"], bot)
                bucket.hits += 1
                bucket.reasons[reason] += 1
                bucket.ips[record["ip"]] += 1

                if status == "spoofed":
                    bucket.spoofed += 1
                    bucket.spoofed_targets[url] += 1
                    continue

                if status == "verified":
                    bucket.verified += 1
                else:
                    bucket.unverifiable += 1

                bucket.bytes += record["bytes"]
                bucket.status[str(record["status"])] += 1
                bucket.sections[section_of(url)] += 1
                bucket.daily[day.isoformat()] += 1
                bucket.monthly[day.isoformat()[:7]] += 1
                if bucket.first is None or stamp < bucket.first:
                    bucket.first = stamp
                if bucket.last is None or stamp > bucket.last:
                    bucket.last = stamp
                if record["rt_ms"] is not None:
                    bucket.rt.add(record["rt_ms"])
                if len(bucket.urls) < args.max_urls or url in bucket.urls:
                    bucket.urls[url] += 1
                else:
                    bucket.url_cap_hit = True

                if bot["purpose"] in AI_PURPOSES:
                    status_to_bots[str(record["status"])] += 1
                    if 300 <= record["status"] < 400:
                        redirect_hits += 1
                        redirect_urls[url] += 1
                    if "?" in url:
                        query_hits += 1
                        for pair in url.split("?", 1)[1].split("&"):
                            name = pair.split("=")[0]
                            if name:
                                param_names[name] += 1
                    if PAGINATION_RE.search(url):
                        pagination_hits += 1

    return build_output(
        args, files, verifier, buckets, formats, malformed_samples, lines_read,
        lines_parsed, lines_malformed, out_of_range, all_requests, human_requests,
        human_status, human_rt, other_bot_requests, first_seen, last_seen,
        status_to_bots, query_hits, param_names, pagination_hits, redirect_hits,
        redirect_urls,
    )


def parse_day(value, flag):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise SkillError("--%s expects a date like 2026-08-01, got %r." % (flag, value))


def build_output(args, files, verifier, buckets, formats, malformed_samples,
                 lines_read, lines_parsed, lines_malformed, out_of_range,
                 all_requests, human_requests, human_status, human_rt,
                 other_bot_requests, first_seen, last_seen, status_to_bots,
                 query_hits, param_names, pagination_hits, redirect_hits,
                 redirect_urls):
    warnings = []
    if lines_read and lines_malformed / max(lines_read, 1) > 0.2:
        warnings.append(
            "More than 20 percent of the lines could not be parsed. The format is "
            "probably not one of the four supported families. Send three sample "
            "lines before trusting these figures."
        )
    if not buckets:
        warnings.append(
            "No request carrying an AI crawler user agent was found in the range "
            "given. Widen the period, or check that the log covers the public site "
            "and not only the admin vhost."
        )
    if verifier.use_dns and verifier.lookups >= verifier.max_lookups:
        warnings.append(
            "The DNS lookup budget of %d was exhausted, later addresses are "
            "reported as unverifiable. Raise --max-lookups to finish the "
            "verification." % verifier.max_lookups
        )
    if not verifier.networks:
        warnings.append(
            "No IP range file was loaded, so providers that publish ranges but no "
            "reverse DNS domain (OpenAI, Anthropic, Perplexity) can only be "
            "reported as unverifiable. Run with --ip-ranges to settle them."
        )

    crawled = set()
    bots_out = []
    for name, bucket in sorted(buckets.items(), key=lambda kv: kv[1].hits, reverse=True):
        crawled.update(strip_query(u) for u in bucket.urls)
        bots_out.append({
            "bot": name,
            "provider": bucket.meta["provider"],
            "purpose": bucket.meta["purpose"],
            "hits_claimed": bucket.hits,
            "verified": bucket.verified,
            "spoofed": bucket.spoofed,
            "unverifiable": bucket.unverifiable,
            "counted": bucket.verified + bucket.unverifiable,
            "unique_ips": len(bucket.ips),
            "bytes": bucket.bytes,
            "first_seen": bucket.first.isoformat() if bucket.first else None,
            "last_seen": bucket.last.isoformat() if bucket.last else None,
            "status": dict(bucket.status.most_common()),
            "response_time": bucket.rt.summary(),
            "top_urls": bucket.urls.most_common(args.top),
            "sections": dict(bucket.sections.most_common(args.top)),
            "daily": dict(sorted(bucket.daily.items())),
            "monthly": dict(sorted(bucket.monthly.items())),
            "spoofed_targets": bucket.spoofed_targets.most_common(5),
            "verification_reasons": dict(bucket.reasons.most_common(5)),
            "url_list_truncated": bucket.url_cap_hit,
        })

    by_purpose = {}
    for entry in bots_out:
        slot = by_purpose.setdefault(
            entry["purpose"], {"bots": [], "counted": 0, "verified": 0, "spoofed": 0}
        )
        slot["bots"].append(entry["bot"])
        slot["counted"] += entry["counted"]
        slot["verified"] += entry["verified"]
        slot["spoofed"] += entry["spoofed"]

    sections = Counter()
    for bucket in buckets.values():
        if bucket.meta["purpose"] in AI_PURPOSES:
            sections.update(bucket.sections)

    sitemap_block = None
    sitemap_urls = set()
    if args.sitemap:
        sitemap_urls, is_index = load_sitemap(args.sitemap)
        not_crawled = sorted(sitemap_urls - crawled)
        orphan_crawled = sorted(crawled - sitemap_urls)
        sitemap_block = {
            "urls_in_sitemap": len(sitemap_urls),
            "crawled": len(sitemap_urls & crawled),
            "not_crawled": len(not_crawled),
            "sample_not_crawled": not_crawled[:args.top],
            "crawled_not_in_sitemap": len(orphan_crawled),
            "sample_crawled_not_in_sitemap": orphan_crawled[:args.top],
            "is_sitemap_index": is_index,
        }
        if is_index:
            warnings.append(
                "The file given to --sitemap is a sitemap index. Download the child "
                "sitemaps and pass them instead, otherwise the URL universe is empty."
            )

    cited = load_citations(args.citations) if args.citations else None
    universe = sitemap_urls | crawled | (cited or set())
    matrix = {
        "citations_available": cited is not None,
        "crawled": len(crawled),
        "universe": len(universe),
        "universe_source": "sitemap" if sitemap_urls else "observed URLs only",
    }
    if cited is not None:
        crawled_cited = sorted(crawled & cited)
        cited_only = sorted(cited - crawled)
        crawled_only = sorted(crawled - cited)
        neither = sorted(universe - crawled - cited)
        matrix.update({
            "crawled_and_cited": {"count": len(crawled_cited), "sample": crawled_cited[:args.top]},
            "cited_not_crawled": {"count": len(cited_only), "sample": cited_only[:args.top]},
            "crawled_not_cited": {"count": len(crawled_only), "sample": crawled_only[:args.top]},
            "neither": {"count": len(neither), "sample": neither[:args.top]},
        })
    else:
        matrix["note"] = (
            "No citation survey supplied, so only the crawl axis is available. "
            "The report must say so and show the left half of the matrix only."
        )

    total_claimed = sum(b["hits_claimed"] for b in bots_out)
    total_spoofed = sum(b["spoofed"] for b in bots_out)
    total_verified = sum(b["verified"] for b in bots_out)
    total_unverifiable = sum(b["unverifiable"] for b in bots_out)

    return {
        "schema": SCHEMA,
        "generated": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "bot_table_survey_date": BOT_SURVEY_DATE,
        "inputs": {
            "files": files,
            "since": args.since,
            "until": args.until,
            "sitemap": args.sitemap,
            "citations": args.citations,
            "ip_ranges": args.ip_ranges,
        },
        "parsing": {
            "lines_read": lines_read,
            "lines_kept": lines_parsed,
            "lines_malformed": lines_malformed,
            "lines_outside_date_filter": out_of_range,
            "malformed_ratio": round(lines_malformed / lines_read, 4) if lines_read else 0,
            "formats_detected": dict(formats),
            "malformed_samples": malformed_samples,
            "response_time_heuristic": "decimal value read as seconds, bare integer above 1000 read as microseconds",
        },
        "period": {
            "first_hit": first_seen.isoformat() if first_seen else None,
            "last_hit": last_seen.isoformat() if last_seen else None,
        },
        "verification": {
            "mode": "ranges+dns" if verifier.networks and verifier.use_dns
                    else ("ranges" if verifier.networks else ("dns" if verifier.use_dns else "none")),
            "dns_lookups": verifier.lookups,
            "dns_without_ptr": verifier.dns_failures,
            "ranges_loaded": verifier.range_count(),
            "range_sources": verifier.sources,
            "rule": "spoofed hits are excluded from every counter below except hits_claimed and spoofed_targets",
        },
        "totals": {
            "all_requests": all_requests,
            "ai_claimed": total_claimed,
            "ai_verified": total_verified,
            "ai_unverifiable": total_unverifiable,
            "ai_spoofed": total_spoofed,
            "ai_counted": total_verified + total_unverifiable,
            "human_like_requests": human_requests,
            "other_bot_requests": other_bot_requests,
        },
        "bots": bots_out,
        "by_purpose": by_purpose,
        "sections": [{"section": s, "hits": n} for s, n in sections.most_common(args.top)],
        "status_served_to_ai_bots": dict(status_to_bots.most_common()),
        "human_baseline": {
            "requests": human_requests,
            "status": dict(human_status.most_common(8)),
            "response_time": human_rt.summary(),
            "caveat": "user agent based, a rough comparison point, not a session count",
        },
        "crawl_waste": {
            "hits_with_query_string": query_hits,
            "top_query_parameters": param_names.most_common(10),
            "pagination_hits": pagination_hits,
        },
        "redirects": {
            "3xx_served_to_ai_bots": redirect_hits,
            "top_redirected_urls": redirect_urls.most_common(10),
        },
        "sitemap": sitemap_block,
        "matrix": matrix,
        "warnings": warnings,
    }


def build_parser():
    parser = argparse.ArgumentParser(
        prog="parse_logs.py",
        description="Find and verify AI crawler hits in server access logs.",
        epilog="Output is one JSON document on stdout, or in the file given to --out.",
    )
    parser.add_argument("logs", nargs="*", help="log files or a folder of rotated logs")
    parser.add_argument("--since", help="keep hits from this day, YYYY-MM-DD")
    parser.add_argument("--until", help="keep hits up to this day, YYYY-MM-DD")
    parser.add_argument("--ip-ranges", help="JSON file of published provider IP ranges")
    parser.add_argument("--no-dns", action="store_true",
                        help="skip reverse DNS, use published ranges only")
    parser.add_argument("--max-lookups", type=int, default=800,
                        help="cap on reverse DNS lookups, default 800")
    parser.add_argument("--dns-timeout", type=float, default=3.0,
                        help="per lookup timeout in seconds, default 3")
    parser.add_argument("--sitemap", help="sitemap XML or a text file of URLs, one per line")
    parser.add_argument("--citations", help="JSON list or text file of cited URLs")
    parser.add_argument("--top", type=int, default=25, help="length of every top list, default 25")
    parser.add_argument("--max-urls", type=int, default=200000,
                        help="per bot URL table cap, protects memory on huge logs")
    parser.add_argument("--out", help="write the JSON here instead of stdout")
    parser.add_argument("--quiet", action="store_true", help="no progress on stderr")
    parser.add_argument("--print-ranges-template", action="store_true",
                        help="print an empty IP ranges file with the source URLs, then exit")
    return parser


def main(argv):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.print_ranges_template:
        print(json.dumps(RANGES_TEMPLATE, indent=2, ensure_ascii=False))
        return 0
    if not args.logs:
        raise SkillError(
            "no log file given. Usage: python3 parse_logs.py access.log [more.log.gz] "
            "[--since 2026-08-01] [--ip-ranges ranges.json]. Use "
            "--print-ranges-template to create the ranges file."
        )

    report = run(args)
    payload = json.dumps(report, indent=2, ensure_ascii=False)
    if args.out:
        try:
            with open(args.out, "w", encoding="utf-8") as handle:
                handle.write(payload + "\n")
        except OSError as exc:
            raise SkillError("cannot write %s (%s)." % (args.out, exc.strerror or exc))
        if not args.quiet:
            sys.stderr.write("written: %s\n" % args.out)
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except SkillError as error:
        sys.stderr.write("parse_logs: %s\n" % error)
        sys.exit(2)
    except KeyboardInterrupt:
        sys.stderr.write("parse_logs: interrupted, nothing written.\n")
        sys.exit(130)
    except MemoryError:
        sys.stderr.write(
            "parse_logs: out of memory. Lower --max-urls, or split the log and "
            "run one month at a time.\n"
        )
        sys.exit(2)
    except Exception as error:  # last resort, still actionable, never a traceback
        sys.stderr.write(
            "parse_logs: unexpected failure (%s: %s). Re-run on a 1000 line "
            "extract with: head -1000 access.log > sample.log, and send that "
            "sample if it still fails.\n" % (type(error).__name__, error)
        )
        sys.exit(2)
