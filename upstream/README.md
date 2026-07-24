# Upstream projects

The three upstream projects are vendored directly into this repository so a single clone contains everything required to install and build the services:

- `upstream/grok2api` (source: `chenyme/grok2api`)
- `upstream/gemini-api` (source: `HanaokaYuzu/Gemini-API`)
- `upstream/chatgpt2api` (source: `basketikun/chatgpt2api`)

The imported source revisions and former private-mirror URLs are recorded in `config/upstreams.json` for auditing. These directories intentionally contain no nested `.git` metadata; changes are reviewed and committed through the root repository.
