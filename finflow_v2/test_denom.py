from app import app, db, Account, Denomination

with app.app_context():
    # Check if denomination table exists
    from sqlalchemy import inspect
    insp = inspect(db.engine)
    tables = insp.get_table_names()
    print('Tables:', tables)
    
    if 'denomination' in tables:
        print('✅ Denomination table exists')
        
        # Check columns
        columns = insp.get_columns('denomination')
        print('Columns:', [col['name'] for col in columns])
        
        # Check if there are any denominations
        count = Denomination.query.count()
        print(f'Denomination records: {count}')
        
        # Show sample denominations
        denoms = Denomination.query.limit(5).all()
        for d in denoms:
            print(f'Account {d.account_id}: {d.denomination_value} x {d.count}')
    else:
        print('❌ Denomination table not found')