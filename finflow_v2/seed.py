"""
FinFlow Demo Data Seeder
Run: python seed.py
"""
import json
from app import app, db
from app import User, Account, Transaction, Category, Schedule, Denomination
from datetime import date, timedelta

with app.app_context():
    db.create_all()

    # Create demo user
    if not User.query.filter_by(email='demo@finflow.in').first():
        u = User(name='Demo User', email='demo@finflow.in', mobile='9876543210')
        u.set_password('demo123')
        db.session.add(u)
        db.session.commit()
        uid = u.id
        print(f'✅ Demo user created (email: demo@finflow.in | password: demo123)')
    else:
        uid = User.query.filter_by(email='demo@finflow.in').first().id
        print('Demo user already exists')
        # Clear old demo data
        Transaction.query.filter_by(user_id=uid).delete()
        Schedule.query.filter_by(user_id=uid).delete()
        Denomination.query.filter(Denomination.account_id.in_(db.session.query(Account.id).filter_by(user_id=uid))).delete()
        Account.query.filter_by(user_id=uid).delete()
        db.session.commit()
        print('Cleared previous demo data')

    # Accounts
    accounts_data = [
        ('SBI Savings', 'bank', 'Savings', 'State Bank of India', '12345', 50000, '#3b82f6', '🏦'),
        ('HDFC Salary', 'bank', 'Salary Account', 'HDFC Bank', '67890', 85000, '#10b981', '🏦'),
        ('Axis Credit Card', 'bank', 'Credit Card', 'Axis Bank', '4321', -15000, '#ef4444', '💳'),
        ('IDFC FD', 'bank', 'FD', 'IDFC Bank', 'FD001', 100000, '#8b5cf6', '🏦'),
        ('Icici PPF', 'bank', 'PPF', 'ICICI Bank', 'PPF001', 50000, '#06b6d4', '🏦'),
        ('Angel One', 'investment', 'Demat/Trading', 'Angel One', 'A001', 57666.72, '#f59e0b', '📊'),
        ('5Paisa', 'investment', 'Demat', '5Paisa', 'P001', 10191.03, '#6366f1', '📈'),
        ('FundzBazar', 'investment', 'Mutual Fund', 'FundzBazar', 'F001', 18000, '#8b5cf6', '📈'),
        ('PhonePe Wallet', 'wallet', 'UPI Wallet', 'PhonePe', '', 2500, '#5b21b6', '👛'),
        ('Google Pay', 'wallet', 'UPI Wallet', 'Google Pay', '', 1500, '#4f46e5', '📱'),
        ('Cash', 'wallet', 'Cash in Hand', '', '', 5000, '#64748b', '💵'),
        ('Personal Loan', 'bank', 'Loan', 'HDFC Bank', 'LOAN001', -200000, '#dc2626', '💰'),
    ]
    acc_ids = []
    for name, atype, sub, inst, num, bal, color, icon in accounts_data:
        if not Account.query.filter_by(user_id=uid, name=name).first():
            acc = Account(user_id=uid, name=name, account_type=atype, sub_type=sub,
                         institution=inst, account_number=num,
                         opening_balance=bal, current_balance=bal, color=color, icon=icon)
            db.session.add(acc)
            db.session.commit()  # Commit to get acc.id
            
            if atype == 'wallet':
                # Add sample denominations for wallets
                if name == 'PhonePe Wallet':
                    db.session.add(Denomination(account_id=acc.id, denomination_value=2000, count=1))
                    db.session.add(Denomination(account_id=acc.id, denomination_value=500, count=1))
                elif name == 'Google Pay':
                    db.session.add(Denomination(account_id=acc.id, denomination_value=1000, count=1))
                    db.session.add(Denomination(account_id=acc.id, denomination_value=500, count=1))
                elif name == 'Cash':
                    # 5000 = 2x2000 + 1x1000
                    db.session.add(Denomination(account_id=acc.id, denomination_value=2000, count=2))
                    db.session.add(Denomination(account_id=acc.id, denomination_value=1000, count=1))
    db.session.commit()
    accs = Account.query.filter_by(user_id=uid).all()
    acc_map = {a.name: a.id for a in accs}
    print(f'✅ {len(accs)} accounts created')

    # Sample transactions - covering a month of activity
    cats = {c.subcategory: c for c in Category.query.all()}
    today = date.today()
    txns_data = [
        # May 1 - Salary
        (today - timedelta(8), 45000, 'Income', 'Salary', 'NEFT', 'HDFC Salary', 'May Salary'),
        
        # May 2 - Food & Transport
        (today - timedelta(7), 1200, 'Expense', 'Foods & Dining', 'UPI', 'PhonePe Wallet', 'Zomato Lunch'),
        (today - timedelta(7), 500, 'Expense', 'Travelling', 'UPI', 'PhonePe Wallet', 'Ola Cab to Office'),
        (today - timedelta(7), 300, 'Expense', 'Foods & Dining', 'Cash', 'Cash', 'Street Food Dinner'),
        
        # May 3 - Bills & Utilities
        (today - timedelta(6), 800, 'Expense', 'Bills Payment', 'Net Banking', 'SBI Savings', 'Electricity Bill'),
        (today - timedelta(6), 5000, 'Not Reported', 'Rent', 'NEFT', 'SBI Savings', 'April House Rent'),
        (today - timedelta(6), 600, 'Expense', 'Bills Payment', 'UPI', 'PhonePe Wallet', 'Internet Bill'),
        
        # May 4 - Shopping & Entertainment
        (today - timedelta(5), 2000, 'Expense', 'Shopping', 'Credit Card', 'Axis Credit Card', 'Flipkart Electronics'),
        (today - timedelta(5), 400, 'Expense', 'Entertainments', 'UPI', 'Google Pay', 'Netflix + Prime Video'),
        (today - timedelta(5), 250, 'Expense', 'Foods & Dining', 'UPI', 'PhonePe Wallet', 'Coffee Shop'),
        
        # May 5 - Travel & Transport
        (today - timedelta(4), 1500, 'Expense', 'Travelling', 'CASH', 'Cash', 'Fuel for Car'),
        (today - timedelta(4), 3000, 'Expense', 'Travelling', 'Credit Card', 'Axis Credit Card', 'Ola Auto Travel Pass'),
        
        # May 6 - Medical & Health
        (today - timedelta(3), 1500, 'Expense', 'Medical', 'Cash', 'Cash', 'Apollo Pharmacy'),
        (today - timedelta(3), 500, 'Expense', 'Medical', 'UPI', 'PhonePe Wallet', 'Netmeds Medicine'),
        
        # May 7 - Education & Learning
        (today - timedelta(3), 5000, 'Expense', 'Education', 'Net Banking', 'HDFC Salary', 'Udemy Course - Python'),
        (today - timedelta(3), 200, 'Income', 'Cashback', 'UPI', 'PhonePe Wallet', 'Swiggy Cashback'),
        
        # May 8 - More transactions
        (today - timedelta(2), 1000, 'Expense', 'Shopping', 'UPI', 'PhonePe Wallet', 'Amazon Order Books'),
        (today - timedelta(2), 2000, 'Expense', 'Entertainments', 'Credit Card', 'Axis Credit Card', 'Movie Tickets + Dinner'),
        (today - timedelta(2), 1200, 'Expense', 'Foods & Dining', 'UPI', 'Google Pay', 'Swiggy Food Order'),
        (today - timedelta(2), 500, 'Expense', 'Travelling', 'UPI', 'PhonePe Wallet', 'Auto Rickshaw'),
        
        # May 9 - Recent transactions
        (today - timedelta(1), 2500, 'Expense', 'Shopping', 'Credit Card', 'Axis Credit Card', 'Myntra Clothes'),
        (today - timedelta(1), 1500, 'Expense', 'Foods & Dining', 'UPI', 'PhonePe Wallet', 'Restaurant Dinner'),
        (today - timedelta(1), 300, 'Expense', 'Foods & Dining', 'Cash', 'Cash', 'Coffee & Snacks'),
        
        # Today
        (today, 100, 'Income', 'Cashback', 'UPI', 'PhonePe Wallet', 'Flipkart Cashback'),
        (today, 450, 'Expense', 'Foods & Dining', 'UPI', 'PhonePe Wallet', 'Zomato Lunch'),
    ]
    for d, amt, ttype, sub, pm, acc_name, desc in txns_data:
        cat = cats.get(sub)
        acc_id = acc_map.get(acc_name)
        txn = Transaction(user_id=uid, date=d, amount=amt, txn_type=ttype,
                         category_id=cat.id if cat else None,
                         payment_mode=pm, account_id=acc_id, description=desc)
        db.session.add(txn)
    db.session.commit()
    print(f'✅ Sample transactions added')

    # Schedules
    scheds_data = [
        ('House Rent', 8000, 'Rent', 5, 'monthly', 3),
        ('HDFC MidCap SIP', 5000, 'SIP', 7, 'monthly', 2),
        ('LIC Premium', 12000, 'Insurances', 15, 'quarterly', 7),
        ('Electricity Bill', 800, 'Bills Payment', 20, 'monthly', 3),
        ('Internet Bill', 600, 'Bills Payment', 25, 'monthly', 2),
        ('Gym Membership', 1500, 'Health & Fitness', 1, 'monthly', 1),
        ('Mobile Recharge', 499, 'Mobile Recharge', 10, 'monthly', 2),
        ('Car Insurance', 18000, 'Insurances', 18, 'yearly', 10),
        ('Water Bill', 500, 'Bills Payment', 12, 'monthly', 5),
        ('Netflix Subscription', 149, 'Entertainments', 15, 'monthly', 1),
    ]
    for name, amt, sub, due_day, freq, remind in scheds_data:
        cat = cats.get(sub)
        if today.day <= due_day:
            try:
                next_due = today.replace(day=due_day)
            except ValueError:
                next_due = (today.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        else:
            next_month = today.replace(day=1) + timedelta(days=32)
            try:
                next_due = next_month.replace(day=due_day)
            except ValueError:
                next_due = (next_month.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        s = Schedule(user_id=uid, name=name, amount=amt,
                    category_id=cat.id if cat else None,
                    frequency=freq, due_day=due_day, next_due=next_due,
                    remind_days_before=remind)
        db.session.add(s)
    db.session.commit()
    print('✅ Schedules/reminders added')

    print('\n🎉 Demo data seeded successfully!')
    print('   Login: demo@finflow.in | Password: demo123')
    print('   Run: python app.py → http://localhost:5002')
