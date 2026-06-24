# Frontend Call Transcript Field Contract

The intake frontend shows Call Intelligence output in the lead Calls tab when the server `GET /calls/:leadId` response includes a call row with a non-empty `transcription` value.

## PhoneCall fields expected by the frontend

The agent should write or preserve these `PhoneCall` fields:

- `id`: CRM PhoneCall id, returned as `id` and `phoneCallId`.
- `leadId`: Lead record id used by `/calls/:leadId`.
- `remoteCallId`: Source telephony call id for traceability.
- `callName`: Human-readable call label when available.
- `transcription`: Full transcript. A non-empty value triggers the expandable transcript panel.
- `direction`: Displayed in the existing Status column for PhoneCall-backed rows.
- `to.name` and `to.phoneNumber`: Displayed as the lead/contact side of the call.
- `from.name` and `from.phoneNumber`: Displayed as the agent side of the call.
- `recordUrl`: Optional recording URL used by the existing Recording column.

## Linked Note fields expected by the frontend

The agent should create a Note linked to the PhoneCall through NoteTarget:

- Note `title` must start with `Call Intelligence -`.
- Note `bodyV2.markdown` should contain a `## Call Summary` section.
- NoteTarget should include `leadId`, `noteId`, and `phoneCallId`.

The server extracts the first markdown section after `## Call Summary` and before the next `##` heading as `callSummary`.

## Transcript format recommendation

Use one speaker turn per line when possible:

```text
[Agent] (00:00): Greeting and intake question.
[Lead] (00:08): Lead response.
```

Timestamps are optional. These forms are also accepted:

```text
[Agent]: Text
Agent [00:00]: Text
[00:00] Lead: Text
Lead: Text
```

Speaker names containing `lead`, `client`, `customer`, `caller`, or `prospect` render with the lead style. Speaker names containing `agent`, `representative`, `rep`, `staff`, `intake`, or `operator` render with the agent style.

## Notes tab behavior

The intake frontend hides notes whose title starts with `Call Intelligence -` from the Notes tab by default. Keep that prefix for AI-generated call notes so users do not see duplicate Call Intelligence content in both Notes and Calls.
