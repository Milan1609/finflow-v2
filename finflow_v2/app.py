import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_file, abort, g
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, date, timedelta, timezone
from sqlalchemy import func, event
from functools import wraps
from sqlalchemy import text
from markupsafe import Markup
import platform, json, io, csv, secrets, re, time

from security_utils import generate_2fa_secret, generate_totp_code, generate_qr_code_data_url, verify_totp_code, validate_password

try:
    from PIL import Image, UnidentifiedImageError
except Exception:
    Image = None
    UnidentifiedImageError = ValueError

app = Flask(__name__)

IS_PRODUCTION = os.environ.get('FLASK_ENV') == 'production' or os.environ.get('FINFLOW_ENV') == 'production'
DEV_SECRET_KEY = 'dev-only-change-me-finflow-local'
_secret_key = os.environ.get('SECRET_KEY')
if IS_PRODUCTION and (not _secret_key or _secret_key == DEV_SECRET_KEY):
    raise RuntimeError('Set a strong SECRET_KEY environment variable before running FinFlow in production.')

app.config['SECRET_KEY'] = _secret_key or DEV_SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///finflow.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER', 'static/img/avatars')
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024
app.config['MAX_FORM_MEMORY_SIZE'] = 1024 * 1024
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Strict'
app.config['SESSION_COOKIE_SECURE'] = IS_PRODUCTION
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)
app.config['SESSION_REFRESH_EACH_REQUEST'] = False
app.config['PREFERRED_URL_SCHEME'] = 'https' if IS_PRODUCTION else 'http'

