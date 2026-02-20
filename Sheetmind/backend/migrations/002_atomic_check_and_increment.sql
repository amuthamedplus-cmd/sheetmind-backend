-- Migration: Atomic check-and-increment
-- Fixes the TOCTOU race condition where check_limit() passes for multiple
-- concurrent requests before any of them increment the counter.
--
-- Run this in the Supabase SQL Editor (Dashboard > SQL Editor > New query).

-- Atomic check-and-increment for PAID tiers (monthly limits).
-- Returns TRUE if increment succeeded, FALSE if limit would be exceeded.
-- Uses FOR UPDATE row lock to prevent concurrent bypass.
CREATE OR REPLACE FUNCTION check_and_increment_usage(
    p_user_id UUID,
    p_period DATE,
    p_column_name TEXT,
    p_limit INT
)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_current_total INT;
    v_record_id UUID;
BEGIN
    -- Validate column name to prevent SQL injection
    IF p_column_name NOT IN ('chat_count', 'formula_count', 'query_count') THEN
        RAISE EXCEPTION 'Invalid column name: %', p_column_name;
    END IF;

    -- Try to lock the existing row for this user+period
    SELECT id,
           COALESCE(query_count, 0) + COALESCE(formula_count, 0) + COALESCE(chat_count, 0)
    INTO v_record_id, v_current_total
    FROM usage_records
    WHERE user_id = p_user_id AND period = p_period
    FOR UPDATE;

    IF v_record_id IS NULL THEN
        -- No record exists yet — total is 0, which is under any limit > 0.
        -- Insert a new row with the target column set to 1.
        INSERT INTO usage_records (user_id, period, chat_count, formula_count, query_count)
        VALUES (
            p_user_id,
            p_period,
            CASE WHEN p_column_name = 'chat_count' THEN 1 ELSE 0 END,
            CASE WHEN p_column_name = 'formula_count' THEN 1 ELSE 0 END,
            CASE WHEN p_column_name = 'query_count' THEN 1 ELSE 0 END
        )
        ON CONFLICT (user_id, period) DO UPDATE SET
            chat_count = CASE WHEN p_column_name = 'chat_count'
                             THEN usage_records.chat_count + 1
                             ELSE usage_records.chat_count END,
            formula_count = CASE WHEN p_column_name = 'formula_count'
                                 THEN usage_records.formula_count + 1
                                 ELSE usage_records.formula_count END,
            query_count = CASE WHEN p_column_name = 'query_count'
                               THEN usage_records.query_count + 1
                               ELSE usage_records.query_count END;
        RETURN TRUE;
    END IF;

    -- Record exists — check the limit before incrementing
    IF v_current_total >= p_limit THEN
        RETURN FALSE;  -- Limit exceeded, do NOT increment
    END IF;

    -- Under the limit — increment atomically (row is locked by FOR UPDATE)
    EXECUTE format(
        'UPDATE usage_records SET %I = %I + 1 WHERE id = $1',
        p_column_name, p_column_name
    ) USING v_record_id;

    RETURN TRUE;
END;
$$;


-- Atomic check-and-increment for FREE tier (lifetime limit across ALL periods).
-- Sums usage across all periods, then increments the current period if under limit.
CREATE OR REPLACE FUNCTION check_and_increment_trial(
    p_user_id UUID,
    p_period DATE,
    p_column_name TEXT,
    p_lifetime_limit INT
)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_lifetime_total INT;
BEGIN
    -- Validate column name
    IF p_column_name NOT IN ('chat_count', 'formula_count', 'query_count') THEN
        RAISE EXCEPTION 'Invalid column name: %', p_column_name;
    END IF;

    -- Lock ALL rows for this user to prevent concurrent trial bypass.
    -- Sum total usage across all periods.
    SELECT COALESCE(SUM(COALESCE(query_count, 0) + COALESCE(formula_count, 0) + COALESCE(chat_count, 0)), 0)
    INTO v_lifetime_total
    FROM usage_records
    WHERE user_id = p_user_id
    FOR UPDATE;

    -- Check lifetime limit
    IF v_lifetime_total >= p_lifetime_limit THEN
        RETURN FALSE;
    END IF;

    -- Under the limit — upsert the current period's record with increment
    INSERT INTO usage_records (user_id, period, chat_count, formula_count, query_count)
    VALUES (
        p_user_id,
        p_period,
        CASE WHEN p_column_name = 'chat_count' THEN 1 ELSE 0 END,
        CASE WHEN p_column_name = 'formula_count' THEN 1 ELSE 0 END,
        CASE WHEN p_column_name = 'query_count' THEN 1 ELSE 0 END
    )
    ON CONFLICT (user_id, period) DO UPDATE SET
        chat_count = CASE WHEN p_column_name = 'chat_count'
                         THEN usage_records.chat_count + 1
                         ELSE usage_records.chat_count END,
        formula_count = CASE WHEN p_column_name = 'formula_count'
                             THEN usage_records.formula_count + 1
                             ELSE usage_records.formula_count END,
        query_count = CASE WHEN p_column_name = 'query_count'
                           THEN usage_records.query_count + 1
                           ELSE usage_records.query_count END;

    RETURN TRUE;
END;
$$;
