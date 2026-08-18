CREATE INDEX IF NOT EXISTS idx_account_user_active ON account(user_id, is_active);
CREATE INDEX IF NOT EXISTS idx_category_user_active ON category(user_id, is_active);
CREATE INDEX IF NOT EXISTS idx_transaction_user_date ON "transaction"(user_id, date DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_transaction_account_active ON "transaction"(account_id, is_deleted);
CREATE INDEX IF NOT EXISTS idx_transaction_category_active ON "transaction"(category_id, is_deleted);
CREATE INDEX IF NOT EXISTS idx_schedule_user_active_due ON schedule(user_id, is_active, next_due);
CREATE INDEX IF NOT EXISTS idx_notification_user_read_due ON notification(user_id, is_read, due_date);
CREATE INDEX IF NOT EXISTS idx_audit_log_record ON audit_log(table_name, record_id, timestamp DESC);
CREATE UNIQUE INDEX IF NOT EXISTS uq_denomination_account_value ON denomination(account_id, denomination_value);
CREATE UNIQUE INDEX IF NOT EXISTS uq_notification_schedule_due ON notification(user_id, schedule_id, due_date);

DROP TRIGGER IF EXISTS transaction_validate_insert;
CREATE TRIGGER transaction_validate_insert
BEFORE INSERT ON "transaction"
FOR EACH ROW
BEGIN
    SELECT CASE WHEN NEW.amount IS NULL OR NEW.amount <= 0 THEN RAISE(ABORT, 'Transaction amount must be greater than zero.') END;
    SELECT CASE WHEN NEW.txn_type NOT IN ('Income', 'Expense', 'Not Reported') THEN RAISE(ABORT, 'Invalid transaction type.') END;
    SELECT CASE WHEN NEW.payment_mode IS NOT NULL AND NEW.payment_mode NOT IN ('Cash', 'UPI', 'NEFT', 'RTGS', 'IMPS', 'NACH', 'Credit Card', 'Debit Card', 'Net Banking', 'Cheque', 'EMI', 'Auto Debit', 'Wallet') THEN RAISE(ABORT, 'Invalid payment mode.') END;
    SELECT CASE WHEN NEW.account_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM account WHERE id = NEW.account_id AND user_id = NEW.user_id) THEN RAISE(ABORT, 'Transaction account must belong to the user.') END;
    SELECT CASE WHEN NEW.transfer_account_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM account WHERE id = NEW.transfer_account_id AND user_id = NEW.user_id) THEN RAISE(ABORT, 'Transfer account must belong to the user.') END;
    SELECT CASE WHEN NEW.transfer_account_id IS NOT NULL AND NEW.transfer_account_id = NEW.account_id THEN RAISE(ABORT, 'Transfer accounts must be different.') END;
    SELECT CASE WHEN NEW.category_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM category WHERE id = NEW.category_id AND (user_id = NEW.user_id OR user_id IS NULL) AND is_active = 1) THEN RAISE(ABORT, 'Transaction category is unavailable to the user.') END;
END;

DROP TRIGGER IF EXISTS transaction_validate_update;
CREATE TRIGGER transaction_validate_update
BEFORE UPDATE ON "transaction"
FOR EACH ROW
BEGIN
    SELECT CASE WHEN NEW.amount IS NULL OR NEW.amount <= 0 THEN RAISE(ABORT, 'Transaction amount must be greater than zero.') END;
    SELECT CASE WHEN NEW.txn_type NOT IN ('Income', 'Expense', 'Not Reported') THEN RAISE(ABORT, 'Invalid transaction type.') END;
    SELECT CASE WHEN NEW.payment_mode IS NOT NULL AND NEW.payment_mode NOT IN ('Cash', 'UPI', 'NEFT', 'RTGS', 'IMPS', 'NACH', 'Credit Card', 'Debit Card', 'Net Banking', 'Cheque', 'EMI', 'Auto Debit', 'Wallet') THEN RAISE(ABORT, 'Invalid payment mode.') END;
    SELECT CASE WHEN NEW.account_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM account WHERE id = NEW.account_id AND user_id = NEW.user_id) THEN RAISE(ABORT, 'Transaction account must belong to the user.') END;
    SELECT CASE WHEN NEW.transfer_account_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM account WHERE id = NEW.transfer_account_id AND user_id = NEW.user_id) THEN RAISE(ABORT, 'Transfer account must belong to the user.') END;
    SELECT CASE WHEN NEW.transfer_account_id IS NOT NULL AND NEW.transfer_account_id = NEW.account_id THEN RAISE(ABORT, 'Transfer accounts must be different.') END;
    SELECT CASE WHEN NEW.category_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM category WHERE id = NEW.category_id AND (user_id = NEW.user_id OR user_id IS NULL) AND is_active = 1) THEN RAISE(ABORT, 'Transaction category is unavailable to the user.') END;
