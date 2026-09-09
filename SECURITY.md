# Security

## Reporting a vulnerability

Email **security@hacktheseo.com** with the skill name, what you did, and what
happened. Please do not open a public issue for anything exploitable.

We aim to acknowledge within three working days and to ship a fix or a documented
mitigation within fourteen. If you want credit in the changelog, say so.

## What these skills do and do not do

An Agent Skill is instructions plus code that runs on your machine, with whatever
access your agent has. That is worth taking seriously, including with ours.

**These skills do:**

- Read files you point them at: access logs, CSV exports, HTML you saved.
- Fetch public URLs you name, and treat what comes back as data.
- Write output files into your working directory.
- Run Python scripts from their own `scripts/` folder, standard library only.
- Perform DNS lookups, in one place. `ai-bot-log-forensics` does a reverse then
  forward DNS resolution on the IP addresses found in your log, because that is the
  only way to tell a real GPTBot from anything that types `GPTBot` in a header. It
  is a DNS query against your own resolver, it carries no payload, and it is the
  entire point of the verification step. Run the parser with `--no-dns` to skip it,
  and you get an unverified count you should not put in a client report.

**These skills do not:**

- Send anything anywhere. There is no telemetry, no analytics, no phone home. Apart
  from the DNS lookups above, the only network traffic is fetching a URL you
  explicitly asked to audit, and `shared/fetch_ranges.py`, which you run on
  purpose and which downloads only the providers' own published IP range files
  (openai.com, claude.com, google.com, perplexity.ai, apple.com, bing.com). It
  sends nothing, and it never invents a prefix: a source that fails to answer
  leaves that provider empty, so its hits are reported as unverifiable.
- Contain any secret, key, token or internal hostname.
- Install anything. No `pip install`, no downloaded binary, no package registry.
- Write outside your working directory, and never into `~/.claude/`, `.git/hooks/`,
  shell profiles, or any agent configuration file.
- Modify your WordPress site. Everything here is read only. The write path lives in
  the plugin, behind its own permissions, not in a skill.

## Prompt injection

Two of these skills read content that someone else controls: a fetched web page, an
access log where the user agent and the requested path are attacker-supplied strings.

Every such input is treated as data, never as instructions. This is stated inside the
skills themselves so the agent reading them inherits the rule, and the log parser
escapes what it emits. If you find a path where fetched or logged content changes the
agent's behaviour, that is a vulnerability and we want to hear about it.

## Verifying before you install

```bash
git clone https://github.com/hacktheseo/wordpress-seo-skills.git
cd wordpress-seo-skills
# every network and shell call, word boundaries so "evals" and "executed" do not match
grep -rnE "\burllib\b|\brequests\.|\bsocket\.|\bsubprocess\b" --include=*.py skills/ shared/
# nothing should match: these are the patterns tools/verify.py itself refuses
grep -rnE "\beval\(|\bexec\(|\bbase64\b|__import__|os\.system\(|shell\s*=\s*True" --include=*.py skills/ shared/
find . -name "*.py" | xargs wc -l                                  # it is all readable Python
```

Then read `SKILL.md` for the skills you plan to use. They are under 300 lines each,
on purpose.

## Windows

Use `py -3` in place of `python3`. If neither works, install Python from
python.org and tick "Add python.exe to PATH" during setup.

## A general note

In an audit of 3 984 published skills in February 2026, 36,8 % had at least one
security flaw, 10,9 % contained a hard-coded secret, and 76 malicious payloads were
confirmed by hand. Install skills from sources you can identify, and read them first.
That advice includes this repository.