SUPPORTED_CURRENCIES = {'INR','USD','EUR','GBP','AED','SAR','SGD','JPY','AUD','CAD'}
ALLOWED_AVATAR_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
ALLOWED_AVATAR_FORMATS = {'PNG': 'png', 'JPEG': 'jpg', 'GIF': 'gif'}
ACCOUNT_TYPES = {'bank', 'investment', 'wallet', 'other'}
TRANSACTION_TYPES = {'Income', 'Expense', 'Not Reported'}
PAYMENT_MODES = {'Cash','UPI','NEFT','RTGS','IMPS','NACH','Credit Card','Debit Card','Net Banking','Cheque','EMI','Auto Debit','Wallet'}
SCHEDULE_FREQUENCIES = {'monthly', 'quarterly', 'half-yearly', 'yearly', 'weekly'}
DENOMINATION_VALUES = {2000, 500, 200, 100, 50, 20, 10, 5, 2, 1}
MAX_MONEY_AMOUNT = 1_000_000_000
MAX_FAILED_LOGINS = 5
LOGIN_LOCKOUT_MINUTES = 15
RATE_LIMITS = {}
TEXT_CONTROL_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')
EMAIL_RE = re.compile(r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_AVATAR_EXTENSIONS

db = SQLAlchemy(app)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

class BaseModel(db.Model):
    __abstract__ = True

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

# ─── MODELS ───────────────────────────────────────────────────────────────────

class User(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    mobile = db.Column(db.String(15))
    password_hash = db.Column(db.String(256), nullable=False)
    avatar = db.Column(db.String(200), default='')
    theme = db.Column(db.String(20), default='system')
    primary_currency = db.Column(db.String(10), default='INR')
    two_factor_enabled = db.Column(db.Boolean, default=False)
    two_factor_secret = db.Column(db.String(64))
    failed_login_count = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime)
    last_login_at = db.Column(db.DateTime)
    last_login_ip = db.Column(db.String(50))
    password_changed_at = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def set_password(self, pw): self.password_hash = generate_password_hash(pw)
    def check_password(self, pw): return check_password_hash(self.password_hash, pw)

class Category(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # null=system default
    name = db.Column(db.String(100), nullable=False)
    subcategory = db.Column(db.String(100), nullable=False)
    category_type = db.Column(db.String(30), nullable=False)  # Expense, Income, Not Reported
    is_system = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)

class Account(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    account_type = db.Column(db.String(50), nullable=False)  # bank, investment, wallet
    sub_type = db.Column(db.String(50))  # savings/current/demat/sip/mf/share etc
    institution = db.Column(db.String(100))
    account_number = db.Column(db.String(50))
    currency = db.Column(db.String(10), default='INR')
    opening_balance = db.Column(db.Float, default=0.0)
    current_balance = db.Column(db.Float, default=0.0)
    color = db.Column(db.String(20), default='#6366f1')
    icon = db.Column(db.String(10), default='🏦')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    notes = db.Column(db.Text)
    # Bank Account Details (FD/PPF/OD)
    start_date = db.Column(db.Date)
    maturity_date = db.Column(db.Date)
    due_date = db.Column(db.Date)
    notification_days = db.Column(db.Integer)
    # Loan/RD/Pigmy Details
    installment_date = db.Column(db.Date)
    installment_amount = db.Column(db.Float)
    installment_type = db.Column(db.String(10))  # M, Q, HY, Y
    # Cash/Wallet Denomination
    denom_data = db.Column(db.Text)  # JSON string with denomination counts
    machine_name = db.Column(db.String(100))

class Denomination(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    denomination_value = db.Column(db.Integer, nullable=False)  # e.g., 2000, 500, 200, etc.
    count = db.Column(db.Integer, nullable=False, default=0)  # number of notes/coins
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class Transaction(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    amount = db.Column(db.Float, nullable=False)
    txn_type = db.Column(db.String(20), nullable=False)  # Income, Expense, Not Reported
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    category = db.relationship('Category', backref='transactions')
    payment_mode = db.Column(db.String(30))
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'))
    account = db.relationship('Account', backref='transactions')
    description = db.Column(db.String(255))
    reference_no = db.Column(db.String(100))
    tags = db.Column(db.String(200))
    denom_data = db.Column(db.Text)
    machine_name = db.Column(db.String(100))
    is_deleted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class Schedule(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    category = db.relationship('Category')
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'))
    account = db.relationship('Account')
    payment_mode = db.Column(db.String(30))
    frequency = db.Column(db.String(20))  # monthly, quarterly, half-yearly, yearly
    due_day = db.Column(db.Integer)  # day of month
    next_due = db.Column(db.Date)
    remind_days_before = db.Column(db.Integer, default=3)
    is_active = db.Column(db.Boolean, default=True)
    notes = db.Column(db.Text)

class Notification(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    schedule_id = db.Column(db.Integer, db.ForeignKey('schedule.id'))
    schedule = db.relationship('Schedule')
    message = db.Column(db.String(300))
    due_date = db.Column(db.Date)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class AuditLog(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    table_name = db.Column(db.String(50))
    record_id = db.Column(db.Integer)
    action = db.Column(db.String(20))  # INSERT, UPDATE, DELETE
    old_data = db.Column(db.Text)
    new_data = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    ip_address = db.Column(db.String(50))


class PasswordReset(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    token = db.Column(db.String(128), unique=True, nullable=False)
    used = db.Column(db.Boolean, default=False)
    expires_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


def ensure_user_columns():
    with db.engine.begin() as conn:
        result = conn.execute(text('PRAGMA table_info("user")'))
        existing = {row[1] for row in result.fetchall()}
        alter_commands = []
        for column_name, column_type in [
            ('primary_currency', 'VARCHAR(10)'),
            ('two_factor_enabled', 'BOOLEAN'),
            ('two_factor_secret', 'VARCHAR(64)'),
            ('failed_login_count', 'INTEGER'),
            ('locked_until', 'DATETIME'),
            ('last_login_at', 'DATETIME'),
            ('last_login_ip', 'VARCHAR(50)'),
            ('password_changed_at', 'DATETIME'),
        ]:
            if column_name not in existing:
                alter_commands.append(
                    f'ALTER TABLE "user" ADD COLUMN "{column_name}" {column_type}'
                )
        for sql in alter_commands:
            conn.execute(text(sql))
        if alter_commands:
            print('Updated user table schema with new columns:', ', '.join([cmd.split()[5] for cmd in alter_commands]))


def ensure_account_columns():
    with db.engine.begin() as conn:
        result = conn.execute(text('PRAGMA table_info("account")'))
        existing = {row[1] for row in result.fetchall()}
        alter_commands = []
        for column_name, column_type in [
            ('currency', 'VARCHAR(10)'),
            ('start_date', 'DATE'),
            ('maturity_date', 'DATE'),
            ('due_date', 'DATE'),
            ('notification_days', 'INTEGER'),
            ('installment_date', 'DATE'),
            ('installment_amount', 'FLOAT'),
            ('installment_type', 'VARCHAR(10)'),
            ('denom_data', 'TEXT'),
            ('machine_name', 'VARCHAR(100)'),
        ]:
            if column_name not in existing:
                alter_commands.append(
                    f"ALTER TABLE \"account\" ADD COLUMN \"{column_name}\" {column_type}"
                )
        for sql in alter_commands:
            conn.execute(text(sql))
        if alter_commands:
            print('Updated account table schema with new columns:', ', '.join([cmd.split()[5] for cmd in alter_commands]))


def ensure_transaction_columns():
    with db.engine.begin() as conn:
        result = conn.execute(text('PRAGMA table_info("transaction")'))
        existing = {row[1] for row in result.fetchall()}
        alter_commands = []
        for column_name, column_type in [
            ('denom_data', 'TEXT'),
            ('machine_name', 'VARCHAR(100)'),
        ]:
            if column_name not in existing:
                alter_commands.append(
                    f"ALTER TABLE \"transaction\" ADD COLUMN \"{column_name}\" {column_type}"
                )
        for sql in alter_commands:
            conn.execute(text(sql))
        if alter_commands:
            print('Updated transaction table schema with new columns:', ', '.join([cmd.split()[5] for cmd in alter_commands]))

def ensure_denomination_table():
    with db.engine.begin() as conn:
        # Check if denomination table exists
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='denomination'"))
        if not result.fetchone():
            # Create denomination table
            conn.execute(text('''
                CREATE TABLE denomination (
                    id INTEGER PRIMARY KEY,
                    account_id INTEGER NOT NULL,
                    denomination_value INTEGER NOT NULL,
                    count INTEGER NOT NULL DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (account_id) REFERENCES account (id)
                )
            '''))
            print('Created denomination table')

# ─── HELPERS ──────────────────────────────────────────────────────────────────

def utc_now():
    return datetime.now(timezone.utc)


def as_utc(value):
    if not value:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def client_ip():
    return request.remote_addr or 'unknown'


def clean_text(value, max_len=255, *, required=False):
    value = TEXT_CONTROL_RE.sub('', (value or '').strip())
    value = re.sub(r'\s+', ' ', value)
    if required and not value:
        raise ValueError('This field is required.')
    return value[:max_len]


def validate_email(value):
    value = (value or '').strip().lower()
    return value if EMAIL_RE.match(value) else None


def validate_mobile(value):
    value = re.sub(r'\D', '', value or '')
    if not value:
        return ''
    if len(value) != 10:
        raise ValueError('Mobile number must be 10 digits.')
    return value


def parse_money(value, field='Amount', *, min_value=0.01, max_value=MAX_MONEY_AMOUNT):
    try:
        amount = float(str(value).replace(',', '').strip())
    except (TypeError, ValueError):
        raise ValueError(f'{field} must be a valid number.')
    if amount < min_value or amount > max_value:
        raise ValueError(f'{field} must be between {min_value:g} and {max_value:g}.')
    return round(amount, 2)


def parse_optional_money(value, field='Amount'):
    if value in (None, ''):
        return None
    return parse_money(value, field, min_value=0, max_value=MAX_MONEY_AMOUNT)


def parse_date_field(value, field='Date'):
    if not value:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        raise ValueError(f'{field} must be a valid date.')


def parse_int_range(value, field, min_value, max_value, default=None):
    if value in (None, ''):
        if default is not None:
            return default
        raise ValueError(f'{field} is required.')
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError(f'{field} must be a whole number.')
    if parsed < min_value or parsed > max_value:
        raise ValueError(f'{field} must be between {min_value} and {max_value}.')
    return parsed


def category_for_user(user_id, category_id):
    if not category_id:
        return None
    try:
        cid = int(category_id)
    except (TypeError, ValueError):
        raise ValueError('Invalid category selected.')
    cat = Category.query.filter(
        Category.id == cid,
        Category.is_active == True,
        (Category.user_id == user_id) | (Category.user_id == None)
    ).first()
    if not cat:
        raise ValueError('Invalid category selected.')
    return cat


def account_for_user(user_id, account_id, *, active=True):
    if not account_id:
        return None
    try:
        aid = int(account_id)
    except (TypeError, ValueError):
        raise ValueError('Invalid account selected.')
    query = Account.query.filter_by(id=aid, user_id=user_id)
    if active:
        query = query.filter_by(is_active=True)
    acc = query.first()
    if not acc:
        raise ValueError('Invalid account selected.')
    return acc


def parse_denomination_payload(raw, expected_total=None):
    if not raw:
        return {}, 0.0
    try:
        data = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        raise ValueError('Invalid denomination data.')
    if not isinstance(data, dict):
        raise ValueError('Invalid denomination data.')
    clean = {}
    total = 0
    for value_raw, count_raw in data.items():
        try:
            value = int(value_raw)
            count = int(count_raw)
        except (TypeError, ValueError):
            raise ValueError('Invalid denomination data.')
        if value not in DENOMINATION_VALUES or count < 0 or count > 1_000_000:
            raise ValueError('Invalid denomination data.')
        if count:
            clean[str(value)] = count
            total += value * count
    total = round(float(total), 2)
    if expected_total is not None and abs(total - expected_total) > 0.01:
        raise ValueError('Denomination total must match the amount exactly.')
    return clean, total


def rate_limited(bucket, limit, window_seconds):
    now = time.time()
    key = f'{bucket}:{client_ip()}'
    hits = [hit for hit in RATE_LIMITS.get(key, []) if now - hit < window_seconds]
    if len(hits) >= limit:
        RATE_LIMITS[key] = hits
        return True
    hits.append(now)
    RATE_LIMITS[key] = hits
    return False


def record_failed_login(user):
    if not user:
        return
    user.failed_login_count = (user.failed_login_count or 0) + 1
    if user.failed_login_count >= MAX_FAILED_LOGINS:
        user.locked_until = utc_now() + timedelta(minutes=LOGIN_LOCKOUT_MINUTES)
        user.failed_login_count = 0
    db.session.commit()


def record_successful_login(user):
    session.clear()
    session.permanent = True
    session['user_id'] = user.id
    session['user_name'] = user.name
    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = utc_now()
    user.last_login_ip = client_ip()
    db.session.commit()


def save_avatar_upload(file_storage, user_id):
    if not file_storage or not file_storage.filename:
        return None
    if not allowed_file(file_storage.filename):
        raise ValueError('Invalid avatar file type. Only PNG, JPG, JPEG, and GIF are allowed.')
    if Image is None:
        raise ValueError('Image validation is unavailable on this server.')
    try:
        image = Image.open(file_storage.stream)
        image.verify()
        image_format = image.format
    except (UnidentifiedImageError, OSError, ValueError):
        raise ValueError('Uploaded avatar is not a valid image.')
    if image_format not in ALLOWED_AVATAR_FORMATS:
        raise ValueError('Invalid avatar image format.')
    file_storage.stream.seek(0)
    ext = ALLOWED_AVATAR_FORMATS[image_format]
    filename = secure_filename(f'{user_id}_{secrets.token_hex(12)}.{ext}')
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file_storage.save(path)
    return filename


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def current_user():
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None

def generate_csrf_token():
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_urlsafe(32)
    return session['_csrf_token']


def validate_csrf_token(token):
    if not token or '_csrf_token' not in session:
        return False
    return secrets.compare_digest(session['_csrf_token'], token)

def csrf_field():
    return Markup(f'<input type="hidden" name="csrf_token" value="{generate_csrf_token()}">')

@app.before_request
def prepare_request_security_context():
    g.csp_nonce = secrets.token_urlsafe(16)


@app.before_request
def csrf_protect():
    if request.method == 'POST':
        token = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token')
        if not validate_csrf_token(token):
            abort(400, description='Invalid CSRF token.')


def log_audit(table, record_id, action, old=None, new=None):
    try:
        log = AuditLog(
            user_id=session.get('user_id'),
            table_name=table, record_id=record_id,
            action=action,
            old_data=json.dumps(old) if old else None,
            new_data=json.dumps(new) if new else None,
            ip_address=request.remote_addr
        )
        db.session.add(log)
    except: pass

def check_notifications(user_id):
    today = date.today()
    schedules = Schedule.query.filter_by(user_id=user_id, is_active=True).all()
    for s in schedules:
        if not s.next_due: continue
        remind_date = s.next_due - timedelta(days=s.remind_days_before or 3)
        if remind_date <= today <= s.next_due:
            existing = Notification.query.filter_by(
                user_id=user_id, schedule_id=s.id, due_date=s.next_due
            ).first()
            if not existing:
                notif = Notification(
                    user_id=user_id, schedule_id=s.id,
                    message=f"📅 {s.name} payment of ₹{s.amount:,.0f} due on {s.next_due.strftime('%d %b %Y')}",
                    due_date=s.next_due
                )
                db.session.add(notif)
    db.session.commit()

def seed_categories():
    defaults = [
        ("Living Expenses","Rent","Expense"),("Living Expenses","Bills Payment","Expense"),
        ("Living Expenses","Foods & Dining","Expense"),("Living Expenses","Family Expense","Expense"),
        ("Living Expenses","Friends Expense","Expense"),("Variable","Pocket Money","Income"),
        ("Transport","Travelling","Expense"),("Discretionary","Shopping","Expense"),
        ("Discretionary","Entertainments","Expense"),("Discretionary","Personal Care","Expense"),
        ("Education","Education","Expense"),("Medical","Medical","Expense"),
        ("Fixed","Salary","Income"),("Variable","Bonus","Income"),
        ("Variable","Dividend","Income"),("Variable","Interest","Income"),
        ("Variable","Family Received","Income"),("Variable","Friends Received","Income"),
        ("Investment","Investment","Not Reported"),("Investment","Share Sell","Income"),
        ("Investment","Share Buy","Expense"),("Investment","SIP","Not Reported"),
        ("Investment","IPO","Not Reported"),("Transfer","Transfer C-E","Not Reported"),
        ("Financial","Taxes","Expense"),("Financial","Insurances","Expense"),
        ("Other","Voucher","Income"),("Other","Cashback","Income"),("Other","Other","Expense"),
    ]
    for name, sub, ctype in defaults:
        if not Category.query.filter_by(name=name, subcategory=sub, user_id=None).first():
            db.session.add(Category(name=name, subcategory=sub, category_type=ctype, is_system=True))
    db.session.commit()

# ─── CONTEXT PROCESSOR ────────────────────────────────────────────────────────
@app.route('/help')
def help_page():
    return render_template('help.html')


@app.route('/about')
def about_page():
    return render_template('about.html')


@app.route('/rate', methods=['GET', 'POST'])
def rate_page():
    if request.method == 'POST':
        rating = request.form.get('rating')
        feedback = request.form.get('feedback', '').strip()

        if not rating:
            flash('Please choose a rating so we can improve your experience.', 'error')
        else:
            print('Rating:', rating)
            print('Feedback:', feedback)
            flash('Thanks for your feedback!', 'success')

    return render_template('rate.html')

@app.context_processor
def inject_globals():
    uid = session.get('user_id')
    notif_count = 0
    notifs = []
    user = None
    if uid:
        try:
            notif_count = Notification.query.filter_by(user_id=uid, is_read=False).count()
            notifs = Notification.query.filter_by(user_id=uid, is_read=False)\
                .order_by(Notification.due_date).limit(5).all()
            user = User.query.get(uid)
        except: pass
    return dict(notif_count=notif_count, notifs=notifs, user=user, enumerate=enumerate,
                csrf_token=generate_csrf_token, csrf_field=csrf_field,
                csp_nonce=getattr(g, 'csp_nonce', ''))

@app.after_request
def apply_security_headers(response):
    nonce = getattr(g, 'csp_nonce', '')
    response.headers.setdefault('X-Frame-Options', 'DENY')
    response.headers.setdefault('X-Content-Type-Options', 'nosniff')
    response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
    response.headers.setdefault('Permissions-Policy', 'geolocation=(), microphone=(), camera=(), payment=(), usb=()')
    response.headers.setdefault('Cross-Origin-Opener-Policy', 'same-origin')
    response.headers.setdefault('Cross-Origin-Resource-Policy', 'same-origin')
    if IS_PRODUCTION:
        csp = (
            "default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; form-action 'self'; "
            f"script-src 'self' https://cdn.jsdelivr.net 'nonce-{nonce}'; script-src-attr 'unsafe-inline'; "
            "style-src 'self' https://fonts.googleapis.com 'unsafe-inline'; font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: blob:; connect-src 'self'; upgrade-insecure-requests"
        )
    else:
        csp = (
            "default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; form-action 'self'; "
            f"script-src 'self' https://cdn.jsdelivr.net 'nonce-{nonce}'; script-src-attr 'unsafe-inline'; "
            "style-src 'self' https://fonts.googleapis.com 'unsafe-inline'; font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: blob:; connect-src 'self'"
        )
    response.headers.setdefault('Content-Security-Policy', csp)
    if request.endpoint != 'static' and session.get('user_id'):
        response.headers.setdefault('Cache-Control', 'no-store, max-age=0')
        response.headers.setdefault('Pragma', 'no-cache')
    if request.is_secure or app.config['SESSION_COOKIE_SECURE']:
        response.headers.setdefault('Strict-Transport-Security', 'max-age=63072000; includeSubDomains; preload')
    return response


@app.errorhandler(400)
@app.errorhandler(403)
@app.errorhandler(404)
@app.errorhandler(413)
@app.errorhandler(429)
def handle_client_error(error):
    status = getattr(error, 'code', 500)
    message = getattr(error, 'description', 'Request could not be completed.')
    if status == 429:
        message = 'Too many attempts. Please wait and try again.'
    if status == 413:
        message = 'The uploaded file is too large.'
    return render_template('error.html', status=status, message=message), status


@app.errorhandler(500)
def handle_server_error(error):
    db.session.rollback()
    return render_template('error.html', status=500, message='Something went wrong. Please try again.'), 500

# ─── ROUTES: PUBLIC# ─── ROUTES: PUBLIC ───────────────────────────────────────────────────────────

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        if rate_limited('login', 20, 15 * 60):
            abort(429)
        identifier = clean_text(request.form.get('identifier',''), 150).lower()
        password = request.form.get('password','')
        errors = {}
        form_data = {'identifier': identifier}

        if '@' in identifier:
            if not validate_email(identifier):
                errors['identifier'] = 'Please enter a valid email address.'
        else:
            try:
                identifier = validate_mobile(identifier)
            except ValueError as exc:
                errors['identifier'] = str(exc)
            if not identifier:
                errors['identifier'] = 'Enter a valid email or 10-digit mobile number.'
        if not password:
            errors['password'] = 'Please enter your password.'
        if errors:
            return render_template('auth.html', mode='login', errors=errors, form_data=form_data)

        user = User.query.filter_by(email=identifier).first() if '@' in identifier else User.query.filter_by(mobile=identifier).first()
        locked_until = as_utc(user.locked_until) if user and user.locked_until else None
        if locked_until and locked_until > utc_now():
            errors['identifier'] = 'Too many failed attempts. Please try again later.'
            return render_template('auth.html', mode='login', errors=errors, form_data=form_data)
        if not user or not user.check_password(password) or not user.is_active:
            record_failed_login(user)
            errors['identifier'] = 'Invalid credentials.'
            return render_template('auth.html', mode='login', errors=errors, form_data=form_data)

        if user.two_factor_enabled:
            if rate_limited(f'totp:{user.id}', 10, 10 * 60):
                abort(429)
            totp_code = request.form.get('totp_code','').strip()
            if not totp_code:
                errors['totp_code'] = 'Enter the 6-digit code from your authenticator app.'
            elif not verify_totp_code(user.two_factor_secret or '', totp_code, window=1):
                errors['totp_code'] = 'The verification code is invalid.'
                record_failed_login(user)
            if errors:
                return render_template('auth.html', mode='login', errors=errors, form_data=form_data, require_totp=True)

        record_successful_login(user)
        check_notifications(user.id)
        flash(f'Welcome back, {user.name}!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('auth.html', mode='login')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        if rate_limited('register', 8, 60 * 60):
            abort(429)
        errors = {}
        raw_name = request.form.get('name','')
        try:
            name = clean_text(raw_name, 100, required=True)
        except ValueError:
            name = ''
            errors['name'] = 'Please enter your full name.'
        email = validate_email(request.form.get('email',''))
        mobile_raw = request.form.get('mobile','')
        password = request.form.get('password','')
        primary_currency = (request.form.get('primary_currency', 'INR') or 'INR').strip().upper()
        enable_2fa = request.form.get('enable_2fa') == 'on'
        form_data = {'name': raw_name.strip(), 'email': request.form.get('email','').strip().lower(), 'mobile': mobile_raw, 'primary_currency': primary_currency}

        if not email:
            errors['email'] = 'Please enter a valid email address.'
        elif User.query.filter_by(email=email).first():
            errors['email'] = 'Email already registered.'
        try:
            mobile = validate_mobile(mobile_raw)
        except ValueError as exc:
            errors['mobile'] = str(exc)
            mobile = mobile_raw
        if mobile and User.query.filter_by(mobile=mobile).first():
            errors['mobile'] = 'Mobile number already registered.'
        if primary_currency not in SUPPORTED_CURRENCIES:
            errors['primary_currency'] = 'Please choose a supported currency.'
        pw_err = validate_password(password)
        if pw_err:
            errors['password'] = pw_err
        if errors:
            return render_template('auth.html', mode='register', errors=errors, form_data=form_data)

        user = User(name=name, email=email, mobile=mobile, primary_currency=primary_currency, password_changed_at=utc_now())
        user.set_password(password)
        if enable_2fa:
            user.two_factor_secret = generate_2fa_secret()
            user.two_factor_enabled = False
        db.session.add(user)
        db.session.commit()
        log_audit('user', user.id, 'INSERT', new={'name':name,'email':email})
        db.session.commit()
        if enable_2fa:
            session.clear()
            session['pending_2fa_user_id'] = user.id
            session['pending_2fa_secret'] = user.two_factor_secret
            flash('Secure your account by verifying the authenticator code below.', 'info')
            return redirect(url_for('two_factor_setup'))
        record_successful_login(user)
        flash('Account created! Start by adding your accounts.', 'success')
        return redirect(url_for('dashboard'))
    return render_template('auth.html', mode='register')

@app.route('/2fa/setup', methods=['GET','POST'])
def two_factor_setup():
    pending_user_id = session.get('pending_2fa_user_id')
    pending_secret = session.get('pending_2fa_secret')
    if not pending_user_id or not pending_secret:
        return redirect(url_for('login'))

    user = User.query.get(pending_user_id)
    if not user:
        session.pop('pending_2fa_user_id', None)
        session.pop('pending_2fa_secret', None)
        return redirect(url_for('login'))

    if request.method == 'POST':
        code = request.form.get('totp_code','').strip()
        if not verify_totp_code(pending_secret, code):
            return render_template(
                'two_factor_setup.html',
                user=user,
                secret=pending_secret,
                qr_image_data_url=generate_qr_code_data_url(pending_secret, user.email, 'FinFlow'),
                error='The verification code is invalid.'
            )
        user.two_factor_enabled = True
        user.two_factor_secret = pending_secret
        db.session.commit()
        session.pop('pending_2fa_user_id', None)
        session.pop('pending_2fa_secret', None)
        session['user_id'] = user.id
        session['user_name'] = user.name
        flash('Two-factor authentication is enabled for your account.', 'success')
        return redirect(url_for('dashboard'))

    return render_template(
        'two_factor_setup.html',
        user=user,
        secret=pending_secret,
        qr_image_data_url=generate_qr_code_data_url(pending_secret, user.email, 'FinFlow')
    )

@app.route('/password/forgot', methods=['GET','POST'])
def password_forgot():
    if request.method == 'POST':
        if rate_limited('password-forgot', 5, 60 * 60):
            abort(429)
        email = validate_email(request.form.get('email',''))
        if not email:
            return render_template('password_forgot.html', error='Please enter a valid email address.', email=request.form.get('email',''))
        user = User.query.filter_by(email=email, is_active=True).first()
        if not user:
            return render_template('password_forgot.html', info='If an account exists, a reset link has been sent to the email.')
        token = secrets.token_urlsafe(48)
        expires = utc_now() + timedelta(hours=1)
        pr = PasswordReset(user_id=user.id, token=token, expires_at=expires)
        db.session.add(pr)
        db.session.commit()
        reset_link = url_for('password_reset', token=token, _external=True)
        if IS_PRODUCTION:
            return render_template('password_forgot.html', info='If an account exists, a reset link has been sent to the email.')
        return render_template('password_forgot.html', info='Demo reset link generated.', reset_link=reset_link)
    return render_template('password_forgot.html')


@app.route('/password/reset/<token>', methods=['GET','POST'])
def password_reset(token):
    if not re.fullmatch(r'[A-Za-z0-9_-]{40,128}', token or ''):
        return render_template('password_reset.html', error='Invalid or expired token.')
    pr = PasswordReset.query.filter_by(token=token).first()
    expires_at = as_utc(pr.expires_at) if pr and pr.expires_at else None
    if not pr or pr.used or (expires_at and expires_at < utc_now()):
        return render_template('password_reset.html', error='Invalid or expired token.')
    user = User.query.get(pr.user_id)
    if not user or not user.is_active:
        return render_template('password_reset.html', error='Invalid token.')
    if request.method == 'POST':
        if rate_limited('password-reset', 8, 60 * 60):
            abort(429)
        pw = request.form.get('password','')
        pw_err = validate_password(pw)
        if pw_err:
            return render_template('password_reset.html', error=pw_err, token=token)
        user.set_password(pw)
        user.password_changed_at = utc_now()
        user.failed_login_count = 0
        user.locked_until = None
        pr.used = True
        db.session.commit()
        session.clear()
        flash('Password reset successful. You can now login.', 'success')
        return redirect(url_for('login'))
    return render_template('password_reset.html', token=token)

@app.route('/logout', methods=['POST'])
@login_required
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('home'))

# ─── ROUTES: DASHBOARD# ─── ROUTES: DASHBOARD ────────────────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    uid = session['user_id']
    today = date.today()
    month_start = today.replace(day=1)

    selected_year = request.args.get('year', type=int) or today.year
    selected_month = request.args.get('month', type=int)
    if selected_month is None:
        selected_month = today.month
    selected_category_id = request.args.get('category_id', type=int)

    year_options = [int(row[0]) for row in db.session.query(func.strftime('%Y', Transaction.date)).filter(
        Transaction.user_id==uid,
        Transaction.is_deleted==False
    ).group_by(func.strftime('%Y', Transaction.date)).order_by(func.strftime('%Y', Transaction.date).desc()).all()]
    if not year_options:
        year_options = [today.year]
    elif selected_year not in year_options:
        year_options.insert(0, selected_year)

    month_options = [
        {'value': 0, 'label': 'All Months'},
        {'value': 1, 'label': 'January'},
        {'value': 2, 'label': 'February'},
        {'value': 3, 'label': 'March'},
        {'value': 4, 'label': 'April'},
        {'value': 5, 'label': 'May'},
        {'value': 6, 'label': 'June'},
        {'value': 7, 'label': 'July'},
        {'value': 8, 'label': 'August'},
        {'value': 9, 'label': 'September'},
        {'value': 10, 'label': 'October'},
        {'value': 11, 'label': 'November'},
        {'value': 12, 'label': 'December'},
    ]

    category_filter = [Transaction.user_id==uid, Transaction.is_deleted==False]
    if selected_year:
        category_filter.append(func.strftime('%Y', Transaction.date) == str(selected_year))
    if selected_month and selected_month != 0:
        category_filter.append(func.strftime('%m', Transaction.date) == f"{selected_month:02d}")
    if selected_category_id:
        category_filter.append(Transaction.category_id == selected_category_id)

    income = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.txn_type=='Income', *category_filter).scalar() or 0
    expense = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.txn_type=='Expense', *category_filter).scalar() or 0

    accounts = Account.query.filter_by(user_id=uid, is_active=True).all()
    total_balance = sum(a.current_balance for a in accounts)

    recent = Transaction.query.filter(*category_filter).order_by(
        Transaction.date.desc(), Transaction.created_at.desc()).limit(8).all()

    daily = []
    for i in range(6,-1,-1):
        d = today - timedelta(days=i)
        inc = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.txn_type=='Income',
            Transaction.date==d,
            *([Transaction.user_id==uid, Transaction.is_deleted==False] + ([Transaction.category_id == selected_category_id] if selected_category_id else []) + (
                [func.strftime('%Y', Transaction.date) == str(selected_year)] if selected_year else []) + (
                [func.strftime('%m', Transaction.date) == f"{selected_month:02d}"] if selected_month and selected_month != 0 else []))
        ).scalar() or 0
        exp = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.txn_type=='Expense',
            Transaction.date==d,
            *([Transaction.user_id==uid, Transaction.is_deleted==False] + ([Transaction.category_id == selected_category_id] if selected_category_id else []) + (
                [func.strftime('%Y', Transaction.date) == str(selected_year)] if selected_year else []) + (
                [func.strftime('%m', Transaction.date) == f"{selected_month:02d}"] if selected_month and selected_month != 0 else []))
        ).scalar() or 0
        daily.append({'date': d.strftime('%d %b'), 'income': round(inc,2), 'expense': round(exp,2)})

    notifs = Notification.query.filter_by(user_id=uid, is_read=False)\
        .order_by(Notification.due_date).limit(5).all()
    notif_count = Notification.query.filter_by(user_id=uid, is_read=False).count()

    schedules_due = Schedule.query.filter(
        Schedule.user_id==uid, Schedule.is_active==True,
        Schedule.next_due <= today+timedelta(days=7)
    ).order_by(Schedule.next_due).all()

    categories = Category.query.filter(
        (Category.user_id==uid) | (Category.user_id==None),
        Category.is_active==True,
        Category.category_type.in_(['Income', 'Expense'])
    ).order_by(Category.name, Category.subcategory).all()

    # Category Analytics Data
    category_data = db.session.query(
        Category.name,
        func.sum(Transaction.amount).label('total')
    ).join(Transaction).filter(
        Transaction.user_id==uid,
        Transaction.is_deleted==False,
        Category.category_type.in_(['Income', 'Expense'])
    )
    if selected_year:
        category_data = category_data.filter(func.strftime('%Y', Transaction.date) == str(selected_year))
    if selected_month and selected_month != 0:
        category_data = category_data.filter(func.strftime('%m', Transaction.date) == f"{selected_month:02d}")
    if selected_category_id:
        category_data = category_data.filter(Transaction.category_id == selected_category_id)
    category_data = category_data.group_by(Category.name).all()

    subcategory_data = db.session.query(
        Category.name,
        Category.subcategory,
        func.sum(Transaction.amount).label('total')
    ).join(Transaction).filter(
        Transaction.user_id==uid,
        Transaction.is_deleted==False,
        Category.category_type.in_(['Income', 'Expense'])
    )
    if selected_year:
        subcategory_data = subcategory_data.filter(func.strftime('%Y', Transaction.date) == str(selected_year))
    if selected_month and selected_month != 0:
        subcategory_data = subcategory_data.filter(func.strftime('%m', Transaction.date) == f"{selected_month:02d}")
    if selected_category_id:
        subcategory_data = subcategory_data.filter(Transaction.category_id == selected_category_id)
    subcategory_data = subcategory_data.group_by(Category.name, Category.subcategory).all()

    return render_template('dashboard.html',
    income=income,
    expense=expense,
    savings=income - expense,
    total_balance=total_balance,
    accounts=accounts,
    recent=recent,
    daily_data=json.dumps(daily),
    schedules_due=schedules_due,
    today=today,
    categories=categories,
    year_options=year_options,
    month_options=month_options,
    selected_year=selected_year,
    selected_month=selected_month,
    selected_category_id=selected_category_id,
    category_data=json.dumps([{'name': c.name, 'total': float(c.total)} for c in category_data]),
    subcategory_data=json.dumps([{'category': s.name, 'subcategory': s.subcategory, 'total': float(s.total)} for s in subcategory_data])
    )

# ─── ROUTES: ACCOUNTS ─────────────────────────────────────────────────────────

@app.route('/accounts')
@login_required
def accounts():
    uid = session['user_id']
    all_accounts = Account.query.filter_by(user_id=uid, is_active=True).all()
    grouped = {}
    for a in all_accounts:
        # Fetch denomination details for wallet accounts
        if a.account_type == 'wallet':
            a.denominations = Denomination.query.filter_by(account_id=a.id).order_by(Denomination.denomination_value.desc()).all()
        else:
            a.denominations = []
        grouped.setdefault(a.account_type, []).append(a)
    return render_template('accounts.html', grouped=grouped)

@app.route('/accounts/add', methods=['GET','POST'])
@login_required
def add_account():
    uid = session['user_id']
    user = User.query.get(uid)
    if request.method == 'POST':
        try:
            opening_balance = parse_money(request.form.get('opening_balance', 0), 'Opening balance', min_value=0)
            account_type = clean_text(request.form.get('account_type'), 50, required=True)
            if account_type not in ACCOUNT_TYPES:
                raise ValueError('Invalid account type selected.')
            sub_type = clean_text(request.form.get('sub_type'), 50)
            if sub_type == 'Other':
                sub_type = clean_text(request.form.get('sub_type_custom'), 50) or 'Other'
            currency = (request.form.get('currency') or (user.primary_currency if user else 'INR') or 'INR').strip().upper()
            if currency not in SUPPORTED_CURRENCIES:
                raise ValueError('Unsupported currency selected.')
            denom_payload = None
            if account_type == 'wallet':
                denom_payload, _ = parse_denomination_payload(request.form.get('denom_data'), opening_balance)
            start_date = parse_date_field(request.form.get('start_date'), 'Start date')
            maturity_date = parse_date_field(request.form.get('maturity_date'), 'Maturity date')
            due_date = parse_date_field(request.form.get('due_date'), 'Due date')
            installment_date = parse_date_field(request.form.get('installment_date'), 'Installment date')
            notification_days = parse_int_range(request.form.get('notification_days'), 'Notification days', 1, 30, default=None) if request.form.get('notification_days') else None
            installment_amount = parse_optional_money(request.form.get('installment_amount'), 'Installment amount')
            installment_type = clean_text(request.form.get('installment_type'), 10) or None
            acc = Account(
                user_id=uid,
                name=clean_text(request.form.get('name'), 100, required=True),
                account_type=account_type,
                sub_type=sub_type,
                institution=clean_text(request.form.get('institution'), 100),
                account_number=clean_text(request.form.get('account_number'), 50),
                currency=currency,
                opening_balance=opening_balance,
                current_balance=opening_balance,
                color=clean_text(request.form.get('color','#6366f1'), 20) or '#6366f1',
                icon=clean_text(request.form.get('icon','🏦'), 10) or '🏦',
                notes=clean_text(request.form.get('notes'), 1000),
                start_date=start_date,
                maturity_date=maturity_date,
                due_date=due_date,
                notification_days=notification_days,
                installment_date=installment_date,
                installment_amount=installment_amount,
                installment_type=installment_type,
                denom_data=json.dumps(denom_payload) if denom_payload else None,
                machine_name=platform.node() or client_ip()
            )
            db.session.add(acc)
            db.session.commit()
            if denom_payload:
                for value_str, count in denom_payload.items():
                    db.session.add(Denomination(account_id=acc.id, denomination_value=int(value_str), count=count))
                db.session.commit()
            log_audit('account', acc.id, 'INSERT', new={'name':acc.name,'balance':acc.opening_balance})
            db.session.commit()
            flash('Account added!', 'success')
            return redirect(url_for('accounts'))
        except ValueError as exc:
            flash(str(exc), 'error')
    return render_template('add_account.html')

@app.route('/accounts/edit/<int:id>', methods=['GET','POST'])
@login_required
def edit_account(id):
    uid = session['user_id']
    acc = Account.query.filter_by(id=id, user_id=uid, is_active=True).first()
    if not acc:
        flash('Account not found.', 'error')
        return redirect(url_for('accounts'))
    if request.method == 'POST':
        try:
            closing_date = request.form.get('closing_date')
            if closing_date and acc.sub_type not in ['Loan', 'OD'] and abs(acc.current_balance or 0) > 0.01:
                raise ValueError('Closing balance must be zero to close this account.')
            acc.name = clean_text(request.form.get('name'), 100, required=True)
            acc.institution = clean_text(request.form.get('institution'), 100)
            acc.account_number = clean_text(request.form.get('account_number'), 50)
            currency = (request.form.get('currency') or acc.currency or 'INR').strip().upper()
            if currency not in SUPPORTED_CURRENCIES:
                raise ValueError('Unsupported currency selected.')
            acc.currency = currency
            acc.color = clean_text(request.form.get('color', acc.color or '#3b82f6'), 20) or '#3b82f6'
            acc.icon = clean_text(request.form.get('icon', acc.icon or '🏦'), 10) or '🏦'
            acc.start_date = parse_date_field(request.form.get('start_date'), 'Start date')
            acc.maturity_date = parse_date_field(request.form.get('maturity_date'), 'Maturity date')
            acc.due_date = parse_date_field(request.form.get('due_date'), 'Due date')
            acc.installment_date = parse_date_field(request.form.get('installment_date'), 'Installment date')
            acc.notification_days = parse_int_range(request.form.get('notification_days'), 'Notification days', 1, 30, default=None) if request.form.get('notification_days') else None
            acc.installment_amount = parse_optional_money(request.form.get('installment_amount'), 'Installment amount')
            acc.installment_type = clean_text(request.form.get('installment_type'), 10) or None
            notes = clean_text(request.form.get('notes'), 1000)
            if closing_date:
                closing = parse_date_field(closing_date, 'Closing date')
                closing_note = f'Closing Date: {closing.isoformat()}'
                notes = notes + '\n' + closing_note if notes else closing_note
                acc.is_active = False
            acc.notes = notes
            denom_data = request.form.get('denom_data')
            if denom_data:
                denom_payload, _ = parse_denomination_payload(denom_data, acc.current_balance if acc.account_type == 'wallet' else None)
                Denomination.query.filter_by(account_id=acc.id).delete()
                for value_str, count in denom_payload.items():
                    db.session.add(Denomination(account_id=acc.id, denomination_value=int(value_str), count=count))
                acc.denom_data = json.dumps(denom_payload) if denom_payload else None
            db.session.commit()
            flash('Account updated!', 'success')
            return redirect(url_for('accounts'))
        except ValueError as exc:
            flash(str(exc), 'error')
    if not acc.color:
        acc.color = '#3b82f6'
    if not acc.icon:
        acc.icon = '🏦'
    acc.denominations = Denomination.query.filter_by(account_id=acc.id).order_by(Denomination.denomination_value.desc()).all() if acc.account_type == 'wallet' else []
    return render_template('edit_account.html', acc=acc)

@app.route('/accounts/delete/<int:id>', methods=['POST'])
@login_required
def delete_account(id):
    uid = session['user_id']
    acc = Account.query.filter_by(id=id, user_id=uid).first_or_404()
    log_audit('account', acc.id, 'DELETE', old={'name':acc.name})
    acc.is_active = False
    db.session.commit()
    flash('Account removed.', 'info')
    return redirect(url_for('accounts'))

# ─── ROUTES: STATEMENT ────────────────────────────────────────────────────────

@app.route('/statement')
@login_required
def statement():
    uid = session['user_id']
    accounts = Account.query.filter_by(user_id=uid, is_active=True).all()
    account_type = request.args.get('account_type','')
    account_id = request.args.get('account_id', type=int)

    # Build statement rows per account
    rows = []
    filtered_accounts = accounts
    if account_type:
        filtered_accounts = [a for a in accounts if a.account_type == account_type]
    if account_id:
        filtered_accounts = [a for a in accounts if a.id == account_id]

    for acc in filtered_accounts:
        debit = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id==uid, Transaction.account_id==acc.id,
            Transaction.txn_type=='Expense', Transaction.is_deleted==False).scalar() or 0
        credit = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id==uid, Transaction.account_id==acc.id,
            Transaction.txn_type=='Income', Transaction.is_deleted==False).scalar() or 0
        rows.append({
            'id': acc.id, 'name': acc.name, 'icon': acc.icon,
            'opening': acc.opening_balance,
            'debit': debit, 'credit': credit,
            'closing': acc.opening_balance - debit + credit
        })

    totals = {
        'opening': sum(r['opening'] for r in rows),
        'debit': sum(r['debit'] for r in rows),
        'credit': sum(r['credit'] for r in rows),
        'closing': sum(r['closing'] for r in rows),
    }
    return render_template('statement.html', rows=rows, totals=totals,
        accounts=accounts, sel_type=account_type, sel_id=account_id)

# ─── ROUTES: TRANSACTIONS ─────────────────────────────────────────────────────

@app.route('/transactions')
@login_required
def transactions():
    uid = session['user_id']
    page = request.args.get('page', 1, type=int)
    txn_type = clean_text(request.args.get('txn_type',''), 20)
    payment_mode = clean_text(request.args.get('payment_mode',''), 30)
    account_id = request.args.get('account_id','')
    cat_id = request.args.get('category_id','')
    start_date = request.args.get('start_date','')
    end_date = request.args.get('end_date','')
    search = clean_text(request.args.get('search',''), 100)

    q = Transaction.query.filter_by(user_id=uid, is_deleted=False)
    if txn_type in TRANSACTION_TYPES:
        q = q.filter_by(txn_type=txn_type)
    if payment_mode in PAYMENT_MODES:
        q = q.filter_by(payment_mode=payment_mode)
    try:
        if account_id:
            acc = account_for_user(uid, account_id, active=False)
            q = q.filter_by(account_id=acc.id)
        if cat_id:
            cat = category_for_user(uid, cat_id)
            q = q.filter_by(category_id=cat.id)
        if start_date:
            q = q.filter(Transaction.date >= parse_date_field(start_date, 'Start date'))
        if end_date:
            q = q.filter(Transaction.date <= parse_date_field(end_date, 'End date'))
    except ValueError as exc:
        flash(str(exc), 'error')
    if search:
        amount_filter = -1
        try:
            amount_filter = parse_money(search, 'Search amount', min_value=0)
        except ValueError:
            pass
        q = q.filter((Transaction.description.ilike(f'%{search}%')) | (Transaction.amount == amount_filter))

    txns = q.order_by(Transaction.date.desc(), Transaction.created_at.desc()).paginate(page=max(page, 1), per_page=25)
    accounts = Account.query.filter_by(user_id=uid, is_active=True).all()
    categories = Category.query.filter(
        (Category.user_id==uid)|(Category.user_id==None)
    ).filter_by(is_active=True).all()
    return render_template('transactions.html', txns=txns, accounts=accounts,
        categories=categories)

@app.route('/transactions/add', methods=['GET','POST'])
@login_required
def add_transaction():
    uid = session['user_id']
    accounts = Account.query.filter_by(user_id=uid, is_active=True).all()
    categories = Category.query.filter(
        (Category.user_id==uid)|(Category.user_id==None)
    ).filter_by(is_active=True).order_by(Category.name).all()
    if request.method == 'POST':
        try:
            amount = parse_money(request.form.get('amount'), 'Transaction amount')
            payment_mode = clean_text(request.form.get('payment_mode'), 30, required=True)
            if payment_mode not in PAYMENT_MODES:
                raise ValueError('Invalid payment mode selected.')
            denom_payload = None
            if payment_mode in ('Cash', 'Wallet'):
                denom_payload, _ = parse_denomination_payload(request.form.get('denom_data'), amount)
            cat = category_for_user(uid, request.form.get('category_id'))
            acc = account_for_user(uid, request.form.get('account_id')) if request.form.get('account_id') else None
            txn = Transaction(
                user_id=uid,
                date=parse_date_field(request.form.get('date'), 'Transaction date') or date.today(),
                amount=amount,
                txn_type=cat.category_type if cat else clean_text(request.form.get('txn_type','Expense'), 20),
                category_id=cat.id if cat else None,
                payment_mode=payment_mode,
                account_id=acc.id if acc else None,
                description=clean_text(request.form.get('description'), 255),
                reference_no=clean_text(request.form.get('reference_no'), 100),
                tags=clean_text(request.form.get('tags'), 200),
                denom_data=json.dumps(denom_payload) if denom_payload else None,
                machine_name=platform.node() or client_ip()
            )
            if txn.txn_type not in TRANSACTION_TYPES:
                raise ValueError('Invalid transaction type.')
            if acc:
                if txn.txn_type == 'Income':
                    acc.current_balance += txn.amount
                elif txn.txn_type == 'Expense':
                    acc.current_balance -= txn.amount
            db.session.add(txn)
            db.session.commit()
            log_audit('transaction', txn.id, 'INSERT', new={'amount':txn.amount,'type':txn.txn_type})
            db.session.commit()
            flash('Transaction added!', 'success')
            return redirect(url_for('transactions'))
        except ValueError as exc:
            flash(str(exc), 'error')
    return render_template('add_transaction.html', accounts=accounts,
        categories=categories, today=date.today().isoformat())

@app.route('/transactions/edit/<int:id>', methods=['GET','POST'])
@login_required
def edit_transaction(id):
    uid = session['user_id']
    txn = Transaction.query.filter_by(id=id, user_id=uid, is_deleted=False).first_or_404()
    accounts = Account.query.filter_by(user_id=uid, is_active=True).all()
    categories = Category.query.filter(
        (Category.user_id==uid)|(Category.user_id==None)
    ).filter_by(is_active=True).order_by(Category.name).all()
    if request.method == 'POST':
        try:
            old = {'amount':txn.amount,'type':txn.txn_type,'date':str(txn.date)}
            old_acc = account_for_user(uid, txn.account_id, active=False) if txn.account_id else None
            if old_acc:
                if txn.txn_type == 'Income': old_acc.current_balance -= txn.amount
                elif txn.txn_type == 'Expense': old_acc.current_balance += txn.amount
            amount = parse_money(request.form.get('amount'), 'Transaction amount')
            cat = category_for_user(uid, request.form.get('category_id'))
            new_acc = account_for_user(uid, request.form.get('account_id')) if request.form.get('account_id') else None
            payment_mode = clean_text(request.form.get('payment_mode'), 30, required=True)
            if payment_mode not in PAYMENT_MODES:
                raise ValueError('Invalid payment mode selected.')
            denom_payload = None
            if payment_mode in ('Cash', 'Wallet') and request.form.get('denom_data'):
                denom_payload, _ = parse_denomination_payload(request.form.get('denom_data'), amount)
            txn.date = parse_date_field(request.form.get('date'), 'Transaction date') or date.today()
            txn.amount = amount
            txn.txn_type = cat.category_type if cat else txn.txn_type
            txn.category_id = cat.id if cat else None
            txn.payment_mode = payment_mode
            txn.account_id = new_acc.id if new_acc else None
            txn.description = clean_text(request.form.get('description'), 255)
            txn.reference_no = clean_text(request.form.get('reference_no'), 100)
            txn.tags = clean_text(request.form.get('tags'), 200)
            txn.denom_data = json.dumps(denom_payload) if denom_payload else None
            txn.updated_at = utc_now()
            if txn.txn_type not in TRANSACTION_TYPES:
                raise ValueError('Invalid transaction type.')
            if new_acc:
                if txn.txn_type == 'Income': new_acc.current_balance += txn.amount
                elif txn.txn_type == 'Expense': new_acc.current_balance -= txn.amount
            db.session.commit()
            log_audit('transaction', txn.id, 'UPDATE', old=old, new={'amount':txn.amount})
            db.session.commit()
            flash('Transaction updated!', 'success')
            return redirect(url_for('transactions'))
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), 'error')
    return render_template('edit_transaction.html', txn=txn, accounts=accounts,
        categories=categories)

