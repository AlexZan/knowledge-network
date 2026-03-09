# Decision 024: TOTP Review Attestation

**Date**: 2026-03-07
**Status**: Draft

## Context

Decision 023 introduced edge reclassification with review provenance — raw chat excerpts and reasoning summaries attached to edges when a human reviewer resolves conflicts. However, nothing prevents the AI agent from writing `reviewed_by: "lex"` on the human's behalf. The AI has full write access to the knowledge graph, review files, and git — it can fabricate any artifact.

### The Problem

In a system where the AI can:
- Write any file
- Create any git commit
- Set any metadata field

...the only unforgeable proof of human involvement is **something the AI physically cannot produce**.

### Options Considered

1. **Git signed commits** — the AI can commit with existing signature config, so this proves nothing.
2. **Out-of-band command** — user runs `oi-approve S3` manually. Clunky; relies on the user denying AI tool calls.
3. **Conversation log as evidence** — Claude Code's client (not the AI) records user messages. Auditable after the fact, but not preventable.
4. **TOTP verification** — time-based one-time password, like Google Authenticator. The human types a 6-digit code that rotates every 30 seconds. The AI cannot generate it.

## Decision

Implement TOTP-based attestation for human review sign-off (when needed).

### How It Works

1. **Setup**: User generates a TOTP secret (standard RFC 6238). The secret is added to their authenticator app (phone). A verification-only copy is stored in the KG config (or system keyring).
2. **Review flow**: User reviews a conflict, gives their verdict in chat. The AI prepares the reclassification. User types the current TOTP code (e.g., `approve 847291`). The system verifies it and stamps the edge.
3. **Edge metadata**: `totp_verified: true`, `approved_at: <timestamp>`, `approved_by: <identity linked to TOTP secret>`.
4. **Audit**: The TOTP code is time-bound — it proves a human with the authenticator app was present at that exact moment. The AI never has access to the authenticator app, so it cannot forge approval.

### Security Properties

- **Unforgeable**: The AI has access to the verification secret on disk, but TOTP codes are time-dependent — the AI would need to call the verify function at the exact moment, which would be visible in the conversation log. The strongest version stores the secret in a keyring or HSM the AI process cannot access.
- **Low friction**: Typing 6 digits is fast. No GPG passphrase, no separate CLI tool.
- **Standard protocol**: RFC 6238 TOTP is well-understood, supported by every authenticator app.
- **Portable**: Works for any review action — conflict resolution, node approval, edge reclassification.

### When to Use

- **Personal KG (current)**: Optional. The conversation log + provenance files provide sufficient audit trail.
- **Multi-user KG**: Required. Different reviewers need distinct attestation.
- **High-stakes decisions**: Required. Any edge reclassification or node supersession that affects published research or shared knowledge.

## Consequences

- Human review decisions become cryptographically attributable
- AI agents cannot forge human approval
- Standard TOTP tooling (Google Authenticator, Authy, etc.) — no custom apps
- Small implementation: `pyotp` library, ~50 lines of code
- Future-proofs provenance for multi-user and open-system scenarios (Phase 4-5 of the big picture)
