# PLAN.md

## Status: Phase 0 — Discovery in progress

### Confirmed
- Intake telephony: PhoneBurner
- Intake audio bucket: `pb-dispositions-call-recordings` (exists)
- MedHub telephony: RingCentral
- Both Intake and MedHub use Twenty CRM (same server)
- CRM server URL: `https://crm-server-prod-878822316507.us-central1.run.app`
- GraphQL endpoint: `/graphql`
- Auth: `Authorization: Bearer <token>` — no extra headers needed
- Tokens are workspace-scoped — one token per workspace
- Intake token: working ✅
- MedHub token: working ✅
- Primary object for matching and write: `leads` (not `people` or `persons`)
- Phone field on Lead: `phones` composite — `primaryPhoneCallingCode` + `primaryPhoneNumber`
  - Normalization required before querying: `+13055551234` → `{ callingCode: "+1", number: "3055551234" }`
- Write flow per call (confirmed via Fireflies integration reference):
  1. `createPhoneCall` (remoteCallId, transcription, direction, from, to, leadId, recordUrl)
  2. `createNote` (title, bodyV2.markdown with summary + GCS transcript link)
  3. `createNoteTarget` (noteId + phoneCallId + leadId) — can be combined in one request
  4. `updateLead` (summary, lastContactAttemptAt, contactAttemptCount)
- Native `PhoneCall` object exists with fields: `callName`, `transcription`, `direction`, `to`, `from`, `leadId`, `remoteCallId`, `recordUrl`
- No custom call fields exist yet (callDisposition, nextFollowUpAt) — need DATA_MODEL approval to create
- Existing native Lead fields usable: `summary`, `lastContactAttemptAt`, `contactAttemptCount`, `statusReason`
- Metadata endpoint (`/metadata`) requires Super Admin role

### Pending — do not build yet
- [ ] MedHub GCS bucket name for RingCentral recordings (awaiting confirmation)
- [ ] GRS telephony provider
- [ ] GRS API token
- [ ] PhoneBurner webhook: confirm if it fires on call end or requires polling the bucket
- [ ] RingCentral webhook: confirm `call.completed` event is enabled for MedHub
- [ ] Custom fields decision: `callDisposition` (SELECT) and `nextFollowUpAt` (DATE_TIME) on Lead — needs DATA_MODEL approval per workspace
- [ ] HIPAA/BAA clearance for MedHub
- [ ] Real note examples from operations team (5–10 per workspace) for LLM prompt engineering
- [ ] Disposition list from operations team

### Decision log
| Date | Decision | Reason |
|------|----------|--------|
| 2026-06-16 | Deepgram as primary STT | Best accuracy for VoIP, $0.0043/min, native diarization |
| 2026-06-16 | Intake as MVP CRM | Lowest compliance risk, bucket already exists |
| 2026-06-16 | `leads` as primary matching object | Confirmed via live API + Codex codebase analysis |
| 2026-06-16 | Single CRM server for all workspaces | Workspace selected by token, not by URL |
| 2026-06-16 | `createPhoneCall` as primary write target | Native object with all required fields; Note linked via NoteTarget |