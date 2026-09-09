# Getting the access log, by host

The hardest step of this audit is not the analysis, it is obtaining the file.
Ask for the wrong thing and the client sends a screenshot of a hosting
dashboard. Ask precisely and you get a usable file in one message.

## What to ask for, in one sentence

> The raw HTTP access logs of the site, for the last 30 days if possible, in
> their original format, gzipped. Not the error log, not a summary from a
> statistics panel.

Three things that make a run fail, so state them up front: the **error** log is
useless here, an **AWStats or Matomo export** is a summary and cannot be
verified, and a log **truncated to the last 24 hours** cannot show a bot
disappearing.

## Where the file lives

| Host or stack | Location, and the trap |
|---|---|
| Nginx, self managed | `/var/log/nginx/access.log`, rotated as `access.log.1`, `access.log.2.gz`. Pass the whole folder to the parser, it reads gzip directly |
| Apache, Debian or Ubuntu | `/var/log/apache2/access.log`, plus `other_vhosts_access.log` when several sites share the server |
| Apache, RHEL or CentOS | `/var/log/httpd/access_log` |
| **OVH** shared hosting | Web interface, Hosting then Statistics and logs, or `logs.<cluster>.hosting.ovh.net` over FTP with the separate `logs` account. One gzipped file per day, named `<domain>-<date>.log.gz`. Lines are prefixed with the vhost, the parser handles that |
| **OVH** VPS or dedicated | Standard Nginx or Apache paths above |
| **o2switch** | cPanel, Metrics then Raw Access. Download the archive, or find the live files in `~/logs/` and `~/access-logs/`. cPanel offers to archive logs before monthly removal, ask the client to switch that on, otherwise history is lost every month |
| **Infomaniak** | Manager, hosting then Logs. Export is a delimited file with a header row, not combined format. The parser detects the header and maps the columns |
| Plesk | `/var/www/vhosts/<domain>/logs/access_log`, or the Logs section of the panel |
| WP Engine, Kinsta, Flywheel | User portal, access logs section. WP Engine also exposes `~/logs/` over SFTP |
| **Cloudflare** | Logpush to R2, S3 or a bucket, JSON lines, one object per batch. This is the best source when it exists, because it sees requests the origin never receives, including those blocked at the edge |
| Cloudflare without Logpush | The dashboard analytics are aggregated and cannot be verified per request. Not usable for this audit. Say so rather than working from it |

## Retention, and why it decides the audit

Retention is short and nobody thinks about it until it is too late:

- Shared hosting keeps between 7 and 30 days, often rotating silently.
- cPanel deletes raw logs monthly unless archiving is switched on.
- Cloudflare Logpush retains whatever the destination bucket retains, so it can
  be years.

Two consequences. First, ask on day one, before the analysis is scheduled.
Second, if the client wants the month over month comparison from diagnostic 3,
set up the archiving now, because that history cannot be recovered later. That
recommendation belongs in the report even when nothing else is wrong.

## Check the file before running anything

Thirty seconds, and it avoids analysing the wrong file:

```bash
head -3 access.log                       # format, and whether there is a header row
wc -l access.log                         # volume
grep -ic gptbot access.log               # is there anything to analyse at all
head -1 access.log; tail -1 access.log   # actual period covered
```

If `grep -ic gptbot` returns zero on a 30 day log of a real site, do not
conclude the site is invisible yet. Check first that the file covers the public
site and not only an admin vhost or a staging domain, and that the period is
what you think it is. A wrong file produces a spectacular and completely false
verdict.

## Formats the parser accepts

Four families, detected automatically, no flag to set:

**Apache and Nginx combined**, with or without a vhost prefix, with or without
extra trailing fields:

```
203.0.113.10 - - [12/Aug/2026:04:11:02 +0200] "GET /blog/ HTTP/1.1" 200 48211 "-" "Mozilla/5.0 (compatible; GPTBot/1.2)"
www.example.fr 203.0.113.10 - - [12/Aug/2026:04:11:02 +0200] "GET /blog/ HTTP/1.1" 200 48211 "-" "GPTBot/1.2" 0.213
```

**JSON lines**, Cloudflare Logpush and Nginx `log_format json` alike. Field
names are mapped from a list of known aliases, and timestamps are accepted as
RFC 3339, epoch seconds, milliseconds or nanoseconds:

```
{"ClientIP":"203.0.113.10","ClientRequestURI":"/blog/","EdgeResponseStatus":200,"EdgeStartTimestamp":"2026-08-15T08:12:44Z","ClientRequestUserAgent":"GPTBot/1.2"}
```

**Delimited exports with a header row**, comma, semicolon, tab or pipe. The
header must contain a column for the address, one for the user agent and one for
the URL, under any of the usual English or French names:

```
date;ip;url;user_agent;status;response_time
2026-08-16 09:00:00;203.0.113.10;/blog/;CCBot/2.0;200;0.412
```

**Compressed**, gzip, bzip2 or xz, detected by content rather than by extension.

A line that matches none of these is counted in `parsing.lines_malformed` and
skipped. Check that field: under 5 percent is normal, since real logs always
carry a few truncated lines. Above 20 percent the parser warns, and the right
move is to look at `parsing.malformed_samples` and adapt, not to publish the
numbers.

## Personal data, and what not to do with the file

An IP address is personal data under the GDPR, and an access log is a full
browsing history of every visitor. This is not a formality, it changes how the
audit is handled:

- Work on a copy, delete it when the audit is delivered.
- Never paste raw log lines into a report, a ticket or a chat. The aggregated
  JSON from the parser contains no IP addresses, only counts, which is why the
  report is built from that file and not from the log.
- Do not send the log through a third party service to have it parsed. The
  parser runs locally, with no network access except the DNS lookups used for
  verification, and that is a deliberate design choice you can state to a client
  who asks.
- Under a data processing agreement the log stays with the party the agreement
  names. When in doubt, ask the client to run the parser themselves and send
  only the JSON output, which is enough to build the whole report.
