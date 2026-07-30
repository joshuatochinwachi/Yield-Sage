# Skills

`skills/` contains one directory per Solana-focused agent skill. Each skill combines a
primary workflow in `SKILL.md` with local references so the runtime can ground answers
in repository data instead of relying only on model memory.

## Directory Convention

- `skills/<skill-name>/SKILL.md` — trigger conditions, workflow, guardrails, output format
- `skills/<skill-name>/agents/openai.yaml` — runtime-facing display metadata
- `skills/<skill-name>/references/` — playbooks, policies, API references, and supporting notes

## Skill Catalog

### Yield Intelligence & Research

| Skill | Role |
| --- | --- |
| [`solana-yieldsage-research`](./solana-yieldsage-research/SKILL.md) | Discover, compare, and cryptographically verify live DeFi yield opportunities on Solana using the YieldSage intelligence API |