@app.route('/transactions/delete/<int:id>', methods=['POST'])
@login_required
def delete_transaction(id):
    uid = session['user_id']
    txn = Transaction.query.filter_by(id=id, user_id=uid, is_deleted=False).first_or_404()
    if txn.account_id:
        acc = Account.query.get(txn.account_id)
        if acc:
            if txn.txn_type == 'Income': acc.current_balance -= txn.amount
            elif txn.txn_type == 'Expense': acc.current_balance += txn.amount
    log_audit('transaction', txn.id, 'DELETE', old={'amount':txn.amount,'type':txn.txn_type})
    txn.is_deleted = True
    db.session.commit()
    flash('Transaction deleted.', 'info')
    return redirect(url_for('transactions'))

@app.route('/transactions/export')
@login_required
def export_transactions():
    uid = session['user_id']
    txn_type = clean_text(request.args.get('txn_type',''), 20)
    payment_mode = clean_text(request.args.get('payment_mode',''), 30)
    start_date = request.args.get('start_date','')
    end_date = request.args.get('end_date','')

    q = Transaction.query.filter_by(user_id=uid, is_deleted=False)
    if txn_type in TRANSACTION_TYPES:
        q = q.filter_by(txn_type=txn_type)
    if payment_mode in PAYMENT_MODES:
        q = q.filter_by(payment_mode=payment_mode)
    try:
        if start_date:
            q = q.filter(Transaction.date >= parse_date_field(start_date, 'Start date'))
        if end_date:
            q = q.filter(Transaction.date <= parse_date_field(end_date, 'End date'))
    except ValueError as exc:
        flash(str(exc), 'error')
        return redirect(url_for('transactions'))
    txns = q.order_by(Transaction.date.desc()).limit(10000).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Date','Description','Category','Subcategory','Payment Mode','Account','Type','Amount','Reference','Tags'])
    for t in txns:
        cat = t.category
        writer.writerow([
            t.date, t.description or '',
            cat.name if cat else '', cat.subcategory if cat else '',
            t.payment_mode or '', t.account.name if t.account else '',
            t.txn_type, t.amount, t.reference_no or '', t.tags or ''
        ])
    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode()),
        mimetype='text/csv', as_attachment=True,
        download_name=f'transactions_{date.today()}.csv')

