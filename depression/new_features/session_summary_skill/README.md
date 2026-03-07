# Session Summary Skill (Isolated Feature)

This folder contains a fully isolated feature implementation:

- API: `/api/skills/session-summary`
- Health: `/api/skills/session-summary/health`
- Skill definition: `skills/session-summary/SKILL.md`

Design goals:

1. No changes to existing chat/RAG endpoint behavior.
2. New files are isolated under one folder.
3. Safe fallback when LLM is unavailable.

Request example:

```json
{
  "limit": 30,
  "style": "structured",
  "max_points": 8,
  "include_risk": true
}
```

If `history` is omitted, records are loaded from `counseling_records` by current login user.