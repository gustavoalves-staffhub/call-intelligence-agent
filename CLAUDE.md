# CLAUDE.md — Call Intelligence Agent

## What this repo is
Agent 5 of the Staffhub Marketing AI System. Processes phone call recordings,
transcribes them, and writes structured notes to Twenty CRM workspaces.

## Architecture
Two Cloud Run services: `receiver` (webhook handler) and `worker` (pipeline).
The current worker trigger is BigQuery polling over recent PhoneBurner and
RingCentral call logs. Audio stored in GCS. Notes written via Twenty GraphQL API.

## Key pending items (do not implement until resolved)
- `app/adapters/crm/` — Twenty CRM GraphQL mutations are TBD (pending codebase analysis)
- `app/adapters/crm/base.py` — auth mechanism TBD (Bearer token? API Key?)
- `app/adapters/telephony/ringcentral.py` — GCS bucket name for recordings TBD
- `app/adapters/stt/passthrough.py` — confirm if RingCentral returns transcript natively
- `app/extraction/prompts/` — prompts need real note examples before tuning

## Rules
- Never write to a CRM record without a confident match (confidence >= MATCH_CONFIDENCE_THRESHOLD)
- Always check idempotency before processing (call_id in call_audit_log)
- Never log PII (phone numbers, names, transcript content) at INFO level — DEBUG only
- All secrets via GCP Secret Manager in production, .env only in local dev
- Run `ruff check .` and `mypy app/` before committing

## Branch strategy
- `main` — production
- `develop` — integration
- `feature/*` — individual steps (e.g. feature/s3-transcription)