# ─── ROUTES: CATEGORIES# ─── ROUTES: CATEGORIES ───────────────────────────────────────────────────────

@app.route('/categories')
@login_required
def categories():
    uid = session['user_id']
    cats = Category.query.filter(
        (Category.user_id==uid)|(Category.user_id==None)
    ).filter_by(is_active=True).order_by(Category.name, Category.subcategory).all()
    return render_template('categories.html', cats=cats)

@app.route('/categories/add', methods=['POST'])
@login_required
def add_category():
    uid = session['user_id']
    try:
        category_type = clean_text(request.form.get('category_type'), 30, required=True)
        if category_type not in TRANSACTION_TYPES:
            raise ValueError('Invalid category type.')
        cat = Category(
            user_id=uid,
            name=clean_text(request.form.get('name'), 100, required=True),
            subcategory=clean_text(request.form.get('subcategory'), 100, required=True),
            category_type=category_type,
            is_system=False
        )
        db.session.add(cat)
        db.session.commit()
        flash('Category added!', 'success')
    except ValueError as exc:
        flash(str(exc), 'error')
    return redirect(url_for('categories'))

@app.route('/categories/edit/<int:id>', methods=['POST'])
@login_required
def edit_category(id):
    uid = session['user_id']
    cat = Category.query.filter_by(id=id, user_id=uid, is_system=False).first_or_404()
    try:
        category_type = clean_text(request.form.get('category_type'), 30, required=True)
        if category_type not in TRANSACTION_TYPES:
            raise ValueError('Invalid category type.')
        cat.name = clean_text(request.form.get('name'), 100, required=True)
        cat.subcategory = clean_text(request.form.get('subcategory'), 100, required=True)
        cat.category_type = category_type
        db.session.commit()
        flash('Category updated!', 'success')
    except ValueError as exc:
        flash(str(exc), 'error')
    return redirect(url_for('categories'))

