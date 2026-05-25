# Onboarding Signals (Source of Truth)

This document is the single source of truth for onboarding recommendation logic.

- Scope: project onboarding recommendations for `wiki`, `issues`, `users`.
- Output contract: `sections -> items -> {score, reason}`.
- Code/OpenAPI references:
  - `backend/schemas/onboarding.py`
  - `backend/openapi/openapi-v0.1.0.yaml`

## 1) Data Sources

### Wiki signals
- `tracker.wiki_pages`: `id`, `project_id`, `title`, `version`, `updated_at`, `updated_by`.
- `tracker.wiki_page_revisions`: number of revisions per page.
- `tracker.wiki_page_attachments`: attachment count and latest attachment date.

### Issue signals
- `tracker.issues`: `id`, `project_id`, `parent_id`, `criticality_id`, `updated_at`, `created_at`, `status_id`.
- `tracker.issue_comments`: comments count and latest comment date.
- `tracker.worklogs`: logged hours and latest activity date.
- `tracker.issue_watchers`: watchers count.

### User signals
- `tracker.projects`: `created_by` (project creator).
- `tracker.project_users`: roles (`admin_project`, `user`) for project membership.
- `tracker.issues` / `tracker.issue_comments` / `tracker.worklogs` / `tracker.wiki_pages` / `tracker.wiki_page_revisions`: activity contributors.

## 2) Scoring Heuristics

All section scores are normalized to `[0, 100]`.

### Shared helper metrics
- `freshness_days = now_utc - updated_at`.
- `freshness_score = max(0, 1 - freshness_days / 30)`.
- `activity_30d(entity) = events_count_30d / max_events_count_30d`.

### Wiki item score
`wiki_score = 100 * (0.35 * freshness_score + 0.25 * update_frequency + 0.20 * revision_density + 0.20 * attachments_signal)`

- `update_frequency`: normalized updates/revisions in 30 days.
- `revision_density`: `min(1, revisions_count / 10)`.
- `attachments_signal`: `min(1, attachments_count / 5)`.

### Issue item score
`issue_score = 100 * (0.30 * activity_signal + 0.30 * criticality_signal + 0.20 * freshness_score + 0.20 * epic_link_signal)`

- `activity_signal`: normalized sum of comments/worklogs/watchers.
- `criticality_signal`: mapped by level (`Low=0.3`, `Medium=0.6`, `High=1.0`).
- `epic_link_signal`: `1.0` if issue is linked to epic (`parent_id != null`), else `0.3`.

### User item score
`user_score = 100 * (0.35 * role_signal + 0.45 * activity_signal + 0.20 * cross_domain_signal)`

- `role_signal`: `1.0` for `project_admin`, `0.8` for project creator, `0.5` otherwise.
- `activity_signal`: normalized sum of authored/assigned/commented/worklogged/wiki-edited actions in 30 days.
- `cross_domain_signal`: fraction of domains where user is active (`issues`, `comments`, `worklogs`, `wiki`) in `[0,1]`.

## 3) Selection Rules and Limits

- Exclusions:
  - Never include current user in `users` section.
  - Exclude soft-deleted/inaccessible entities.
  - Exclude wiki pages/issues outside current project.
- Deduplication:
  - `wiki`: by page `id`.
  - `issues`: by issue `id`.
  - `users`: by user `id`.
- Top N (defaults):
  - `wiki`: top 7.
  - `issues`: top 7.
  - `users`: top 5.
- Stable sorting:
  - Primary: `score DESC`.
  - Secondary: `updated_at DESC` (or entity-specific recent activity timestamp).
  - Tertiary: `id ASC` for deterministic output.

## 4) Explainability (`reason`)

Each recommended item must include `reason`.

- `reason.summary`: one-line explanation for UI.
- `reason.facts`: compact machine-readable key-value facts used to derive score.

Example reason:
- `summary`: `"High criticality and active discussion in last 7 days"`
- `facts`: `{"criticality":"high","comments_7d":12,"worklogs_7d":4,"updated_at":"2026-04-20T09:10:00Z"}`

## 5) API Response Format

```json
{
  "project_id": "uuid",
  "generated_at": "2026-04-24T10:00:00Z",
  "sections": [
    {
      "section": "wiki",
      "items": [
        {
          "id": "uuid",
          "entity_type": "wiki_page",
          "title": "On-call runbook",
          "score": 92.4,
          "reason": {
            "summary": "Recently updated by project admins",
            "facts": {
              "version": 14,
              "updated_at": "2026-04-22T16:02:00Z",
              "revisions_30d": 5,
              "attachments_count": 3
            }
          }
        }
      ]
    },
    {
      "section": "issues",
      "items": []
    },
    {
      "section": "users",
      "items": []
    }
  ]
}
```

## 6) Issue Creation Template for This Task

Use `POST /projects/{project_id}/issues` with `type=task` and `parent_id=<EPIC_ID>`.

Minimal payload:

```json
{
  "type": "task",
  "title": "Спроектировать сигналы из реальных данных (что считаем важным)",
  "description": "См. backend/docs/onboarding_signals.md",
  "status_id": "<STATUS_ID>",
  "parent_id": "<EPIC_ID>"
}
```
