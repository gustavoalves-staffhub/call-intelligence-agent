# PLAN.md

## Status: Phase 0 — Discovery in progress

### Confirmed
- Intake telephony: PhoneBurner
- Intake audio bucket: `pb-dispositions-call-recordings` (exists)
- MedHub telephony: RingCentral
- Both Intake and MedHub use Twenty CRM (same server)

### Pending — do not build yet
- [ ] MedHub GCS bucket name (awaiting confirmation)
- [ ] GRS telephony provider
- [ ] Twenty CRM GraphQL mutations for Note creation
- [ ] Twenty CRM auth mechanism and service account token generation
- [ ] Phone field structure on Person records
- [ ] Custom fields per workspace (disposition, callback_date, next_steps)
- [ ] HIPAA/BAA clearance for MedHub
- [ ] Real note examples for LLM prompt engineering
- [ ] Disposition list from operations team

### Decision log
| Date | Decision | Reason |
|------|----------|--------|
| TBD | Deepgram as primary STT | Best accuracy for VoIP, $0.0043/min, native diarization |
| TBD | Intake as MVP CRM | Lowest compliance risk, bucket already exists |
