---
name: session-summary
description: Summarize multi-turn counseling conversations into a concise, actionable Chinese session brief with optional risk hints.
---

# Session Summary Skill

## Purpose
Generate a concise summary from multi-turn counseling dialogue.

## When To Use
- After several chat rounds, produce a quick recap.
- Before intervention handoff, extract key issues and risk hints.
- For periodic follow-up review.

## Inputs
- `history` (optional): conversation records.
- `limit` (optional): load rounds from DB when `history` is omitted.
- `style` (optional): `brief` | `structured` | `clinical`.
- `max_points` (optional): max bullet points.
- `include_risk` (optional): include explicit risk section.

## Outputs
- `summary`: generated Chinese summary text.
- `conversation_rounds`: number of rounds used.
- `source`: `request_history` or `db`.
- `generated_at`: ISO timestamp.

## Invocation
- `GET /api/skills/session-summary`
- `POST /api/skills/session-summary`
- `GET /api/skills/session-summary/health`

## Safety
- Requires login session.
- Falls back to deterministic summary if LLM call fails.
- Does not change existing chat/RAG endpoints.