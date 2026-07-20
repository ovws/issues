# WEB2API Codex workspace instructions

## GitHub CLI and Windows Keyring

- GitHub CLI is installed at `C:\Program Files\GitHub CLI\gh.exe`.
- Run every authenticated `gh` operation in the Windows host environment, not in the Codex sandbox. The OAuth token is stored in Windows Keyring and is intentionally unavailable inside the sandbox.
- A sandbox result such as `token invalid`, HTTP 401, or a `hosts.yml` file without `oauth_token` does not prove that the user's host login is invalid. Never ask the user to log in again based only on a sandbox check.
- Verify authentication on the host with:

  ```powershell
  & 'C:\Program Files\GitHub CLI\gh.exe' auth status -h github.com
  ```

- Never print, copy, persist, or commit the token. A masked token from `gh auth status` is acceptable; `gh auth token` and `--show-token` are prohibited.
- If host authentication really fails, report the exact host-side error once. Do not repeatedly trigger login flows.

## Repository context

- Repository: `ovws/internal-ai-api-config`
- Remote: `https://github.com/ovws/internal-ai-api-config.git`
- Default branch: `main`
- The sandbox owns this worktree while authenticated Git runs as the Windows user. For host-side Git commands, pass the repository-scoped exception inline:

  ```powershell
  git -c safe.directory=D:/WEB2API <command>
  ```

- Do not add `D:/WEB2API` to global Git configuration unless the user explicitly requests that persistent change.

## Standard GitHub workflow

1. Inspect `git status --short --branch`, the diff, current branch, and remote before staging.
2. In a mixed worktree, stage explicit paths; never use `git add -A` without confirmed scope.
3. Keep local secrets and runtime state out of Git, including `.env`, `config/*.local.*`, `data/`, `logs/`, `run/`, upstream checkouts, tokens, cookies, API keys, and Base64 image payloads.
4. Run the relevant tests, linters, script parsers, and `git diff --check` before committing.
5. Use terse commits that include the Linear identifier, for example `feat: deploy native ChatGPT image API (WK-77)`.
6. Push from the host so Git can use Windows Keyring:

   ```powershell
   git -c safe.directory=D:/WEB2API push -u origin <branch>
   ```

7. Default pull requests to Draft unless the user explicitly requests Ready for review.
8. Use real Markdown newlines in Issue and PR bodies. Include what changed, why, impact, validation, remaining gaps, and the Linear link.

## Common `gh` operations

Run these in the host environment with the full executable path:

```powershell
$gh = 'C:\Program Files\GitHub CLI\gh.exe'

& $gh repo view ovws/internal-ai-api-config --json nameWithOwner,url,defaultBranchRef
& $gh issue list --repo ovws/internal-ai-api-config --state all --limit 100
& $gh issue view <number> --repo ovws/internal-ai-api-config --comments
& $gh issue create --repo ovws/internal-ai-api-config --title '<title>' --body-file <file>
& $gh issue comment <number> --repo ovws/internal-ai-api-config --body-file <file>
& $gh issue edit <number> --repo ovws/internal-ai-api-config --add-label '<label>'
& $gh issue close <number> --repo ovws/internal-ai-api-config --comment '<verified result>'

& $gh pr list --repo ovws/internal-ai-api-config --state all --limit 100
& $gh pr view <number> --repo ovws/internal-ai-api-config --comments
& $gh pr create --repo ovws/internal-ai-api-config --draft --base <base> --head <branch> --title '<title>' --body-file <file>
& $gh pr checks <number> --repo ovws/internal-ai-api-config
& $gh pr ready <number> --repo ovws/internal-ai-api-config
```

- Prefer the connected GitHub app for structured Issue/PR reads and writes when it has repository access. Use host-side `gh` when the app lacks access or when local branch context is required.
- Before creating an Issue or PR, search existing open and closed items to avoid duplicates.

## GitHub Issue and Linear synchronization

- GitHub is the code-facing record; Linear is the planning-facing record. Keep the same title, scope, priority, and current status aligned.
- Every implementation Issue/PR must mention its Linear identifier (`WK-…`) and link to the Linear issue.
- Every Linear issue must receive links to its GitHub Issue, branch, commits, and PR through Linear attachments or a concise progress comment.
- When a GitHub Issue already exists, update it rather than creating a duplicate. When a Linear issue already contains the GitHub attachment, do not add the same attachment again.
- Sync meaningful state changes: work started, branch pushed, Draft PR opened, validation result, blocker, Ready for review, merged, and verified completion.
- Do not mark an Issue complete merely because code was pushed. Record unverified external dependencies such as missing accounts, credentials, DNS, firewall, or real-client end-to-end validation as remaining work.
- Do not copy secrets, cookies, authorization headers, private image contents, or raw Base64 payloads between GitHub and Linear.