END;

DROP TRIGGER IF EXISTS schedule_validate_insert;
CREATE TRIGGER schedule_validate_insert
BEFORE INSERT ON schedule
FOR EACH ROW
BEGIN
    SELECT CASE WHEN NEW.amount IS NULL OR NEW.amount <= 0 THEN RAISE(ABORT, 'Schedule amount must be greater than zero.') END;
    SELECT CASE WHEN NEW.frequency NOT IN ('monthly', 'quarterly', 'half-yearly', 'yearly', 'weekly') THEN RAISE(ABORT, 'Invalid schedule frequency.') END;
    SELECT CASE WHEN NEW.due_day IS NOT NULL AND (NEW.due_day < 1 OR NEW.due_day > 31) THEN RAISE(ABORT, 'Schedule due day must be between 1 and 31.') END;
    SELECT CASE WHEN NEW.remind_days_before IS NOT NULL AND (NEW.remind_days_before < 1 OR NEW.remind_days_before > 30) THEN RAISE(ABORT, 'Schedule reminder days must be between 1 and 30.') END;
    SELECT CASE WHEN NEW.account_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM account WHERE id = NEW.account_id AND user_id = NEW.user_id) THEN RAISE(ABORT, 'Schedule account must belong to the user.') END;
    SELECT CASE WHEN NEW.category_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM category WHERE id = NEW.category_id AND (user_id = NEW.user_id OR user_id IS NULL) AND is_active = 1) THEN RAISE(ABORT, 'Schedule category is unavailable to the user.') END;
END;

DROP TRIGGER IF EXISTS schedule_validate_update;
CREATE TRIGGER schedule_validate_update
BEFORE UPDATE ON schedule
FOR EACH ROW
BEGIN
    SELECT CASE WHEN NEW.amount IS NULL OR NEW.amount <= 0 THEN RAISE(ABORT, 'Schedule amount must be greater than zero.') END;
    SELECT CASE WHEN NEW.frequency NOT IN ('monthly', 'quarterly', 'half-yearly', 'yearly', 'weekly') THEN RAISE(ABORT, 'Invalid schedule frequency.') END;
    SELECT CASE WHEN NEW.due_day IS NOT NULL AND (NEW.due_day < 1 OR NEW.due_day > 31) THEN RAISE(ABORT, 'Schedule due day must be between 1 and 31.') END;
    SELECT CASE WHEN NEW.remind_days_before IS NOT NULL AND (NEW.remind_days_before < 1 OR NEW.remind_days_before > 30) THEN RAISE(ABORT, 'Schedule reminder days must be between 1 and 30.') END;
    SELECT CASE WHEN NEW.account_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM account WHERE id = NEW.account_id AND user_id = NEW.user_id) THEN RAISE(ABORT, 'Schedule account must belong to the user.') END;
    SELECT CASE WHEN NEW.category_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM category WHERE id = NEW.category_id AND (user_id = NEW.user_id OR user_id IS NULL) AND is_active = 1) THEN RAISE(ABORT, 'Schedule category is unavailable to the user.') END;
END;

DROP TRIGGER IF EXISTS denomination_validate_insert;
CREATE TRIGGER denomination_validate_insert
BEFORE INSERT ON denomination
FOR EACH ROW
BEGIN
    SELECT CASE WHEN NEW.denomination_value NOT IN (1, 2, 5, 10, 20, 50, 100, 200, 500, 2000) THEN RAISE(ABORT, 'Invalid denomination value.') END;
    SELECT CASE WHEN NEW.count IS NULL OR NEW.count < 0 THEN RAISE(ABORT, 'Denomination count cannot be negative.') END;
END;

