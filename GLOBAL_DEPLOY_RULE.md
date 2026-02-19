# Global Deploy Rule

## One Big Rule

Any server/deploy/ops task MUST include an explicit deploy target:

- `company`
- `personal`

If target is missing or ambiguous, stop immediately and ask for clarification.

## Language Mapping

- "회사서버", "회사 서버" -> `company`
- "개인서버", "개인 서버" -> `personal`

## Source of Truth

- Repo map: `DEPLOY_TARGETS.yaml`
- Agent rule: `AGENTS.md`, `CLAUDE.md`
- Runtime guard: `scripts/preflight-target.sh`
