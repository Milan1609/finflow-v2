CREATE OR REPLACE FUNCTION recalculate_account_balance(p_account_id INTEGER)
RETURNS VOID
LANGUAGE plpgsql
AS $function$
BEGIN
    IF p_account_id IS NULL THEN
        RETURN;
    END IF;

    UPDATE account
    SET current_balance = ROUND(
        opening_balance + COALESCE((
            SELECT SUM(CASE
                WHEN txn_type = 'Income' THEN amount
                WHEN txn_type = 'Expense' THEN -amount
                ELSE 0
            END)
            FROM "transaction"
            WHERE account_id = p_account_id AND is_deleted = FALSE
        ), 0),
        2
    )
    WHERE id = p_account_id;
END;
$function$;

CREATE OR REPLACE PROCEDURE rebuild_account_balances()
LANGUAGE plpgsql
AS $procedure$
DECLARE
    account_record RECORD;
BEGIN
    FOR account_record IN SELECT id FROM account LOOP
        PERFORM recalculate_account_balance(account_record.id);
    END LOOP;
END;
$procedure$;

CREATE OR REPLACE FUNCTION next_schedule_due(p_due_date DATE, p_frequency VARCHAR, p_due_day INTEGER)
RETURNS DATE
LANGUAGE plpgsql
IMMUTABLE
AS $function$
DECLARE
    month_start DATE;
    month_end DATE;
BEGIN
    IF p_due_date IS NULL THEN
        RAISE EXCEPTION 'A due date is required.';
    END IF;

    IF p_frequency = 'weekly' THEN
        RETURN p_due_date + 7;
    END IF;

    month_start := DATE_TRUNC('month', p_due_date)::DATE;
    IF p_frequency = 'monthly' THEN
        month_start := (month_start + INTERVAL '1 month')::DATE;
    ELSIF p_frequency = 'quarterly' THEN
        month_start := (month_start + INTERVAL '3 months')::DATE;
    ELSIF p_frequency = 'half-yearly' THEN
        month_start := (month_start + INTERVAL '6 months')::DATE;
    ELSIF p_frequency = 'yearly' THEN
        month_start := (month_start + INTERVAL '1 year')::DATE;
    ELSE
        RAISE EXCEPTION 'Unsupported schedule frequency: %', p_frequency;
    END IF;

    month_end := (month_start + INTERVAL '1 month - 1 day')::DATE;
    RETURN month_start + (LEAST(GREATEST(p_due_day, 1), EXTRACT(DAY FROM month_end)::INTEGER) - 1);
END;
$function$;

CREATE OR REPLACE PROCEDURE advance_due_schedules(p_as_of DATE DEFAULT CURRENT_DATE)
LANGUAGE plpgsql
AS $procedure$
DECLARE
    schedule_record RECORD;
    due_date_to_process DATE;
BEGIN
    FOR schedule_record IN
        SELECT id, user_id, name, amount, frequency, due_day, next_due
        FROM schedule
        WHERE is_active = TRUE AND next_due IS NOT NULL AND next_due <= p_as_of
    LOOP
        due_date_to_process := schedule_record.next_due;
        WHILE due_date_to_process <= p_as_of LOOP
            INSERT INTO notification (user_id, schedule_id, message, due_date)
            VALUES (
                schedule_record.user_id,
                schedule_record.id,
                'Payment reminder: ' || schedule_record.name || ' of ' || schedule_record.amount || ' is due.',
                due_date_to_process
            )
            ON CONFLICT (user_id, schedule_id, due_date) DO NOTHING;

            due_date_to_process := next_schedule_due(
                due_date_to_process,
                schedule_record.frequency,
                schedule_record.due_day
            );
        END LOOP;

        UPDATE schedule
        SET next_due = due_date_to_process
        WHERE id = schedule_record.id;
    END LOOP;
END;
$procedure$;

CREATE OR REPLACE FUNCTION validate_transaction()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $function$
BEGIN
    IF NEW.amount IS NULL OR NEW.amount <= 0 THEN
        RAISE EXCEPTION 'Transaction amount must be greater than zero.';
    END IF;

    IF NEW.account_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM account WHERE id = NEW.account_id AND user_id = NEW.user_id
    ) THEN
        RAISE EXCEPTION 'Transaction account must belong to the user.';
    END IF;

    IF NEW.transfer_account_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM account WHERE id = NEW.transfer_account_id AND user_id = NEW.user_id
    ) THEN
        RAISE EXCEPTION 'Transfer account must belong to the user.';
    END IF;

    IF NEW.category_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM category
        WHERE id = NEW.category_id
          AND (user_id = NEW.user_id OR user_id IS NULL)
          AND is_active = TRUE
    ) THEN
        RAISE EXCEPTION 'Transaction category is unavailable to the user.';
    END IF;

    RETURN NEW;
END;
$function$;

CREATE OR REPLACE FUNCTION validate_schedule()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $function$
BEGIN
    IF NEW.account_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM account WHERE id = NEW.account_id AND user_id = NEW.user_id
    ) THEN
        RAISE EXCEPTION 'Schedule account must belong to the user.';
    END IF;

    IF NEW.category_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM category
        WHERE id = NEW.category_id
          AND (user_id = NEW.user_id OR user_id IS NULL)
          AND is_active = TRUE
    ) THEN
        RAISE EXCEPTION 'Schedule category is unavailable to the user.';
    END IF;

    RETURN NEW;
END;
$function$;

CREATE OR REPLACE FUNCTION set_transaction_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $function$
BEGIN
    NEW.updated_at := CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$function$;

CREATE OR REPLACE FUNCTION sync_transaction_account_balance()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $function$
BEGIN
    IF TG_OP = 'DELETE' THEN
        PERFORM recalculate_account_balance(OLD.account_id);
        RETURN OLD;
    END IF;

    IF TG_OP = 'UPDATE' AND OLD.account_id IS DISTINCT FROM NEW.account_id THEN
        PERFORM recalculate_account_balance(OLD.account_id);
    END IF;

    PERFORM recalculate_account_balance(NEW.account_id);
    RETURN NEW;
END;
$function$;

DROP TRIGGER IF EXISTS transaction_before_validate ON "transaction";
CREATE TRIGGER transaction_before_validate
BEFORE INSERT OR UPDATE ON "transaction"
FOR EACH ROW
EXECUTE FUNCTION validate_transaction();

DROP TRIGGER IF EXISTS transaction_before_timestamp ON "transaction";
CREATE TRIGGER transaction_before_timestamp
BEFORE UPDATE ON "transaction"
FOR EACH ROW
EXECUTE FUNCTION set_transaction_updated_at();

DROP TRIGGER IF EXISTS transaction_after_balance_sync ON "transaction";
CREATE TRIGGER transaction_after_balance_sync
AFTER INSERT OR UPDATE OR DELETE ON "transaction"
FOR EACH ROW
EXECUTE FUNCTION sync_transaction_account_balance();

DROP TRIGGER IF EXISTS schedule_before_validate ON schedule;
CREATE TRIGGER schedule_before_validate
BEFORE INSERT OR UPDATE ON schedule
FOR EACH ROW
EXECUTE FUNCTION validate_schedule();
