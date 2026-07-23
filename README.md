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
- Example: Install Infisical's [`agent-vault`](https://docs.agent-vault.dev/quickstart/cursor)

### Agent Vault



## Guardrails

Agentic coding works best with deterministic guardrails!

- 