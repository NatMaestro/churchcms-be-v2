-- Reset one church back to an empty, ready-to-use state.
--
-- FOR TEST DATA ONLY. This permanently deletes everything inside the church
-- (members, events, announcements, giving, ...) and every user account linked
-- to it. Before running it on production, take a Neon branch snapshot.
--
-- Kept:    the church itself (name, subdomain, settings, branding), its domains,
--          its subscription payment history, and every superadmin account.
-- Removed: all rows in the church's own schema (except migration history) and
--          all non-superadmin users linked to the church, with their tokens,
--          activity log and permissions.
-- Added:   one admin account for the church, with no usable password. The admin
--          sets a password through "Forgot password" on the login page.
--          The church is also marked as never needing a subscription
--          (bypass_subscription_check), which is right for the free pilot church.
--
-- Everything runs as one transaction: if any check fails, nothing changes.
--
-- HOW TO RUN (Neon SQL Editor): edit the three values below, then run the
-- whole file. The SELECT at the end shows the result.

DO $$
DECLARE
    target_subdomain CONSTANT text := 'olamchurch';
    admin_email      CONSTANT text := 'admin@example.com';
    admin_name       CONSTANT text := 'Church Admin';

    v_church_id    bigint;
    v_schema       text;
    tables_to_clear text;
    clash          record;
BEGIN
    SELECT id, schema_name INTO v_church_id, v_schema
    FROM churches WHERE subdomain = target_subdomain;
    IF v_church_id IS NULL THEN
        RAISE EXCEPTION 'No church with subdomain "%". Nothing was changed.', target_subdomain;
    END IF;
    IF v_schema = 'public' THEN
        RAISE EXCEPTION 'Refusing to clear the public schema. Nothing was changed.';
    END IF;

    -- Stop before deleting anything if the admin email belongs to an account
    -- that this reset keeps (a superadmin, or a user of another church).
    SELECT id, role INTO clash
    FROM users
    WHERE lower(email) = lower(admin_email)
      AND (church_id IS DISTINCT FROM v_church_id
           OR role = 'superadmin' OR is_superuser);
    IF FOUND THEN
        RAISE EXCEPTION 'The email % is already used by an account this reset keeps (role %). Use another address, e.g. a Gmail "+olam" alias. Nothing was changed.',
            admin_email, clash.role;
    END IF;

    -- 1. Empty every table in the church's schema except migration history.
    SELECT string_agg(format('%I.%I', schemaname, tablename), ', ')
    INTO tables_to_clear
    FROM pg_tables
    WHERE schemaname = v_schema AND tablename <> 'django_migrations';
    IF tables_to_clear IS NOT NULL THEN
        EXECUTE 'TRUNCATE ' || tables_to_clear || ' RESTART IDENTITY';
    END IF;

    -- 2. Remove the church's users (never superadmins) and what points at them.
    CREATE TEMP TABLE reset_users ON COMMIT DROP AS
        SELECT id FROM users
        WHERE users.church_id = v_church_id
          AND role <> 'superadmin' AND NOT is_superuser;

    DELETE FROM token_blacklist_blacklistedtoken
        WHERE token_id IN (SELECT id FROM token_blacklist_outstandingtoken
                           WHERE user_id IN (SELECT id FROM reset_users));
    DELETE FROM token_blacklist_outstandingtoken WHERE user_id IN (SELECT id FROM reset_users);
    DELETE FROM password_reset_tokens            WHERE user_id IN (SELECT id FROM reset_users);
    DELETE FROM user_activities                  WHERE user_id IN (SELECT id FROM reset_users);
    DELETE FROM django_admin_log                 WHERE user_id IN (SELECT id FROM reset_users);
    DELETE FROM users_groups                     WHERE user_id IN (SELECT id FROM reset_users);
    DELETE FROM users_user_permissions           WHERE user_id IN (SELECT id FROM reset_users);
    DELETE FROM users                            WHERE id      IN (SELECT id FROM reset_users);

    -- 3. Create the church admin. A password starting with "!" is Django's
    --    "unusable password": nobody can log in until it is set via reset.
    INSERT INTO users (password, is_superuser, email, name, role, is_active, is_staff,
                       must_change_password, password_history, created_at, updated_at,
                       church_id)
    VALUES ('!' || md5(random()::text || clock_timestamp()::text), false,
            lower(admin_email), admin_name, 'admin', true, false,
            false, '[]'::jsonb, now(), now(), v_church_id);

    -- 4. The pilot church is free: never block it for subscription reasons.
    UPDATE churches SET bypass_subscription_check = true, updated_at = now()
    WHERE id = v_church_id;
END $$;

-- Result: the church's accounts after the reset (use the same subdomain as above).
SELECT c.subdomain, c.bypass_subscription_check, u.name, u.email, u.role, u.is_active
FROM churches c LEFT JOIN users u ON u.church_id = c.id
WHERE c.subdomain = 'olamchurch';
