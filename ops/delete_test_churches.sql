-- Permanently delete every church except one (and the system's own "public" row).
--
-- FOR TEST DATA ONLY. For each deleted church this drops its schema (all of its
-- members, events, giving, ...), deletes its domains, its subscription payment
-- records and its non-superadmin users, then deletes the church itself.
-- Superadmins are never deleted; a superadmin linked to a deleted church is
-- simply unlinked. Before running it on production, take a Neon branch snapshot.
--
-- Everything runs as one transaction: if any check fails, nothing changes.
--
-- HOW TO RUN (Neon SQL Editor):
--   1. Run the preview query below on its own and check the list.
--   2. Set expected_count to the number of rows the preview showed.
--   3. Paste the whole file into a cleared editor and run it with nothing selected.
--
-- Preview (read-only): the churches this script will delete.
--   SELECT name, subdomain, schema_name FROM churches
--   WHERE subdomain <> 'olamchurch' AND schema_name <> 'public' ORDER BY created_at;

DO $$
DECLARE
    keep_subdomain CONSTANT text := 'olamchurch';
    expected_count CONSTANT int  := -1;   -- set to the preview's row count

    doomed_count int;
    s            text;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM churches WHERE subdomain = keep_subdomain) THEN
        RAISE EXCEPTION 'No church with subdomain "%" to keep. Nothing was changed.', keep_subdomain;
    END IF;

    CREATE TEMP TABLE doomed_churches ON COMMIT DROP AS
        SELECT id, schema_name FROM churches
        WHERE subdomain <> keep_subdomain AND schema_name <> 'public';

    SELECT count(*) INTO doomed_count FROM doomed_churches;
    IF doomed_count <> expected_count THEN
        RAISE EXCEPTION 'This would delete % churches but expected_count is %. Run the preview, then set expected_count. Nothing was changed.',
            doomed_count, expected_count;
    END IF;

    -- 1. Drop each church's own schema with everything in it.
    FOR s IN SELECT schema_name FROM doomed_churches LOOP
        IF s IN ('public', 'information_schema') OR s LIKE 'pg\_%' THEN
            RAISE EXCEPTION 'Refusing to drop system schema "%". Nothing was changed.', s;
        END IF;
        EXECUTE format('DROP SCHEMA IF EXISTS %I CASCADE', s);
    END LOOP;

    -- 2. Their users (never superadmins) and everything that points at them.
    CREATE TEMP TABLE doomed_users ON COMMIT DROP AS
        SELECT id FROM users
        WHERE church_id IN (SELECT id FROM doomed_churches)
          AND role <> 'superadmin' AND NOT is_superuser;

    DELETE FROM token_blacklist_blacklistedtoken
        WHERE token_id IN (SELECT id FROM token_blacklist_outstandingtoken
                           WHERE user_id IN (SELECT id FROM doomed_users));
    DELETE FROM token_blacklist_outstandingtoken WHERE user_id IN (SELECT id FROM doomed_users);
    DELETE FROM password_reset_tokens            WHERE user_id IN (SELECT id FROM doomed_users);
    DELETE FROM user_activities                  WHERE user_id IN (SELECT id FROM doomed_users);
    DELETE FROM django_admin_log                 WHERE user_id IN (SELECT id FROM doomed_users);
    DELETE FROM users_groups                     WHERE user_id IN (SELECT id FROM doomed_users);
    DELETE FROM users_user_permissions           WHERE user_id IN (SELECT id FROM doomed_users);
    DELETE FROM users                            WHERE id      IN (SELECT id FROM doomed_users);

    -- Superadmins stay; they just stop being linked to a church that is going away.
    UPDATE users SET church_id = NULL, updated_at = now()
        WHERE church_id IN (SELECT id FROM doomed_churches);

    -- 3. The church rows and what hangs off them.
    DELETE FROM domains               WHERE tenant_id IN (SELECT id FROM doomed_churches);
    DELETE FROM subscription_payments WHERE church_id IN (SELECT id FROM doomed_churches);
    DELETE FROM churches              WHERE id        IN (SELECT id FROM doomed_churches);
END $$;

-- Result: the churches left, with their user counts.
SELECT c.name, c.subdomain, c.schema_name,
       (SELECT count(*) FROM users u WHERE u.church_id = c.id) AS users
FROM churches c ORDER BY c.created_at;
