"""
Admin route to view all database data (for development/testing only)
Add this to your app.py before if __name__ == '__main__':
"""

ADMIN_PASSWORD = 'admin123'  # Change this!

@app.route('/admin', methods=['GET', 'POST'])
def admin_panel():
    """Simple admin panel to view all data"""
    
    # Check password
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password != ADMIN_PASSWORD:
            return render_template('admin.html', error='Invalid password'), 401
        session['admin_logged_in'] = True
        return redirect(url_for('admin_panel'))
    
    if not session.get('admin_logged_in'):
        return render_template('admin.html', error=None)
    
    # Get all users
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