# ─── ROUTES: SCHEDULE# ─── ROUTES: SCHEDULE / REMINDERS ─────────────────────────────────────────────

@app.route('/schedules')
@login_required
def schedules():
    uid = session['user_id']
    today = date.today()
    scheds = Schedule.query.filter_by(user_id=uid, is_active=True).order_by(Schedule.next_due).all()
    accounts = Account.query.filter_by(user_id=uid, is_active=True).all()
    categories = Category.query.filter(
        (Category.user_id==uid)|(Category.user_id==None)
    ).filter_by(is_active=True).all()
    notifs = Notification.query.filter_by(user_id=uid).order_by(
        Notification.is_read, Notification.due_date).limit(20).all()
    return render_template('schedules.html', scheds=scheds, accounts=accounts,
        categories=categories, notifs=notifs, today=today)

@app.route('/schedules/add', methods=['POST'])
@login_required
def add_schedule():
    uid = session['user_id']
    try:
        freq = clean_text(request.form.get('frequency'), 20, required=True)
        if freq not in SCHEDULE_FREQUENCIES:
            raise ValueError('Invalid frequency selected.')
        due_day = parse_int_range(request.form.get('due_day', 1), 'Due day', 1, 31)
        today = date.today()
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
        cat = category_for_user(uid, request.form.get('category_id')) if request.form.get('category_id') else None
        acc = account_for_user(uid, request.form.get('account_id')) if request.form.get('account_id') else None
        payment_mode = clean_text(request.form.get('payment_mode'), 30)
        if payment_mode and payment_mode not in PAYMENT_MODES:
            raise ValueError('Invalid payment mode selected.')
        s = Schedule(
            user_id=uid,
            name=clean_text(request.form.get('name'), 100, required=True),
            amount=parse_money(request.form.get('amount'), 'Schedule amount'),
            category_id=cat.id if cat else None,
            account_id=acc.id if acc else None,
            payment_mode=payment_mode or None,
            frequency=freq,
            due_day=due_day,
            next_due=next_due,
            remind_days_before=parse_int_range(request.form.get('remind_days_before',3), 'Reminder days', 1, 30),
            notes=clean_text(request.form.get('notes'), 1000)
        )
        db.session.add(s)
        db.session.commit()
        flash('Schedule added!', 'success')
    except ValueError as exc:
        flash(str(exc), 'error')
    return redirect(url_for('schedules'))

