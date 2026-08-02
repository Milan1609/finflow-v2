#!/usr/bin/env python
"""Add admin routes to app.py"""

admin_code = '''
# ─── ADMIN PANEL ───────────────────────────────────────────────────────────────

ADMIN_PASSWORD = 'admin123'  # CHANGE THIS TO A SECURE PASSWORD!

@app.route('/admin', methods=['GET', 'POST'])
def admin_panel():
    """Admin panel to view all database data"""
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password != ADMIN_PASSWORD:
            return render_template('admin.html', error='Invalid password'), 401
        session['admin_logged_in'] = True
        return redirect(url_for('admin_panel'))
    
    if not session.get('admin_logged_in'):
        return render_template('admin.html', error=None)
    
    users = User.query.all()
    accounts = Account.query.all()
    transactions = Transaction.query.all()
    schedules = Schedule.query.all()
    
    stats = {
        'total_users': len(users),
        'total_accounts': len(accounts),
        'total_transactions': len(transactions),
        'total_schedules': len(schedules),
    }
    
    return render_template('admin.html', 
                          users=users, 
                          accounts=accounts, 
                          transactions=transactions,
                          schedules=schedules,
                          stats=stats,
                          logged_in=True)

@app.route('/admin/logout', methods=['POST'])
def admin_logout():
    session.pop('admin_logged_in', None)
    flash('Logged out from admin panel', 'info')
    return redirect(url_for('admin_panel'))

'''

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

if 'def admin_panel' not in content:
    content = content.replace('def init_app():', admin_code + '\ndef init_app():')
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('✅ Admin routes added successfully!')
else:
    print('ℹ️ Admin routes already present')
