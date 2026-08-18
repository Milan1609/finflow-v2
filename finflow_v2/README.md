# 💸 FinFlow v2 — Personal Finance Tracker

Complete Indian personal finance tracker with multi-user login, accounts, transactions, investments, reminders, and analytics.

---

## 🚀 Quick Start

```bash
# 1. Extract zip and enter folder
cd finflow_v2

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
python app.py

# 5. Open in browser
http://localhost:5001
```

### Optional: Load demo data
```bash
python seed.py
# Login: demo@finflow.in | Password: demo123
```

---

## 🗄️ Database Setup

FinFlow works locally with SQLite by default. For a public multi-user website, use PostgreSQL so the data remains available after deployments and database rules are enforced centrally.

### 1. Local development (SQLite)

No installation or configuration is needed. Run `python app.py` and FinFlow creates `instance/finflow.db` automatically. The app installs indexes, data-validation triggers, and account-balance triggers at startup.

### 2. Free PostgreSQL for a public deployment

1. Create a free PostgreSQL project with [Neon](https://neon.com/pricing) or [Supabase](https://supabase.com/pricing).
2. Copy the provider's PostgreSQL connection string. Use the pooled connection string when the provider supplies one.
3. In PowerShell, set these environment variables for the current session:

```powershell
$env:DATABASE_URL = 'postgresql://USER:PASSWORD@HOST/DATABASE?sslmode=require'
$env:SECRET_KEY = 'replace-this-with-a-long-random-secret'
$env:FINFLOW_ENV = 'production'
```

4. Install the PostgreSQL driver and initialize the database:

```powershell
pip install -r requirements.txt
python database_setup.py
```

5. Start FinFlow:

```powershell
python app.py
```

The application converts `postgres://` and `postgresql://` connection strings to the Psycopg driver format automatically. Never commit the connection string or secret key; add them in your hosting provider's environment-variable settings.

The free Neon plan currently advertises no credit card requirement, 0.5 GB storage per project, and a monthly compute allowance. The Supabase Free plan currently includes a 500 MB database, but inactive projects are paused after one week. Check the provider's current limits before choosing one. [Neon pricing](https://neon.com/pricing) and [Supabase pricing](https://supabase.com/pricing) have the latest details.

### Database objects installed

| Object | Purpose |
|---|---|
| Tables | Users, categories, accounts, denominations, transactions, schedules, notifications, audit logs, and password resets |
| Indexes | Fast account, category, transaction, schedule, notification, and audit-log queries |
| Constraints | Valid amounts, currencies, payment modes, transaction types, frequencies, ownership, and denomination values |
| Triggers | Reject invalid cross-user data, keep account balances accurate, and timestamp transaction updates |
| `finflow` schema | PostgreSQL namespace that groups database routines, similar to a package |
| Functions | `finflow.recalculate_account_balance` and `finflow.next_schedule_due` |
| Procedures | `CALL finflow.rebuild_account_balances()` and `CALL finflow.advance_due_schedules()` |

PostgreSQL does not use Oracle-style `PACKAGE` objects. The `finflow` schema is the package-like namespace for all FinFlow database functions and procedures.

### Scheduled reminder procedure

Run this from a daily scheduler in your hosting platform to create overdue reminders and move each schedule to its next due date:

```sql
CALL finflow.advance_due_schedules();
```

Use this maintenance command if you ever import data manually:

```sql
CALL finflow.rebuild_account_balances();
```

### Backups

Export the PostgreSQL database regularly from your provider dashboard or with:

```bash
pg_dump "$DATABASE_URL" > finflow-backup.sql
```

To restore a backup into a new database:

```bash
psql "$DATABASE_URL" < finflow-backup.sql
```

### Deploy the web app

The repository includes a `Procfile` for hosts that support it. Connect the GitHub repository to a Python web host, add `DATABASE_URL`, `SECRET_KEY`, and `FINFLOW_ENV=production` in that host's environment settings, then use this start command:

```bash
gunicorn --bind 0.0.0.0:$PORT app:app
```

---

## ✅ Complete Feature List

### 🏠 Home Page (Public)
- Landing page with features, how-to guide, contact info
- Login / Register buttons

### 🔐 Authentication
- Register with email + mobile
- Login with email OR mobile number
- Secure password hashing
- Session management

### 📊 Dashboard
- Monthly income / expense / savings stats
- Net balance across all accounts
- 7-day income vs expense bar chart
- Recent 8 transactions
- Upcoming payment reminders (next 7 days)
- All accounts with balances
- 👁️ Eye button — one click hides ALL balances

### 💸 Transactions
- Add / Edit / Delete (all data is editable)
- **29 built-in categories** across Income, Expense, Not Reported
- **Payment modes:** Cash, UPI, NEFT, RTGS, IMPS, NACH, Auto Debit, Credit Card, Debit Card, Net Banking, Cheque, EMI, Wallet
- Search by amount or description
- Filter by: type, payment mode, account, category, date range
- Column sort (click headers — like Excel)
- Pagination (25 per page)
- **Export to CSV** with all active filters

### 🏦 Accounts
- Bank accounts, Investment/Demat accounts, Wallets, Cash
- Add with opening balance — auto tracks current balance
- Edit any account (name, institution, number, icon, color, notes)
- Delete (soft delete)
- Eye toggle hides all balances
- Color-coded cards

### 📈 Statement
- Angel One–style table: SR.NO | Name | Opening | Debit | Credit | Closing
- Filter by account type or specific account
- Totals row
- Balance eye toggle
- Export to CSV

### 🗂️ Categories
- 29 system categories (Income, Expense, Not Reported)
- Cashback added as income category
- Add unlimited custom categories
- Edit custom categories (system ones are protected)
- Cannot delete any category (data integrity)

### 🔔 Reminders & Schedules
- Add SIP, EMI, rent, insurance, utility bills
- **Frequencies:** Monthly, Quarterly, Half-Yearly, Yearly, Weekly
- Set custom due day of month
- Set reminder 1–7 days before due date
- Auto-generates notifications when reminder date arrives
- Notification bell in topbar with unread count
- Mark individual or all notifications as read
- Edit / delete schedules

### 👤 Profile
- Edit name, mobile number
- Upload profile photo
- Change password
- **Permanently delete account** (email confirmation required)
- Logout

### ⚙️ Settings
- Dark mode / Light mode / System default
- Theme applied immediately
- Quick action links

### 🔍 Audit Trail (Backend)
- Every INSERT / UPDATE / DELETE logged to `audit_log` table
- Records: user, table, record_id, old data, new data, timestamp, IP address

---

## 📁 Project Structure

```
finflow_v2/
├── app.py                    # All models, routes, logic
├── seed.py                   # Demo data loader
├── requirements.txt
├── static/
│   └── img/avatars/          # User profile photos
└── templates/
    ├── base.html             # Layout, sidebar, notifications
    ├── home.html             # Public landing page
    ├── auth.html             # Login + Register
    ├── dashboard.html        # Main dashboard
    ├── transactions.html     # Transaction list + filters
    ├── add_transaction.html  # Add transaction form
    ├── edit_transaction.html # Edit transaction form
    ├── accounts.html         # All accounts grouped
    ├── add_account.html      # Add account form
    ├── edit_account.html     # Edit account form
    ├── statement.html        # Angel One–style statement
    ├── categories.html       # Category management
    ├── schedules.html        # Reminders + notifications
    ├── profile.html          # User profile
    └── settings.html         # Theme + settings
```

---

## 💳 Category Reference

| Category | Subcategory | Type |
|---|---|---|
| Living Expenses | Rent, Bills Payment, Foods & Dining, Family Expense, Friends Expense | Expense |
| Variable | Pocket Money, Bonus, Dividend, Interest, Family Received, Friends Received | Income |
| Transport | Travelling | Expense |
| Discretionary | Shopping, Entertainments, Personal Care | Expense |
| Education | Education | Expense |
| Medical | Medical | Expense |
| Fixed | Salary | Income |
| Investment | Investment, Share Buy, SIP, IPO | Expense / Not Reported |
| Investment | Share Sell | Income |
| Transfer | Transfer C-E | Not Reported |
| Financial | Taxes, Insurances | Expense |
| Other | Voucher, Cashback, Other | Income / Expense |

---

## 🛡️ Security
- Passwords hashed with Werkzeug PBKDF2
- Session-based authentication
- All routes protected with `@login_required`
- Soft deletes (data preserved in DB)
- Audit log for all data changes

---

## 🔧 Troubleshooting

**Port already in use:**
```bash
# Windows
netstat -ano | findstr :5000
taskkill /PID <pid> /F
```

**Database issues:**
```bash
python database_setup.py
```