DROP TRIGGER IF EXISTS denomination_validate_update;
CREATE TRIGGER denomination_validate_update
BEFORE UPDATE ON denomination
FOR EACH ROW
BEGIN
    SELECT CASE WHEN NEW.denomination_value NOT IN (1, 2, 5, 10, 20, 50, 100, 200, 500, 2000) THEN RAISE(ABORT, 'Invalid denomination value.') END;
    SELECT CASE WHEN NEW.count IS NULL OR NEW.count < 0 THEN RAISE(ABORT, 'Denomination count cannot be negative.') END;
END;

DROP TRIGGER IF EXISTS account_balance_after_transaction_insert;
CREATE TRIGGER account_balance_after_transaction_insert
AFTER INSERT ON "transaction"
FOR EACH ROW
WHEN NEW.account_id IS NOT NULL
BEGIN
    UPDATE account
    SET current_balance = ROUND(
        opening_balance + COALESCE((
            SELECT SUM(CASE
                WHEN txn_type = 'Income' THEN amount
                WHEN txn_type = 'Expense' THEN -amount
                ELSE 0
            END)
            FROM "transaction"
            WHERE account_id = NEW.account_id AND is_deleted = 0
        ), 0),
        2
    )
    WHERE id = NEW.account_id;
END;

DROP TRIGGER IF EXISTS account_balance_after_transaction_update;
CREATE TRIGGER account_balance_after_transaction_update
AFTER UPDATE OF amount, txn_type, account_id, is_deleted ON "transaction"
FOR EACH ROW
BEGIN
    UPDATE account
    SET current_balance = ROUND(
        opening_balance + COALESCE((
            SELECT SUM(CASE
                WHEN txn_type = 'Income' THEN amount
                WHEN txn_type = 'Expense' THEN -amount
                ELSE 0
            END)
            FROM "transaction"
            WHERE account_id = OLD.account_id AND is_deleted = 0
        ), 0),
        2
    )
    WHERE id = OLD.account_id;

    UPDATE account
    SET current_balance = ROUND(
        opening_balance + COALESCE((
            SELECT SUM(CASE
                WHEN txn_type = 'Income' THEN amount
                WHEN txn_type = 'Expense' THEN -amount
                ELSE 0
            END)
            FROM "transaction"
            WHERE account_id = NEW.account_id AND is_deleted = 0
        ), 0),
        2
    )
    WHERE id = NEW.account_id;
END;

DROP TRIGGER IF EXISTS account_balance_after_transaction_delete;
CREATE TRIGGER account_balance_after_transaction_delete
AFTER DELETE ON "transaction"
FOR EACH ROW
WHEN OLD.account_id IS NOT NULL
BEGIN
    UPDATE account
    SET current_balance = ROUND(
        opening_balance + COALESCE((
            SELECT SUM(CASE
                WHEN txn_type = 'Income' THEN amount
                WHEN txn_type = 'Expense' THEN -amount
                ELSE 0
            END)
            FROM "transaction"
            WHERE account_id = OLD.account_id AND is_deleted = 0
        ), 0),
        2
    )
    WHERE id = OLD.account_id;
END;

DROP TRIGGER IF EXISTS account_balance_after_opening_balance_update;
CREATE TRIGGER account_balance_after_opening_balance_update
AFTER UPDATE OF opening_balance ON account
FOR EACH ROW
BEGIN
    UPDATE account
    SET current_balance = ROUND(
        NEW.opening_balance + COALESCE((
            SELECT SUM(CASE
                WHEN txn_type = 'Income' THEN amount
                WHEN txn_type = 'Expense' THEN -amount
                ELSE 0
            END)
            FROM "transaction"
            WHERE account_id = NEW.id AND is_deleted = 0
        ), 0),
        2
    )
    WHERE id = NEW.id;
END;

DROP TRIGGER IF EXISTS transaction_set_updated_at;
CREATE TRIGGER transaction_set_updated_at
AFTER UPDATE ON "transaction"
FOR EACH ROW
WHEN NEW.updated_at IS NULL OR NEW.updated_at = OLD.updated_at
BEGIN
    UPDATE "transaction"
    SET updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.id;
END;

UPDATE account
SET current_balance = ROUND(
    opening_balance + COALESCE((
        SELECT SUM(CASE
            WHEN txn_type = 'Income' THEN amount
            WHEN txn_type = 'Expense' THEN -amount
            ELSE 0
        END)
        FROM "transaction"
        WHERE "transaction".account_id = account.id AND "transaction".is_deleted = 0
    ), 0),
    2
);
