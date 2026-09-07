-- Sprint 6: Seed system user for audit log (TD-04)
-- Well-known UUID: 00000000-0000-0000-0000-000000000001
-- Used by scraper and automated tasks to write admin_audit_log entries.

INSERT INTO users (
    id, email, email_verified, full_name, is_admin, is_active, credit_balance
) VALUES (
    '00000000-0000-0000-0000-000000000001',
    'system@regpulse.internal',
    TRUE,
    'System',
    FALSE,
    TRUE,
    0
) ON CONFLICT (id) DO NOTHING;