@app.route('/schedules/edit/<int:id>', methods=['POST'])
@login_required
def edit_schedule(id):
    uid = session['user_id']
    s = Schedule.query.filter_by(id=id, user_id=uid).first_or_404()
    try:
        freq = clean_text(request.form.get('frequency'), 20, required=True)
        if freq not in SCHEDULE_FREQUENCIES:
            raise ValueError('Invalid frequency selected.')
        s.name = clean_text(request.form.get('name'), 100, required=True)
        s.amount = parse_money(request.form.get('amount'), 'Schedule amount')
        s.frequency = freq
        s.due_day = parse_int_range(request.form.get('due_day',1), 'Due day', 1, 31)
        s.remind_days_before = parse_int_range(request.form.get('remind_days_before',3), 'Reminder days', 1, 30)
        s.notes = clean_text(request.form.get('notes'), 1000)
        db.session.commit()
        flash('Schedule updated!', 'success')
    except ValueError as exc:
        flash(str(exc), 'error')
    return redirect(url_for('schedules'))

@app.route('/schedules/delete/<int:id>', methods=['POST'])
@login_required
def delete_schedule(id):
    uid = session['user_id']
    s = Schedule.query.filter_by(id=id, user_id=uid).first_or_404()
    s.is_active = False
    db.session.commit()
    flash('Schedule removed.', 'info')
    return redirect(url_for('schedules'))

