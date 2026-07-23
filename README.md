## Introduction to Cursor

- Fork of VSCode
- Offers multi-line autocomplete in the IDE interface
- Provides access to all of the major AI coding models in one interface
- Has an "IDE" view and an "Agents" view
- Famously has multi-line "tab complete" in the editor

## Cloud development with Cursor

- Lets you run parallel agents in the cloud
- Lets you switch between cloud and local development with a single click
- Lets you set up automations that run on a trigger
- Supports `AGENTS.md`, "skills", and "hooks"
- Lets you provision cloud containers with secrets via environment variables
- Agent will read your documentation and set up a cloud development container that will be kept warm for you, so a copy of that container can be spun up in less than ten seconds

## Secrets management

**Insecure patterns:**

- Storing secrets in files
- Storing secrets in environment variables
- Storing secrets in a vault, but letting your agent read the vault

**More secure pattern:**

- Store secrets in a vault the agent can't access
- Inject them mechanically into processes when needed ("secrets proxy")
- Examples:
  - 1Password's [Cursor Hooks](https://1password.com/blog/bringing-secure-just-in-time-secrets-to-cursor-with-1password)
  - Infisical's `[agent-vault](https://docs.agent-vault.dev/quickstart/cursor)`

**There's no perfectly secure pattern, so limit the blast radius:**

- Set spend limits on API keys
- Set short expiration times on keys and sessions
- Develop in a cloud container so agents can't access your files

**Impose safeguards to block agents from exposing your secrets:**

- Create a "rule" that the agent should never directly read secrets:
  - Example: "Never read, print, or log secrets. To check if secrets are non-empty in `.env`, you may use `if [ -n "${DEEPSEEK_API_KEY}" ]; then :; else echo "DEEPSEEK_API_KEY is not set"; fi`."
- Create a "hook" that blocks execution of dangerous commands:
  - Example: `beforeShellExecution` hook that denies the command when it matches `cat .env` (return `{ "permission": "deny" }`)

**The best defense is many-layered!**

## Guardrails

Agentic coding works best with deterministic guardrails!

- Use a statically typed language, or type hints + a type checker
- Use a linter
- Use a project management system like GitHub to orchestrate work
- Plan in detail before starting work
- Practice test-driven development, and require the model to always watch tests fail first (RED phase) before beginning implementation work (GREEN phase)

