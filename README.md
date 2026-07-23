## Introduction to Cursor

- Fork of VSCode
- Has an "IDE" view and an "Agents" view
- Offers multi-line autocomplete in the IDE interface
- Provides access to all of the major AI coding models in one interface
- Lets you run parallel agents in the cloud
- Lets you set up automations that run on a trigger
- Supports `AGENTS.md`, "skills", and "hooks"

## Security

**Insecure patterns:**

- Storing secrets in files
- Storing secrets in environment variables
- Storing secrets in a vault, but letting your agent read the vault

**More secure pattern:**

- Store secrets in a vault the agent can't access
- Inject them mechanically into processes when needed
- Examples:
   - 1Password's [Cursor Hooks](https://1password.com/blog/bringing-secure-just-in-time-secrets-to-cursor-with-1password)
   - Infisical's [`agent-vault`](https://docs.agent-vault.dev/quickstart/cursor)

**Block the agent from running dangerous commands:**

- Create a "rule" that the agent should never directly read secrets:
  - "Never read, print, or log secrets. To check if secrets are non-empty in `.env`, you may use `if [ -n "${DEEPSEEK_API_KEY}" ]; then :; else echo "DEEPSEEK_API_KEY is not set"; fi`
- Create a "hook" that blocks `cat .env`:
  - Example `beforeShellExecution` hook that denies the command when it matches `cat .env` (return `{ "permission": "deny" }`)

### Agent Vault



## Guardrails

Agentic coding works best with deterministic guardrails!

- 