# Claude guidance

## HubSpot Agent CLI

Use `hubspot-sb` for sandbox work and `hubspot-prod` for production work.

- Do not use bare `hubspot` for routine repo workflows.
- Default to sandbox unless the task explicitly requires production.
- Current operating mode is read-only unless the user explicitly asks to change that.
- Always run `whoami` before meaningful HubSpot work.
- Run `whoami` again immediately before any future write-capable action.
- Treat ambiguous environment requests as blocked until clarified.

Wrapper locations:

- `~/.local/bin/hubspot-sb`
- `~/.local/bin/hubspot-prod`

Underlying binary:

- `/Users/oliver.jobson/.hubspot/bin/hubspot`

Auth isolation:

- sandbox: `~/.hubspot-agent/sandbox`
- production: `~/.hubspot-agent/prod`

Local HubSpot task guidance is available under `.agents/skills/`. Read the relevant `SKILL.md` before using the HubSpot Agent CLI. In this workspace, the installed bundle is at `/Users/oliver.jobson/Documents/Codex/2026-06-02/run-this-npx-skills-add-hubspot/.agents/skills`.
