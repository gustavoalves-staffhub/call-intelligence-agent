ALTER TABLE call_audit_log
    ADD COLUMN IF NOT EXISTS matched_on_phone VARCHAR(20) DEFAULT 'none';