@app.route('/notifications/read/<int:id>', methods=['POST'])
@login_required
def mark_notification_read(id):
    uid = session['user_id']
    n = Notification.query.filter_by(id=id, user_id=uid).first_or_404()
    n.is_read = True
    db.session.commit()
    return jsonify({'ok': True})

@app.route('/notifications/read-all', methods=['POST'])
@login_required
def mark_all_read():
    uid = session['user_id']
    Notification.query.filter_by(user_id=uid, is_read=False).update({'is_read': True})
    db.session.commit()
    return jsonify({'ok': True})

# ─── ROUTES: PROFILE & SETTINGS ───────────────────────────────────────────────

@app.route('/profile', methods=['GET','POST'])
@login_required
def profile():
    uid = session['user_id']
    user = User.query.get(uid)
    if not user:
        abort(404)
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'update_profile':
            try:
                user.name = clean_text(request.form.get('name', user.name), 100, required=True)
                user.mobile = validate_mobile(request.form.get('mobile', user.mobile or ''))
                primary_currency = (request.form.get('primary_currency') or user.primary_currency or 'INR').strip().upper()
                if primary_currency not in SUPPORTED_CURRENCIES:
                    raise ValueError('Unsupported currency selected. Please choose a supported currency.')
                user.primary_currency = primary_currency
                if 'avatar' in request.files:
                    filename = save_avatar_upload(request.files.get('avatar'), uid)
                    if filename:
                        user.avatar = filename
                db.session.commit()
                session['user_name'] = user.name
                flash('Profile updated!', 'success')
            except ValueError as exc:
                flash(str(exc), 'error')
        elif action == 'change_password':
            old_pw = request.form.get('old_password')
            new_pw = request.form.get('new_password')
            errors = {}
            if not user.check_password(old_pw):
                errors['old_password'] = 'Incorrect current password.'
            else:
                pw_err = validate_password(new_pw or '')
                if pw_err:
                    errors['new_password'] = pw_err
            if errors:
                return render_template('profile.html', user=user, errors=errors)
            user.set_password(new_pw)
            user.password_changed_at = utc_now()
            db.session.commit()
            flash('Password changed!', 'success')
        elif action == 'delete_account':
            confirm = request.form.get('confirm_delete')
            if confirm == user.email:
                user.is_active = False
                db.session.commit()
                session.clear()
                flash('Account permanently deleted.', 'info')
                return redirect(url_for('home'))
            flash('Email did not match. Account not deleted.', 'error')
        return redirect(url_for('profile'))
    return render_template('profile.html', user=user)

