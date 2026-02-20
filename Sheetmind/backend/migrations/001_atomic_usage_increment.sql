-- Migration: Atomic usage increment
-- Fixes the race condition where concurrent requests can bypass usage limits.
--
-- Run this in the Supabase SQL Editor (Dashboard > SQL Editor > New query).

-- 1. Add unique constraint on (user_id, period) if it doesn't exist.
--    Required for upsert ON CONFLICT to work.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'usage_records_user_id_period_key'
    ) THEN
        ALTER TABLE usage_records
            ADD CONSTRAINT usage_records_user_id_period_key
            UNIQUE (user_id, period);
    END IF;
END $$;

-- 2. Create the atomic increment RPC function.
--    Single INSERT ... ON CONFLICT ... DO UPDATE with col = col + 1.
CREATE OR REPLACE FUNCTION increment_usage_counter(
    p_user_id UUID,
    p_period DATE,
    p_column_name TEXT
)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_chat INT := 0;
    v_formula INT := 0;
    v_query INT := 0;
BEGIN
    -- Validate column name to prevent SQL injection
    IF p_column_name NOT IN ('chat_count', 'formula_count', 'query_count') THEN
        RAISE EXCEPTION 'Invalid column name: %', p_column_name;
    END IF;

    -- Set initial value for the target column (used on INSERT)
    IF p_column_name = 'chat_count' THEN v_chat := 1;
    ELSIF p_column_name = 'formula_count' THEN v_formula := 1;
    ELSIF p_column_name = 'query_count' THEN v_query := 1;
    END IF;

    -- Atomic upsert: INSERT new row OR increment existing column
    INSERT INTO usage_records (user_id, period, chat_count, formula_count, query_count)
    VALUES (p_user_id, p_period, v_chat, v_formula, v_query)
    ON CONFLICT (user_id, period)
    DO UPDATE SET
        chat_count = CASE WHEN p_column_name = 'chat_count'
                         THEN usage_records.chat_count + 1
                         ELSE usage_records.chat_count END,
        formula_count = CASE WHEN p_column_name = 'formula_count'
                             THEN usage_records.formula_count + 1
                             ELSE usage_records.formula_count END,
        query_count = CASE WHEN p_column_name = 'query_count'
                          THEN usage_records.query_count + 1
                          ELSE usage_records.query_count END;
END;
$$;
