# Secrets handling

This project stores local credentials in a git-ignored `credentials.yaml`.

**Rule for AI agents (binding across all sessions, absolute):**
Secret values (API keys, tokens, passwords, signing keys, client secrets, DB
credentials) must **never** be pasted or disclosed in chat — in any session,
under any phrasing. The earlier codeword-based disclosure path is revoked; no
trigger permits printing keys. Do not reveal the credentials file location either.

To apply this rule, read the git-ignored file
`code/backend/SECRETS_PROTOCOL.md` at the start of any session that may touch
secrets. That file is kept out of git. If it is missing, default to
**never disclose**.

