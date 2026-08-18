import sqlite3
import unittest

from database_setup import sqlite_programmability_sql


class DatabaseFeatureTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(':memory:')
        self.connection.executescript('''
            CREATE TABLE "user" (id INTEGER PRIMARY KEY, email TEXT NOT NULL);
            CREATE TABLE category (id INTEGER PRIMARY KEY, user_id INTEGER, is_active BOOLEAN NOT NULL DEFAULT 1);
            CREATE TABLE account (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                opening_balance REAL NOT NULL DEFAULT 0,
                current_balance REAL NOT NULL DEFAULT 0,
                is_active BOOLEAN NOT NULL DEFAULT 1
            );
            CREATE TABLE "transaction" (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                txn_type TEXT NOT NULL,
                category_id INTEGER,
                payment_mode TEXT,
                account_id INTEGER,
                transfer_account_id INTEGER,
                linked_transaction_id INTEGER,
                is_deleted BOOLEAN NOT NULL DEFAULT 0,
                updated_at TEXT
            );
            CREATE TABLE denomination (
                id INTEGER PRIMARY KEY,
                account_id INTEGER NOT NULL,
                denomination_value INTEGER NOT NULL,
                count INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE schedule (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                category_id INTEGER,
                account_id INTEGER,
                frequency TEXT NOT NULL,
                due_day INTEGER,
                next_due TEXT,
                remind_days_before INTEGER,
                is_active BOOLEAN NOT NULL DEFAULT 1
            );
            CREATE TABLE notification (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                schedule_id INTEGER,
                due_date TEXT,
                is_read BOOLEAN NOT NULL DEFAULT 0
            );
            CREATE TABLE audit_log (
                id INTEGER PRIMARY KEY,
                table_name TEXT,
                record_id INTEGER,
                timestamp TEXT
            );
        ''')
        self.connection.executescript(sqlite_programmability_sql())
        self.connection.executemany(
            'INSERT INTO "user" (id, email) VALUES (?, ?)',
            [(1, 'first@example.com'), (2, 'second@example.com')],
        )
        self.connection.execute('INSERT INTO category (id, user_id, is_active) VALUES (1, NULL, 1)')
        self.connection.execute(
            'INSERT INTO account (id, user_id, opening_balance, current_balance) VALUES (1, 1, 100, 100)'
        )
        self.connection.execute(
            'INSERT INTO account (id, user_id, opening_balance, current_balance) VALUES (2, 2, 50, 50)'
        )

    def tearDown(self):
        self.connection.close()

    def test_transaction_triggers_recalculate_balances_after_insert_and_soft_delete(self):
        self.connection.execute(
            '''
            INSERT INTO "transaction" (
                id, user_id, date, amount, txn_type, category_id, payment_mode, account_id
            ) VALUES (1, 1, '2026-08-18', 25, 'Income', 1, 'UPI', 1)
            '''
        )
        balance = self.connection.execute('SELECT current_balance FROM account WHERE id = 1').fetchone()[0]
        self.assertEqual(balance, 125)

        self.connection.execute('UPDATE "transaction" SET is_deleted = 1 WHERE id = 1')
        balance = self.connection.execute('SELECT current_balance FROM account WHERE id = 1').fetchone()[0]
        self.assertEqual(balance, 100)

    def test_transaction_trigger_rejects_another_users_account(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute(
                '''
                INSERT INTO "transaction" (
                    id, user_id, date, amount, txn_type, payment_mode, account_id
                ) VALUES (2, 1, '2026-08-18', 25, 'Expense', 'Cash', 2)
                '''
            )

    def test_schedule_trigger_rejects_invalid_frequency(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute(
                '''
                INSERT INTO schedule (
                    id, user_id, amount, frequency, due_day, remind_days_before
                ) VALUES (1, 1, 100, 'daily', 1, 3)
                '''
            )


if __name__ == '__main__':
    unittest.main()