@app.route('/settings', methods=['GET','POST'])
@login_required
def settings():
    uid = session['user_id']
    user = User.query.get(uid)
    if not user:
        abort(404)
    if request.method == 'POST':
        if 'theme' in request.form:
            user.theme = request.form.get('theme', 'system')
            db.session.commit()
            flash('Settings saved!', 'success')
            return redirect(url_for('settings'))

        action = request.form.get('two_factor_action')
        if action == 'enable_2fa':
            password = request.form.get('current_password', '').strip()
            if not password:
                flash('Please enter your current password to continue.', 'error')
            elif not user.check_password(password):
                flash('Your current password is incorrect.', 'error')
            else:
                secret = generate_2fa_secret()
                session['pending_enable_2fa_user_id'] = user.id
                session['pending_enable_2fa_secret'] = secret
                flash('Enter the 6-digit code from your authenticator app to finish enabling 2FA.', 'info')
                return render_template(
                    'settings.html',
                    user=user,
                    two_factor_step='confirm_enable',
                    two_factor_secret=secret,
                    qr_image_data_url=generate_qr_code_data_url(secret, user.email, 'FinFlow')
                )
            return render_template('settings.html', user=user)

        if action == 'enable_2fa_confirm':
            pending_secret = session.get('pending_enable_2fa_secret')
            if not pending_secret:
                flash('Your 2FA confirmation expired. Please try again.', 'error')
                return redirect(url_for('settings'))
            code = request.form.get('totp_code', '').strip()
            if not verify_totp_code(pending_secret, code):
                flash('The authenticator code is invalid.', 'error')
                return render_template(
                    'settings.html',
                    user=user,
                    two_factor_step='confirm_enable',
                    two_factor_secret=pending_secret,
                    qr_image_data_url=generate_qr_code_data_url(pending_secret, user.email, 'FinFlow')
                )
            user.two_factor_enabled = True
            user.two_factor_secret = pending_secret
            db.session.commit()
            session.pop('pending_enable_2fa_user_id', None)
            session.pop('pending_enable_2fa_secret', None)
            flash('Two-factor authentication is now enabled.', 'success')
            return redirect(url_for('settings'))

        if action == 'disable_2fa':
            code = request.form.get('totp_code', '').strip()
            if not user.two_factor_enabled:
                flash('Two-factor authentication is already disabled.', 'info')
                return redirect(url_for('settings'))
            if not code:
                flash('Please enter your current authenticator code.', 'error')
                return render_template('settings.html', user=user)
            if not verify_totp_code(user.two_factor_secret or '', code):
                flash('The authenticator code is invalid.', 'error')
                return render_template('settings.html', user=user)
            session['pending_disable_2fa_user_id'] = user.id
            flash('Now enter your password to confirm disabling 2FA.', 'info')
            return render_template('settings.html', user=user, two_factor_step='confirm_disable')

        if action == 'disable_2fa_confirm':
            password = request.form.get('current_password', '').strip()
            if not password:
                flash('Please enter your current password.', 'error')
                return render_template('settings.html', user=user, two_factor_step='confirm_disable')
            if not user.check_password(password):
                flash('Your current password is incorrect.', 'error')
                return render_template('settings.html', user=user, two_factor_step='confirm_disable')
            user.two_factor_enabled = False
            user.two_factor_secret = None
            db.session.commit()
            session.pop('pending_disable_2fa_user_id', None)
            flash('Two-factor authentication has been disabled.', 'success')
            return redirect(url_for('settings'))

    return render_template('settings.html', user=user)

# ─── API ──────────────────────────────────────────────────────────────────────

@app.route('/api/categories')
@login_required
def api_categories():
    uid = session['user_id']
    cats = Category.query.filter(
        (Category.user_id==uid)|(Category.user_id==None)
    ).filter_by(is_active=True).all()
    return jsonify([{
        'id':c.id,'name':c.name,'subcategory':c.subcategory,'type':c.category_type
    } for c in cats])

@app.route('/api/notif-count')
@login_required
def api_notif_count():
    uid = session['user_id']
    count = Notification.query.filter_by(user_id=uid, is_read=False).count()
    return jsonify({'count': count})

# ─── INIT ─────────────────────────────────────────────────────────────────────

# --- ADMIN PANEL ---

ADMIN_PASSWORD = 'admin123'  # CHANGE THIS!

@app.route('/admin', methods=['GET', 'POST'])
def admin_panel():
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password != ADMIN_PASSWORD:
            return render_template('admin.html', login_error='Invalid password'), 401
        session['admin_logged_in'] = True
        return redirect(url_for('admin_panel'))
    
    if not session.get('admin_logged_in'):
        return render_template('admin.html', login_error=None)
    
    users = User.query.all()
    accounts = Account.query.all()
    transactions = Transaction.query.all()
    schedules = Schedule.query.all()
    
    stats = {'total_users': len(users), 'total_accounts': len(accounts), 'total_transactions': len(transactions), 'total_schedules': len(schedules)}
    
    return render_template('admin.html', users=users, accounts=accounts, transactions=transactions, schedules=schedules, stats=stats, logged_in=True)

@app.route('/admin/logout', methods=['POST'])
def admin_logout():
    session.pop('admin_logged_in', None)
    flash('Logged out from admin panel', 'info')
    return redirect(url_for('admin_panel'))


def init_app():
    with app.app_context():
        db.create_all()
        ensure_user_columns()
        ensure_account_columns()
        ensure_transaction_columns()
        ensure_denomination_table()
        seed_categories()


init_app()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=not IS_PRODUCTION, host='0.0.0.0', port=port)
