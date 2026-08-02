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
python -c "from app import app, db; app.app_context().push(); db.create_all(); print('DB OK')"
```
