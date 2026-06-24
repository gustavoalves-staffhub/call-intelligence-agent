CREATE TABLE IF NOT EXISTS call_audit_log (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id             VARCHAR(255) UNIQUE NOT NULL,
    source              VARCHAR(50) NOT NULL,
    workspace           VARCHAR(50),
    crm_record_id       VARCHAR(255),
    phone_from          VARCHAR(50),
    phone_to            VARCHAR(50),
    duration_sec        INTEGER,
    gcs_audio_uri       TEXT,
    gcs_transcript_uri  TEXT,
    match_confidence    FLOAT,
    match_method        VARCHAR(50),
    matched_on_phone    VARCHAR(20) DEFAULT 'none',
    note_created        BOOLEAN DEFAULT FALSE,
    review_required     BOOLEAN DEFAULT FALSE,
    error_message       TEXT,
    processed_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_call_audit_call_id
    ON call_audit_log(call_id);
CREATE INDEX IF NOT EXISTS idx_call_audit_workspace
    ON call_audit_log(workspace);
CREATE INDEX IF NOT EXISTS idx_call_audit_review
    ON call_audit_log(review_required)
    WHERE review_required = TRUE;
