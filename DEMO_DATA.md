# Demo Data Setup - FinFlow

## To Load Demo Data

Run this command in the FinFlow v2 directory:
```bash
python seed.py
```

## Demo Account

- **Email**: demo@finflow.in
- **Password**: demo123

## Demo Data Included

### 12 Accounts Created

#### Bank Accounts
1. **SBI Savings** - ₹50,000 opening balance
2. **HDFC Salary** - ₹85,000 opening balance
3. **IDFC FD** - ₹100,000 (Fixed Deposit)
4. **Icici PPF** - ₹50,000 (Public Provident Fund)
5. **Axis Credit Card** - -₹15,000 (credit limit)

#### Investment Accounts
6. **Angel One** - ₹57,666.72 (Demat/Trading)
7. **5Paisa** - ₹10,191.03 (Demat)
8. **FundzBazar** - ₹18,000 (Mutual Funds)

#### Wallet & Cash
9. **PhonePe Wallet** - ₹2,500 (UPI)
   - Denominations: 1×₹2000 + 1×₹500
10. **Google Pay** - ₹1,500 (UPI)
    - Denominations: 1×₹1000 + 1×₹500
11. **Cash in Hand** - ₹5,000
    - Denominations: 2×₹2000 + 1×₹1000

#### Loan
12. **Personal Loan** - -₹200,000 (HDFC Bank)

### 25 Sample Transactions

Transaction history spanning ~8 days with:
- **Salary**: ₹45,000 (May 1)
- **Food & Dining**: Zomato, restaurants, street food (₹4,200)
- **Travel**: Ola, Auto, Fuel (₹5,500)
- **Shopping**: Amazon, Flipkart, Myntra (₹5,500)
- **Bills & Utilities**: Electricity, Internet, Water (₹1,900)
- **Medical**: Pharmacy, Netmeds (₹2,000)
- **Entertainment**: Netflix, Movies, Prime (₹2,800)
- **Education**: Udemy course (₹5,000)
- **Cashback**: Income rewards (₹300)

Different payment modes:
- UPI (PhonePe, Google Pay)
- Cash
- Credit Card
- Net Banking
- NEFT

### 10 Recurring Schedules

1. House Rent - ₹8,000 (monthly, 5th)
2. HDFC MidCap SIP - ₹5,000 (monthly, 7th)
3. LIC Premium - ₹12,000 (quarterly, 15th)
4. Electricity Bill - ₹800 (monthly, 20th)
5. Internet Bill - ₹600 (monthly, 25th)
6. Gym Membership - ₹1,500 (monthly, 1st)
7. Mobile Recharge - ₹499 (monthly, 10th)
8. Car Insurance - ₹18,000 (yearly, 18th)
9. Water Bill - ₹500 (monthly, 12th)
10. Netflix Subscription - ₹149 (monthly, 15th)

## Features Demonstrated

✅ Multiple account types (Bank, Investment, Wallet, Loan)
✅ Different payment modes
✅ Cash denomination tracking
✅ Various transaction categories
✅ Recurring payments/schedules
✅ Income and expense tracking
✅ Credit cards and loans

## Next Steps

1. Run `python seed.py` to populate demo data
2. Login with demo@finflow.in / demo123
3. View accounts, transactions, and schedules
4. Test filtering, reports, and other features
