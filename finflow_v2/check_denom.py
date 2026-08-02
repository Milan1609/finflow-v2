from app import app, db, Account

with app.app_context():
    wallets = Account.query.filter_by(account_type='wallet').all()
    for w in wallets:
        print(f"{w.name}: denom_data = {w.denom_data}")