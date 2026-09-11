# Answer engine APIs, as documented on 2026-09-11

`run_survey.py` sends one POST per answer. Keys are read from the
environment: `OPENAI_API_KEY`, `PERPLEXITY_API_KEY`, `GEMINI_API_KEY`,
`ANTHROPIC_API_KEY`. Models come from `engines.json`; the template carries
the names printed in each provider's documentation that day. Check them.

| Engine | Endpoint | Search tool | Cited sources (JSON path) | Search fee |
|---|---|---|---|---|
| OpenAI | `POST /v1/responses` | `{"type": "web_search"}` | `output[type=message].content[type=output_text].annotations[type=url_citation].url`; everything consulted in `output[type=web_search_call].action.sources` with `include: ["web_search_call.action.sources"]` | $10 per 1 000 calls |
| Perplexity | `POST /v1/agent` | `{"type": "web_search"}` | `output[type=search_results].results[].url` | $2.50 per 1 000 calls |
| Gemini | `POST /v1beta/models/{model}:generateContent` | `{"google_search": {}}` | `candidates[0].groundingMetadata.groundingChunks[].web` | $14 per 1 000 queries after 5 000 free a month (Gemini 3) |
| Anthropic | `POST /v1/messages` | `{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}` | `content[type=text].citations[].url`; retrieved pages in `content[type=web_search_tool_result]` | $10 per 1 000 searches |

Tokens are billed on top of every fee. The dry run prints the search fees
only, as an upper bound for them.

## What each one does differently

- **OpenAI.** In the Responses API the model decides whether to search at
  all; answers without a search are kept and noted "no web search", because
  the app does the same. https://developers.openai.com/api/docs/guides/tools-web-search
- **Perplexity.** "Sonar Chat Completions is now Agent API. Sonar will be
  supported until September 27, 2026." The script calls the Agent API and
  still parses the old Sonar shape (`search_results`) for saved answers.
  https://docs.perplexity.ai/docs/agent-api/tools/web-search
- **Gemini.** The classic endpoint returns redirect links
  (`vertexaisearch.cloud.google.com/grounding-api-redirect/...`) whose `title`
  holds the source domain; the script records the domain. Grounding is a
  separate product from AI Overviews and AI Mode, which have no public API.
  https://ai.google.dev/gemini-api/docs/google-search
- **Anthropic.** Each answer may run up to `max_uses` searches; the fee counts
  searches, not answers. https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool
- **Copilot.** No answer and citations API; the Bing Search APIs were retired
  in August 2025. Use Bing Webmaster Tools' AI Performance instead, see
  [first-party.md](first-party.md).

## Checking a parser

A provider can change its answer shape. Test one saved answer before a wave:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/run_survey.py" --parse raw/openai-dec-01-r1.json \
  --engine openai --brand brand.json
```

It prints whether a search ran, whether the brand was named, the position,
the brands found and the cited sources. Zero sources on an answer that
obviously cites some means the shape moved: stop the wave and fix the parser.
