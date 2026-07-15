# Secrets handling

This project stores local credentials in a git-ignored `credentials.yaml`.

**Rule for AI agents (binding across all sessions):**
Sensitive data (secret values, the credentials file location, API keys, tokens,
DB passwords, signing keys) must **never** be disclosed unless the operator
includes their private codeword in the message. The codeword is intentionally
NOT written here or in any committed file.

To apply this rule, read the git-ignored file
`code/backend/SECRETS_PROTOCOL.md` at the start of any session that may touch
secrets. That file is kept out of git. If it is missing, default to
**never disclose** until the operator supplies the codeword.
