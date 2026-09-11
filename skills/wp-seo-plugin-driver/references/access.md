# Access: credentials, blocked routes, least privilege

## Application passwords

Built into WordPress since 5.6. A 24 character password tied to one user,
created under Users, Profile, Application Passwords, revocable on its own.
They require HTTPS (or a local environment): `wp_is_application_passwords_supported()`
returns false otherwise, and security plugins often switch them off through
the `wp_is_application_passwords_available` filter.
https://make.wordpress.org/core/2020/11/05/application-passwords-integration-guide/

Rules for this skill:

- Create a dedicated user with the **Editor** role for SEO field changes. An
  administrator account is never needed to write post metadata.
- One application password per job, named after it ("SEO bulk September"),
  revoked when the job is verified.
- Read it from the environment: `WP_SITE`, `WP_USER`, `WP_APP_PASSWORD`. Never
  in `changes.csv`, `apply.sh`, a report, or the conversation.

Test the credentials before anything else:

```bash
printf 'user = "%s:%s"\n' "$WP_USER" "$WP_APP_PASSWORD" | \
  curl -sS --config - "$WP_SITE/wp-json/wp/v2/users/me?context=edit" -o /dev/null -w "%{http_code}\n"
```

`printf` is a shell builtin and curl reads the credentials on stdin, so the
password never shows in a process list or the shell history. `apply.sh` does
the same for every call.

## When the answer is 401 or 403

| Symptom | Likely cause | Fix |
|---|---|---|
| 401 with correct credentials, Apache host | the `Authorization` header is stripped (CGI or FastCGI) | re-save Permalinks so WordPress rewrites its `.htaccess` line `RewriteRule .* - [E=HTTP_AUTHORIZATION:%{HTTP:Authorization}]`, or add `SetEnvIf Authorization "(.*)" HTTP_AUTHORIZATION=$1` |
| 401, Site Health says "authorization header is missing" | same | same |
| 403 on one plugin route only | a WAF rule (Cloudflare has blocked `rankmath/v1/updateMeta` on some zones) | allow the route for the user's IP, or use WP-CLI |
| 403 on everything under `/wp-json/` | a security plugin closing the REST API | allow authenticated requests, or use WP-CLI |
| 200 but the page does not change | the key is not registered for that post type (Yoast on pages), or a page cache | read the plugin's row in [plugins.md](plugins.md), purge the cache |

## WP-CLI

When SSH is available, `wp post meta update <id> <key> <value>` writes Yoast,
Rank Math and SEOPress fields directly and keeps Yoast's indexables in sync.
It cannot write AIOSEO, whose data lives in its own table. `apply.sh` prints
the WP-CLI line as a comment wherever REST cannot do the job.

## MCP

If the site's own MCP endpoint is connected to the client (the WordPress MCP
Adapter bundled by Rank Math, or installed alongside AIOSEO or SEOPress), the
plugin's abilities appear as tools. They use the same application password or
OAuth. Prefer them when they cover the field, and keep the discipline:
snapshot, one change, verify, the rest.
