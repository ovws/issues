# Upstream projects

This directory is intentionally excluded from the root repository. The installer clones private mirrors from the `ovws` GitHub account:

- `ovws/internal-ai-grok2api` to `upstream/grok2api` (upstream: `chenyme/grok2api`)
- `ovws/internal-ai-gemini-api` to `upstream/gemini-api` (upstream: `HanaokaYuzu/Gemini-API`)
- `ovws/internal-ai-chatgpt2api` to `upstream/chatgpt2api` (upstream: `basketikun/chatgpt2api`)

Each directory keeps its own Git metadata. Run `scripts/install.ps1` to clone or update them.
